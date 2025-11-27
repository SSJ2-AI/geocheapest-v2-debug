# Amazon Affiliate Integration Setup Guide

## What You Need

To pull Amazon products with your affiliate code, you need:

1. **Amazon Associate Tag** (Your affiliate ID)
   - Example format: `yourname-20` or `geocheapest-20`
   - Get this from: https://affiliate-program.amazon.ca/

2. **RapidAPI Key** (To access Amazon product data)
   - Sign up at: https://rapidapi.com/
   - Subscribe to "Amazon Data Scraper" API
   - Copy your API key

## How to Configure

### Option 1: Update Deployment Script (For Cloud Run)

Edit `deploy_cloudbuild.ps1` and add these to the `$ENV_VARS` line:

```powershell
AMAZON_CA_AFFILIATE_TAG=your-affiliate-tag-20
RAPIDAPI_KEY=your-rapidapi-key-here
```

### Option 2: Local Testing (For Backend on localhost)

Create a `.env` file in the `backend/` directory:

```bash
AMAZON_CA_AFFILIATE_TAG=your-affiliate-tag-20
RAPIDAPI_KEY=your-rapidapi-key-here
AMAZON_MIN_RATING=4.0
AMAZON_MIN_REVIEWS=50
```

## How It Works

Once configured, the backend will:

1. **Automatically sync Amazon products** every 24 hours
2. **Filter products** by:
   - Minimum rating: 4.0 stars
   - Minimum reviews: 50
   - TCG-related keywords (Pokemon, Magic, Yu-Gi-Oh, etc.)
3. **Add your affiliate tag** to all Amazon product links
4. **Store products** in Firestore for display on the site

## Supported TCG Products

The system searches for:
- Pokemon TCG sealed booster boxes
- Magic: The Gathering sealed boosters
- Yu-Gi-Oh sealed booster boxes
- One Piece TCG sealed products
- Disney Lorcana sealed boosters
- Flesh and Blood sealed boosters
- Digimon sealed booster boxes
- Weiss Schwarz sealed boosters
- Dragon Ball Super sealed boosters
- Final Fantasy TCG sealed boosters
- Cardfight Vanguard sealed boosters

## Manual Sync

You can trigger a manual sync via the API:
```bash
POST /api/admin/amazon/sync
Headers: admin_key: your-admin-key
```

## Next Steps

**Please provide me with:**
1. Your Amazon Associate Tag
2. Your RapidAPI Key (or let me know if you need help getting one)

I'll update the configuration and redeploy the backend for you!
