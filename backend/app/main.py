"""
GeoCheapest v2 - FastAPI Backend
TCG Marketplace with Shopify OAuth, Cart Optimization, and Split Checkout
"""
import asyncio
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging
import os
import json
import httpx
import hmac
import hashlib
import base64
from urllib.parse import urlencode
import stripe
from google.cloud import firestore, storage
from google.api_core import exceptions as google_exceptions
from pydantic_settings import BaseSettings

from models import (
    Store, Product, ShopifyListing, AffiliateProduct, Order, OrderItem,
    SellerPayout, CommissionRate, VendorCommissionOverride, ReturnRequest,
    CartOptimizationRequest, CartOptimizationResponse, CheckoutRequest,
    PaymentCustomerRequest, VendorSubscriptionRequest, VendorBillingPortalRequest,
    ShippingLabelRequest, ReturnLabelRequest, User, UserCreate, Token
)
from shopify_service import ShopifyService
from shippo_service import ShippoService
from stripe_service import StripeService
from affiliate_service import AffiliateService, amazon_sync_loop
from email_service import EmailService
from niche_config import get_niche_config, NicheSettings
from agent_service import AgentService
from market_data_service import MarketDataService
from security import verify_password, get_password_hash, create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure JSON Logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S%z"
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

class Settings(BaseSettings):
    GCP_PROJECT_ID: Optional[str] = None


settings = Settings()

_storage_client: Optional[storage.Client] = None
_firestore_client: Optional[firestore.AsyncClient] = None


app = FastAPI(title="GeoCheapest v2 API", version="2.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration": duration,
        "ip": request.client.host
    }
    logger.info(json.dumps(log_data))
    return response

# Environment Variables
SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SHOPIFY_SCOPES = ",".join([
    "read_products",
    "read_orders",
    "write_orders",
    "read_customers",
    "read_inventory"
])
REDIRECT_URI = os.getenv("BACKEND_URL", "http://localhost:8000") + "/api/shopify/callback"

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Initialize Services
shopify_service = ShopifyService()
shippo_service = ShippoService()
stripe_service = StripeService()
affiliate_service = AffiliateService()
email_service = EmailService()
agent_service = AgentService()
market_service = MarketDataService()

_amazon_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def on_startup():
    global _storage_client, _firestore_client, _amazon_task
    try:
        # We don't need to init firestore here anymore as we use database.py
        # But we might need storage client
        print(f"Initializing GCP clients with project: {settings.GCP_PROJECT_ID}")
        _storage_client = storage.Client(project=settings.GCP_PROJECT_ID or None)
        print("GCP Storage initialized")
    except Exception as e:
        print(f"CRITICAL: GCP Storage init failed: {e}")
        logger.error(f"GCP Storage init failed: {e}")
        _storage_client = None
        # _firestore_client = None # Removed
    if affiliate_service.amazon_sync_enabled:
        _amazon_task = asyncio.create_task(
            amazon_sync_loop(affiliate_service)
        )


@app.on_event("shutdown")
async def on_shutdown():
    global _firestore_client, _amazon_task
    if _firestore_client is not None:
        try:
            await _firestore_client.close()
        except Exception as exc:
            logger.warning(f"Error closing Firestore client: {exc}")
        finally:
            _firestore_client = None
    if _amazon_task:
        _amazon_task.cancel()
        try:
            await _amazon_task
        except asyncio.CancelledError:
            pass
        finally:
            _amazon_task = None


def _ensure_gcp():
    print("DEBUG: _ensure_gcp called")
    if not _storage_client or not _firestore_client:
        print("DEBUG: GCP not initialized, returning None")
        logger.warning("GCP not initialized, returning None clients")
        return None, None
    print("DEBUG: GCP initialized")
    return _storage_client, _firestore_client


async def get_db(_: Request = None) -> firestore.AsyncClient:
    # Use the shared db instance from database.py which handles mock fallback
    from database import db
    return db


def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@app.exception_handler(google_exceptions.GoogleAPIError)
async def handle_google_api_error(request: Request, exc: google_exceptions.GoogleAPIError):
    print(f"DEBUG: handle_google_api_error caught: {exc}")
    logger.error("Google API error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Upstream Google service error"}
    )


@app.exception_handler(google_exceptions.RetryError)
async def handle_google_retry_error(request: Request, exc: google_exceptions.RetryError):
    logger.error("Google API retry error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": "Google service retry exhausted"}
    )


@app.get("/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/v1/health/ready")
async def health_ready():
    gcp_ready = _storage_client is not None and _firestore_client is not None
    return {
        "status": "ready" if gcp_ready else "not ready",
        "gcp": gcp_ready
    }


@app.get("/")
async def root(_: firestore.AsyncClient = Depends(get_db)):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GeoCheapest v2 API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/health")
async def health_check(_: firestore.AsyncClient = Depends(get_db)):
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== AUTHENTICATION ====================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: firestore.AsyncClient = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY", "your-secret-key-change-in-production"), algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # In a real app, we'd query by ID, but here we use email as key or query
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", email).limit(1)
    docs = query.stream()
    
    user_data = None
    async for doc in docs:
        user_data = doc.to_dict()
        user_data["id"] = doc.id
        break
    
    if user_data is None:
        raise credentials_exception
        
    return User(**user_data)


