# Google Custom Search API Setup Guide

## Step 1: Create Custom Search Engine

1. Go to https://programmablesearchengine.google.com/
2. Click "Add" to create a new search engine
3. **Sites to search:** Leave blank or enter `*.gov` to search only government sites
4. **Name:** Give it a name (e.g., "Municipal Permit Portals")
5. Click "Create"

## Step 2: Get Search Engine ID (CX)

1. After creating the search engine, you'll see a page with your search engine details
2. Look for **"Search engine ID"** or **"CX"** parameter
3. It looks like: `012345678901234567890:abcdefghijk`
4. Copy this ID - you'll need it for `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`

## Step 3: Get API Key

1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable "Custom Search API"
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy the API key - this is your `GOOGLE_CUSTOM_SEARCH_API_KEY`

## Step 4: Add to .env

Add both values to your `.env` file:

```bash
# Phase 1.4: Google Custom Search API
GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_engine_id_here
```

## Step 5: Test

```bash
poetry run python scripts/phase1_4/test_portal_discovery.py
```

## Free Tier Limits

- **100 queries per day** (free tier)
- Each city search uses ~7 queries (one per search pattern)
- Can discover portals for ~14 cities per day on free tier
- For more, upgrade to paid tier ($5 per 1,000 queries)

## Troubleshooting

### "API key not valid"
- Check that API key is correct
- Ensure Custom Search API is enabled in Google Cloud Console

### "Search engine ID not found"
- Make sure you copied the CX parameter from the search engine page
- It's different from the API key

### "Quota exceeded"
- You've used your 100 free queries for the day
- Wait 24 hours or upgrade to paid tier
