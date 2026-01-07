# Phase 1.1 Testing Guide

This document describes how to verify that all Phase 1.1 components work correctly.

## Quick Verification

Run the quick verification script to check that all files exist and imports work:

```bash
./scripts/verify_phase1_1.sh
```

This script checks:
- ✅ Poetry is installed
- ✅ Required files exist
- ✅ APScheduler is in dependencies
- ✅ All imports work correctly

## Comprehensive Testing

Run the full test suite to verify all Phase 1.1 functionality:

```bash
poetry run python scripts/test_phase1_1_complete.py
```

### What Gets Tested

1. **Scraper Basic Functionality**
   - Mecklenburg scraper can extract permits
   - San Antonio scraper can extract permits
   - Permit data structure is correct

2. **Applicant Extraction**
   - Works when disabled (all applicant_name = None)
   - Works when enabled (extracts from detail pages)
   - Doesn't crash on missing applicant info

3. **Scheduler Functionality**
   - Can be instantiated
   - Last run timestamps are saved/loaded correctly
   - Jobs can be added and configured

4. **Utilities**
   - Permit deduplication works correctly
   - Last write wins for duplicate permits

### Test Options

**Test with applicant extraction enabled** (slower, but more thorough):
```bash
TEST_APPLICANT_EXTRACTION=true poetry run python scripts/test_phase1_1_complete.py
```

**Test individual scrapers:**
```bash
# Mecklenburg
TENANT_ID=demo SEARCH_TYPE="address" SEARCH_VALUE="Tryon" STREET_NUMBER="600" \
  poetry run python scripts/test_mecklenburg.py

# San Antonio
TENANT_ID=demo RECORD_TYPE="Fire Alarm" DAYS_BACK=120 \
  poetry run python scripts/test_san_antonio.py
```

## Manual Testing

### Test Scheduled Job Runner

1. **Start the scheduler:**
   ```bash
   poetry run python scripts/run_scheduled_scrapers.py
   ```

2. **Verify it runs:**
   - Check console output for job execution
   - Verify `data/scraper_last_runs.json` is created
   - Check that permits are extracted

3. **Stop with Ctrl+C**

### Test Applicant Extraction

1. **Run with applicant extraction enabled:**
   ```bash
   TENANT_ID=demo SEARCH_TYPE="address" SEARCH_VALUE="Tryon" STREET_NUMBER="600" \
     poetry run python -c "
   from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper
   import asyncio
   from src.core.security import tenant_scoped_session
   
   async def test():
       scraper = mecklenburg_county_scraper(
           search_type='address',
           search_value='Tryon',
           street_number='600',
           extract_applicant=True
       )
       async with tenant_scoped_session('demo'):
           permits = await scraper.scrape()
           print(f'Found {len(permits)} permits')
           for p in permits[:3]:
               print(f'  {p.permit_id}: applicant={p.applicant_name}')
   
   asyncio.run(test())
   "
   ```

2. **Verify:**
   - Some permits may have `applicant_name` populated
   - No crashes occur
   - Permits without detail URLs have `applicant_name=None`

## Expected Results

### Successful Test Run

```
============================================================
PHASE 1.1 COMPREHENSIVE TEST SUITE
============================================================
Testing all Phase 1.1 components...

Testing Scrapers...
✅ Mecklenburg Scraper - Basic Extraction
   Extracted 15 permits (sample: 12345)
✅ San Antonio Scraper - Basic Extraction
   Extracted 11 permits (sample: FIRE-2025-001)

Testing Applicant Extraction...
✅ Applicant Extraction - Disabled Mode
✅ Applicant Extraction - Enabled Mode
   Tested 10 permits with detail URLs
   Found applicant info for 3 permits

Testing Scheduler...
✅ Scheduler - Instantiation
✅ Scheduler - Last Run Persistence
✅ Scheduler - Job Configuration

Testing Utilities...
✅ Scraper - Deduplication

============================================================
PHASE 1.1 TEST SUMMARY
============================================================
✅ Passed: 8
❌ Failed: 0
============================================================

✅ All Phase 1.1 tests passed!
```

## Troubleshooting

### Import Errors

If you see import errors:
```bash
# Install dependencies
poetry install

# Verify virtual environment
poetry env info
```

### Scraper Timeouts

If scrapers timeout:
- Check internet connection
- Verify portal URLs are accessible
- Try different search values
- Check for portal maintenance

### No Permits Found

If no permits are found:
- **Mecklenburg:** Try different address or project name
- **San Antonio:** Try different date range or record type
- Check if portals have data in the specified date range

### Applicant Extraction Fails

If applicant extraction fails:
- This is acceptable - not all portals expose applicant info
- Check `detail_url` is populated
- Verify detail pages are accessible
- Applicant extraction is optional and can be disabled

## Next Steps

After verifying Phase 1.1:
1. ✅ All tests pass → Ready for Phase 1.2 or 1.3
2. ⚠️ Some tests fail → Review failures and fix issues
3. 📝 Document any portal-specific issues discovered

