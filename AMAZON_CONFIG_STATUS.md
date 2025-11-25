# Amazon Affiliate Configuration Status

## ✅ Configured
- **Amazon Associate Tag**: `geocheapest-20`
- **Minimum Rating Filter**: 4.0 stars
- **Minimum Reviews Filter**: 50 reviews

## ⏳ Pending
- **RapidAPI Key**: Not yet configured

## How to Add RapidAPI Key

### Option 1: Via RapidAPI Website
1. Log in to https://rapidapi.com/
2. Go to "My Apps" or "Dashboard"
3. Find your API key (usually under "Security" or "API Keys")
4. Copy the key

### Option 2: Subscribe to Amazon Data Scraper API
1. Go to: https://rapidapi.com/letscrape-6bRBa3QguO5/api/real-time-amazon-data
2. Click "Subscribe to Test"
3. Choose a plan (Free tier available)
4. Copy your X-RapidAPI-Key from the code snippets

### Then Update Deployment
Once you have the RapidAPI key, run:
```powershell
# Edit deploy_cloudbuild.ps1 and add to $ENV_VARS:
RAPIDAPI_KEY=your-actual-key-here
```

## Current Status
Your Amazon affiliate tag is configured in the deployment script. The backend will use `geocheapest-20` for all Amazon product links. 

To enable automatic product syncing from Amazon, you just need to add the RapidAPI key and redeploy.
