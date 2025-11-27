# Manual Amazon Product Import Guide

## Quick Process for Adding Amazon.ca TCG Products

Since you're already signed into Amazon.ca with your affiliate account, here's how to manually add products:

### Step 1: Search for TCG Products on Amazon.ca
Search terms to use:
- "Pokemon TCG booster box sealed"
- "Magic The Gathering booster box sealed"
- "Yu-Gi-Oh booster box sealed"
- "One Piece TCG sealed"
- "Lorcana booster box sealed"

### Step 2: Filter for Quality Products
Look for:
- ✅ **4+ star ratings**
- ✅ **50+ reviews**
- ✅ **In Stock** status
- ✅ **Vetted vendors**: Amazon.ca, 401 Games, Hobbiesville, Dolly's Toys and Games, Game Shack, Red Nails II

### Step 3: Get Your Affiliate Link
For each product:
1. Click the product
2. Use Amazon Associates SiteStripe toolbar (top of page)
3. Click "Get Link" → "Full Link"
4. Copy the affiliate link (includes `tag=geocheapest-20`)

### Step 4: Add to GeoCheapest Database
Use the Super Admin portal (being created) to add products with:
- Product name
- ASIN (from URL: `/dp/ASIN/`)
- Price
- Affiliate link
- Image URL
- Vendor name
- Rating & review count
- Stock status

## Automated Alternative (Future)
Once you provide the RapidAPI key, the system will automatically:
- Search Amazon.ca every 24 hours
- Filter by rating/reviews
- Extract product data
- Add affiliate tag
- Store in database

For now, manual import via Super Admin portal is the fastest way to get products live on your site.
