# Scripts Directory

This directory contains all scripts organized by phase and purpose.

## Organization

### `phase1_1/` - Phase 1.1: Permit Scraping Tests
Tests and utilities for permit scraping functionality.

### `phase1_2/` - Phase 1.2: Regulatory Listener Tests
Tests for regulatory update listeners (EPA, NFPA, Fire Marshal).

### `phase1_3/` - Phase 1.3: Enrichment Pipeline Tests
Tests for data enrichment (geocoding, company matching, email finding).

### `e2e/` - End-to-End Tests
Complete flow tests that verify multiple phases working together.

### `utils/` - Utility Scripts
Production scripts for running scrapers, schedulers, and other utilities.

### `debug/` - Debug Scripts
Debugging and development scripts (not for production use).

## Running Scripts

```bash
# Phase 1.1 tests
poetry run python scripts/phase1_1/test_phase1_1_complete.py

# Phase 1.2 tests
poetry run python scripts/phase1_2/test_regulatory_listeners.py

# Phase 1.3 tests
poetry run python scripts/phase1_3/test_enrichment_pipeline.py

# End-to-end tests
poetry run python scripts/e2e/test_complete_phase1_flow.py

# Production utilities
poetry run python scripts/utils/run_scheduled_scrapers.py
```
