# Permit Discovery Expansion Plan: Free Nationwide Coverage

**Date:** January 13, 2026  
**Status:** Planning  
**Goal:** Expand permit discovery from 2 cities to 50+ cities using free methods  
**Master Plan Position:** Phase 1.4 (Extension of Phase 1.1: Permit Scraper Framework)  
**See Also:** [`permit_discovery_expansion_integration.md`](permit_discovery_expansion_integration.md) for integration details

---

## Executive Summary

This plan outlines a strategy to expand permit discovery from the current 2 municipalities (Mecklenburg County, San Antonio) to 50+ cities nationwide using **100% free methods**. The approach combines automated portal discovery, scraper standardization, and open data API integration to achieve comprehensive coverage without commercial API costs.

**Current State:**
- ✅ 2 municipalities (Mecklenburg County, San Antonio)
- ✅ Working scrapers with applicant extraction
- ✅ Data quality issues (missing applicant names, unclear addresses)

**Target State:**
- 🎯 50+ municipalities with active permit scraping
- 🎯 Standardized scraper framework for common systems
- 🎯 Open data API integration for structured data
- 🎯 Automated portal discovery pipeline
- 🎯 Data quality validation and filtering

**Cost:** $0 (100% free using public resources)

---

## Current State Assessment

### What We Have
1. **Working Scrapers:**
   - Mecklenburg County (WebPermit portal)
   - San Antonio (Accela Fire Module)
   - Playwright-based framework
   - Applicant extraction capability

2. **Infrastructure:**
   - Scheduled job runner (APScheduler)
   - Lead storage system
   - Enrichment pipeline
   - Error handling and retries

### What We're Missing
1. **Coverage:** Only 2 cities
2. **Portal Discovery:** Manual process
3. **Scraper Reusability:** Each city requires custom code
4. **Data Quality:** No pre-filtering before enrichment
5. **System Recognition:** No automated detection of portal types

### Problems Identified
1. **Low-Quality Permits:** Missing applicant names, unclear addresses
2. **Limited Coverage:** Can't scale manually
3. **No Standardization:** Each scraper is custom-built
4. **Wasted Credits:** Enriching low-quality permits

---

## Goals and Objectives

### Primary Goals
1. **Expand Coverage:** 50+ cities within 6 months
2. **Zero Cost:** Use only free public resources
3. **High Quality:** Filter permits before enrichment
4. **Automated Discovery:** Find new portals automatically
5. **Standardized Framework:** Reusable scrapers for common systems

### Success Metrics
- **Coverage:** 50+ cities with active scrapers
- **Permit Volume:** 1,000+ permits/month
- **Data Quality:** 70%+ permits with applicant names
- **Enrichment Efficiency:** 60%+ leads with decision maker emails
- **Cost:** $0/month (free methods only)

---

## Strategy Overview

### Three-Pronged Approach

1. **Automated Portal Discovery** (Phase 1)
   - Use Google Custom Search API (free tier)
   - Discover municipal permit portals
   - Identify portal system types (Accela, ViewPoint, etc.)

2. **Scraper Standardization** (Phase 2)
   - Build reusable scrapers for common systems
   - Create scraper registry/factory pattern
   - Template-based scraper generation

3. **Open Data Integration** (Phase 3)
   - Integrate with municipal open data APIs
   - Use Socrata/CKAN APIs
   - Structured data (easier than scraping)

---

## Phase 1: Automated Portal Discovery (Weeks 1-2)

### Objective
Automatically discover municipal permit portals using Google Custom Search API.

### Implementation Steps

#### Step 1.1: Google Custom Search Setup
**Cost:** Free (100 queries/day on free tier)

1. **Create Google Custom Search Engine:**
   - Go to https://programmablesearchengine.google.com/
   - Create custom search engine
   - Configure to search only `.gov` domains
   - Get API key and Search Engine ID

2. **Add to Configuration:**
   ```python
   # src/core/config.py
   GOOGLE_CUSTOM_SEARCH_API_KEY: str | None = None
   GOOGLE_CUSTOM_SEARCH_ENGINE_ID: str | None = None
   ```

