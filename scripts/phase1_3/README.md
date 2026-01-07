# Phase 1.3: Enrichment Pipeline Tests

Tests for data enrichment (geocoding, company matching, email finding).

## Test Scripts

### Main Tests
- `test_enrichment_pipeline.py` - Comprehensive enrichment pipeline test
- `test_hybrid_enrichment.py` - Hybrid Apollo + Hunter.io workflow test
- `test_enrichment_real_permits.py` - Test with real scraped permits

### Component Tests
- `test_enrichment_quick.py` - Quick test with sample permits
- `test_enrichment_with_domain.py` - Test with known company domains
- `test_hunter_integration.py` - Hunter.io integration test
- `test_hunter_real_api.py` - Real Hunter.io API test
- `test_hunter_with_known_company.py` - Test with known companies
- `test_hybrid_end_to_end.py` - End-to-end hybrid workflow test

## Usage

```bash
# Test complete enrichment pipeline
poetry run python scripts/phase1_3/test_enrichment_pipeline.py

# Test hybrid Apollo + Hunter.io workflow
poetry run python scripts/phase1_3/test_hybrid_enrichment.py

# Test with real permits
poetry run python scripts/phase1_3/test_enrichment_real_permits.py

# Test Hunter.io integration
poetry run python scripts/phase1_3/test_hunter_integration.py
```

## What's Tested

- Geocoding (Nominatim)
- Company matching
- Apollo domain lookup
- Hunter.io email finder
- Credit safety mechanisms
- Lead storage

