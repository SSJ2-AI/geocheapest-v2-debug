import asyncio
from unittest.mock import AsyncMock

import pytest

from app.main import affiliate_service, shippo_service


@pytest.mark.asyncio
async def test_admin_add_from_url_creates_affiliate_listing(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    async def fake_details(asin: str):
        return {
            "title": f"Test Product {asin}",
            "price": "$129.99",
            "image": "https://example.com/image.jpg",
            "description": "Test description",
            "rating": 4.5,
            "reviews": 120,
            "in_stock": True
        }

    monkeypatch.setattr(
        affiliate_service,
        "get_amazon_product_details",
        AsyncMock(side_effect=fake_details)
    )

    response = await client.post(
        "/api/admin/products/add_from_url",
        json={
            "url": "https://www.amazon.ca/dp/TEST123456",
            "admin_key": "secret"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["product"]["title"].startswith("Test Product")

    products_resp = await client.get("/api/products")
    assert products_resp.status_code == 200
    payload = products_resp.json()
    assert payload["total"] == 1
    product = payload["products"][0]
    assert product["source"] == "affiliate"
    assert product["best_price"] == 129.99
    assert product["url"].startswith("https://www.amazon.ca/dp/TEST123456")


@pytest.mark.asyncio
async def test_cart_optimize_allows_guest_checkout(client, mock_firestore, monkeypatch):
    product_id = "prod-1"
    product_ref = mock_firestore.collection("products").document(product_id)
    await product_ref.set({
        "name": "Sample Booster Box",
        "description": "Sample",
        "category": "Pokemon",
        "segment": "sealed",
        "image_url": "",
        "created_at": None,
        "updated_at": None,
        "total_sales": 0
    })

    shopify_doc = mock_firestore.collection("shopifyListings").document("store-a_variant")
    await shopify_doc.set({
        "product_id": product_id,
        "store_id": "store-a",
        "store_name": "Store A",
        "shopify_product_id": "shopify_prod",
        "shopify_variant_id": "variant",
        "price": 110.0,
        "quantity": 10,
        "status": "active",
        "is_preorder": False,
        "images": []
    })

    affiliate_doc = mock_firestore.collection("affiliateProducts").document("amazon_test")
    await affiliate_doc.set({
        "product_id": product_id,
        "affiliate_name": "Amazon.ca",
        "affiliate_url": "https://amazon.ca/test",
        "price": 105.0,
        "in_stock": True,
        "quantity": 50,
        "estimated_shipping": 8.0,
        "status": "active",
        "asin": "TESTASIN"
    })

    monkeypatch.setattr(
        shippo_service,
        "calculate_shipping",
        AsyncMock(return_value=12.0)
    )

    response = await client.post(
        "/api/cart/optimize",
        json={
            "items": [{"product_id": product_id, "quantity": 1}],
            "shipping_address": {
                "name": "Guest",
                "street": "1 Main St",
                "city": "Toronto",
                "province": "ON",
                "postal_code": "A1A1A1",
                "country": "CA"
            }
        }
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["total_price"] > 0
    assert payload["strategy"] in ["split", f"bundle:store-a"]
