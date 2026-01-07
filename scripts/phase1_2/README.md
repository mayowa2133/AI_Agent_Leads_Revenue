# Phase 1.2: Regulatory Listener Tests

Tests for regulatory update listeners (EPA, NFPA, Fire Marshal).

## Test Scripts

- `test_regulatory_listeners.py` - Comprehensive test suite for all regulatory listeners
- `verify_regulatory_setup.py` - Setup verification script

## Usage

```bash
# Test all regulatory listeners
poetry run python scripts/phase1_2/test_regulatory_listeners.py

# Verify setup and configuration
poetry run python scripts/phase1_2/verify_regulatory_setup.py
```

## What's Tested

- EPA Regulatory Listener (Federal Register API)
- NFPA Listener (NFPA.org scraping)
- Fire Marshal Listener (RSS feeds)
- Regulatory Storage (JSON persistence)
- LLM Content Processor (compliance trigger extraction)

