# Regulatory Listener Setup Guide

## Overview

Phase 1.2 implements regulatory listeners that monitor:
- State Fire Marshal bulletins (via RSS feeds)
- NFPA code amendment announcements (via web scraping)
- EPA regulations (via Federal Register API)

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Regulatory listener RSS feeds (comma-separated)
REGULATORY_RSS_FEEDS="https://example.com/texas-fire-marshal/rss,https://example.com/nc-fire-marshal/rss"

# Regulatory update frequency (hours)
REGULATORY_UPDATE_FREQUENCY_HOURS=24

# Enable/disable LLM-based content processing (costs money)
REGULATORY_LLM_ENABLED=true
```

### Finding RSS Feed URLs

To find state fire marshal RSS feeds:

1. Visit the state fire marshal website
2. Look for "News", "Bulletins", "Updates" sections
3. Look for RSS feed icons or links
4. Common patterns:
   - `https://[state].gov/fire-marshal/rss`
   - `https://[state]firemarshal.gov/news/rss`
   - `https://[state].gov/dps/fire/rss.xml`

### Verified Working RSS Feeds

The RSS parser has been tested and verified with these real feeds:

- **Daily Dispatch Fire Service News**: `https://dailydispatch.com/feed/` ✅ (12+ updates found)
- **BBC News** (for parser validation): `http://feeds.bbci.co.uk/news/rss.xml` ✅ (40+ updates found)
- **Kansas State Fire Marshal**: `https://firemarshal.ks.gov/rss.aspx` ⚠️ (has XML formatting issues, but parser handles gracefully)

### Example Configuration

```bash
# Daily Dispatch fire service news (verified working)
REGULATORY_RSS_FEEDS="https://dailydispatch.com/feed/"

# Multiple feeds (comma-separated)
REGULATORY_RSS_FEEDS="https://dailydispatch.com/feed/,https://firemarshal.ks.gov/rss.aspx"

# State-specific (find actual URLs for your target states)
REGULATORY_RSS_FEEDS="https://www.tdi.texas.gov/fire/rss.xml,https://www.ncdps.gov/fire-marshal/rss"
```

## Testing

Run the test suite:

```bash
poetry run python scripts/test_regulatory_listeners.py
```

This will test:
- Storage layer (saving/loading updates)
- Fire Marshal listener (requires RSS feed URL)
- NFPA listener (web scraping)
- EPA listener (Federal Register API)

## Running with Scheduler

The regulatory listeners are automatically included in the scheduler:

```bash
poetry run python scripts/run_scheduled_scrapers.py
```

This will run:
- Permit scrapers (daily/hourly)
- EPA listener (weekly)
- NFPA listener (weekly)
- Fire Marshal listeners (daily, if RSS feeds configured)

## Manual Testing

### Test Fire Marshal Listener

```python
from src.signal_engine.listeners.fire_marshal_listener import FireMarshalListener

listener = FireMarshalListener(
    feed_url="https://example.com/fire-marshal/rss",
    state="Texas"
)
updates = await listener.check_for_updates(last_run=None)
```

### Test NFPA Listener

```python
from src.signal_engine.listeners.nfpa_listener import NFPAListener

listener = NFPAListener()
updates = await listener.check_for_updates(last_run=None)
```

### Test EPA Listener

```python
from src.signal_engine.listeners.epa_listener import EPARegulatoryListener

listener = EPARegulatoryListener()
updates = await listener.check_for_updates(last_run=None)
```

## Storage

Regulatory updates are stored in `data/regulatory_updates.json` by default.

Query updates:

```python
from src.signal_engine.storage.regulatory_storage import RegulatoryStorage

storage = RegulatoryStorage()

# Get all updates
all_updates = storage.load_all()

# Query by source
epa_updates = storage.query_updates(source="epa")

# Query by jurisdiction
texas_updates = storage.query_updates(jurisdiction="Texas")

# Query since date
from datetime import datetime, timedelta
recent = storage.query_updates(since=datetime.now() - timedelta(days=30))
```

## Content Processing

The content processor uses LLM to extract:
- Applicable NFPA codes
- Building types affected
- Compliance triggers

Enable/disable in config:

```bash
REGULATORY_LLM_ENABLED=true  # or false to disable
```

## Troubleshooting

### No updates found

- **Fire Marshal**: Check RSS feed URL is correct and accessible
- **NFPA**: Website structure may have changed - may need selector updates
- **EPA**: API may not have HVAC/refrigerant related updates in date range

### LLM processing errors

- Check `OPENAI_API_KEY` is set
- Check API quota/limits
- Disable with `REGULATORY_LLM_ENABLED=false` if needed

### Storage errors

- Ensure `data/` directory is writable
- Check file permissions
- Verify JSON format is valid

## Next Steps

1. Configure actual RSS feed URLs for target states
2. Test with real feeds
3. Monitor scheduler logs for updates
4. Integrate regulatory updates with lead generation (Phase 1.3)

