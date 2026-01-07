# Verified RSS Feeds for Regulatory Listeners

This document lists RSS feeds that have been tested and verified to work with the regulatory listener system.

## ✅ Verified Working Feeds

### Fire Service News Feeds

1. **Daily Dispatch Fire Service News**
   - URL: `https://dailydispatch.com/feed/`
   - Status: ✅ **VERIFIED** - Successfully parsed 12+ updates
   - Content: Fire service news, incidents, and updates
   - Last Tested: 2026-01-06
   - Notes: Good for testing and general fire service monitoring

2. **BBC News** (for parser validation)
   - URL: `http://feeds.bbci.co.uk/news/rss.xml`
   - Status: ✅ **VERIFIED** - Successfully parsed 40+ updates
   - Content: General news (not fire-specific)
   - Last Tested: 2026-01-06
   - Notes: Used to validate RSS parser functionality

### State Fire Marshal Feeds

1. **Kansas State Fire Marshal**
   - URL: `https://firemarshal.ks.gov/rss.aspx`
   - Status: ⚠️ **PARTIAL** - Feed has XML formatting issues
   - Content: Kansas State Fire Marshal bulletins
   - Last Tested: 2026-01-06
   - Notes: Parser handles gracefully but may return 0 updates due to XML issues

## 🔍 Finding State Fire Marshal RSS Feeds

To find RSS feeds for specific states:

1. **Visit State Fire Marshal Website**
   - Look for "News", "Bulletins", "Updates", or "Press Releases" sections
   - Check for RSS feed icons (📡) or links

2. **Check Page Source**
   - Look for `<link rel="alternate" type="application/rss+xml">` tags
   - Common patterns:
     - `https://[state].gov/fire-marshal/rss`
     - `https://[state]firemarshal.gov/news/rss`
     - `https://[state].gov/dps/fire/rss.xml`

3. **Use RSS Discovery Tools**
   - RSS.app feed finder
   - Browser extensions for RSS discovery

## 📝 Test Results

### Daily Dispatch Feed Test
```
✅ Successfully parsed 12 updates
Sample titles:
- Semi hauling hay catches fire in Box Elder County
- VIDEOS: Firefighter hit by falling AC unit, 5 others hurt in Queens
- Massive fire destroys 120-year-old Hollywood motel
```

### BBC News Feed Test (Parser Validation)
```
✅ Successfully parsed 40 updates
Parser correctly handles:
- Title extraction
- Date parsing
- URL extraction
- Content/summary extraction
```

## 🧪 Testing Your Own Feeds

To test a new RSS feed:

```python
from src.signal_engine.listeners.rss_parser import RSSFeedParser

parser = RSSFeedParser()
updates = parser.parse_feed(
    feed_url="YOUR_FEED_URL_HERE",
    source="test",
    source_name="Test Feed",
    jurisdiction=None
)
print(f"Found {len(updates)} updates")
```

## ⚠️ Common Issues

1. **XML Formatting Errors**
   - Some feeds have malformed XML
   - Parser handles gracefully but may return 0 updates
   - Check feed with W3C Feed Validator: https://validator.w3.org/feed/

2. **Empty Feeds**
   - Feed may be valid but have no recent updates
   - Check feed URL directly in browser

3. **Authentication Required**
   - Some feeds may require authentication
   - Not currently supported (would need enhancement)

## 📚 Resources

- **RSS Feed Validator**: https://validator.w3.org/feed/
- **RSS Feed Finder**: https://rss.app/blog/how-to-find-and-use-a-native-rss-feed
- **Daily Dispatch RSS Feeds**: https://dailydispatch.com/rss-feeds/

