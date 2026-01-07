# Phase 1.1: Permit Scraping Tests

Tests and utilities for permit scraping functionality.

## Test Scripts

### Main Tests
- `test_phase1_1_complete.py` - Comprehensive Phase 1.1 test suite
- `test_mecklenburg.py` - Mecklenburg County scraper test
- `test_san_antonio.py` - San Antonio Fire Module scraper test

### Debug/Development Scripts
- `test_mecklenburg_visible.py` - Visible browser debugging for Mecklenburg
- `test_san_antonio_visible.py` - Visible browser debugging for San Antonio
- `test_san_antonio_globalsearch.py` - GlobalSearch function testing
- `test_san_antonio_comprehensive_debug.py` - Comprehensive debugging
- `test_san_antonio_iframe_debug.py` - IFrame debugging
- `test_san_antonio_js_handler.py` - JavaScript handler testing
- `test_san_antonio_record_search.py` - Record search testing
- `test_san_antonio_with_results.py` - Results page testing
- `test_san_antonio_golden.py` - Golden test cases

### Verification
- `verify_phase1_1.sh` - Quick verification script

## Usage

```bash
# Run comprehensive test suite
poetry run python scripts/phase1_1/test_phase1_1_complete.py

# Test Mecklenburg scraper
poetry run python scripts/phase1_1/test_mecklenburg.py

# Test San Antonio scraper
poetry run python scripts/phase1_1/test_san_antonio.py

# Quick verification
./scripts/phase1_1/verify_phase1_1.sh
```

