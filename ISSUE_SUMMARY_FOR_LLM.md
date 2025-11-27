# GeoCheapest Critical Issues Summary

## Current Problems (Still Unresolved)

### 1. Product Duplication Issue
**Problem:** Same products are showing multiple times on the frontend.

**Backend Deduplication Logic Location:**
- File: `backend/app/main.py`
- Function: `get_products()` (lines 634-779)
- Current approach: Groups products by UPC, ASIN, and normalized name
- Issue: Deduplication logic may not be working correctly

**How it's supposed to work:**
```python
# In get_products() function:
# 1. Fetch all products from Firestore
# 2. For each product, get best price from get_best_price()
# 3. Deduplicate using UPC, ASIN, or name matching
# 4. Keep only the cheapest in-stock version
```

**Deduplication code snippet (lines 745-779):**
```python
# Deduplication Logic
unique_products = []
seen_upcs = {}  # UPC -> index in unique_products
seen_asins = {}  # ASIN -> index in unique_products
seen_names = {}  # Normalized Name -> index in unique_products

for p in products:
    asin = p.get("asin")
    upc = p.get("upc")
    name = p.get("name", "").strip().lower()
    
    existing_idx = None
    
    # Check if we've seen this UPC/ASIN/Name
    if upc and upc in seen_upcs:
        existing_idx = seen_upcs[upc]
    if existing_idx is None and asin and asin in seen_asins:
        existing_idx = seen_asins[asin]
    if existing_idx is None and name and name in seen_names:
        existing_idx = seen_names[name]
        
    if existing_idx is not None:
        # Compare and keep cheaper/in-stock version
        existing = unique_products[existing_idx]
        should_replace = False
        
        if p.get("in_stock") and not existing.get("in_stock"):
            should_replace = True
        elif p.get("in_stock") == existing.get("in_stock"):
            if (p.get("best_price") or float('inf')) < (existing.get("best_price") or float('inf')):
                should_replace = True
        
        if should_replace:
            unique_products[existing_idx] = p
    else:
        # New product, add to list
        unique_products.append(p)
        if upc:
            seen_upcs[upc] = len(unique_products) - 1
        if asin:
            seen_asins[asin] = len(unique_products) - 1
        if name:
            seen_names[name] = len(unique_products) - 1
```

**Possible causes:**
- Products in database have different UPCs/ASINs/names
- Deduplication logic has a bug
- Multiple products are being created with same data but different IDs

---

### 2. Affiliate Links Not Working
**Problem:** "Buy on Amazon.ca" buttons are not redirecting to partner platforms.

**Frontend Code (ProductCard.tsx):**
```tsx
// Lines 98-107 - This SHOULD work but isn't
{product.source === 'affiliate' && product.url ? (
  <a
    href={product.url}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
  >
    <ShoppingCart className="w-4 h-4" />
    Buy on {product.source_name}
  </a>
) : (
  // Internal product - Add to Cart button
  <button onClick={handleAddToCart}>...</button>
)}
```

**Backend Code (main.py - get_best_price function):**
```python
# Lines for affiliate listings (approximate location)
async for doc in affiliate_docs:
    listing = doc.to_dict()
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
```

**Possible causes:**
- `product.url` is undefined/null in frontend
- `product.source` is not "affiliate"
- Backend not returning `url` field properly
- Database records missing `affiliate_url` field

**Debug steps needed:**
1. Check browser console: `console.log(product)` to see actual data
2. Check API response: `curl http://localhost:8000/api/products` and verify `url` field exists
3. Check database: Verify `affiliateListings` collection has `affiliate_url` field

---

### 3. Admin Dashboard Alert Error (Still Occurring)
**Problem:** `TypeError: Illegal invocation` when adding product, even after changing to `window.alert()`

**Current Code (page.tsx line 141):**
```tsx
} catch (error: any) {
  window.alert(`Failed to add product: ${error.response?.data?.detail || error.message}`)
}
```

**Why it's still failing:**
The error might be caused by:
1. Hot reload not picking up changes - need hard refresh
2. Template literal causing issues with error object
3. Next.js build cache issue