3. **Create Discovery Service:**
   ```python
   # src/signal_engine/discovery/portal_discovery.py
   class PortalDiscoveryService:
       async def discover_portals(
           self, 
           cities: list[str],
           max_results_per_city: int = 10
       ) -> list[PortalInfo]:
           """
           Discover permit portals for given cities.
           
           Returns:
               List of PortalInfo with:
               - URL
               - Portal system type (Accela, ViewPoint, etc.)
               - City name
               - Confidence score
           """
   ```

#### Step 1.2: Search Query Strategy
**Queries to Use:**
```python
SEARCH_QUERIES = [
    "building permit search {city}",
    "permit database {city}",
    "building permits {city} site:.gov",
    "accela {city}",
    "viewpoint {city}",
    "permit portal {city}",
    "construction permits {city}",
]
```

**City List (Top 50 by Population):**
- New York, Los Angeles, Chicago, Houston, Phoenix, Philadelphia, San Antonio, San Diego, Dallas, San Jose
- Austin, Jacksonville, Fort Worth, Columbus, Charlotte, San Francisco, Indianapolis, Seattle, Denver, Washington
- Boston, El Paso, Nashville, Detroit, Oklahoma City, Portland, Las Vegas, Memphis, Louisville, Baltimore
- Milwaukee, Albuquerque, Tucson, Fresno, Sacramento, Kansas City, Mesa, Atlanta, Omaha, Raleigh
- Miami, Cleveland, Tulsa, Oakland, Minneapolis, Wichita, Arlington, Tampa, New Orleans, Honolulu

#### Step 1.3: Portal Classification
**Detect Portal System Type:**
```python
def classify_portal(url: str, html_content: str) -> PortalType:
    """
    Classify portal system type based on URL patterns and HTML.
    
    Returns:
        PortalType enum: ACCELA, VIEWPOINT, ENERGOV, CUSTOM, UNKNOWN
    """
    # Accela patterns:
    # - URL contains "accela.com" or "aca-prod.accela.com"
    # - HTML contains "Accela" or "ACA_"
    
    # ViewPoint patterns:
    # - URL contains "viewpointcloud.com"
    # - HTML contains "ViewPoint"
    
    # EnerGov patterns:
    # - URL contains "energov.com"
    # - HTML contains "EnerGov"
```

#### Step 1.4: Portal Validation
**Validate Discovered Portals:**
```python
async def validate_portal(portal_info: PortalInfo) -> bool:
    """
    Validate that portal actually has permit search functionality.
    
    Checks:
    - Page loads successfully
    - Contains permit search form
    - Has results table/list
    - Returns actual permit data
    """
```

### Deliverables
- ✅ Google Custom Search integration
- ✅ Portal discovery service
- ✅ Portal classification system
- ✅ List of 50+ discovered portals
- ✅ Portal validation pipeline

### Success Criteria
- Discovers 50+ valid permit portals
- Correctly classifies 80%+ portals by system type
- Validates 70%+ portals as functional

---

## Phase 2: Scraper Standardization (Weeks 3-4)

### Objective
Build reusable scrapers for common permit portal systems.

### Common Portal Systems

#### 2.1 Accela (Used by 100+ Cities)
**Cities:** San Antonio, Dallas, Tampa, San Diego, Seattle, etc.

**Characteristics:**
- URL pattern: `aca-prod.accela.com/[CITY]/Cap/`
- Search form: General Search with date filters
- Results table: `table.aca_grid_table`
- Detail pages: Standard Accela format

**Implementation:**
```python
# src/signal_engine/scrapers/accela_scraper.py
class AccelaScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for Accela-based permit portals.
    
    Works for any city using Accela by configuring:
    - City code (e.g., "COSA" for San Antonio)
    - Module name (e.g., "Fire")
    """
    
    def __init__(
        self,
        city_code: str,  # e.g., "COSA" for San Antonio
        module: str = "Fire",  # "Fire", "Building", etc.
        record_type: str | None = None,
        **kwargs
    ):
        # Build URL: https://aca-prod.accela.com/{city_code}/Cap/CapHome.aspx?module={module}
        # Use San Antonio scraper as template
```

