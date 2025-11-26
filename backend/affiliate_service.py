"""
Amazon.ca affiliate ingestion and pricing utilities.
"""
import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from database import AFFILIATE_PRODUCTS, PRODUCTS, db

logger = logging.getLogger(__name__)

AMAZON_TCG_QUERIES: List[Tuple[str, str]] = [
    ("Pokemon TCG sealed booster box", "Pokemon"),
    ("Magic The Gathering sealed booster", "Magic: The Gathering"),
    ("Yu-Gi-Oh sealed booster box", "Yu-Gi-Oh"),
    ("One Piece TCG sealed", "One Piece"),
    ("Disney Lorcana sealed booster", "Lorcana"),
    ("Flesh and Blood sealed booster", "Flesh and Blood"),
    ("Digimon sealed booster box", "Digimon"),
    ("Weiss Schwarz sealed booster", "Weiss Schwarz"),
    ("Dragon Ball Super sealed booster", "Dragon Ball Super"),
    ("Final Fantasy TCG sealed booster", "Final Fantasy TCG"),
    ("Cardfight Vanguard sealed booster", "Cardfight Vanguard"),
]


class AffiliateService:
    """Handle Amazon.ca affiliate integrations."""

    def __init__(self):
        self.amazon_tag = (
            os.getenv("AMAZON_CA_AFFILIATE_TAG")
            or os.getenv("AMAZON_ASSOCIATE_TAG")
            or "geocheapest-20"
        )
        self.amazon_api_key = os.getenv("RAPIDAPI_KEY")
        self.amazon_host = os.getenv(
            "RAPIDAPI_AMAZON_HOST", "amazon-data-scraper126.p.rapidapi.com"
        )
        self.amazon_min_rating = float(os.getenv("AMAZON_MIN_RATING", "4.0"))
        self.amazon_min_reviews = int(os.getenv("AMAZON_MIN_REVIEWS", "50"))
        self.amazon_sync_interval = int(os.getenv("AMAZON_SYNC_INTERVAL_SECONDS", "86400"))
        self.amazon_sync_interval = int(os.getenv("AMAZON_SYNC_INTERVAL_SECONDS", "86400"))
        self.amazon_sync_enabled = bool(self.amazon_api_key)
        
        # Vetted Vendors (Can be moved to DB/Env later)
        self.vetted_vendors = [
            "Amazon.ca",
            "Amazon",
            "401 Games",
            "Hobbiesville",
            "Dolly's Toys and Games",
            "Game Shack",
            "Red Nails II"
        ]

    # ------------------------------------------------------------------
    # Amazon helpers
    # ------------------------------------------------------------------
    async def search_amazon_product(self, search_query: str) -> List[Dict[str, Any]]:
        """Search Amazon.ca for products using RapidAPI."""
        if not self.amazon_api_key:
            return []

        url = f"https://{self.amazon_host}/search"
        headers = {
            "X-RapidAPI-Key": self.amazon_api_key,
            "X-RapidAPI-Host": self.amazon_host,
        }
        params = {"query": search_query, "country": "CA"}

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", data.get("items", []))
                logger.warning("Amazon search failed (%s): %s", response.status_code, response.text[:200])
        except Exception as exc:
            logger.error("Amazon search error: %s", exc)
        return []

    async def get_amazon_product_details(self, asin: str) -> Optional[Dict[str, Any]]:
        if not self.amazon_api_key:
            return None
        url = f"https://{self.amazon_host}/product/{asin}"
        headers = {
            "X-RapidAPI-Key": self.amazon_api_key,
            "X-RapidAPI-Host": self.amazon_host,
        }
        params = {"country": "CA"}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return response.json()
        except Exception as exc:
            logger.error("Amazon details error: %s", exc)
        return None

    def build_amazon_affiliate_url(self, asin: str) -> str:
        return f"https://www.amazon.ca/dp/{asin}?tag={self.amazon_tag}"

    async def sync_amazon_tcg_products(self) -> int:
        """Pull sealed TCG inventory for every supported game."""
        if not self.amazon_sync_enabled:
            return 0

        total = 0
        for query, game in AMAZON_TCG_QUERIES:
            results = await self.search_amazon_product(query)
            for result in results:
                normalized = self._normalize_amazon_result(result, game)
                if not normalized:
                    continue
                product_id = self._upsert_product(normalized)
                self._upsert_amazon_listing(product_id, normalized)
                total += 1
        logger.info("Amazon sync completed with %s listings", total)
        return total

    def _normalize_amazon_result(
        self, result: Dict[str, Any], game: str
    ) -> Optional[Dict[str, Any]]:
        asin = result.get("asin") or result.get("asin_id") or result.get("product_id")
        if not asin:
            return None

        rating = float(result.get("rating") or result.get("stars") or 0)
        review_count = int(result.get("reviews_count") or result.get("reviews") or 0)
        if rating < self.amazon_min_rating or review_count < self.amazon_min_reviews:
            return None

        price_raw = (
            result.get("price")
            or result.get("price_current")
            or result.get("price_string")
            or ""
        )
        price = self._parse_price(price_raw)
        if price <= 0:
            return None

        availability = result.get("availability", True)
        in_stock = (
            result.get("in_stock", True)
            if isinstance(result.get("in_stock"), bool)
            else "out of stock" not in str(availability).lower()
        )
        if not in_stock:
            return None

        title = result.get("title") or result.get("name")
        if not title:
            return None

        image = (
            result.get("image")
            or result.get("thumbnail")
            or (result.get("images") or [None])[0]
        )
        description = result.get("description") or result.get("snippet") or ""
        product_type = self._classify_product_type(title)
        release_status = self._classify_release_status(title, availability)
        seller = result.get("merchant") or result.get("seller_name") or "Amazon Marketplace"
        
        # Vetted Vendor Check
        if not any(v.lower() in seller.lower() for v in self.vetted_vendors):
            # Optional: Log skipped vendor for review
            # logger.debug(f"Skipping non-vetted vendor: {seller}")
            return None

        return {
            "asin": asin,
            "title": title,
            "description": description,
            "price": price,
            "image": image,
            "url": result.get("url") or f"https://www.amazon.ca/dp/{asin}",
            "rating": rating,
            "review_count": review_count,
            "prime": bool(result.get("is_prime") or result.get("amazonPrime")),
            "game": game,
            "product_type": product_type,
            "release_status": release_status,
            "seller": seller,
            "quantity": int(result.get("stock_count") or 50),
            "in_stock": in_stock,
        }

    def _parse_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        cleaned = re.sub(r"[^0-9\.]", "", str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _classify_product_type(self, title: str) -> str:
        lowered = title.lower()
        if "booster" in lowered:
            return "booster_box"
        if "elite trainer" in lowered or "etb" in lowered:
            return "elite_trainer_box"
        if "starter" in lowered or "structure deck" in lowered:
            return "starter_deck"
        if "bundle" in lowered or "gift" in lowered:
            return "bundle"
        if "collector" in lowered:
            return "collector_box"
        if "case" in lowered:
            return "case"
        return "sealed_product"

    def _classify_release_status(self, title: str, availability: Any) -> str:
        title_lower = title.lower()
        if "pre-order" in title_lower or "preorder" in title_lower:
            return "preorder"
        if "new release" in title_lower:
            return "new_release"
        if isinstance(availability, str) and "best seller" in availability.lower():
            return "best_seller"
        return "available"

    def _detect_game_from_title(self, title: Optional[str], fallback: str = "Other") -> str:
        if not title:
            return fallback
        lowered = title.lower()
        keyword_map = [
            (["pokemon"], "Pokemon"),
            (["magic: the gathering", "magic the gathering", "mtg"], "Magic: The Gathering"),
            (["yu-gi-oh", "yugioh", "yu gi oh", "ygo"], "Yu-Gi-Oh"),
            (["one piece"], "One Piece"),
            (["lorcana"], "Lorcana"),
            (["flesh and blood", "fab"], "Flesh and Blood"),
            (["digimon"], "Digimon"),
            (["weiss schwarz"], "Weiss Schwarz"),
            (["dragon ball"], "Dragon Ball"),
            (["final fantasy"], "Final Fantasy TCG"),
            (["cardfight", "vanguard"], "Cardfight Vanguard"),
            (["metazoo"], "MetaZoo"),
            (["grand archive"], "Grand Archive"),
        ]
        for keywords, game in keyword_map:
            if any(keyword in lowered for keyword in keywords):
                return game
        return fallback

    async def _upsert_product(self, normalized: Dict[str, Any]) -> str:
        async def find_by(field: str, value: str):
            if not value:
                return None
            query = (
                db.collection(PRODUCTS)
                .where(field, "==", value)
                .limit(1)
            )
            async for doc in query.stream():
                return doc
            return None

        product_doc = None
        product_doc = product_doc or await find_by("asin", normalized.get("asin"))
        product_doc = product_doc or await find_by("upc", normalized.get("upc"))
        product_doc = product_doc or await find_by("name", normalized["title"])

        data = {
            "name": normalized["title"],
            "description": normalized["description"],
            "category": normalized["game"],
            "segment": "sealed",
            "image_url": normalized["image"],
            "asin": normalized.get("asin"),
            "upc": normalized.get("upc"),
            "updated_at": datetime.utcnow(),
        }

        if product_doc:
            await product_doc.reference.update(data)
            return product_doc.id

        ref = db.collection(PRODUCTS).document()
        data["created_at"] = datetime.utcnow()
        data["total_sales"] = 0
        await ref.set(data)
        return ref.id

    async def _upsert_amazon_listing(self, product_id: str, normalized: Dict[str, Any]):
        doc_id = f"amazon_{normalized['asin']}"
        affiliate_url = self.build_amazon_affiliate_url(normalized["asin"])
        data = {
            "product_id": product_id,
            "affiliate_name": "Amazon.ca",
            "affiliate_url": affiliate_url,
            "asin": normalized["asin"],
            "price": normalized["price"],
            "in_stock": normalized["in_stock"],
            "quantity": normalized["quantity"],
            "estimated_shipping": 0.0,
            "commission_rate": 0.05,
            "source": "amazon",
            "game": normalized["game"],
            "product_type": normalized["product_type"],
            "release_status": normalized["release_status"],
            "vendor_rating": normalized["rating"],
            "review_count": normalized["review_count"],
            "is_prime": normalized["prime"],
            "images": [normalized["image"]] if normalized["image"] else [],
            "description": normalized["description"],
            "status": "active",
            "updated_at": datetime.utcnow(),
        }
        listing_ref = db.collection(AFFILIATE_PRODUCTS).document(doc_id)
        existing = await listing_ref.get()
        if existing.exists:
            data["created_at"] = existing.to_dict().get("created_at")
        else:
            data["created_at"] = datetime.utcnow()
        await listing_ref.set(data)

    # ------------------------------------------------------------------
    # Price refresh
    # ------------------------------------------------------------------
    async def update_affiliate_prices(self):
        """Lightweight price refresh for Amazon listings."""
        amazon_docs = db.collection(AFFILIATE_PRODUCTS).where(
            "affiliate_name", "==", "Amazon.ca"
        ).stream()
        for doc in amazon_docs:
            listing = doc.to_dict()
            asin = listing.get("asin")
            if not asin:
                continue
            details = await self.get_amazon_product_details(asin)
            if details:
                price = self._parse_price(details.get("price") or "")
                stock = details.get("in_stock", True)
                doc.reference.update(
                    {
                        "price": price or listing.get("price", 0),
                        "in_stock": bool(stock),
                        "updated_at": datetime.utcnow(),
                    }
                )

    # ------------------------------------------------------------------
    # Unified Add from URL
    # ------------------------------------------------------------------
    async def add_product_from_url(self, url: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scrape product details from a URL (Amazon or eBay) and add to DB.
        Returns the added product data.
        """
        # Handle short URLs
        if "amzn.to" in url or "bit.ly" in url:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=15.0) as client:
                    response = await client.get(url)
                    # Sometimes the final URL is in the history or just the response URL
                    url = str(response.url)
                    logger.info(f"Expanded short URL to: {url}")
            except Exception as e:
                logger.error(f"Failed to expand short URL: {e}")
                raise ValueError(f"Could not expand short URL: {e}")

        domain = url.lower()
        if "amazon.ca" in domain or "amazon.com" in domain:
            return await self._add_amazon_from_url(url, overrides)
        elif "ebay.ca" in domain or "ebay.com" in domain:
            return await self._add_ebay_from_url(url, overrides)
        else:
            raise ValueError("Unsupported URL. Only Amazon and eBay are supported.")

    async def _add_amazon_from_url(self, url: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Extract ASIN
        asin_match = re.search(r"/dp/([A-Z0-9]{10})", url)
        if not asin_match:
            asin_match = re.search(r"/gp/product/([A-Z0-9]{10})", url)
        
        if not asin_match:
            raise ValueError("Could not extract ASIN from Amazon URL")
        
        asin = asin_match.group(1)
        
        # Try to get details from API
        details = await self.get_amazon_product_details(asin)

        scraped = None
        if not details or not details.get("price"):
            scraped = await self._scrape_amazon_page(url)

        base_details: Dict[str, Any] = details or {}
        if scraped:
            base_details.update(scraped)

        if overrides:
            base_details = self._apply_overrides(base_details, overrides)

        if not base_details:
            raise ValueError("Unable to fetch Amazon product details. Please provide metadata manually.")

        title = base_details.get("title")
        if not title and details:
            title = details.get("title") or details.get("product_title")
        if not title:
            title = f"Amazon Product {asin}"
        price_str = base_details.get("price") or base_details.get("current_price") or "0"
        price = self._parse_price(str(price_str))
        image = (
            base_details.get("main_image")
            or base_details.get("image")
            or base_details.get("product_photo")
            or "https://placehold.co/400?text=Amazon+Product"
        )
        
        base_game = None
        if overrides:
            base_game = overrides.get("game") or overrides.get("category")
        base_game = base_game or base_details.get("game") or base_details.get("category")
        if isinstance(base_game, str) and base_game.strip().upper() in {"TBD", "UNKNOWN", "OTHER"}:
            base_game = None
        detected_game = self._detect_game_from_title(title)
        normalized = {
            "asin": asin,
            "title": title,
            "description": base_details.get("description", ""),
            "price": price,
            "image": image,
            "url": self.build_amazon_affiliate_url(asin),
            "rating": float(base_details.get("rating", 0) or base_details.get("stars", 0) or 0),
            "review_count": int(base_details.get("reviews", 0) or base_details.get("reviews_count", 0) or 0),
            "prime": False, 
            "game": base_game or detected_game,
            "product_type": "sealed_product",
            "release_status": "available",
            "seller": base_details.get("seller") or "Amazon",
            "quantity": int(base_details.get("quantity") or 10),
            "in_stock": bool(base_details.get("in_stock", True))
        }

        if normalized["price"] <= 0:
            raise ValueError("Unable to determine product price. Provide a price override.")
        
        # Upsert
        product_id = await self._upsert_product(normalized)
        await self._upsert_amazon_listing(product_id, normalized)
        
        return {**normalized, "id": product_id}

    async def _add_ebay_from_url(self, url: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item_id_match = re.search(r"/itm/(\d+)", url)
        item_id = item_id_match.group(1) if item_id_match else "unknown"
        
        scraped = await self._scrape_ebay_page(url)
        details = scraped or {}

        if overrides:
            details = self._apply_overrides(details, overrides)

        title = details.get("title") or f"eBay Product {item_id}"
        price = self._parse_price(details.get("price"))
        if price <= 0:
            raise ValueError("Unable to determine eBay price. Provide a price override.")

        existing_game = details.get("game")
        if isinstance(existing_game, str) and existing_game.strip().upper() in {"TBD", "UNKNOWN", "OTHER"}:
            existing_game = None
        detected_game = existing_game or self._detect_game_from_title(title)
        normalized = {
            "asin": f"ebay_{item_id}",
            "title": title,
            "description": details.get("description", "Imported from eBay"),
            "price": price,
            "image": details.get("image") or "https://placehold.co/400?text=eBay+Product",
            "url": url,
            "rating": float(details.get("rating", 0) or 0),
            "review_count": int(details.get("review_count", 0) or 0),
            "prime": False,
            "game": detected_game,
            "product_type": "sealed_product",
            "release_status": "available",
            "seller": details.get("seller", "eBay Seller"),
            "quantity": int(details.get("quantity") or 1),
            "in_stock": bool(details.get("in_stock", True))
        }
        
        product_id = await self._upsert_product(normalized)
        
        # Custom upsert for eBay to ensure correct source
        doc_id = f"ebay_{item_id}"
        data = {
            "product_id": product_id,
            "affiliate_name": "eBay",
            "affiliate_url": url, 
            "asin": item_id,
            "price": normalized["price"],
            "in_stock": True,
            "quantity": 1,
            "source": "ebay",
            "game": detected_game,
            "images": [normalized["image"]],
            "status": "active",
            "updated_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        await db.collection(AFFILIATE_PRODUCTS).document(doc_id).set(data)
        
        return {**normalized, "id": product_id}

    def _apply_overrides(self, data: Dict[str, Any], overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not overrides:
            return data
        merged = {**data}
        for key, value in overrides.items():
            if value in (None, ""):
                continue
            if key == "price":
                merged["price"] = self._parse_price(value)
            elif key == "rating":
                merged["rating"] = float(value)
            elif key in ("review_count", "reviews"):
                merged["review_count"] = int(value)
            else:
                merged[key] = value
        return merged

    async def _scrape_amazon_page(self, url: str) -> Optional[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Amazon scrape failed %s: %s", resp.status_code, url)
                return None
        except Exception as exc:
            logger.error("Amazon scrape error: %s", exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.select_one("#productTitle")
        price_selectors = [
            "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
            "#corePriceDisplay_mobile_feature_div span.a-price span.a-offscreen",
            "#corePriceDisplay_desktop_feature_div span.a-offscreen",
            "#corePriceDisplay_mobile_feature_div span.a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#priceblock_saleprice",
            "span[data-a-color='base'] span.a-offscreen",
            "span.a-price span.a-offscreen",
        ]
        price_text = None
        price_value = 0.0
        for selector in price_selectors:
            candidate = soup.select_one(selector)
            if candidate and candidate.get_text(strip=True):
                candidate_text = candidate.get_text(strip=True)
                candidate_value = self._parse_price(candidate_text)
                if candidate_value > 0:
                    price_text = candidate_text
                    price_value = candidate_value
                    break
        # Collect all price candidates so we can fall back to the cheapest if needed
        all_prices = []
        for span in soup.select("span.a-offscreen"):
            text = span.get_text(strip=True)
            if text:
                value = self._parse_price(text)
                if value > 0:
                    all_prices.append((value, text))
        if all_prices:
            all_prices.sort(key=lambda item: item[0])
            cheapest_value, cheapest_text = all_prices[0]
            if not price_text or cheapest_value + 0.01 < price_value or price_value == 0.0:
                price_text = cheapest_text
                price_value = cheapest_value
        image_el = soup.select_one("#landingImage")
        desc_items = soup.select("#feature-bullets ul li")
        rating_el = soup.select_one("span#acrPopover")
        reviews_el = soup.select_one("#acrCustomerReviewText")

        description = ""
        if desc_items:
            description = "\n".join(
                li.get_text(strip=True) for li in desc_items if li.get_text(strip=True)
            )

        rating = 0.0
        if rating_el and rating_el.get("title"):
            try:
                rating = float(rating_el["title"].split(" ")[0])
            except ValueError:
                rating = 0.0

        review_count = 0
        if reviews_el:
            review_text = reviews_el.get_text(strip=True).replace(",", "")
            digits = re.findall(r"\d+", review_text)
            if digits:
                review_count = int(digits[0])

        image_url = None
        if image_el:
            image_url = image_el.get("data-old-hires") or image_el.get("src")

        return {
            "title": title.get_text(strip=True) if title else None,
            "price": price_text,
            "image": image_url,
            "description": description,
            "rating": rating,
            "reviews": review_count,
            "in_stock": True
        }

    async def _scrape_ebay_page(self, url: str) -> Optional[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
        except Exception as exc:
            logger.error("eBay scrape error: %s", exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        title_el = soup.select_one("#itemTitle")
        price_el = soup.select_one("#prcIsum") or soup.select_one("span[itemprop='price']")
        image_el = soup.select_one("#icImg")
        desc_el = soup.select_one("#viTabs_0_is")

        return {
            "title": title_el.get_text(strip=True).replace("Details about  ", "") if title_el else None,
            "price": price_el.get_text(strip=True) if price_el else None,
            "image": image_el.get("src") if image_el else None,
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "seller": None,
            "rating": 0,
            "review_count": 0,
            "in_stock": True
        }

async def amazon_sync_loop(service: AffiliateService):
    """Background cron loop to keep Amazon listings fresh."""
    if not service.amazon_sync_enabled:
        return
    delay = max(3600, service.amazon_sync_interval)
    while True:
        try:
            await service.sync_amazon_tcg_products()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Amazon sync loop error: %s", exc)
        await asyncio.sleep(delay)