**Attempted Fix:**
Changed all `alert()` to `window.alert()` in 9 locations in `frontend/src/app/admin/dashboard/page.tsx`

**Better solution to try:**
```tsx
} catch (error: any) {
  const errorMsg = error.response?.data?.detail || error.message || 'Unknown error';
  window.alert(`Failed to add product: ${errorMsg}`);
}
```

Or use a toast notification library instead of alert.

---

## Files Modified

### 1. frontend/src/app/admin/dashboard/page.tsx
**Changes:** Replaced all `alert()` with `window.alert()`
- Line 20: Admin key validation
- Lines 32-35: Authentication errors
- Lines 50-52: Amazon sync alerts
- Lines 65-68: Store approval alerts
- Lines 127, 136, 141: Product addition alerts

### 2. frontend/src/components/ProductCard.tsx
**Status:** No changes needed - code is correct
- Lines 36-43: Clickable image with affiliate link
- Lines 67-72: Clickable title with affiliate link
- Lines 98-107: "Buy on [Source]" button for affiliates

### 3. backend/app/main.py
**Status:** Reviewed, no changes made
- `get_products()` function has deduplication logic
- `get_best_price()` function returns `url` field for affiliates

---

## Test Data Added

Created test Amazon affiliate product via API:
```python
# Script: add_test_product_api.py
test_url = "https://www.amazon.ca/dp/B0BKTWHV8T"
response = requests.post(
    "http://localhost:8000/api/admin/products/add_from_url",
    json={"url": test_url, "admin_key": "admin123"}
)
```

**Result:** Product added successfully to database

---

## Server Status

- **Backend:** Running on http://localhost:8000 (Uvicorn)
- **Frontend:** Running on http://localhost:3000 (Next.js 14.1.0)
- **Admin Key:** `admin123`

---

## Recommended Next Steps

1. **Fix Duplication:**
   - Add logging to deduplication logic to see what's happening
   - Check database for duplicate product entries
   - Verify UPC/ASIN fields are being set correctly

2. **Fix Affiliate Links:**
   - Add `console.log(product)` in ProductCard to see actual data
   - Verify API response includes `url` field
   - Check if `product.source === 'affiliate'` condition is true

3. **Fix Alert Error:**
   - Clear Next.js cache: `rm -rf .next` and restart
   - Try hard refresh in browser (Ctrl+Shift+R)
   - Replace `window.alert()` with a proper toast notification library

4. **Database Verification:**
   - Check `products` collection structure
   - Check `affiliateListings` collection structure
   - Verify relationships between collections

---

## Key Code Locations

- **Frontend Product Display:** `frontend/src/app/page.tsx` (lines 124-129)
- **Product Card Component:** `frontend/src/components/ProductCard.tsx`
- **Admin Dashboard:** `frontend/src/app/admin/dashboard/page.tsx`
- **Backend Products API:** `backend/app/main.py` - `get_products()` function (line 634)
- **Backend Best Price Logic:** `backend/app/main.py` - `get_best_price()` function
- **Deduplication Logic:** `backend/app/main.py` (lines 745-779)

---

## Environment Details

- **OS:** Windows
- **Python:** Located at C:\Users\csc20\AppData\Local\Programs\Python\Python311\python.exe
- **Node:** Running Next.js 14.1.0
- **Database:** Google Cloud Firestore (geocheapest-v2 project)
- **Credentials:** gcp_complete_key.json

---

## What Works

✅ Servers start successfully
✅ Backend API responds to requests
✅ Frontend loads without errors
✅ Products can be added via admin API
✅ ProductCard component code is correct

## What Doesn't Work

❌ Product duplication on frontend
❌ Affiliate links not redirecting
❌ Admin alert still throwing error

---

## Additional Context

The application is a TCG (Trading Card Game) marketplace that aggregates prices from multiple vendors. It supports:
- Internal Shopify vendor products
- External affiliate products (Amazon, eBay)
- "Buy Box" model showing cheapest price per product
- Admin portal for managing products and vendors

The core issue seems to be data flow between backend → frontend and proper deduplication logic.
