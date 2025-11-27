"""
Amazon.ca affiliate ingestion and pricing utilities.
"""
import asyncio
import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from database import AFFILIATE_PRODUCTS, PRODUCTS, db

logger = logging.getLogger(__name__)

AMAZON_TCG_QUERIES: List[Tuple[str, str]] = [
    # Pokemon
    ("Pokemon TCG Booster Box", "Pokemon"),
    ("Pokemon TCG Elite Trainer Box", "Pokemon"),
    ("Pokemon TCG Ultra Premium Collection", "Pokemon"),
    ("Pokemon TCG Booster Bundle", "Pokemon"),
    ("Pokemon TCG Tin", "Pokemon"),
    
    # Magic: The Gathering
    ("Magic The Gathering Play Booster Box", "Magic: The Gathering"),
    ("Magic The Gathering Collector Booster Box", "Magic: The Gathering"),
    ("Magic The Gathering Commander Deck", "Magic: The Gathering"),
    ("Magic The Gathering Bundle", "Magic: The Gathering"),
    
    # Yu-Gi-Oh
    ("Yu-Gi-Oh Booster Box", "Yu-Gi-Oh"),
    ("Yu-Gi-Oh Structure Deck", "Yu-Gi-Oh"),
    ("Yu-Gi-Oh Tin", "Yu-Gi-Oh"),
    ("Yu-Gi-Oh 25th Anniversary", "Yu-Gi-Oh"),
    
    # One Piece
    ("One Piece TCG Booster Box", "One Piece"),
    ("One Piece TCG Starter Deck", "One Piece"),
    ("One Piece TCG Double Pack", "One Piece"),
    
    # Lorcana
    ("Disney Lorcana Booster Box", "Lorcana"),
    ("Disney Lorcana Trove", "Lorcana"),
    ("Disney Lorcana Starter Deck", "Lorcana"),
    ("Disney Lorcana Gift Set", "Lorcana"),
    
    # Star Wars Unlimited
    ("Star Wars Unlimited Booster Box", "Star Wars Unlimited"),
    ("Star Wars Unlimited Two Player Starter", "Star Wars Unlimited"),
    
    # Union Arena
    ("Union Arena Booster Box", "Union Arena"),
    ("Union Arena Starter Deck", "Union Arena"),
    
    # Dragon Ball
    ("Dragon Ball Super Card Game Booster Box", "Dragon Ball Super"),
    ("Dragon Ball Fusion World Booster Box", "Dragon Ball Super"),
    
    # Digimon
    ("Digimon TCG Booster Box", "Digimon"),
    ("Digimon TCG Starter Deck", "Digimon"),
    
    # Flesh and Blood
    ("Flesh and Blood TCG Booster Box", "Flesh and Blood"),
    ("Flesh and Blood TCG Blitz Deck", "Flesh and Blood"),
    
    # Weiss Schwarz
    ("Weiss Schwarz Booster Box", "Weiss Schwarz"),
    ("Weiss Schwarz Trial Deck", "Weiss Schwarz"),
    
    # Others
    ("Final Fantasy TCG Booster Box", "Final Fantasy TCG"),
    ("Cardfight Vanguard Booster Box", "Cardfight Vanguard"),
    ("Shadowverse Evolve Booster Box", "Shadowverse Evolve"),
    ("Battle Spirits Saga Booster Box", "Battle Spirits Saga"),
    ("Grand Archive TCG Booster Box", "Grand Archive"),
    ("Sorcery Contested Realm Booster Box", "Sorcery: Contested Realm"),
    ("MetaZoo Booster Box", "MetaZoo"),
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
            "RAPIDAPI_AMAZON_HOST", "real-time-amazon-data.p.rapidapi.com"
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
            logger.warning("Amazon API key not configured")
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
                    data = response.json()
                    logger.debug(f"Retrieved Amazon product details for ASIN {asin}")
                    return data
                else:
                    logger.warning(f"Amazon API returned status {response.status_code} for ASIN {asin}: {response.text[:200]}")
        except Exception as exc:
            logger.error(f"Amazon details error for ASIN {asin}: {exc}", exc_info=True)
        return None

    def build_amazon_affiliate_url(self, asin: str) -> str:
        return f"https://www.amazon.ca/dp/{asin}?tag={self.amazon_tag}"

    async def sync_amazon_tcg_products(self, max_products: int = 50) -> int:
        """Pull sealed TCG inventory for every supported game.
        
        Args:
            max_products: Maximum number of products to add (stops early to avoid long waits)
        """
        if not self.amazon_sync_enabled:
            logger.warning("Amazon sync is disabled (missing RAPIDAPI_KEY)")
            return 0

        total = 0
        skipped = 0
        max_queries = min(10, len(AMAZON_TCG_QUERIES))  # Process max 10 queries at a time
        logger.info(f"Starting Amazon sync (processing {max_queries} queries, max {max_products} products)...")
        
        for idx, (query, game) in enumerate(AMAZON_TCG_QUERIES[:max_queries], 1):
            if total >= max_products:
                logger.info(f"Reached max products limit ({max_products}), stopping early")
                break
                
            try:
                logger.info(f"Processing query {idx}/{max_queries}: {query} ({game})")
                results = await self.search_amazon_product(query)
                logger.info(f"Found {len(results)} results for {query}")
                
                # Limit results per query to avoid processing too many
                results_to_process = results[:10]  # Max 10 results per query
                
                for result in results_to_process:
                    if total >= max_products:
                        break
                        
                    normalized = self._normalize_amazon_result(result, game)
                    if not normalized:
                        skipped += 1
                        continue
                    
                    try:
                        product_id = await self._upsert_product(normalized)
                        await self._upsert_amazon_listing(product_id, normalized)
                        total += 1
                        if total % 5 == 0:
                            logger.info(f"Progress: {total} products added, {skipped} skipped")
                    except Exception as e:
                        logger.error(f"Error upserting product {normalized.get('asin', 'unknown')}: {e}")
                        skipped += 1
                
                # Rate limiting: delay between queries
                if idx < max_queries and total < max_products:
                    await asyncio.sleep(0.5)  # Reduced delay
                    
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}", exc_info=True)
                continue
        
        logger.info(f"Amazon sync completed: {total} products added, {skipped} skipped")
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
            and "currently unavailable" not in str(availability).lower()
        )
        
        # STRICT ENFORCEMENT: Do not import if out of stock
        if not in_stock:
            logger.info(f"Skipping out of stock item: {result.get('asin')} ({availability})")
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
        
        # Vetted Vendor Check REMOVED to allow all high-rated sellers
        # if not any(v.lower() in seller.lower() for v in self.vetted_vendors):
        #     return None

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
        normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
        lowered = normalized.lower()
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
        """
        Deep Refresh: Iterate ALL Amazon listings in DB and update price/stock.
        This ensures out-of-stock items (hidden from search) are correctly marked.
        """
        if not self.amazon_sync_enabled:
            return

        logger.info("Starting Deep Refresh for Amazon listings...")
        
        # Stream all Amazon affiliate products
        amazon_docs = db.collection(AFFILIATE_PRODUCTS).where(
            "affiliate_name", "==", "Amazon.ca"
        ).stream()
        
        count = 0
        updated = 0
        
        async for doc in amazon_docs:
            listing = doc.to_dict()
            asin = listing.get("asin")
            if not asin:
                continue
                
            count += 1
            # Rate limit protection (simple sleep)
            await asyncio.sleep(1.0) 
            
            try:
                details = await self.get_amazon_product_details(asin)
                if details:
                    # Parse new values
                    price_raw = (
                        details.get("price") 
                        or details.get("price_current") 
                        or details.get("price_string") 
                        or ""
                    )
                    price = self._parse_price(price_raw)
                    
                    # Check stock status
                    availability = details.get("availability", True)
                    in_stock = (
                        details.get("in_stock", True)
                        if isinstance(details.get("in_stock"), bool)
                        else "out of stock" not in str(availability).lower()
                        and "currently unavailable" not in str(availability).lower()
                    )
                    
                    # Update Firestore
                    await doc.reference.update({
                        "price": price,
                        "in_stock": in_stock,
                        "updated_at": datetime.utcnow(),
                        # Optional: Update other fields if changed
                        "vendor_rating": float(details.get("rating") or details.get("stars") or listing.get("vendor_rating", 0)),
                        "review_count": int(details.get("reviews_count") or details.get("reviews") or listing.get("review_count", 0))
                    })
                    updated += 1
                    logger.info(f"Deep Refresh: Updated {asin} | Price: {price} | Stock: {in_stock}")
                else:
                    logger.warning(f"Deep Refresh: Could not fetch details for {asin}")
            except Exception as e:
                logger.error(f"Deep Refresh Error for {asin}: {e}")
                
        logger.info(f"Deep Refresh Completed. Processed {count} listings, Updated {updated}.")

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

        # Extract all possible fields from RapidAPI response
        title = (
            base_details.get("title") 
            or base_details.get("product_title")
            or base_details.get("name")
            or (details and (details.get("title") or details.get("product_title") or details.get("name")))
        )
        if not title:
            title = f"Amazon Product {asin}"
        
        # Price extraction - try all possible fields
        price_str = (
            base_details.get("price")
            or base_details.get("current_price")
            or base_details.get("price_string")
            or base_details.get("price_current")
            or (details and (details.get("price") or details.get("current_price") or details.get("price_string")))
            or "0"
        )
        price = self._parse_price(str(price_str))
        
        # Image extraction - try all possible fields
        image = (
            base_details.get("main_image")
            or base_details.get("image")
            or base_details.get("product_photo")
            or base_details.get("thumbnail")
            or (base_details.get("images") and base_details["images"][0] if isinstance(base_details.get("images"), list) else None)
            or (details and (details.get("main_image") or details.get("image") or details.get("product_photo") or details.get("thumbnail")))
            or "https://placehold.co/400?text=Amazon+Product"
        )
        
        # Description extraction
        description = (
            base_details.get("description")
            or base_details.get("snippet")
            or base_details.get("product_description")
            or (details and (details.get("description") or details.get("snippet")))
            or ""
        )
        
        # Rating extraction
        rating = float(
            base_details.get("rating", 0)
            or base_details.get("stars", 0)
            or base_details.get("average_rating", 0)
            or (details and (details.get("rating") or details.get("stars") or details.get("average_rating")))
            or 0
        )
        
        # Review count extraction
        review_count = int(
            base_details.get("reviews", 0)
            or base_details.get("reviews_count", 0)
            or base_details.get("review_count", 0)
            or base_details.get("total_reviews", 0)
            or (details and (details.get("reviews") or details.get("reviews_count") or details.get("review_count")))
            or 0
        )
        
        # Prime status
        is_prime = bool(
            base_details.get("is_prime")
            or base_details.get("amazonPrime")
            or base_details.get("prime")
            or (details and (details.get("is_prime") or details.get("amazonPrime")))
        )
        
        # Stock status
        in_stock = bool(
            base_details.get("in_stock", True)
            if isinstance(base_details.get("in_stock"), bool)
            else (details and details.get("in_stock", True))
            if details and isinstance(details.get("in_stock"), bool)
            else "out of stock" not in str(base_details.get("availability", "")).lower()
            and "currently unavailable" not in str(base_details.get("availability", "")).lower()
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
            "description": description,
            "price": price,
            "image": image,
            "url": self.build_amazon_affiliate_url(asin),
            "rating": rating,
            "review_count": review_count,
            "prime": is_prime, 
            "game": base_game or detected_game,
            "product_type": "sealed_product",
            "release_status": "available",
            "seller": base_details.get("seller") or base_details.get("merchant") or details.get("seller") if details else "Amazon",
            "quantity": int(base_details.get("quantity") or base_details.get("stock_count") or details.get("quantity") if details else 10),
            "in_stock": in_stock
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
            "Accept-Language": "en-CA,en;q=0.9",
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
        for selector in price_selectors:
            candidate = soup.select_one(selector)
            if candidate and candidate.get_text(strip=True):
                candidate_text = candidate.get_text(strip=True)
                if self._parse_price(candidate_text) > 0:
                    price_text = candidate_text
                    break
        if not price_text:
            # Fallback to the first price Amazon renders on the page
            for span in soup.select("span.a-offscreen"):
                text = span.get_text(strip=True)
                if text and self._parse_price(text) > 0:
                    price_text = text
                    break
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
            await service.update_affiliate_prices()  # Run Deep Refresh after search sync
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Amazon sync loop error: %s", exc)
        await asyncio.sleep(delay)