**Cities to Add:**
- Dallas, TX
- Tampa, FL
- San Diego, CA
- Seattle, WA
- (Any city with Accela)

#### 2.2 ViewPoint Cloud (Used by 50+ Cities)
**Characteristics:**
- URL pattern: `[city].viewpointcloud.com`
- Search interface: Modern React-based
- API endpoints available

**Implementation:**
```python
# src/signal_engine/scrapers/viewpoint_scraper.py
class ViewPointScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for ViewPoint Cloud portals.
    """
```

#### 2.3 EnerGov (Used by 30+ Cities)
**Characteristics:**
- URL pattern: `[city].energov.com`
- Search interface: Standard EnerGov format

**Implementation:**
```python
# src/signal_engine/scrapers/energov_scraper.py
class EnerGovScraper(PlaywrightPermitScraper):
    """
    Reusable scraper for EnerGov portals.
    """
```

#### 2.4 Custom Portals (Like Mecklenburg)
**Strategy:**
- Keep custom scrapers for unique systems
- Document patterns for future reference
- Build template generator for similar systems

### Scraper Registry Pattern

```python
# src/signal_engine/scrapers/registry.py
class ScraperRegistry:
    """
    Registry of available scrapers by portal type.
    """
    
    REGISTRY = {
        PortalType.ACCELA: AccelaScraper,
        PortalType.VIEWPOINT: ViewPointScraper,
        PortalType.ENERGOV: EnerGovScraper,
        PortalType.MECKLENBURG: MecklenburgPermitScraper,
        PortalType.CUSTOM: PlaywrightPermitScraper,  # Generic fallback
    }
    
    @classmethod
    def create_scraper(
        cls,
        portal_info: PortalInfo,
        **kwargs
    ) -> BaseScraper:
        """
        Factory method to create appropriate scraper.
        """
        scraper_class = cls.REGISTRY.get(portal_info.system_type)
        return scraper_class(**portal_info.config, **kwargs)
```

### Deliverables
- ✅ Accela scraper (reusable for 100+ cities)
- ✅ ViewPoint scraper (reusable for 50+ cities)
- ✅ EnerGov scraper (reusable for 30+ cities)
- ✅ Scraper registry/factory pattern
- ✅ Configuration system for city-specific settings

### Success Criteria
- 3+ reusable scrapers for common systems
- Can add new Accela city with < 10 lines of config
- Scraper registry successfully routes to correct scraper

---

## Phase 3: Open Data API Integration (Weeks 5-6)

### Objective
Integrate with municipal open data portals for structured permit data.

### Open Data Platforms

#### 3.1 Socrata (Used by 100+ Cities)
**Examples:**
- data.cityofcharlotte.org
- data.seattle.gov
- data.cityofnewyork.us

**API Pattern:**
```python
# Socrata API example
# GET https://data.cityofcharlotte.org/resource/{dataset_id}.json
# Query params: $where, $limit, $order

class SocrataPermitClient:
    async def get_permits(
        self,
        dataset_id: str,
        filters: dict,
        limit: int = 1000
    ) -> list[PermitData]:
        """
        Fetch permits from Socrata open data portal.
        """
```

#### 3.2 CKAN (Used by 50+ Cities)
**Examples:**
- data.gov (federal)
- Many state/local portals

**API Pattern:**
```python
# CKAN API example
# GET {portal_url}/api/3/action/datastore_search
# Params: resource_id, filters, limit

class CKANPermitClient:
    async def get_permits(
        self,
        portal_url: str,
        resource_id: str,
        filters: dict
    ) -> list[PermitData]:
        """
        Fetch permits from CKAN open data portal.
        """
```