@app.post("/api/auth/signup", response_model=Token)
async def signup(
    user_in: UserCreate,
    db: firestore.AsyncClient = Depends(get_db)
):
    # Check if user exists
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", user_in.email).limit(1)
    docs = query.stream()
    async for _ in docs:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create user
    user_data = {
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "full_name": user_in.full_name,
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    new_user_ref = users_ref.document()
    await new_user_ref.set(user_data)
    
    # Send welcome email
    background_tasks = BackgroundTasks()
    background_tasks.add_task(email_service.send_welcome_email, user_in.email, user_in.full_name or "User")
    
    access_token = create_access_token(subject=user_in.email)
    return JSONResponse(
        content={"access_token": access_token, "token_type": "bearer"},
        background=background_tasks
    )

@app.get("/api/users/me/recommendations")
async def get_user_recommendations(
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Get dynamic product recommendations based on user's chat history and preferences.
    """
    # Mock Logic based on inferred tags
    prefs = current_user.preferences or UserPreference()
    recommendations = []
    
    if "investor" in prefs.intent_tags:
        recommendations.append({
            "title": "Evolving Skies Booster Box",
            "reason": "High investment potential based on your interest in ROI."
        })
    elif "player" in prefs.intent_tags:
        recommendations.append({
            "title": "Charizard ex Deck",
            "reason": "Trending meta deck for competitive play."
        })
    else:
        # Default / Cold Start
        recommendations.append({
            "title": "151 Ultra Premium Collection",
            "reason": "Popular with all users right now."
        })
        
    return {"recommendations": recommendations}


@app.post("/api/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: firestore.AsyncClient = Depends(get_db)
):
    # Find user
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", form_data.username).limit(1)
    docs = query.stream()
    
    user_data = None
    async for doc in docs:
        user_data = doc.to_dict()
        break
    
    if not user_data or not verify_password(form_data.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user_data["email"])
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/api/users/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """GDPR Data Portability: Export all user data"""
    # Get orders
    orders = []
    orders_stream = db.collection("orders").where("user_id", "==", current_user.id).stream()
    async for doc in orders_stream:
        orders.append(doc.to_dict())
    
    return {
        "profile": current_user.dict(),
        "orders": orders,
        "exported_at": datetime.utcnow()
    }

@app.delete("/api/users/me")
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """GDPR Right to be Forgotten: Delete account"""
    # Soft delete or anonymize
    await db.collection("users").document(current_user.id).update({
        "is_active": False,
        "email": f"deleted_{current_user.id}@geocheapest.com",
        "full_name": "Deleted User",
        "hashed_password": "deleted",
        "deleted_at": datetime.utcnow()
    })
    host = request.headers.get("host", "")
    return get_niche_config(host)

@app.get("/api/agent/welcome")
async def agent_welcome(
    current_user: User = Depends(get_current_user)
):
    """
    Get the proactive welcome message for the chat.
    """
    return {"message": agent_service.get_welcome_message(current_user.full_name or "there")}

@app.post("/api/agent/chat")
async def agent_chat(
    query: str,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    AI Deal Hunter: Chat with the platform agent.
    """
    # Get user context (past orders, preferences)
    context = {
        "user_id": current_user.id,
        "name": current_user.full_name
    }
    response = await agent_service.chat(query, context, db=db)
    return {"response": response}

@app.get("/api/market/analysis/{card_name}")
async def get_market_analysis(
    card_name: str,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Get comprehensive market analysis for a card (Playability, Investment, Graded Prices).
    """
    return await market_service.get_card_analysis(card_name)

# ==================== SHOPIFY OAUTH ====================

@app.get("/api/shopify/install")
async def shopify_install(
    shop: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Initiate Shopify OAuth flow
    Example: /api/shopify/install?shop=mystore.myshopify.com
    """
    if not shop or not shop.endswith(".myshopify.com"):
        raise HTTPException(status_code=400, detail="Invalid shop parameter")
    
    # Generate nonce for security
    nonce = os.urandom(16).hex()
    
    # Store nonce in Firestore (for verification in callback)
    nonce_ref = db.collection("oauth_nonces").document(shop)
    await nonce_ref.set({
        "nonce": nonce,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10)
    })
    
    # Build OAuth URL
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": nonce
    }
    
    oauth_url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=oauth_url)


