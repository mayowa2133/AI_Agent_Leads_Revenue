# Phase 1 Study Guide: Complete Background Knowledge

**Purpose:** This guide provides comprehensive background knowledge required to fully understand and work with Phase 1 (Signal Engine) implementation, covering permit scraping, regulatory listening, and data enrichment.

**Estimated Study Time:** 4-6 weeks (depending on prior experience)

**Last Updated:** 2025-01-27

---

## Table of Contents

1. [Web Scraping Fundamentals](#1-web-scraping-fundamentals)
2. [Playwright Deep Dive](#2-playwright-deep-dive)
3. [RSS/Atom Feed Parsing](#3-rssatom-feed-parsing)
4. [Geocoding Services](#4-geocoding-services)
5. [Company Matching & Enrichment](#5-company-matching--enrichment)
6. [Email Finding APIs](#6-email-finding-apis)
7. [Job Scheduling](#7-job-scheduling)
8. [Data Storage Patterns](#8-data-storage-patterns)
9. [Error Handling & Resilience](#9-error-handling--resilience)
10. [API Integration Patterns](#10-api-integration-patterns)
11. [Data Modeling with Pydantic](#11-data-modeling-with-pydantic)
12. [Testing Strategies](#12-testing-strategies)
13. [Learning Path](#13-recommended-learning-path)
14. [Hands-On Exercises](#14-hands-on-exercises)

---

## 1. Web Scraping Fundamentals

### 1.1 What is Web Scraping?

**Definition:**
- Automated extraction of data from websites
- Programmatically accessing web pages and parsing HTML/JavaScript
- Converting unstructured web content into structured data

**Why Scrape?**
- No API available
- Need real-time data
- Cost-effective for bulk data collection
- Custom data extraction

**Challenges:**
- Websites change structure frequently
- Rate limiting and blocking
- JavaScript-rendered content
- Anti-bot measures (CAPTCHA, fingerprinting)

### 1.2 Scraping Approaches

**Static HTML Scraping:**
- Parse HTML directly (BeautifulSoup, lxml)
- Fast and simple
- Doesn't work for JavaScript-heavy sites

**Browser Automation:**
- Use real browsers (Playwright, Selenium)
- Handles JavaScript rendering
- More resource-intensive
- Better for complex sites

**API Scraping:**
- If site has API, use it instead
- More reliable and faster
- Respects rate limits

### 1.3 Ethical Scraping

**Best Practices:**
- **Respect robots.txt:** Check `robots.txt` before scraping
- **Rate Limiting:** Don't overwhelm servers (1 request/second minimum)
- **User-Agent:** Identify yourself with proper User-Agent
- **Terms of Service:** Read and respect ToS
- **Caching:** Cache results to avoid redundant requests
- **Error Handling:** Handle failures gracefully

**Legal Considerations:**
- Public data is generally legal to scrape
- Don't bypass authentication
- Don't violate copyright
- Check local laws and regulations

### 1.4 Scraper Architecture Patterns

**Base Scraper Pattern:**
```python
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    source: str  # Identifier for this scraper
    
    @abstractmethod
    async def scrape(self) -> list[Data]:
        """Full scrape (initial ingest)."""
    
    @abstractmethod
    async def check_for_updates(self, last_run: datetime) -> list[Data]:
        """Incremental scrape since last run."""
```

**Benefits:**
- Consistent interface across scrapers
- Easy to add new scrapers
- Shared retry/error handling logic
- Testable and maintainable

**Real Example from Code:**
```python
class BaseScraper(ABC):
    def __init__(self, *, max_retries: int = 3, base_delay_s: float = 1.0):
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
    
    async def _with_retries(self, coro_fn, *args, **kwargs):
        """Retry logic with exponential backoff."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(self.base_delay_s * (2 ** (attempt - 1)))
```

### 1.5 Retry Logic and Error Handling

**Exponential Backoff:**
```python
async def retry_with_backoff(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
            await asyncio.sleep(delay)
```

**Why Exponential Backoff?**
- Gives server time to recover
- Reduces load on failing services
- Standard practice for retry logic

**Error Types:**
- **Network Errors:** Connection timeout, DNS failure
- **HTTP Errors:** 404, 500, rate limit (429)
- **Parsing Errors:** HTML structure changed
- **Business Logic Errors:** Data validation failures

### 1.6 Rate Limiting

**Why Rate Limit?**
- Avoid overwhelming servers
- Prevent IP bans
- Be a good internet citizen
- Respect API/service limits

**Implementation:**
```python
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = datetime.min
    
    async def wait_if_needed(self):
        now = datetime.now()
        elapsed = (now - self.last_request).total_seconds()
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = datetime.now()
```

**Usage:**
```python
rate_limiter = RateLimiter(requests_per_second=1.0)

async def scrape_page(url):
    await rate_limiter.wait_if_needed()
    # Make request...
```

### 1.7 Deduplication

**Why Deduplicate?**
- Same data may appear multiple times
- Prevents duplicate processing
- Reduces storage costs

**Implementation:**
```python
def dedupe_permits(items: list[PermitData]) -> list[PermitData]:
    """Deduplicate by (source, permit_id)."""
    seen = {}
    for item in items:
        key = (item.source, item.permit_id)
        seen[key] = item  # Last write wins
    return list(seen.values())
```

### 1.8 Resources

- **Web Scraping Guide:** https://realpython.com/python-web-scraping-practical-introduction/
- **BeautifulSoup Docs:** https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Scrapy Framework:** https://scrapy.org/
- **Legal Guide:** https://www.eff.org/issues/coders/scraping-faq

---

## 2. Playwright Deep Dive

### 2.1 What is Playwright?

**Definition:**
- Browser automation library
- Supports Chromium, Firefox, WebKit
- Modern alternative to Selenium
- Better for JavaScript-heavy sites

**Why Playwright?**
- Handles JavaScript rendering
- Faster than Selenium
- Better API design
- Built-in waiting mechanisms
- Screenshot/PDF capabilities

### 2.2 Basic Playwright Usage

**Installation:**
```bash
pip install playwright
playwright install chromium
```

**Basic Example:**
```python
from playwright.async_api import async_playwright

async def scrape_example():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://example.com")
        title = await page.title()
        
        await browser.close()
        return title
```

### 2.3 Page Navigation

**Loading Pages:**
```python
# Basic navigation
await page.goto("https://example.com")

# Wait for specific state
await page.goto("https://example.com", wait_until="networkidle")
# Options: "load", "domcontentloaded", "networkidle", "commit"

# Set timeout
await page.goto("https://example.com", timeout=30000)
```

**Waiting Strategies:**
```python
# Wait for element to appear
await page.wait_for_selector("#content")

# Wait for network to be idle
await page.wait_for_load_state("networkidle")

# Wait for specific time
await page.wait_for_timeout(2000)  # 2 seconds

# Wait for navigation
await page.wait_for_url("**/success")
```

### 2.4 Element Selection

**Selectors:**
```python
# CSS selector
element = await page.query_selector(".class-name")
elements = await page.query_selector_all("div.items")

# Text-based
link = await page.query_selector('a:has-text("Click me")')

# XPath (if needed)
element = await page.query_selector("xpath=//div[@id='content']")
```

**Extracting Data:**
```python
# Text content
text = await element.inner_text()

# HTML content
html = await element.inner_html()

# Attributes
href = await element.get_attribute("href")
value = await element.get_attribute("value")

# Input values
input_value = await page.input_value("#input-id")
```

### 2.5 Form Interaction

**Filling Forms:**
```python
# Fill input
await page.fill("#username", "myusername")
await page.fill("#password", "mypassword")

# Select dropdown
await page.select_option("#country", "US")

# Check checkbox
await page.check("#agree-terms")

# Click button
await page.click("#submit-button")
```

**Real Example from Code:**
```python
# Mecklenburg scraper form interaction
search_input = await page.query_selector('#search-input')
if search_input:
    await search_input.fill("Fire")
    await page.click('#search-button')
    await page.wait_for_load_state("networkidle")
```

### 2.6 Handling Dynamic Content

**Waiting for Elements:**
```python
# Wait for element to be visible
await page.wait_for_selector(".results", state="visible")

# Wait for element count
await page.wait_for_function(
    "document.querySelectorAll('.item').length > 10"
)

# Wait for text to appear
await page.wait_for_selector("text=Results found")
```

**JavaScript Execution:**
```python
# Execute JavaScript
result = await page.evaluate("document.title")

# Pass arguments
result = await page.evaluate(
    "(element) => element.textContent",
    element
)

# Return complex objects
data = await page.evaluate("""
    () => ({
        title: document.title,
        items: Array.from(document.querySelectorAll('.item'))
            .map(el => el.textContent)
    })
""")
```

### 2.7 Real Example: Permit Scraper

**From Code:**
```python
class PlaywrightPermitScraper(BaseScraper):
    async def _scrape_full(self) -> list[PermitData]:
        from playwright.async_api import async_playwright
        
        permits: list[PermitData] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to search page
            await page.goto(self.start_url, wait_until="networkidle")
            
            # Find and click search link
            search_link = await page.query_selector('a:has-text("Search")')
            await search_link.click()
            await page.wait_for_load_state("networkidle")
            
            # Extract permit rows
            rows = await page.query_selector_all(self.selectors.row)
            for row in rows:
                permit_id = await (await row.query_selector(
                    self.selectors.permit_id
                )).inner_text()
                
                # Extract other fields...
                permits.append(PermitData(...))
            
            await browser.close()
        
        return permits
```

### 2.8 Best Practices

**1. Use Headless Mode:**
```python
browser = await p.chromium.launch(headless=True)  # Faster, no UI
```

**2. Set Timeouts:**
```python
page.set_default_timeout(30000)  # 30 seconds
```

**3. Handle Errors:**
```python
try:
    await page.goto(url)
except PlaywrightTimeoutError:
    logger.error(f"Timeout loading {url}")
    return []
```

**4. Clean Up:**
```python
try:
    # Scraping code...
finally:
    await browser.close()  # Always close browser
```

**5. Reuse Browser:**
```python
# For multiple pages, reuse browser
browser = await p.chromium.launch()
for url in urls:
    page = await browser.new_page()
    await page.goto(url)
    # ...
    await page.close()
await browser.close()
```

### 2.9 Resources

- **Playwright Docs:** https://playwright.dev/python/
- **Playwright Guide:** https://playwright.dev/python/docs/intro
- **API Reference:** https://playwright.dev/python/docs/api/class-playwright
- **Best Practices:** https://playwright.dev/python/docs/best-practices

---

## 3. RSS/Atom Feed Parsing

### 3.1 What are RSS/Atom Feeds?

**RSS (Really Simple Syndication):**
- XML format for web content syndication
- Standardized format for news/blog updates
- Widely supported by websites

**Atom:**
- Similar to RSS, more modern
- Better namespace support
- Also XML-based

**Why Use Feeds?**
- Structured, machine-readable
- No scraping needed
- Standardized format
- Incremental updates (check for new items)

### 3.2 Feed Structure

**RSS Example:**
```xml
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <link>https://example.com</link>
    <item>
      <title>Article Title</title>
      <link>https://example.com/article</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <description>Article content...</description>
    </item>
  </channel>
</rss>
```

**Atom Example:**
```xml
<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Feed</title>
  <entry>
    <title>Article Title</title>
    <link href="https://example.com/article"/>
    <published>2024-01-01T12:00:00Z</published>
    <content>Article content...</content>
  </entry>
</feed>
```

### 3.3 Parsing with feedparser

**Installation:**
```bash
pip install feedparser
```

**Basic Usage:**
```python
import feedparser

feed = feedparser.parse("https://example.com/feed.xml")

# Access feed metadata
print(feed.feed.title)
print(feed.feed.link)

# Access entries
for entry in feed.entries:
    print(entry.title)
    print(entry.link)
    print(entry.published)
    print(entry.summary)
```

**Real Example from Code:**
```python
class RSSFeedParser:
    def parse_feed(
        self,
        feed_url: str,
        source: str,
        source_name: str,
        last_run: datetime | None = None,
    ) -> list[RegulatoryUpdate]:
        updates: list[RegulatoryUpdate] = []
        
        # Parse feed
        feed = feedparser.parse(feed_url)
        
        # Check for parsing errors
        if feed.bozo:
            logger.warning(f"Feed parsing issues: {feed.bozo_exception}")
        
        # Process entries
        for entry in feed.entries:
            # Parse entry into RegulatoryUpdate
            update = self._parse_entry(entry, source, source_name)
            
            # Filter by date if last_run provided
            if last_run and update.published_date <= last_run:
                continue
            
            updates.append(update)
        
        return updates
```

### 3.4 Handling Feed Formats

**Feedparser Handles:**
- RSS 0.9x, 1.0, 2.0
- Atom 0.3, 1.0
- Mixed formats
- Malformed feeds (with warnings)

**Common Fields:**
```python
entry.title          # Entry title
entry.link           # Entry URL
entry.published      # Publication date (string)
entry.published_parsed  # Parsed date (time.struct_time)
entry.summary        # Summary/description
entry.content        # Full content (if available)
entry.author         # Author name
entry.tags           # Categories/tags
```

### 3.5 Date Parsing

**Challenge:**
- Dates come in various formats
- Need to normalize to datetime objects

**Solution:**
```python
from datetime import datetime
import feedparser

feed = feedparser.parse(url)

for entry in feed.entries:
    # Option 1: Use published_parsed (time.struct_time)
    if entry.published_parsed:
        pub_date = datetime(*entry.published_parsed[:6])
    
    # Option 2: Parse published string
    from dateutil import parser
    pub_date = parser.parse(entry.published)
```

**Real Example:**
```python
def _parse_entry(self, entry, source, source_name) -> RegulatoryUpdate:
    # Parse published date
    published_date = datetime.now(tz=timezone.utc)
    if entry.published_parsed:
        published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif hasattr(entry, 'published'):
        from dateutil import parser
        published_date = parser.parse(entry.published)
    
    # Create update
    return RegulatoryUpdate(
        update_id=self._generate_id(entry),
        source=source,
        source_name=source_name,
        title=entry.title,
        content=entry.summary or entry.content[0].value if entry.content else "",
        published_date=published_date,
        url=entry.link,
    )
```

### 3.6 Incremental Updates

**Strategy:**
- Track last run timestamp
- Only process entries published after last run
- Store last run per feed

**Implementation:**
```python
def parse_feed(self, feed_url: str, last_run: datetime | None = None):
    feed = feedparser.parse(feed_url)
    updates = []
    
    for entry in feed.entries:
        # Parse entry date
        entry_date = self._parse_date(entry.published)
        
        # Skip if before last run
        if last_run and entry_date <= last_run:
            continue
        
        updates.append(self._parse_entry(entry))
    
    return updates
```

### 3.7 Error Handling

**Common Issues:**
- Network errors (feed unavailable)
- Malformed XML
- Missing fields
- Encoding issues

**Handling:**
```python
try:
    feed = feedparser.parse(feed_url)
    
    if feed.bozo:
        logger.warning(f"Feed parsing issues: {feed.bozo_exception}")
    
    # Process entries with try/except
    for entry in feed.entries:
        try:
            update = self._parse_entry(entry)
            updates.append(update)
        except Exception as e:
            logger.warning(f"Error parsing entry: {e}")
            continue

except Exception as e:
    logger.error(f"Error parsing feed {feed_url}: {e}")
    raise
```

### 3.8 Resources

- **feedparser Docs:** https://feedparser.readthedocs.io/
- **RSS 2.0 Spec:** https://www.rssboard.org/rss-specification
- **Atom Spec:** https://tools.ietf.org/html/rfc4287

---

## 4. Geocoding Services

### 4.1 What is Geocoding?

**Definition:**
- Converting addresses to coordinates (latitude, longitude)
- Reverse geocoding: coordinates → address
- Extracting jurisdiction information (city, county, state)

**Why Geocode?**
- Location-based matching
- Map visualization
- Jurisdiction identification
- Distance calculations

### 4.2 Geocoding Services

**Nominatim (OpenStreetMap):**
- Free, no API key required
- Rate limited (1 request/second)
- Good accuracy
- Open data

**Google Geocoding API:**
- Paid service
- High accuracy
- Fast and reliable
- Requires API key

**Mapbox Geocoding:**
- Paid service (free tier available)
- Good for addresses
- Requires API key

**For Phase 1:** We use Nominatim (free, no API key)

### 4.3 Nominatim API

**Basic Usage:**
```python
import httpx

async def geocode(address: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()
        
        if data:
            result = data[0]
            return {
                "lat": float(result["lat"]),
                "lon": float(result["lon"]),
                "display_name": result["display_name"],
                "address": result.get("address", {})
            }
```

**Response Structure:**
```json
{
  "lat": "35.2271",
  "lon": "-80.8431",
  "display_name": "Charlotte, Mecklenburg County, North Carolina, USA",
  "address": {
    "city": "Charlotte",
    "county": "Mecklenburg County",
    "state": "North Carolina",
    "country": "United States"
  }
}
```

### 4.4 Real Implementation

**From Code:**
```python
class Geocoder:
    def __init__(self, *, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: dict[str, dict] = {}
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": "AORO-Enrichment/1.0"}
        )
    
    async def geocode(self, address: str) -> GeocodeResult:
        # Check cache
        if self.cache_enabled and address in self._cache:
            return GeocodeResult(**self._cache[address])
        
        # Call API
        url = f"{self.base_url}/search"
        params = {
            "q": address,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        
        resp = await self._client.get(url, params=params)
        data = resp.json()
        
        # Parse result
        result = data[0]
        geocode_result = GeocodeResult(
            latitude=float(result["lat"]),
            longitude=float(result["lon"]),
            formatted_address=result["display_name"],
            city=result["address"].get("city"),
            county=result["address"].get("county"),
            state=result["address"].get("state"),
            country=result["address"].get("country"),
        )
        
        # Cache result
        if self.cache_enabled:
            self._cache[address] = geocode_result.__dict__
        
        return geocode_result
```

### 4.5 Caching

**Why Cache?**
- Reduce API calls (rate limits)
- Faster responses
- Lower costs
- Better reliability

**Implementation:**
```python
class Geocoder:
    def __init__(self, cache_file: Path = "data/geocoding_cache.json"):
        self.cache_file = cache_file
        self._cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            return json.loads(self.cache_file.read_text())
        return {}
    
    def _save_cache(self):
        self.cache_file.write_text(json.dumps(self._cache, indent=2))
    
    async def geocode(self, address: str):
        # Check cache first
        if address in self._cache:
            return GeocodeResult(**self._cache[address])
        
        # Geocode and cache
        result = await self._geocode_api(address)
        self._cache[address] = result.__dict__
        self._save_cache()
        return result
```

### 4.6 Rate Limiting

**Nominatim Requirements:**
- 1 request per second maximum
- Must include User-Agent header
- Polite usage policy

**Implementation:**
```python
import asyncio
from datetime import datetime, timedelta

class RateLimitedGeocoder:
    def __init__(self):
        self.last_request = datetime.min
        self.min_interval = timedelta(seconds=1.0)
    
    async def geocode(self, address: str):
        # Wait if needed
        now = datetime.now()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep((self.min_interval - elapsed).total_seconds())
        
        self.last_request = datetime.now()
        return await self._geocode_api(address)
```

### 4.7 Error Handling

**Common Errors:**
- Address not found
- Network timeout
- Rate limit exceeded
- Invalid address format

**Handling:**
```python
async def geocode(self, address: str) -> GeocodeResult:
    try:
        resp = await self._client.get(url, params=params, timeout=10.0)
        
        if resp.status_code == 429:  # Rate limited
            await asyncio.sleep(2.0)
            return await self.geocode(address)  # Retry
        
        data = resp.json()
        if not data:
            raise GeocodingError(f"No results for: {address}")
        
        return self._parse_result(data[0])
    
    except httpx.TimeoutException:
        raise GeocodingError(f"Timeout geocoding: {address}")
    except Exception as e:
        raise GeocodingError(f"Geocoding failed: {e}")
```

### 4.8 Resources

- **Nominatim Docs:** https://nominatim.org/release-docs/latest/api/Overview/
- **OpenStreetMap:** https://www.openstreetmap.org/
- **Geocoding Guide:** https://developers.google.com/maps/documentation/geocoding/overview

---

## 5. Company Matching & Enrichment

### 5.1 Company Matching Strategy

**Goal:**
- Match permit applicant to real company
- Extract company domain/website
- Get company metadata (industry, size, etc.)

**Challenges:**
- Applicant name may be person or company
- Company names vary (legal vs. common name)
- Multiple companies with similar names
- Missing or incomplete data

### 5.2 Name Parsing

**Person vs Company Detection:**
```python
def _is_likely_person_name(name: str) -> bool:
    """Heuristic to determine if name is person vs company."""
    
    # Check for titles
    if re.search(r"^(mr|mrs|ms|dr|prof)\.?\s+", name.lower()):
        return True
    
    # Check for suffixes
    if re.search(r"\s+(jr|sr|ii|iii|iv)\.?$", name.lower()):
        return True
    
    # Check word count and company indicators
    words = name.split()
    if 2 <= len(words) <= 3:
        company_words = ["inc", "llc", "corp", "ltd", "company", "co"]
        if not any(word.lower() in name.lower() for word in company_words):
            return True
    
    return False
```

**Real Example from Code:**
```python
async def match_company(permit: PermitData, geocode_result: GeocodeResult) -> Company:
    # Strategy 1: Extract from applicant_name if not a person
    applicant_name = permit.applicant_name
    if applicant_name and not _is_likely_person_name(applicant_name):
        company_name = applicant_name.strip()
    else:
        # Fallback: extract from address or use placeholder
        company_name = "Unknown Company"
    
    # Strategy 2: Use Apollo to find domain
    apollo_client = ApolloClient(api_key=settings.apollo_api_key)
    apollo_company = await apollo_client.search_organization(company_name)
    
    if apollo_company:
        domain = apollo_company.website_url or apollo_company.primary_domain
    else:
        domain = None
    
    return Company(
        name=company_name,
        website=domain,
        # ... other fields
    )
```

### 5.3 Apollo Company Search

**Free Tier Endpoint:**
- `organizations/search` - Search companies by name
- Returns company data including domain
- No credits required (free tier)

**Usage:**
```python
class ApolloClient:
    async def search_organization(self, company_name: str) -> ApolloCompany | None:
        url = f"{self.base_url}/organizations/search"
        payload = {
            "q_organization_name": company_name,
            "page": 1,
            "per_page": 1,
        }
        
        resp = await self._client.post(url, json=payload, headers=self._headers)
        
        if resp.status_code == 200:
            data = resp.json()
            orgs = data.get("organizations", [])
            if orgs:
                org = orgs[0]
                return ApolloCompany(
                    name=org.get("name"),
                    website=org.get("website_url") or org.get("primary_domain"),
                    employee_count=org.get("estimated_num_employees"),
                    # ...
                )
        
        return None
```

### 5.4 Hybrid Strategy

**Phase 1.3 Approach:**
1. Extract company name from permit (applicant_name)
2. Use Apollo free tier to find domain
3. Use domain with Hunter.io to find email
4. Fallback gracefully if any step fails

**Flow:**
```
Permit → Extract Name → Apollo Search → Domain → Hunter.io → Email
```

**Benefits:**
- Uses free Apollo tier for domain lookup
- Uses Hunter.io free tier for email finding
- No paid services required
- Graceful degradation

### 5.5 Company Enrichment Pipeline

**Full Pipeline:**
```python
async def enrich_permit_to_lead(inputs: EnrichmentInputs) -> EnrichedLead:
    permit = inputs.permit
    
    # Step 1: Geocode address
    geocode_result = await geocode_address(permit.address)
    
    # Step 2: Match company
    company = await match_company(permit, geocode_result)
    
    # Step 3: Find decision maker
    decision_maker = await find_decision_maker(company, geocode_result)
    
    # Step 4: Match regulatory updates
    regulatory_matches = await match_regulatory_updates(permit, geocode_result)
    
    # Step 5: Build enriched lead
    return EnrichedLead(
        lead_id=str(uuid.uuid4()),
        tenant_id=inputs.tenant_id,
        company=company,
        decision_maker=decision_maker,
        permit=permit,
        compliance=ComplianceContext(
            applicable_codes=[],
            triggers=[u.title for u in regulatory_matches]
        ),
    )
```

### 5.6 Resources

- **Apollo API Docs:** https://apolloio.github.io/apollo-api-docs/
- **Company Matching Guide:** https://www.clearbit.com/resources/guides/company-enrichment

---

## 6. Email Finding APIs

### 6.1 Hunter.io API

**What is Hunter.io?**
- Email finding service
- Free tier: 50 credits/month
- API access for free users
- Email verification included

**Key Features:**
- Email finder (name + domain → email)
- Domain search (domain → emails)
- Email verification
- Confidence scoring

### 6.2 Hunter.io API Usage

**Email Finder:**
```python
class HunterClient:
    async def find_email(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        full_name: str | None = None,
        domain: str,
    ) -> HunterEmailResult | None:
        url = "https://api.hunter.io/v2/email-finder"
        params = {
            "api_key": self.api_key,
            "domain": domain,
        }
        
        if first_name and last_name:
            params["first_name"] = first_name
            params["last_name"] = last_name
        elif full_name:
            params["full_name"] = full_name
        
        resp = await self._client.get(url, params=params)
        data = resp.json()
        
        if data.get("data"):
            email_data = data["data"]
            return HunterEmailResult(
                email=email_data.get("email"),
                score=email_data.get("score"),  # 0-100 confidence
                sources=email_data.get("sources", []),
                first_name=email_data.get("first_name"),
                last_name=email_data.get("last_name"),
                domain=domain,
            )
        
        return None
```

**Credit System:**
- 1 credit per email found
- No credit if email not found
- Free tier: 50 credits/month
- Resets monthly

### 6.3 Credit-Safe Integration

**Safety Mechanisms:**
1. **Mock Client:** Test without spending credits
2. **Dry-Run Mode:** Skip real API calls
3. **Credit Limits:** Hard limit per run
4. **Error Handling:** Graceful degradation

**Implementation:**
```python
class ProviderManager:
    def __init__(self, *, dry_run: bool = True, max_credits: int = 3):
        self.dry_run = dry_run
        self.max_credits = max_credits
        self.credits_used = 0
    
    async def find_email(self, domain: str, name: str) -> EmailResult | None:
        # Check credit limit
        if self.credits_used >= self.max_credits:
            logger.warning("Credit limit reached, skipping email find")
            return None
        
        # Dry-run mode
        if self.dry_run:
            logger.info(f"[DRY RUN] Would find email for {name} @ {domain}")
            return MockEmailResult()
        
        # Real API call
        result = await self.hunter_client.find_email(domain=domain, full_name=name)
        
        if result and result.email:
            self.credits_used += 1
        
        return result
```

### 6.4 Apollo Email Finding

**Free Tier Limitations:**
- `organizations/search` - Works (finds domain)
- `organization_top_people` - Works (finds names)
- `mixed_people/search` - Limited (may not return emails)
- Email reveal - Not available on free tier

**Hybrid Strategy:**
1. Use Apollo to find domain (free)
2. Use Apollo to find decision maker names (free)
3. Use Hunter.io to find emails (1 credit per email)

### 6.5 Provider Abstraction

**ProviderManager Pattern:**
```python
class ProviderManager:
    """Manages multiple enrichment providers with fallback logic."""
    
    def __init__(self, priority: str = "auto"):
        self.priority = priority
        self.hunter = HunterClient(api_key=settings.hunter_api_key)
        self.apollo = ApolloClient(api_key=settings.apollo_api_key)
    
    async def find_email(self, domain: str, name: str) -> EmailResult | None:
        # Try Hunter.io first (free tier)
        if self.priority in ["hunter", "auto"]:
            result = await self.hunter.find_email(domain=domain, full_name=name)
            if result and result.email:
                return result
        
        # Fallback to Apollo (if available)
        if self.priority in ["apollo", "auto"]:
            # Apollo email finding logic...
            pass
        
        return None
```

### 6.6 Resources

- **Hunter.io Docs:** https://hunter.io/api-documentation
- **Apollo API Docs:** https://apolloio.github.io/apollo-api-docs/
- **Email Finding Guide:** https://hunter.io/resources/email-finder-api

---

## 7. Job Scheduling

### 7.1 What is Job Scheduling?

**Definition:**
- Running tasks at specific times or intervals
- Automated execution of scrapers/listeners
- Persistent scheduling across restarts

**Use Cases:**
- Daily permit scraping
- Hourly regulatory updates
- Weekly data cleanup
- Periodic enrichment runs

### 7.2 APScheduler

**What is APScheduler?**
- Advanced Python Scheduler
- Supports cron-like scheduling
- Async support
- Multiple job stores

**Installation:**
```bash
pip install apscheduler
```

### 7.3 Basic Usage

**Simple Scheduler:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()

# Schedule job to run every hour
scheduler.add_job(
    my_function,
    trigger=IntervalTrigger(hours=1)
)

scheduler.start()
```

**Cron-Like Scheduling:**
```python
from apscheduler.triggers.cron import CronTrigger

# Run daily at 9 AM
scheduler.add_job(
    my_function,
    trigger=CronTrigger(hour=9, minute=0)
)

# Run every weekday at 8 AM
scheduler.add_job(
    my_function,
    trigger=CronTrigger(day_of_week="mon-fri", hour=8, minute=0)
)
```

### 7.4 Real Implementation

**From Code:**
```python
class ScraperScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.last_run_file = Path("data/scraper_last_runs.json")
    
    def setup_jobs(self):
        # Schedule permit scraper (daily at 6 AM)
        self.scheduler.add_job(
            self.run_scraper_job,
            trigger=CronTrigger(hour=6, minute=0),
            args=["mecklenburg", MecklenburgPermitScraper(), "tenant-1"],
            id="mecklenburg_daily"
        )
        
        # Schedule regulatory listener (every 12 hours)
        self.scheduler.add_job(
            self.run_regulatory_listener_job,
            trigger=IntervalTrigger(hours=12),
            args=["fire_marshal", FireMarshalListener(), "tenant-1"],
            id="fire_marshal_listener"
        )
    
    def start(self):
        self.scheduler.start()
    
    def shutdown(self):
        self.scheduler.shutdown()
```

### 7.5 Persistence

**Last Run Tracking:**
```python
class ScraperScheduler:
    def _get_last_run(self, job_id: str, tenant_id: str) -> datetime | None:
        """Load last run timestamp from file."""
        if not self.last_run_file.exists():
            return None
        
        data = json.loads(self.last_run_file.read_text())
        key = f"{job_id}_{tenant_id}"
        last_run_str = data.get(key)
        
        if last_run_str:
            return datetime.fromisoformat(last_run_str)
        return None
    
    def _save_last_run(self, job_id: str, tenant_id: str, timestamp: datetime):
        """Save last run timestamp to file."""
        if not self.last_run_file.exists():
            data = {}
        else:
            data = json.loads(self.last_run_file.read_text())
        
        key = f"{job_id}_{tenant_id}"
        data[key] = timestamp.isoformat()
        
        self.last_run_file.write_text(json.dumps(data, indent=2))
```

### 7.6 Error Handling

**Job Error Handling:**
```python
async def run_scraper_job(self, scraper_name: str, scraper: BaseScraper, tenant_id: str):
    try:
        logger.info(f"Starting scraper: {scraper_name}")
        
        # Get last run
        last_run = self._get_last_run(scraper_name, tenant_id)
        
        # Run scraper
        permits = await scraper.check_for_updates(last_run)
        logger.info(f"Found {len(permits)} permits")
        
        # Save last run
        self._save_last_run(scraper_name, tenant_id, datetime.now())
        
    except Exception as e:
        logger.error(f"Scraper {scraper_name} failed: {e}", exc_info=True)
        # Don't update last_run on error - will retry from same point
```

### 7.7 Resources

- **APScheduler Docs:** https://apscheduler.readthedocs.io/
- **Cron Guide:** https://crontab.guru/
- **Scheduling Patterns:** https://apscheduler.readthedocs.io/en/stable/userguide.html

---

## 8. Data Storage Patterns

### 8.1 Storage Options

**JSON File Storage (MVP):**
- Simple, no database setup
- Easy to inspect and debug
- Good for small datasets
- Not scalable for production

**SQLite:**
- File-based database
- SQL queries
- Better for larger datasets
- Still single-file

**PostgreSQL/MySQL:**
- Full-featured databases
- Multi-user support
- Production-ready
- Requires setup

**For Phase 1:** JSON file storage (simple, works for MVP)

### 8.2 JSON Storage Pattern

**Basic Structure:**
```python
class LeadStorage:
    def __init__(self, storage_file: Path = "data/enriched_leads.json"):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> dict:
        """Load all leads from file."""
        if not self.storage_file.exists():
            return {}
        
        content = self.storage_file.read_text()
        return json.loads(content)
    
    def _save(self, data: dict):
        """Save leads to file."""
        self.storage_file.write_text(json.dumps(data, indent=2, default=str))
    
    def save_lead(self, lead: EnrichedLead):
        """Save a single lead."""
        data = self._load()
        data[lead.lead_id] = lead.model_dump()
        self._save(data)
    
    def load_all(self) -> list[EnrichedLead]:
        """Load all leads."""
        data = self._load()
        return [EnrichedLead(**lead_data) for lead_data in data.values()]
```

### 8.3 Deduplication

**Strategy:**
- Use unique key (lead_id, permit_id)
- Last write wins
- Check before saving

**Implementation:**
```python
def save_lead(self, lead: EnrichedLead):
    data = self._load()
    
    # Deduplicate by lead_id
    data[lead.lead_id] = lead.model_dump()
    
    self._save(data)
```

### 8.4 Querying

**Simple Queries:**
```python
def get_by_tenant(self, tenant_id: str) -> list[EnrichedLead]:
    """Get all leads for a tenant."""
    all_leads = self.load_all()
    return [lead for lead in all_leads if lead.tenant_id == tenant_id]

def get_by_permit_id(self, permit_id: str) -> EnrichedLead | None:
    """Get lead by permit ID."""
    all_leads = self.load_all()
    for lead in all_leads:
        if lead.permit.permit_id == permit_id:
            return lead
    return None

def get_recent(self, days: int = 7) -> list[EnrichedLead]:
    """Get leads created in last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    all_leads = self.load_all()
    return [lead for lead in all_leads if lead.created_at >= cutoff]
```

### 8.5 Resources

- **JSON in Python:** https://docs.python.org/3/library/json.html
- **SQLite Tutorial:** https://www.sqlitetutorial.net/
- **Data Storage Patterns:** https://realpython.com/python-json/

---

## 9. Error Handling & Resilience

### 9.1 Error Types

**Network Errors:**
- Connection timeout
- DNS failure
- HTTP errors (404, 500, 429)

**Parsing Errors:**
- HTML structure changed
- Missing expected fields
- Invalid data format

**Business Logic Errors:**
- Data validation failures
- Missing required fields
- Invalid state transitions

### 9.2 Retry Logic

**Exponential Backoff:**
```python
async def retry_with_backoff(operation, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
            await asyncio.sleep(delay)
    
    raise Exception("Max retries exceeded")
```

**Real Example:**
```python
class BaseScraper:
    async def _with_retries(self, coro_fn, *args, **kwargs):
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.base_delay_s * (2 ** (attempt - 1)))
        
        raise ScraperError(f"Failed after {self.max_retries} retries") from last_exc
```

### 9.3 Graceful Degradation

**Strategy:**
- Continue with partial data
- Log warnings instead of failing
- Return empty/default values
- Don't break entire pipeline

**Example:**
```python
async def enrich_permit_to_lead(inputs: EnrichmentInputs) -> EnrichedLead:
    # Try geocoding, but continue if it fails
    try:
        geocode_result = await geocode_address(permit.address)
    except Exception as e:
        logger.warning(f"Geocoding failed: {e}")
        geocode_result = None
    
    # Try company matching, use placeholder if fails
    try:
        company = await match_company(permit, geocode_result)
    except Exception as e:
        logger.warning(f"Company matching failed: {e}")
        company = Company(name="Unknown Company")
    
    # Continue with enrichment even if some steps failed
    return EnrichedLead(...)
```

### 9.4 Logging

**Structured Logging:**
```python
import logging

logger = logging.getLogger(__name__)

# Info for normal operations
logger.info(f"Scraped {len(permits)} permits")

# Warning for recoverable issues
logger.warning(f"Geocoding failed for address: {address}")

# Error for failures
logger.error(f"Scraper failed: {e}", exc_info=True)

# Debug for detailed information
logger.debug(f"Parsed entry: {entry.title}")
```

### 9.5 Resources

- **Python Logging:** https://docs.python.org/3/library/logging.html
- **Error Handling:** https://realpython.com/python-exceptions/
- **Resilience Patterns:** https://docs.microsoft.com/en-us/azure/architecture/patterns/category/resilience

---

## 10. API Integration Patterns

### 10.1 HTTP Client Usage

**HTTPX (Async HTTP Client):**
```python
import httpx

async def call_api(url: str, data: dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=data)
        response.raise_for_status()
        return response.json()
```

**Headers:**
```python
headers = {
    "X-Api-Key": api_key,
    "Content-Type": "application/json",
    "User-Agent": "AORO-Enrichment/1.0"
}

response = await client.get(url, headers=headers)
```

### 10.2 Error Handling

**HTTP Errors:**
```python
try:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:  # Rate limited
        await asyncio.sleep(2.0)
        return await call_api(url)  # Retry
    raise
except httpx.TimeoutException:
    logger.error("Request timeout")
    return None
```

### 10.3 Rate Limiting

**Client-Side Rate Limiting:**
```python
from datetime import datetime, timedelta

class RateLimitedClient:
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = timedelta(seconds=1.0 / requests_per_second)
        self.last_request = datetime.min
    
    async def get(self, url: str):
        now = datetime.now()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep((self.min_interval - elapsed).total_seconds())
        
        self.last_request = datetime.now()
        return await self._client.get(url)
```

### 10.4 Resources

- **HTTPX Docs:** https://www.python-httpx.org/
- **API Integration:** https://realpython.com/python-requests/

---

## 11. Data Modeling with Pydantic

### 11.1 Pydantic Basics

**What is Pydantic?**
- Data validation library
- Type checking at runtime
- Automatic serialization/deserialization
- Great for API models

**Basic Model:**
```python
from pydantic import BaseModel, Field
from datetime import datetime

class PermitData(BaseModel):
    source: str
    permit_id: str
    permit_type: str
    address: str
    building_type: str | None = None
    status: str
    applicant_name: str | None = None
    issued_date: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 11.2 Field Validation

**Validation:**
```python
from pydantic import BaseModel, Field, validator

class Company(BaseModel):
    name: str = Field(..., min_length=1)
    domain: str | None = None
    employee_count: int | None = Field(None, ge=0)  # >= 0
    
    @validator('domain')
    def validate_domain(cls, v):
        if v and not v.startswith('http'):
            return f"https://{v}"
        return v
```

### 11.3 Nested Models

**Composition:**
```python
class Location(BaseModel):
    address: str
    city: str | None
    state: str | None

class Company(BaseModel):
    name: str
    location: Location | None
    domain: str | None

class EnrichedLead(BaseModel):
    lead_id: str
    company: Company
    permit: PermitData
    decision_maker: DecisionMaker | None
```

### 11.4 Serialization

**To Dict:**
```python
lead = EnrichedLead(...)
data = lead.model_dump()  # Convert to dict
json_str = lead.model_dump_json()  # Convert to JSON string
```

**From Dict:**
```python
data = {...}
lead = EnrichedLead(**data)  # Create from dict

json_str = '{"lead_id": "123", ...}'
lead = EnrichedLead.model_validate_json(json_str)  # From JSON
```

### 11.5 Resources

- **Pydantic Docs:** https://docs.pydantic.dev/
- **Data Validation:** https://docs.pydantic.dev/usage/validators/

---

## 12. Testing Strategies

### 12.1 Unit Testing

**Testing Scrapers:**
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_scraper():
    scraper = MecklenburgPermitScraper(search_value="Fire")
    
    # Mock Playwright
    with patch('playwright.async_api.async_playwright') as mock_playwright:
        # Setup mocks...
        permits = await scraper.scrape()
        
        assert len(permits) > 0
        assert all(p.source == "mecklenburg" for p in permits)
```

### 12.2 Integration Testing

**End-to-End Tests:**
```python
@pytest.mark.asyncio
async def test_enrichment_pipeline():
    permit = PermitData(
        source="test",
        permit_id="123",
        permit_type="Fire Alarm",
        address="123 Main St, Charlotte, NC",
        status="Issued"
    )
    
    inputs = EnrichmentInputs(tenant_id="test", permit=permit)
    lead = await enrich_permit_to_lead(inputs)
    
    assert lead.company.name is not None
    assert lead.permit.permit_id == "123"
```

### 12.3 Mocking External APIs

**Mock HTTP Calls:**
```python
from unittest.mock import patch
import httpx

@pytest.mark.asyncio
async def test_geocoding():
    mock_response = {
        "lat": "35.2271",
        "lon": "-80.8431",
        "display_name": "Charlotte, NC"
    }
    
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.json.return_value = [mock_response]
        
        result = await geocode_address("123 Main St, Charlotte, NC")
        assert result.latitude == 35.2271
```

### 12.4 Resources

- **pytest Docs:** https://docs.pytest.org/
- **Testing Guide:** https://realpython.com/pytest-python-testing/

---

## 13. Recommended Learning Path

### Week 1: Web Scraping Foundation
- [ ] Web scraping fundamentals
- [ ] Playwright basics
- [ ] HTML/CSS selectors
- [ ] Error handling patterns

**Deliverable:** Build a simple scraper for a public website

### Week 2: Advanced Scraping
- [ ] Playwright advanced features
- [ ] Form interaction
- [ ] Dynamic content handling
- [ ] Retry logic and resilience

**Deliverable:** Build a scraper that handles forms and dynamic content

### Week 3: Data Processing
- [ ] RSS/Atom feed parsing
- [ ] Geocoding services
- [ ] Data validation with Pydantic
- [ ] JSON storage patterns

**Deliverable:** Build a feed parser and geocoding service

### Week 4: API Integration
- [ ] HTTPX async client
- [ ] API integration patterns
- [ ] Rate limiting
- [ ] Error handling

**Deliverable:** Integrate with Hunter.io and Apollo APIs

### Week 5: Enrichment Pipeline
- [ ] Company matching logic
- [ ] Email finding strategies
- [ ] Data enrichment patterns
- [ ] Pipeline orchestration

**Deliverable:** Build a complete enrichment pipeline

### Week 6: Scheduling & Production
- [ ] APScheduler
- [ ] Job persistence
- [ ] Production patterns
- [ ] Testing strategies

**Deliverable:** Build a scheduled job system

---

## 14. Hands-On Exercises

### Exercise 1: Simple Web Scraper

**Goal:** Build a basic Playwright scraper.

**Steps:**
1. Install Playwright
2. Scrape a simple website (e.g., news site)
3. Extract titles and links
4. Save to JSON file

### Exercise 2: Form-Based Scraper

**Goal:** Build a scraper that interacts with forms.

**Steps:**
1. Find a website with a search form
2. Fill in search form
3. Extract results
4. Handle pagination

### Exercise 3: RSS Feed Parser

**Goal:** Parse RSS feeds and extract updates.

**Steps:**
1. Find an RSS feed URL
2. Parse with feedparser
3. Extract entries
4. Filter by date
5. Save to JSON

### Exercise 4: Geocoding Service

**Goal:** Build a geocoding service with caching.

**Steps:**
1. Use Nominatim API
2. Implement caching
3. Add rate limiting
4. Handle errors gracefully

### Exercise 5: Company Enrichment

**Goal:** Build a company matching service.

**Steps:**
1. Parse company names from text
2. Use Apollo API to find domains
3. Extract company metadata
4. Build Company objects

### Exercise 6: Email Finding

**Goal:** Integrate Hunter.io email finding.

**Steps:**
1. Set up Hunter.io account
2. Implement email finder
3. Add credit tracking
4. Implement dry-run mode
5. Test with real data

### Exercise 7: Full Enrichment Pipeline

**Goal:** Build complete Phase 1.3 pipeline.

**Steps:**
1. Geocode addresses
2. Match companies
3. Find decision makers
4. Match regulatory updates
5. Build EnrichedLead objects
6. Save to storage

### Exercise 8: Scheduled Jobs

**Goal:** Build a job scheduler.

**Steps:**
1. Set up APScheduler
2. Schedule scraper jobs
3. Track last run times
4. Handle errors
5. Test persistence

---

## Additional Resources

### Documentation
- **Playwright:** https://playwright.dev/python/
- **feedparser:** https://feedparser.readthedocs.io/
- **HTTPX:** https://www.python-httpx.org/
- **APScheduler:** https://apscheduler.readthedocs.io/
- **Pydantic:** https://docs.pydantic.dev/

### Tutorials
- **Web Scraping:** https://realpython.com/python-web-scraping-practical-introduction/
- **Async Python:** https://realpython.com/async-io-python/
- **API Integration:** https://realpython.com/python-requests/

### Tools
- **Playwright Inspector:** Built-in debugging tool
- **Postman:** API testing
- **JSON Formatter:** Validate JSON

---

## Study Tips

1. **Start Simple:** Begin with basic examples, then add complexity
2. **Read the Code:** Study the actual Phase 1 implementation
3. **Experiment:** Try modifying scrapers to see what happens
4. **Test Everything:** Write tests as you learn
5. **Handle Errors:** Always think about error cases
6. **Be Polite:** Respect rate limits and robots.txt
7. **Cache Aggressively:** Reduce API calls and improve performance

---

**Good luck with your studies! This guide should give you a solid foundation for understanding Phase 1.**