#### 3.3 Custom JSON APIs
**Many cities have custom REST APIs:**
- data.sanantonio.gov/api
- data.austintexas.gov/api

**Implementation:**
```python
class CustomAPIPermitClient:
    async def get_permits(
        self,
        api_url: str,
        endpoint: str,
        filters: dict
    ) -> list[PermitData]:
        """
        Generic client for custom permit APIs.
        """
```

### Discovery Strategy
1. **Search for Open Data Portals:**
   - Query: `"{city} open data" site:.gov`
   - Look for data.cityof{city}.gov patterns

2. **Identify Permit Datasets:**
   - Search for "building permit" or "construction permit" datasets
   - Check dataset schemas for required fields

3. **Test API Access:**
   - Verify API endpoints work
   - Check rate limits
   - Validate data format

### Deliverables
- ✅ Socrata API client
- ✅ CKAN API client
- ✅ Custom API client
- ✅ Unified permit data interface
- ✅ List of 20+ cities with open data APIs

### Success Criteria
- Integrate with 20+ open data portals
- Unified interface for all API types
- API data quality matches scraped data

---

## Phase 4: Data Quality & Filtering (Week 7)

### Objective
Filter low-quality permits before enrichment to save credits and improve results.

### Quality Scoring System

```python
# src/signal_engine/quality/permit_quality.py
class PermitQualityScorer:
    """
    Score permits before enrichment to filter low-quality ones.
    """
    
    def score(self, permit: PermitData) -> float:
        """
        Score permit quality (0.0 - 1.0).
        
        Factors:
        - Has applicant name: +0.3
        - Complete address: +0.2
        - Valid permit type: +0.2
        - Recent (last 30 days): +0.1
        - Status is "Issued": +0.1
        - Address is geocodable: +0.1
        """
        score = 0.0
        
        if permit.applicant_name and len(permit.applicant_name) > 3:
            score += 0.3
        
        if permit.address and len(permit.address) > 10:
            score += 0.2
        
        if permit.permit_type and "fire" in permit.permit_type.lower():
            score += 0.2
        
        # ... more factors
        
        return min(score, 1.0)
    
    def should_enrich(self, permit: PermitData, threshold: float = 0.5) -> bool:
        """
        Determine if permit should be enriched.
        """
        return self.score(permit) >= threshold
```

### Pre-Enrichment Filtering

```python
# src/signal_engine/jobs/scraper_scheduler.py
async def process_permits(permits: list[PermitData]) -> list[EnrichedLead]:
    """
    Process permits with quality filtering.
    """
    scorer = PermitQualityScorer()
    
    # Filter low-quality permits
    quality_permits = [
        p for p in permits 
        if scorer.should_enrich(p, threshold=0.5)
    ]
    
    logger.info(
        f"Filtered {len(permits)} permits to {len(quality_permits)} "
        f"high-quality permits ({len(quality_permits)/len(permits)*100:.1f}%)"
    )
    
    # Enrich only quality permits
    enriched_leads = []
    for permit in quality_permits:
        lead = await enrich_permit_to_lead(...)
        enriched_leads.append(lead)
    
    return enriched_leads
```

### Address Validation

```python
# src/signal_engine/quality/address_validator.py
class AddressValidator:
    """
    Validate and normalize addresses before enrichment.
    """
    
    async def validate(self, address: str) -> AddressValidationResult:
        """
        Validate address and return normalized version.
        
        Returns:
            AddressValidationResult with:
            - is_valid: bool
            - normalized_address: str
            - geocode_result: GeocodeResult | None
        """
        # Try geocoding
        geocode_result = await geocode_address(address)
        
        if geocode_result and geocode_result.city:
            return AddressValidationResult(
                is_valid=True,
                normalized_address=geocode_result.formatted_address,
                geocode_result=geocode_result
            )
        
        return AddressValidationResult(is_valid=False)
```

### Deliverables
- ✅ Permit quality scoring system
- ✅ Pre-enrichment filtering
- ✅ Address validation
- ✅ Quality metrics dashboard