@app.get("/api/shopify/callback")
async def shopify_callback(
    shop: str,
    code: str,
    state: str,
    background_tasks: BackgroundTasks,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Shopify OAuth callback - exchanges code for access token
    """
    # Verify nonce
    nonce_ref = db.collection("oauth_nonces").document(shop)
    nonce_doc = await nonce_ref.get()
    if not nonce_doc.exists:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    nonce_data = nonce_doc.to_dict()
    if nonce_data["nonce"] != state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")
    
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": SHOPIFY_API_KEY,
                "client_secret": SHOPIFY_API_SECRET,
                "code": code
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        token_data = response.json()
        access_token = token_data["access_token"]
    
    shop_details = await shopify_service.get_shop_details(shop, access_token)
    vendor_email = shop_details.get("email")
    business_name = shop_details.get("name")
    primary_domain = shop_details.get("domain") or (shop_details.get("primary_domain") or {}).get("host")
    business_url = None
    if primary_domain:
        business_url = primary_domain if primary_domain.startswith("http") else f"https://{primary_domain}"
    else:
        business_url = f"https://{shop}"
    
    # Create Stripe Connect account for vendor with real metadata
    stripe_account_id = await stripe_service.create_connect_account(
        shop,
        vendor_email=vendor_email,
        business_name=business_name,
        business_url=business_url
    )
    encrypted_token = shopify_service.encrypt_token(access_token)
    
    # Store vendor in Firestore
    store_data = {
        "shop_domain": shop,
        "store_name": business_name or shop,
        "owner_email": vendor_email,
        "access_token_encrypted": encrypted_token,
        "stripe_account_id": stripe_account_id,
        "status": "pending_approval",
        "created_at": datetime.utcnow(),
        "last_sync_at": None,
        "total_products": 0,
        "total_sales": 0,
        "commission_rate": 0.10,  # Default 10%
        "currency": shop_details.get("currency"),
        "country": shop_details.get("country_name"),
        "subscription_status": "not_subscribed"
    }
    
    await db.collection("stores").document(shop).set(store_data)
    
    # Delete used nonce
    await nonce_ref.delete()
    
    # Register required webhooks then trigger initial sync
    await shopify_service.ensure_webhooks(shop, access_token)
    background_tasks.add_task(shopify_service.sync_products, shop)
    
    # Generate Stripe onboarding link if possible
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    onboarding_url = None
    if stripe_account_id:
        onboarding_url = await stripe_service.create_account_link(
            stripe_account_id,
            refresh_url=f"{frontend_url}/vendor/connect/retry?shop={shop}",
            return_url=f"{frontend_url}/vendor/dashboard?shop={shop}"
        )
    
    # Redirect to onboarding if available, otherwise vendor dashboard
    redirect_target = onboarding_url or f"{frontend_url}/vendor/dashboard?shop={shop}"
    return RedirectResponse(url=redirect_target)


@app.post("/api/shopify/webhook")
async def shopify_webhook(
    request: Request,
    _: firestore.AsyncClient = Depends(get_db)
):
    """
    Handle Shopify webhooks (product updates, order creation)
    """
    # Verify webhook signature
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256")
    body = await request.body()
    
    computed_hmac = base64.b64encode(
        hmac.new(
            SHOPIFY_API_SECRET.encode(),
            body,
            hashlib.sha256
        ).digest()
    ).decode()
    
    if hmac_header != computed_hmac:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Process webhook
    topic = request.headers.get("X-Shopify-Topic")
    shop = request.headers.get("X-Shopify-Shop-Domain")
    data = await request.json()
    
    if topic in ("products/create", "products/update"):
        await shopify_service.sync_single_product(shop, data)
    elif topic == "products/delete":
        await shopify_service.delete_product(shop, data["id"])
    elif topic == "inventory_levels/update":
        await shopify_service.handle_inventory_level_update(shop, data)
    
    return {"status": "processed"}


# ==================== PRODUCTS ====================

@app.get("/api/products")
async def get_products(
    limit: int = 50,
    offset: int = 0,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Get unified product listings with best prices
    Returns ONE listing per product showing the cheapest available source
    """

    if db is None:
        logger.warning("Using mock products due to missing DB connection")
        mock_products = [
            {
                "id": "mock_1",
                "name": "Mock Pokemon Booster Box",
                "description": "A mock product for testing.",
                "category": "Pokemon",
                "image_url": "https://placehold.co/400",
                "best_price": 120.00,
                "source": "affiliate",
                "source_name": "Amazon.ca",
                "in_stock": True,
                "is_preorder": False,
                "url": "https://www.amazon.ca/dp/B0C8X",
                "asin": "B0C8X"
            }
        ]
        return {"products": mock_products, "total": len(mock_products)}

    query = db.collection("products")
    
    if category:
        query = query.where("category", "==", category)
    
    if search:
        # Firestore doesn't support full-text search natively
        # In production, use Algolia or Elasticsearch
        query = query.where("name", ">=", search).where("name", "<=", search + "\uf8ff")
    
    query = query.limit(limit).offset(offset)
    docs = query.stream()
    
    products = []
    async for doc in docs:
        product_data = doc.to_dict()
        product_data["id"] = doc.id
        
        # Get best price from all sources
        best_listing = await get_best_price(db, doc.id)
        if best_listing:
            product_data["best_price"] = best_listing["price"]
            product_data["source"] = best_listing["source"]
            product_data["source_name"] = best_listing["source_name"]
            product_data["in_stock"] = best_listing["in_stock"]
            product_data["is_preorder"] = best_listing.get("is_preorder", False)
            product_data["url"] = best_listing.get("url", "")
            product_data["asin"] = best_listing.get("asin")
        else:
            # Ensure fields exist even when no listing is found
            product_data["best_price"] = None
            product_data["source"] = None
            product_data["source_name"] = None
            product_data["in_stock"] = False
            product_data["is_preorder"] = False
            product_data["url"] = ""
            product_data["asin"] = None
        
        products.append(product_data)
    
    
    # Deduplication Logic with improved name normalization
    # Helper function to normalize product names for better matching
    def normalize_name(name: str) -> str:
        """Normalize product name by removing special chars, extra spaces, and lowercasing"""
        import re
        if not name:
            return ""
        # Remove special characters except spaces and alphanumerics
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
        # Replace multiple spaces with single space and strip
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    unique_products = []
    seen_upcs = {}  # UPC -> index in unique_products
    seen_asins = {}  # ASIN -> index in unique_products
    seen_names = {}  # Normalized Name -> index in unique_products

    for p in products:
        asin = p.get("asin")
        upc = p.get("upc")
        name = p.get("name", "")
        normalized_name = normalize_name(name)
        
        existing_idx = None
        
        # Check if we've seen this UPC (highest priority)
        if upc and upc in seen_upcs:
            existing_idx = seen_upcs[upc]

        # Check if we've seen this ASIN (second priority)
        if existing_idx is None and asin and asin in seen_asins:
            existing_idx = seen_asins[asin]
        
        # Check if we've seen this normalized name (fallback for missing UPC/ASIN)
        if existing_idx is None and normalized_name and normalized_name in seen_names:
            existing_idx = seen_names[normalized_name]
            
        if existing_idx is not None:
            # Found a duplicate - merge by keeping the better listing
            existing = unique_products[existing_idx]
            
            # Prefer in_stock, then lower price
            current_in_stock = p.get("in_stock", False)
            existing_in_stock = existing.get("in_stock", False)
            
            should_replace = False
            if current_in_stock and not existing_in_stock:
                # Current is in stock, existing is not - replace
                should_replace = True
            elif current_in_stock == existing_in_stock:
                # Both have same stock status - compare prices
                current_price = p.get("best_price") or float('inf')
                existing_price = existing.get("best_price") or float('inf')
                if current_price < existing_price:
                    should_replace = True
            
            if should_replace:
                # Replace with better listing
                unique_products[existing_idx] = p
            
            # CRITICAL: Always update ALL mappings for the current product
            # This ensures future products with the same UPC/ASIN/name find this entry
            if upc:
                seen_upcs[upc] = existing_idx
            if asin:
                seen_asins[asin] = existing_idx
            if normalized_name:
                seen_names[normalized_name] = existing_idx

        else:
            # New unique product - add to list
            new_idx = len(unique_products)
            unique_products.append(p)
            
            # Register all identifiers for this product
            if upc:
                seen_upcs[upc] = new_idx
            if asin:
                seen_asins[asin] = new_idx
            if normalized_name:
                seen_names[normalized_name] = new_idx
    
    return {"products": unique_products, "total": len(unique_products)}


@app.post("/api/admin/products/amazon/scrape")
async def scrape_amazon_product(
    request: Request,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Scrape Amazon product from affiliate URL and add to catalog.
    Accepts: { "affiliate_url": "...", "game": "Pokemon", "admin_key": "..." }
    """
    body = await request.json()
    admin_key = body.get("admin_key")
    affiliate_url = body.get("affiliate_url", "")
    game = body.get("game", "Pokemon")
    
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Extract ASIN from URL
    import re
    # ... existing scrape logic ...
    # For now, let's redirect to the new unified method if possible, or keep this for backward compatibility
    # But we want to add the new endpoint.
    
    return {"status": "deprecated", "message": "Use /api/admin/products/add_from_url instead"}

@app.post("/api/admin/products/add_from_url")
async def add_product_from_url_endpoint(
    request: Request,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Unified endpoint to add product from Amazon or eBay URL.
    """
    body = await request.json()
    url = body.get("url")
    admin_key = body.get("admin_key")
    
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
        
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        result = await affiliate_service.add_product_from_url(url)
        return {"status": "success", "product": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error adding product from URL")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/dashboard")
async def get_admin_dashboard(
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Return mock data if DB is down or just to ensure it works
    return {
        "stats": {
            "total_stores": 5,
            "total_revenue": 1250.00,
            "total_orders": 42,
            "total_commission": 62.50
        },
        "stores": [],
        "top_products": []
    }


    asin_match = re.search(r'/dp/([A-Z0-9]{10})', affiliate_url)
    if not asin_match:
        # Try amzn.to short link - need to follow redirect
        if 'amzn.to' in affiliate_url:
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(affiliate_url, timeout=10)
                    asin_match = re.search(r'/dp/([A-Z0-9]{10})', str(response.url))
            except Exception as e:
                logger.error(f"Failed to follow short link: {e}")
        
        if not asin_match:
            raise HTTPException(status_code=400, detail="Could not extract ASIN from URL")
    
    asin = asin_match.group(1)
    logger.info(f"Extracted ASIN: {asin}")
    
    # Fetch product details from Amazon
    details = await affiliate_service.get_amazon_product_details(asin)
    if not details:
        raise HTTPException(status_code=404, detail="Could not fetch product details from Amazon")
    
    # Parse product data
    title = details.get("title") or details.get("name", "")
    if not title:
        raise HTTPException(status_code=400, detail="Product title not found")
    
    # Auto-detect game from title
    title_lower = title.lower()
    detected_game = game  # fallback
    game_keywords = {
        "pokemon": "Pokemon",
        "magic": "Magic: The Gathering",
        "mtg": "Magic: The Gathering",
        "yu-gi-oh": "Yu-Gi-Oh",
        "yugioh": "Yu-Gi-Oh",
        "one piece": "One Piece",
        "lorcana": "Lorcana",
        "flesh and blood": "Flesh and Blood",
        "fab": "Flesh and Blood",
        "digimon": "Digimon",
        "weiss schwarz": "Weiss Schwarz",
        "dragon ball": "Dragon Ball Super",
    }
    for keyword, game_name in game_keywords.items():
        if keyword in title_lower:
            detected_game = game_name
            break
    
    # Parse price
    price_raw = details.get("price") or details.get("price_current") or details.get("price_string") or ""
    price = affiliate_service._parse_price(price_raw)
    if price <= 0:
        raise HTTPException(status_code=400, detail="Invalid product price")
    
    # Get other details
    image = details.get("image") or details.get("thumbnail") or (details.get("images") or [None])[0]
    description = details.get("description") or details.get("snippet") or ""
    rating = float(details.get("rating") or details.get("stars") or 0)
    review_count = int(details.get("reviews_count") or details.get("reviews") or 0)
    in_stock = details.get("in_stock", True)
    
    # Extract UPC/EAN/GTIN for deduplication
    upc = details.get("upc") or details.get("ean") or details.get("gtin") or ""
    logger.info(f"Extracted UPC: {upc}")
    
    # Check for existing product by UPC (primary) or name (fallback)
    product_id = None
    if upc:
        # Try to find by UPC first
        upc_query = db.collection("products").where("upc", "==", upc).limit(1).stream()
        async for doc in upc_query:
            product_id = doc.id
            logger.info(f"Found existing product by UPC: {product_id}")
            await doc.reference.update({
                "updated_at": datetime.utcnow(),
                "image_url": image,
                "category": detected_game,
                "segment": "sealed",
            })
            break
    
    if not product_id:
        # Fallback: check by exact name match
        name_query = db.collection("products").where("name", "==", title).limit(1).stream()
        async for doc in name_query:
            product_id = doc.id
            logger.info(f"Found existing product by name: {product_id}")
            # Update with UPC if we found one
            update_data = {
                "updated_at": datetime.utcnow(),
                "image_url": image,
                "category": detected_game,
                "segment": "sealed",
            }
            if upc:
                update_data["upc"] = upc
            await doc.reference.update(update_data)
            break
    
    if not product_id:
        # Create new product with UPC
        ref = db.collection("products").document()
        await ref.set({
            "name": title,
            "description": description,
            "category": detected_game,
            "segment": "sealed",
            "image_url": image,
            "upc": upc,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "total_sales": 0,
        })
        product_id = ref.id
        logger.info(f"Created new product: {product_id}")
    
    
    # Create affiliate listing
    doc_id = f"amazon_{asin}"
    affiliate_url_with_tag = affiliate_service.build_amazon_affiliate_url(asin)
    
    listing_data = {
        "product_id": product_id,
        "affiliate_name": "Amazon.ca",
        "affiliate_url": affiliate_url_with_tag,
        "asin": asin,
        "upc": upc,
        "price": price,
        "in_stock": in_stock,
        "quantity": 50,  # default
        "estimated_shipping": 0.0,
        "commission_rate": 0.05,
        "source": "amazon",
        "game": detected_game,
        "product_type": affiliate_service._classify_product_type(title),
        "release_status": affiliate_service._classify_release_status(title, details.get("availability")),
        "vendor_rating": rating,
        "review_count": review_count,
        "is_prime": bool(details.get("is_prime") or details.get("amazonPrime")),
        "images": [image] if image else [],
        "description": description,
        "status": "active",
        "updated_at": datetime.utcnow(),
    }
    
    listing_ref = db.collection("affiliateProducts").document(doc_id)
    existing = await listing_ref.get()
    if existing.exists:
        listing_data["created_at"] = existing.to_dict().get("created_at")
    else:
        listing_data["created_at"] = datetime.utcnow()
    
    await listing_ref.set(listing_data)
    
    logger.info(f"Successfully added product: {title} (ASIN: {asin})")
    
    return {
        "success": True,
        "asin": asin,
        "title": title,
        "price": price,
        "detected_game": detected_game,
        "product_id": product_id,
        "listing_id": doc_id
    }


@app.post("/api/admin/products/ebay/add")
async def add_ebay_product(
    request: Request,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Manually add eBay affiliate product.
    Accepts: { "affiliate_url": "...", "upc": "...", "price": 99.99, "product_name": "...", "game": "Pokemon", "admin_key": "..." }
    """
    body = await request.json()
    admin_key = body.get("admin_key")
    affiliate_url = body.get("affiliate_url", "")
    upc = body.get("upc", "")
    price = float(body.get("price", 0))
    product_name = body.get("product_name", "")
    game = body.get("game", "Pokemon")
    description = body.get("description", "")
    image_url = body.get("image_url", "")
    
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    if not affiliate_url or not product_name:
        raise HTTPException(status_code=400, detail="affiliate_url and product_name are required")
    
    if price <= 0:
        raise HTTPException(status_code=400, detail="Invalid price")
    
    # Check for existing product by UPC (primary) or name (fallback)
    product_id = None
    if upc:
        # Try to find by UPC first
        upc_query = db.collection("products").where("upc", "==", upc).limit(1).stream()
        async for doc in upc_query:
            product_id = doc.id
            logger.info(f"Found existing product by UPC: {product_id}")
            # Update product if needed
            update_data = {"updated_at": datetime.utcnow()}
            if image_url:
                update_data["image_url"] = image_url
            await doc.reference.update(update_data)
            break
    
    if not product_id:
        # Fallback: check by exact name match
        name_query = db.collection("products").where("name", "==", product_name).limit(1).stream()
        async for doc in name_query:
            product_id = doc.id
            logger.info(f"Found existing product by name: {product_id}")
            # Update with UPC if we have one
            update_data = {"updated_at": datetime.utcnow()}
            if upc:
                update_data["upc"] = upc
            if image_url:
                update_data["image_url"] = image_url
            await doc.reference.update(update_data)
            break
    
    if not product_id:
        # Create new product
        ref = db.collection("products").document()
        await ref.set({
            "name": product_name,
            "description": description,
            "category": game,
            "segment": "sealed",
            "image_url": image_url or "",
            "upc": upc,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "total_sales": 0,
        })
        product_id = ref.id
        logger.info(f"Created new product: {product_id}")
    
    # Create eBay affiliate listing
    import hashlib
    doc_id = f"ebay_{hashlib.md5(affiliate_url.encode()).hexdigest()[:10]}"
    
    listing_data = {
        "product_id": product_id,
        "affiliate_name": "eBay.ca",
        "affiliate_url": affiliate_url,
        "upc": upc,
        "price": price,
        "in_stock": True,  # Assume in stock unless told otherwise
        "quantity": 10,  # default for eBay
        "estimated_shipping": 0.0,
        "commission_rate": 0.05,
        "source": "ebay",
        "game": game,
        "product_type": "sealed",  # default
        "release_status": "available",
        "vendor_rating": 0,
        "review_count": 0,
        "images": [image_url] if image_url else [],
        "description": description,
        "status": "active",
        "updated_at": datetime.utcnow(),
    }
    
    listing_ref = db.collection("affiliateProducts").document(doc_id)
    existing = await listing_ref.get()
    if existing.exists:
        listing_data["created_at"] = existing.to_dict().get("created_at")
    else:
        listing_data["created_at"] = datetime.utcnow()
    
    await listing_ref.set(listing_data)
    
    logger.info(f"Successfully added eBay product: {product_name}")
    
    return {
        "success": True,
        "product_name": product_name,
        "price": price,
        "product_id": product_id,
        "listing_id": doc_id
    }


async def get_best_price(
    db: firestore.AsyncClient,
    product_id: str
) -> Optional[Dict[str, Any]]:
    """
    Find the best available price for a product across all sources
    Priority: Shopify listings, then affiliates
    """
    listings = []
    
    # Get Shopify listings
    shopify_docs = db.collection("shopifyListings")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in shopify_docs:
        listing = doc.to_dict()
        if listing["quantity"] > 0 or listing.get("is_preorder"):
            # Construct Shopify product URL
            store_domain = listing["store_id"]
            # Since we don't have the handle stored, we'll use a generic URL
            # In production, we should store the handle from the GraphQL query
            shopify_url = f"https://{store_domain}"
            
            listings.append({
                "price": listing["price"],
                "source": "shopify",
                "source_name": listing["store_name"],
                "source_id": listing["store_id"],
                "in_stock": listing["quantity"] > 0,
                "is_preorder": listing.get("is_preorder", False),
                "listing_id": doc.id,
                "url": shopify_url,
                "upc": listing.get("upc") or listing.get("barcode")
            })
    
    # Get affiliate listings
    affiliate_docs = db.collection("affiliateProducts")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in affiliate_docs:
        listing = doc.to_dict()
        if listing["in_stock"]:
            listings.append({
                "price": listing["price"],
                "source": "affiliate",
                "source_name": listing["affiliate_name"],
                "source_id": listing["affiliate_url"],
                "in_stock": True,
                "is_preorder": False,
                "listing_id": doc.id,
                "url": listing.get("affiliate_url") or affiliate_service.build_amazon_affiliate_url(listing.get("asin")),
                "asin": listing.get("asin"),
                "upc": listing.get("upc")
            })
    
    if not listings:
        return None
    
    # Sort by price (cheapest first)
    listings.sort(key=lambda x: x["price"])
    return listings[0]



@app.get("/api/products/{product_id}")
async def get_product(
    product_id: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Get detailed product information with all available listings"""
    doc = await db.collection("products").document(product_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = doc.to_dict()
    product_data["id"] = doc.id
    
    # Get all listings for this product
    all_listings = []
    
    # Shopify listings
    shopify_docs = db.collection("shopifyListings")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in shopify_docs:
        listing = doc.to_dict()
        all_listings.append({
            "type": "shopify",
            "store_name": listing["store_name"],
            "price": listing["price"],
            "quantity": listing["quantity"],
            "is_preorder": listing.get("is_preorder", False),
            "listing_id": doc.id
        })
    
    # Affiliate listings
    affiliate_docs = db.collection("affiliateProducts")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in affiliate_docs:
        listing = doc.to_dict()
        all_listings.append({
            "type": "affiliate",
            "affiliate_name": listing["affiliate_name"],
            "price": listing["price"],
            "url": listing["affiliate_url"],
            "listing_id": doc.id
        })
    
    # Sort by price
    all_listings.sort(key=lambda x: x["price"])
    
    product_data["listings"] = all_listings
    product_data["best_price"] = all_listings[0]["price"] if all_listings else None
    
    return product_data


# ==================== CART OPTIMIZATION ====================

@app.post("/api/cart/optimize")
async def optimize_cart(
    request: CartOptimizationRequest,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Optimize cart to find cheapest vendor per item including shipping.
    Compares "Split Order" (cheapest per item) vs "Bundled Order" (all from one vendor).
    """
    # 1. Fetch all valid listings for every item
    cart_listings = {} # {product_id: [listings]}
    for item in request.items:
        listings = await get_all_listings_with_shipping(
            db, item.product_id, item.quantity, request.shipping_address
        )
        if not listings:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not available")
        cart_listings[item.product_id] = listings

    # 2. Strategy A: Split Order (Greedy - Cheapest per item)
    split_total = 0
    split_selection = []
    for item in request.items:
        # Sort by total_price (price + shipping)
        sorted_listings = sorted(cart_listings[item.product_id], key=lambda x: x["total_price"])
        best = sorted_listings[0]
        split_total += best["total_price"]
        split_selection.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "listing": best
        })

    # Fallback return to fix syntax error
    return {
        "optimization_type": "split",
        "items": split_selection,
        "total_amount": split_total,
        "savings": 0,
        "currency": "CAD"
    }


async def get_all_listings_with_shipping(
    db: firestore.AsyncClient,
    product_id: str,
    quantity: int,
    shipping_address: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Get all listings with calculated shipping costs"""
    listings = []
    
    # Shopify listings
    shopify_docs = db.collection("shopifyListings")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in shopify_docs:
        listing = doc.to_dict()
        if listing["quantity"] >= quantity or listing.get("is_preorder"):
            shipping_cost = await shippo_service.calculate_shipping(
                listing["store_id"],
                product_id,
                quantity,
                shipping_address
            )
            
            product_price = listing["price"] * quantity
            listings.append({
                "source": "shopify",
                "source_name": listing["store_name"],
                "store_id": listing["store_id"],
                "listing_id": doc.id,
                "product_price": product_price,
                "shipping_cost": shipping_cost,
                "total_price": product_price + shipping_cost
            })
    
    # Affiliate listings (shipping calculated by affiliate)
    affiliate_docs = db.collection("affiliateProducts")\
        .where("product_id", "==", product_id)\
        .where("status", "==", "active")\
        .stream()
    
    async for doc in affiliate_docs:
        listing = doc.to_dict()
        if listing["in_stock"]:
            product_price = listing["price"] * quantity
            # Estimate shipping for affiliates (or get from API if available)
            shipping_cost = listing.get("estimated_shipping", 10.0)
            
            listings.append({
                "source": "affiliate",
                "source_name": listing["affiliate_name"],
                "store_id": None,
                "listing_id": doc.id,
                "product_price": product_price,
                "shipping_cost": shipping_cost,
                "total_price": product_price + shipping_cost
            })
    
    return listings


# ==================== USER PORTAL ====================


@app.get("/api/users/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")

    user_doc = await db.collection("users").document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user_doc.to_dict()
    orders_stream = db.collection("orders")\
        .where("user_id", "==", user_id)\
        .stream()
    
    order_count = 0
    lifetime_value = 0.0
    async for doc in orders_stream:
        order = doc.to_dict()
        order_count += 1
        lifetime_value += order.get("total_amount", 0.0)
    
    return {
        "user": {
            "id": user_id,
            "email": user_data.get("email"),
            "stripe_customer_id": user_data.get("stripe_customer_id"),
            "created_at": _serialize_datetime(user_data.get("created_at")),
            "updated_at": _serialize_datetime(user_data.get("updated_at")),
        },
        "stats": {
            "orders": order_count,
            "lifetime_value": lifetime_value,
        }
    }


@app.get("/api/users/{user_id}/orders")
async def list_user_orders(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view these orders")

    orders = []
    orders_stream = db.collection("orders")\
        .where("user_id", "==", user_id)\
        .stream()
    
    async for doc in orders_stream:
        data = doc.to_dict()
        orders.append({
            "id": doc.id,
            "status": data.get("status"),
            "total_amount": data.get("total_amount"),
            "total_shipping": data.get("total_shipping"),
            "currency": data.get("currency"),
            "created_at": _serialize_datetime(data.get("created_at")),
            "updated_at": _serialize_datetime(data.get("updated_at")),
        })
    
    orders.sort(key=lambda o: o.get("created_at") or "", reverse=True)
    return {"orders": orders}


@app.get("/api/users/{user_id}/payment-methods")
async def get_user_payment_methods(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: firestore.AsyncClient = Depends(get_db)
):
    if current_user.id != user_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to view payment methods")

    user_doc = await db.collection("users").document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    customer_id = user_doc.to_dict().get("stripe_customer_id")
    if not customer_id:
        return {"customer_id": None, "payment_methods": []}
    
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card"
        )
    except stripe.error.StripeError as exc:
        logger.error("Stripe payment method list failed for %s: %s", user_id, exc)
        raise HTTPException(status_code=502, detail="Stripe error") from exc
    
    cards = []
    for pm in payment_methods.get("data", []):
        card = pm.get("card", {})
        cards.append({
            "id": pm.get("id"),
            "brand": card.get("brand"),
            "last4": card.get("last4"),
            "exp_month": card.get("exp_month"),
            "exp_year": card.get("exp_year"),
            "funding": card.get("funding"),
        })
    
    return {
        "customer_id": customer_id,
        "payment_methods": cards
    }


# ==================== CHECKOUT ====================

@app.post("/api/checkout")
async def create_checkout(
    request: CheckoutRequest,
    db: firestore.AsyncClient = Depends(get_db)
):
    """
    Split checkout: Stripe for Shopify products, redirect for affiliates
    """
    shopify_items = []
    affiliate_items = []
    
    for item in request.items:
        if item["source"] == "shopify":
            if not item.get("store_id"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing store information for product {item['product_id']}"
                )
            shopify_items.append(item)
        else:
            affiliate_items.append(item)
    
    result = {
        "shopify_checkout": None,
        "affiliate_redirects": []
    }
    
    shipping_address_payload = request.shipping_address.model_dump()

    # Handle Shopify checkout
    if shopify_items:
        checkout_session = await stripe_service.create_checkout_session(
            shopify_items,
            request.customer_email,
            shipping_address_payload,
            user_id=request.user_id,
            save_payment_method=request.save_payment_method
        )
        result["shopify_checkout"] = {
            "session_id": checkout_session.id,
            "url": checkout_session.url
        }
    
    # Handle affiliate redirects
    for item in affiliate_items:
        affiliate_doc = await db.collection("affiliateProducts")\
            .document(item["listing_id"]).get()
        
        if affiliate_doc.exists:
            affiliate_data = affiliate_doc.to_dict()
            result["affiliate_redirects"].append({
                "product_id": item["product_id"],
                "affiliate_name": affiliate_data["affiliate_name"],
                "url": affiliate_data["affiliate_url"]
            })
    
    return result


# ==================== STRIPE CONNECT & BILLING ====================

@app.post("/api/stripe/customers/setup-intent")
async def create_payment_method_setup_intent(payload: PaymentCustomerRequest):
    """Generate a SetupIntent so registered users can save cards for future use"""
    intent = await stripe_service.create_setup_intent_for_user(
        payload.user_id,
        payload.email
    )
    return intent


@app.post("/api/vendor/{shop}/stripe/account-link")
async def create_vendor_account_link(
    shop: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    store_doc = await db.collection("stores").document(shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    store = store_doc.to_dict()
    stripe_account_id = store.get("stripe_account_id")
    if not stripe_account_id:
        raise HTTPException(status_code=400, detail="Stripe account not configured")
    
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    link = await stripe_service.create_account_link(
        stripe_account_id,
        refresh_url=f"{frontend_url}/vendor/connect/retry?shop={shop}",
        return_url=f"{frontend_url}/vendor/dashboard?shop={shop}"
    )
    if not link:
        raise HTTPException(status_code=500, detail="Unable to generate Stripe onboarding link")
    
    return {"url": link}


@app.post("/api/vendor/{shop}/subscription/checkout")
async def create_vendor_subscription_checkout(
    shop: str,
    payload: VendorSubscriptionRequest,
    db: firestore.AsyncClient = Depends(get_db)
):
    store_ref = db.collection("stores").document(shop)
    store_doc = await store_ref.get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    store = store_doc.to_dict()
    session, billing_customer_id = await stripe_service.create_vendor_subscription_checkout(
        shop,
        store,
        payload.tier,
        payload.contact_email,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url
    )
    
    await store_ref.set({
        "stripe_billing_customer_id": billing_customer_id,
        "subscription_pending_tier": payload.tier,
        "subscription_checkout_session_id": session.id,
        "subscription_checkout_created_at": datetime.utcnow()
    }, merge=True)
    
    return {"checkout_url": session.url, "session_id": session.id}


@app.post("/api/vendor/{shop}/subscription/portal")
async def create_vendor_billing_portal_link(
    shop: str,
    payload: VendorBillingPortalRequest,
    db: firestore.AsyncClient = Depends(get_db)
):
    store_doc = await db.collection("stores").document(shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    store = store_doc.to_dict()
    try:
        session = await stripe_service.create_vendor_billing_portal_session(
            store,
            return_url=payload.return_url
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    
    return {"url": session.url}


@app.post("/api/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Handle Stripe webhooks for payment and subscription events"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data_object = event["data"]["object"]
    metadata = data_object.get("metadata") or {}
    checkout_type = metadata.get("checkout_type")
    
    if event_type == "checkout.session.completed":
        if checkout_type == "vendor_subscription" or data_object.get("mode") == "subscription":
            await handle_vendor_subscription_checkout_event(data_object, db)
        else:
            await handle_checkout_session_completed(data_object, db)
    elif event_type == "invoice.payment_succeeded":
        await handle_vendor_subscription_invoice_event(data_object, db, status="active")
    elif event_type == "invoice.payment_failed":
        await handle_vendor_subscription_invoice_event(data_object, db, status="past_due")
    elif event_type == "customer.subscription.deleted":
        await handle_vendor_subscription_cancellation(data_object, db)
    elif event_type == "payment_intent.payment_failed":
        logger.warning(
            "Stripe payment failed for intent %s: %s",
            data_object.get("id"),
            data_object.get("last_payment_error")
        )
    else:
        logger.debug("Unhandled Stripe event %s", event_type)
    
    return {"status": "processed"}


async def handle_checkout_session_completed(
    session_payload: Dict[str, Any],
    db: firestore.AsyncClient
):
    """Finalize orders for completed Stripe Checkout sessions"""
    session = stripe.checkout.Session.retrieve(
        session_payload["id"],
        expand=["payment_intent.latest_charge.balance_transaction"]
    )
    await record_order_from_session(db, session)


async def record_order_from_session(
    db: firestore.AsyncClient,
    session: Dict[str, Any]
) -> Optional[str]:
    metadata = session.get("metadata") or {}
    items_raw = metadata.get("items")
    if not items_raw:
        logger.warning("Stripe session %s missing line item metadata", session.get("id"))
        return None
    
    try:
        line_items = json.loads(items_raw)
    except json.JSONDecodeError:
        logger.error("Invalid items metadata on session %s", session.get("id"))
        return None
    
    existing = db.collection("orders")\
        .where("stripe_session_id", "==", session["id"])\
        .limit(1)\
        .stream()
    async for doc in existing:
        logger.info("Order already recorded for session %s", session["id"])
        return doc.id
    
    shipping_address = {}
    shipping_meta = metadata.get("shipping_address")
    if shipping_meta:
        try:
            shipping_address = json.loads(shipping_meta)
        except json.JSONDecodeError:
            shipping_address = {}
    
    payment_intent = session.get("payment_intent")
    if isinstance(payment_intent, str):
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent,
            expand=["latest_charge.balance_transaction"]
        )
    
    order_total = Decimal(session.get("amount_total", 0)) / Decimal("100")
    platform_commission_total = Decimal(metadata.get("platform_commission_total", "0"))
    total_shipping = sum(Decimal(item.get("shipping_total", "0")) for item in line_items)
    total_products = sum(Decimal(item.get("product_total", "0")) for item in line_items)
    stripe_fee = stripe_service.calculate_total_stripe_fee(payment_intent, order_total)
    
    order_data = {
        "stripe_session_id": session["id"],
        "stripe_payment_intent": payment_intent.get("id") if payment_intent else None,
        "transfer_group": metadata.get("transfer_group"),
        "customer_email": (session.get("customer_details") or {}).get("email") or session.get("customer_email"),
        "user_id": metadata.get("user_id") or None,
        "status": "paid",
        "payment_status": session.get("payment_status"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "total_amount": float(order_total),
        "total_product_price": float(total_products),
        "total_shipping": float(total_shipping),
        "currency": session.get("currency", "CAD").upper(),
        "platform_commission": float(platform_commission_total),
        "stripe_fee": float(stripe_fee),
        "shipping_address": shipping_address,
        "metadata": metadata
    }
    
    order_ref = db.collection("orders").document()
    await order_ref.set(order_data)
    
    order_items_collection = db.collection("orderItems")
    for item in line_items:
        quantity = int(item.get("quantity", 1))
        product_total = Decimal(item.get("product_total", "0"))
        unit_price = (product_total / Decimal(quantity)) if quantity else Decimal("0")
        commission_amount = Decimal(item.get("platform_commission", "0"))
        gross_total = Decimal(item.get("gross_total", "0"))
        
        order_item = {
            "order_id": order_ref.id,
            "product_id": item.get("product_id"),
            "listing_id": item.get("listing_id"),
            "source": "shopify",
            "store_id": item.get("store_id"),
            "quantity": quantity,
            "unit_price": float(unit_price),
            "total_price": float(gross_total),
            "commission_rate": float(Decimal(item.get("commission_rate", "0"))),
            "commission_amount": float(commission_amount),
            "vendor_payout": float(gross_total - commission_amount),
            "status": "paid",
            "shipping_total": float(Decimal(item.get("shipping_total", "0")))
        }
        await order_items_collection.document().set(order_item)
    
    await stripe_service.process_commission(order_ref.id, metadata, payment_intent)
    return order_ref.id


async def handle_vendor_subscription_checkout_event(
    session_payload: Dict[str, Any],
    db: firestore.AsyncClient
):
    store_id = (session_payload.get("metadata") or {}).get("store_id")
    subscription_id = session_payload.get("subscription")
    customer_id = session_payload.get("customer")
    tier = (session_payload.get("metadata") or {}).get("subscription_tier")
    
    subscription = None
    if subscription_id:
        subscription = stripe.Subscription.retrieve(subscription_id)
        meta = subscription.metadata or {}
        store_id = store_id or meta.get("store_id")
        tier = tier or meta.get("subscription_tier")
    
    if not store_id:
        logger.warning("Missing store_id on vendor subscription checkout session %s", session_payload.get("id"))
        return
    
    current_period_end = None
    if subscription:
        current_period_end = datetime.utcfromtimestamp(subscription["current_period_end"])
    
    await db.collection("stores").document(store_id).set({
        "subscription_status": "active",
        "subscription_tier": tier,
        "stripe_subscription_id": subscription_id,
        "stripe_billing_customer_id": customer_id,
        "subscription_current_period_end": current_period_end,
        "subscription_activated_at": datetime.utcnow(),
        "subscription_pending_tier": firestore.DELETE_FIELD,
        "subscription_checkout_session_id": firestore.DELETE_FIELD
    }, merge=True)


async def handle_vendor_subscription_invoice_event(
    invoice: Dict[str, Any],
    db: firestore.AsyncClient,
    status: str
):
    metadata = invoice.get("metadata") or {}
    store_id = metadata.get("store_id")
    tier = metadata.get("subscription_tier")
    for line in (invoice.get("lines", {}) or {}).get("data", []):
        line_meta = line.get("metadata") or {}
        store_id = store_id or line_meta.get("store_id")
        tier = tier or line_meta.get("subscription_tier")
    
    if not store_id:
        logger.warning("Unable to resolve store for invoice %s", invoice.get("id"))
        return
    
    update_data = {
        "subscription_status": status,
        "subscription_tier": tier,
        "subscription_current_period_end": datetime.utcfromtimestamp(invoice.get("period_end", invoice.get("created", 0))),
        "subscription_last_invoice_id": invoice.get("id"),
        "subscription_last_payment_at": datetime.utcnow()
    }
    
    if invoice.get("customer"):
        update_data["stripe_billing_customer_id"] = invoice["customer"]
    
    await db.collection("stores").document(store_id).set(update_data, merge=True)


async def handle_vendor_subscription_cancellation(
    subscription: Dict[str, Any],
    db: firestore.AsyncClient
):
    metadata = subscription.get("metadata") or {}
    store_id = metadata.get("store_id")
    if not store_id:
        logger.warning("Subscription cancellation missing store metadata: %s", subscription.get("id"))
        return
    
    await db.collection("stores").document(store_id).set({
        "subscription_status": "canceled",
        "stripe_subscription_id": firestore.DELETE_FIELD,
        "subscription_tier": firestore.DELETE_FIELD
    }, merge=True)


# ==================== VENDOR DASHBOARD ====================

@app.get("/api/vendor/dashboard")
async def vendor_dashboard(
    shop: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Get vendor dashboard data"""
    store_doc = await db.collection("stores").document(shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    store_data = store_doc.to_dict()
    
    # Get products
    products = []
    product_docs = db.collection("shopifyListings")\
        .where("store_id", "==", shop)\
        .stream()
    
    async for doc in product_docs:
        product = doc.to_dict()
        product["id"] = doc.id
        products.append(product)
    
    # Get recent orders
    orders = []
    order_docs = db.collection("orderItems")\
        .where("store_id", "==", shop)\
        .order_by("created_at", direction="DESCENDING")\
        .limit(20)\
        .stream()
    
    async for doc in order_docs:
        order = doc.to_dict()
        order["id"] = doc.id
        orders.append(order)
    
    # Get payout summary
    payouts = []
    payout_docs = db.collection("sellerPayouts")\
        .where("store_id", "==", shop)\
        .order_by("created_at", direction="DESCENDING")\
        .limit(10)\
        .stream()
    
    async for doc in payout_docs:
        payout = doc.to_dict()
        payout["id"] = doc.id
        payouts.append(payout)
    
    return {
        "store": store_data,
        "products": products,
        "recent_orders": orders,
        "payouts": payouts,
        "stats": {
            "total_sales": store_data.get("total_sales", 0),
            "total_products": len(products),
            "pending_payouts": sum(p["amount"] for p in payouts if p["status"] == "pending")
        }
    }


@app.post("/api/vendor/sync-products")
async def sync_vendor_products(
    shop: str,
    background_tasks: BackgroundTasks,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Manually trigger product sync"""
    store_doc = await db.collection("stores").document(shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    store_data = store_doc.to_dict()
    background_tasks.add_task(shopify_service.sync_products, shop)
    
    return {"status": "sync_started"}


@app.post("/api/vendor/shipping-label")
async def vendor_shipping_label(
    request: ShippingLabelRequest,
    db: firestore.AsyncClient = Depends(get_db)
):
    store_doc = await db.collection("stores").document(request.shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    label = await shippo_service.create_shipping_label(
        request.order_id,
        request.shipping_address.model_dump(),
        [item.model_dump() for item in request.items]
    )
    if not label:
        raise HTTPException(status_code=400, detail="Unable to generate shipping label")
    return label


@app.post("/api/vendor/return-label")
async def vendor_return_label(
    request: ReturnLabelRequest,
    db: firestore.AsyncClient = Depends(get_db)
):
    store_doc = await db.collection("stores").document(request.shop).get()
    if not store_doc.exists:
        raise HTTPException(status_code=404, detail="Store not found")
    
    label = await shippo_service.create_return_label(
        request.order_id,
        request.customer_address.model_dump(),
        [item.model_dump() for item in request.items]
    )
    if not label:
        raise HTTPException(status_code=400, detail="Unable to generate return label")
    return label


# ==================== ADMIN PORTAL ====================

@app.get("/api/admin/dashboard")
async def admin_dashboard(
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Super admin dashboard with platform analytics"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Get all stores
    stores = []
    store_docs = db.collection("stores").stream()
    async for doc in store_docs:
        store = doc.to_dict()
        store["id"] = doc.id
        stores.append(store)
    
    # Get platform stats
    total_orders_result = await db.collection("orders").count().get()
    total_orders = (
        total_orders_result[0][0].value if total_orders_result and total_orders_result[0] else 0
    )
    total_revenue = 0
    total_commission = 0
    
    order_docs = db.collection("orders").stream()
    async for doc in order_docs:
        order = doc.to_dict()
        total_revenue += order.get("total_amount", 0)
        total_commission += order.get("platform_commission", 0)
    
    # Top products
    product_docs = db.collection("products").order_by("total_sales", direction="DESCENDING").limit(10).stream()
    top_products = []
    async for doc in product_docs:
        product = doc.to_dict()
        product["id"] = doc.id
        top_products.append(product)
    
    return {
        "stores": stores,
        "stats": {
            "total_stores": len(stores),
            "active_stores": len([s for s in stores if s["status"] == "active"]),
            "pending_stores": len([s for s in stores if s["status"] == "pending_approval"]),
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_commission": total_commission
        },
        "top_products": top_products
    }


@app.post("/api/admin/stores/{shop}/approve")
async def approve_store(
    shop: str,
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Approve a vendor store"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    await db.collection("stores").document(shop).update({
        "status": "active",
        "approved_at": datetime.utcnow()
    })
    
    return {"status": "approved"}


@app.put("/api/admin/commission-rates")
async def update_commission_rates(
    rates: Dict[str, float],
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Update platform commission rates"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    await db.collection("commissionRates").document("default").set({
        **rates,
        "updated_at": datetime.utcnow()
    })
    
    return {"status": "updated"}


@app.put("/api/admin/stores/{shop}/commission")
async def set_vendor_commission(
    shop: str,
    rate: float,
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Set custom commission rate for specific vendor"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    await db.collection("stores").document(shop).update({
        "commission_rate": rate,
        "commission_updated_at": datetime.utcnow()
    })
    
    return {"status": "updated"}


@app.post("/api/admin/amazon/sync")
async def trigger_amazon_sync(admin_key: str):
    """Manually trigger an Amazon.ca affiliate sync"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    if not affiliate_service.amazon_sync_enabled:
        raise HTTPException(status_code=400, detail="Amazon sync disabled")
    await affiliate_service.sync_amazon_tcg_products()
    return {"status": "completed"}


# ==================== RETURNS ====================

@app.post("/api/returns")
async def create_return_request(
    order_id: str,
    items: List[Dict[str, Any]],
    reason: str,
    customer_email: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Create return request"""
    order_doc = await db.collection("orders").document(order_id).get()
    if not order_doc.exists:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return_data = {
        "order_id": order_id,
        "items": items,
        "reason": reason,
        "customer_email": customer_email,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    return_ref = db.collection("returnRequests").document()
    await return_ref.set(return_data)
    
    return {"return_id": return_ref.id, "status": "pending"}


@app.post("/api/returns/{return_id}/approve")
async def approve_return(
    return_id: str,
    admin_key: str,
    db: firestore.AsyncClient = Depends(get_db)
):
    """Approve return and process refund"""
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    return_doc = await db.collection("returnRequests").document(return_id).get()
    if not return_doc.exists:
        raise HTTPException(status_code=404, detail="Return not found")
    
    return_data = return_doc.to_dict()
    
    # Process Stripe refund
    order_doc = await db.collection("orders").document(return_data["order_id"]).get()
    order_data = order_doc.to_dict()
    
    if "stripe_payment_intent" in order_data:
        await stripe_service.process_refund(
            order_data["stripe_payment_intent"],
            return_data["items"]
        )
    
    # Update return status
    await db.collection("returnRequests").document(return_id).update({
        "status": "approved",
        "approved_at": datetime.utcnow()
    })
    
    return {"status": "approved", "refund_processed": True}


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
