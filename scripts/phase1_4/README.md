# Phase 1.4: Permit Discovery Expansion

This directory contains scripts and tests for Phase 1.4: Permit Discovery Expansion.

## Phase Structure

- **Phase 1.4.1:** Automated Portal Discovery ✅ COMPLETE
- **Phase 1.4.2:** Scraper Standardization ✅ COMPLETE
- **Phase 1.4.3:** Open Data API Integration ✅ COMPLETE
- **Phase 1.4.4:** Data Quality & Filtering ⏳ NEXT
- **Phase 1.4.5:** Integration & Automation ⏳ PENDING

## Phase 1.4.3: Open Data API Integration

### What Was Implemented

1. **API Clients:**
   - `SocrataPermitClient` - For Socrata open data portals (100+ cities)
   - `CKANPermitClient` - For CKAN open data portals (50+ cities)
   - `CustomAPIPermitClient` - For custom REST APIs

2. **Unified Ingestion:**
   - `UnifiedPermitIngestion` - Single interface for scrapers and APIs
   - `PermitSource` - Configuration class for permit sources

3. **Base Infrastructure:**
   - `BaseAPIPermitClient` - Abstract base class
   - Field mapping system
   - Date normalization
   - Error handling

### Test Results

**Combined Test (Scrapers + APIs):**
- Scrapers: 3 cities = 32 permits
- APIs: 1 city (Seattle) = 47 permits
- **Total: 79 permits from 4 cities**

### Working Portals

**Socrata:**
- ✅ Seattle, WA - 47 permits
  - Portal: https://data.seattle.gov
  - Dataset: 76t5-zqzr

**Scrapers:**
- ✅ San Antonio, TX (COSA) - 11 permits
- ✅ Denver, CO (DENVER) - 11 permits
- ✅ Charlotte, NC (CHARLOTTE) - 10 permits

## Test Scripts

### Test Real Socrata Portals
```bash
poetry run python scripts/phase1_4/test_real_socrata_portals.py
```
Tests real Socrata portals with permit datasets.

### Test Unified Ingestion
```bash
poetry run python scripts/phase1_4/test_unified_ingestion.py
```
Tests the unified ingestion interface with scrapers.

### Test Scrapers + APIs Combined
```bash
poetry run python scripts/phase1_4/test_scrapers_and_apis_combined.py
```
Tests combining scrapers and APIs to show unified ingestion works.

### Test All API Clients
```bash
poetry run python scripts/phase1_4/test_open_data_apis.py
```
Tests all API client types (Socrata, CKAN, Custom).

## Usage Examples

### Using Socrata API Client

```python
from src.signal_engine.api.socrata_client import SocrataPermitClient

client = SocrataPermitClient(
    portal_url="https://data.seattle.gov",
    dataset_id="76t5-zqzr",
    field_mapping={
        "permit_id": "permitnum",
        "permit_type": "permittypedesc",
        "address": "originaladdress1",
        "status": "statuscurrent",
    },
)

permits = await client.get_permits(days_back=30, limit=100)
```

### Using Unified Ingestion

```python
from src.signal_engine.api.unified_ingestion import (
    PermitSource,
    PermitSourceType,
    UnifiedPermitIngestion,
)

# Scraper source
scraper_source = PermitSource(
    source_type=PermitSourceType.SCRAPER,
    city="San Antonio, TX",
    source_id="cosa_fire",
    config={
        "portal_type": "accela",
        "city_code": "COSA",
        "module": "Fire",
    },
)

# API source
api_source = PermitSource(
    source_type=PermitSourceType.SOCRATA_API,
    city="Seattle, WA",
    source_id="seattle_socrata",
    config={
        "portal_url": "https://data.seattle.gov",
        "dataset_id": "76t5-zqzr",
        "field_mapping": {...},
    },
)

# Ingest from both
ingestion = UnifiedPermitIngestion()
scraper_permits = await ingestion.ingest_permits(scraper_source)
api_permits = await ingestion.ingest_permits(api_source)
```

## Next Steps

1. **Find More Socrata Portals:**
   - Search for more cities with Socrata portals
   - Find permit dataset IDs
   - Test and configure

2. **Test CKAN Portals:**
   - Find cities with CKAN portals
   - Test CKAN client
   - Add working portals

3. **Phase 1.4.4:**
   - Implement data quality scoring
   - Pre-enrichment filtering
   - Address validation

## Documentation

- Phase 1.4.3 Complete: [`docs/ai/PHASE_1_4_3_COMPLETE.md`](../../docs/ai/PHASE_1_4_3_COMPLETE.md)
- Master Plan: [`docs/plan/aoro_mvp_master_plan.md`](../../docs/plan/aoro_mvp_master_plan.md)
- Expansion Plan: [`docs/plan/permit_discovery_expansion_plan.md`](../../docs/plan/permit_discovery_expansion_plan.md)