### Success Criteria
- Filter out 40%+ low-quality permits
- 70%+ of enriched permits have applicant names
- 60%+ of enriched leads have decision maker emails

---

## Phase 5: Integration & Automation (Week 8)

### Objective
Integrate all components into automated pipeline.

### Unified Permit Ingestion Layer

```python
# src/signal_engine/ingestion/unified_ingestion.py
class UnifiedPermitIngestion:
    """
    Unified interface for all permit sources.
    """
    
    async def ingest_permits(
        self,
        source: PermitSource,
        filters: dict
    ) -> list[PermitData]:
        """
        Ingest permits from any source (scraper, API, etc.).
        
        Sources:
        - Scraper (Playwright)
        - Socrata API
        - CKAN API
        - Custom API
        """
        if source.type == SourceType.SCRAPER:
            scraper = ScraperRegistry.create_scraper(source.portal_info)
            return await scraper.scrape()
        
        elif source.type == SourceType.SOCRATA:
            client = SocrataPermitClient()
            return await client.get_permits(...)
        
        # ... other sources
```

### Automated Discovery Pipeline

```python
# src/signal_engine/jobs/discovery_scheduler.py
class DiscoveryScheduler:
    """
    Scheduled job to discover new permit portals.
    """
    
    async def discover_new_portals(self):
        """
        Run portal discovery and add new portals to registry.
        """
        discovery = PortalDiscoveryService()
        cities = self.get_target_cities()
        
        for city in cities:
            portals = await discovery.discover_portals([city])
            
            for portal in portals:
                if self.is_new_portal(portal):
                    self.register_portal(portal)
                    logger.info(f"Discovered new portal: {portal.url}")
```

### Configuration Management

```python
# src/signal_engine/config/portal_config.py
class PortalConfig:
    """
    Configuration for each permit portal.
    """
    
    city: str
    portal_url: str
    system_type: PortalType
    source_type: SourceType  # SCRAPER, API, etc.
    config: dict  # City-specific settings
    enabled: bool
    last_scraped: datetime | None
    permit_count: int
```

### Deliverables
- ✅ Unified ingestion layer
- ✅ Automated discovery scheduler
- ✅ Portal configuration system
- ✅ Monitoring dashboard

### Success Criteria
- Automated discovery runs weekly
- New portals automatically added to scheduler
- Unified interface works for all source types

---

## Implementation Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1: Portal Discovery** | Weeks 1-2 | Google Custom Search integration, 50+ portals discovered |
| **Phase 2: Scraper Standardization** | Weeks 3-4 | 3+ reusable scrapers, scraper registry |
| **Phase 3: Open Data APIs** | Weeks 5-6 | API clients for Socrata/CKAN, 20+ cities integrated |
| **Phase 4: Quality Filtering** | Week 7 | Quality scoring, pre-enrichment filtering |
| **Phase 5: Integration** | Week 8 | Unified pipeline, automated discovery |

**Total Duration:** 8 weeks  
**Total Cost:** $0 (100% free)

---

## Cost Analysis

### Free Resources Used

| Resource | Cost | Usage |
|----------|------|-------|
| **Google Custom Search API** | Free (100 queries/day) | Portal discovery |
| **Municipal Websites** | Free | Permit scraping |
| **Open Data APIs** | Free | Structured permit data |
| **Nominatim Geocoding** | Free | Address validation |
| **Playwright** | Free | Web scraping |

### Potential Costs (Optional)

| Service | Cost | Use Case |
|---------|------|----------|
| Google Custom Search (paid) | $5/1,000 queries | If free tier insufficient |
| Proxy Services | $50-200/mo | If rate-limited |
| Cloud Hosting | $20-50/mo | For production deployment |

**Recommendation:** Start with free tier, upgrade only if needed.

---

## Success Metrics

### Coverage Metrics
- **Cities:** 50+ cities with active permit sources
- **Permits/Month:** 1,000+ permits discovered
- **Sources:** Mix of scrapers (30) + APIs (20)

### Quality Metrics
- **Applicant Names:** 70%+ permits have applicant names
- **Decision Maker Emails:** 60%+ enriched leads have emails
- **Enrichment Efficiency:** 60%+ of enriched permits convert to qualified leads

### Operational Metrics
- **Discovery Rate:** 5+ new portals discovered per week
- **Uptime:** 95%+ portal availability
- **Error Rate:** < 5% failed scrapes

---

## Risk Mitigation

### Technical Risks

1. **Portal Changes**
   - **Risk:** Municipalities change portal systems
   - **Mitigation:** Regular validation, automated alerts

2. **Rate Limiting**
   - **Risk:** Too many requests get blocked
   - **Mitigation:** Rate limiting, proxy rotation (if needed)

3. **Data Quality**
   - **Risk:** Low-quality permits waste credits
   - **Mitigation:** Quality scoring before enrichment

### Operational Risks

1. **Maintenance Overhead**
   - **Risk:** Too many custom scrapers to maintain
   - **Mitigation:** Standardize on common systems, prioritize

2. **Discovery Accuracy**
   - **Risk:** Google Search finds irrelevant portals
   - **Mitigation:** Validation pipeline, manual review

---

## Next Steps

### Immediate Actions (Week 1)

1. **Set up Google Custom Search:**
   - Create custom search engine
   - Configure for `.gov` domains
   - Add API keys to `.env`

2. **Build Portal Discovery Service:**
   - Implement `PortalDiscoveryService`
   - Create search query templates
   - Build portal classification logic

3. **Test Discovery:**
   - Run discovery on top 10 cities
   - Validate results
   - Refine search queries

### Short-term (Weeks 2-4)

1. **Build Reusable Scrapers:**
   - Accela scraper (highest priority - 100+ cities)
   - ViewPoint scraper
   - EnerGov scraper

2. **Create Scraper Registry:**
   - Factory pattern for scraper creation
   - Configuration system
   - Testing framework

### Medium-term (Weeks 5-8)

1. **Integrate Open Data APIs:**
   - Socrata client
   - CKAN client
   - Test with 20+ cities

2. **Implement Quality Filtering:**
   - Quality scoring system
   - Pre-enrichment filtering
   - Metrics dashboard

3. **Automate Everything:**
   - Unified ingestion layer
   - Automated discovery scheduler
   - Monitoring and alerts

---

## Conclusion

This plan provides a **100% free path** to expand permit discovery from 2 cities to 50+ cities within 8 weeks. By combining automated portal discovery, scraper standardization, and open data API integration, we can achieve comprehensive coverage without commercial API costs.

**Key Advantages:**
- ✅ Zero cost (free public resources)
- ✅ Scalable (automated discovery)
- ✅ Maintainable (standardized scrapers)
- ✅ High quality (pre-filtering)

**Expected Outcome:**
- 50+ cities with active permit sources
- 1,000+ permits/month
- 70%+ data quality
- $0/month operating cost

---

## Appendix

### A. Top 50 Cities by Population

1. New York, NY
2. Los Angeles, CA
3. Chicago, IL
4. Houston, TX
5. Phoenix, AZ
6. Philadelphia, PA
7. San Antonio, TX ✅
8. San Diego, CA
9. Dallas, TX
10. San Jose, CA
... (see full list in Phase 1.2)

### B. Common Portal Systems

| System | Cities | Scraper Status |
|--------|--------|----------------|
| Accela | 100+ | ✅ Template exists (San Antonio) |
| ViewPoint | 50+ | ⏳ To be built |
| EnerGov | 30+ | ⏳ To be built |
| Custom | 200+ | ⏳ Manual per city |

### C. Open Data Portal Examples

- data.cityofcharlotte.org (Socrata)
- data.seattle.gov (Socrata)
- data.cityofnewyork.us (Socrata)
- data.gov (CKAN)
- data.austintexas.gov (Custom API)

---

**Document Version:** 1.0  
**Last Updated:** January 13, 2026  
**Owner:** AORO Development Team
