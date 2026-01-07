# Hunter.io Integration - Credit-Safe Implementation

## Overview

Hunter.io integration has been implemented with multiple safety layers to protect your 50 free credits while testing and developing Phase 1.3.

## Safety Features Implemented

### 1. Mock Client (Zero Credits)
- `MockHunterClient` - Simulates API responses without network calls
- Use for development and testing logic
- Located in: `src/signal_engine/enrichment/hunter_client.py`

### 2. Dry-Run Mode (Default: Enabled)
- `ENRICHMENT_DRY_RUN=true` in `.env`
- When enabled: Only logs what would be sent, no real API calls
- Automatically enabled when using `test-api-key`
- Protects credits during development

### 3. Credit Limit Safety Brake
- `MAX_CREDITS_PER_RUN=3` in `.env`
- Hard limit enforced by `CreditGuard` class
- Raises `RuntimeError` if limit exceeded
- Prevents runaway loops from draining account

### 4. Automatic Permit Slicing
- Scheduler automatically slices permits to credit limit
- Example: 500 permits → only first 3 processed per run
- Prevents accidentally processing entire dataset

### 5. Test API Key Support
- Hunter.io provides `test-api-key` for zero-cost testing
- Automatically detected and enables dry-run mode
- Returns dummy responses to test code logic

## Current Configuration

Your `.env` file is configured for safe testing:

```env
HUNTER_API_KEY=test-api-key  # Using test key for now
ENRICHMENT_DRY_RUN=true      # Dry-run enabled (default)
MAX_CREDITS_PER_RUN=3        # Safety limit
ENRICHMENT_PROVIDER_PRIORITY=auto  # Hunter first, Apollo fallback
```

## How It Works

### Provider Priority (AUTO mode)
1. **Hunter.io** (free) - Tries first if name + domain available
2. **Apollo** (premium) - Falls back if Hunter unavailable and Apollo key exists

### Email Finding Strategy
1. If `applicant_name` looks like a person name → Use Hunter email finder
2. If only company name available → Use Apollo person search (if key available)
3. Falls back gracefully if no providers available

## Testing

Run the test script to verify everything works:

```bash
poetry run python scripts/test_hunter_integration.py
```

This will test:
- Mock client (zero credits)
- Dry-run mode
- Provider manager
- Full enrichment pipeline
- Credit limit safety

## Moving to Production

When ready to use real credits:

1. **Get your real Hunter.io API key** from https://hunter.io/api-documentation

2. **Update `.env`**:
   ```env
   HUNTER_API_KEY=your_real_key_here
   ENRICHMENT_DRY_RUN=false  # Disable dry-run
   MAX_CREDITS_PER_RUN=3     # Keep safety limit
   ```

3. **Test with 1-2 permits first**:
   - Run scraper for just 1-2 permits
   - Verify emails are found correctly
   - Check credit usage in Hunter.io dashboard

4. **Monitor credit usage**:
   - Hunter.io dashboard shows remaining credits
   - Credit guard will stop at limit
   - Scheduler slices permits automatically

## Credit Usage Notes

- **Hunter.io only charges when email is found**
  - 404 responses = no credit charged
  - Successful finds = 1 credit per email

- **Test key (`test-api-key`) = zero credits**
  - Always returns dummy data
  - Perfect for testing code logic
  - No credit charges ever

- **Dry-run mode = zero credits**
  - Only logs what would be sent
  - No actual API calls made
  - Safe for development

## Files Created/Modified

### New Files
- `src/signal_engine/enrichment/hunter_client.py` - Hunter.io API client
- `src/signal_engine/enrichment/provider_manager.py` - Provider abstraction with credit safety
- `scripts/test_hunter_integration.py` - Integration tests

### Modified Files
- `src/signal_engine/enrichment/company_enricher.py` - Uses ProviderManager
- `src/signal_engine/jobs/scraper_scheduler.py` - Auto-slices permits
- `src/core/config.py` - Added Hunter.io settings
- `.env` - Configured with test key and safety settings

## Apollo Integration Status

✅ **Apollo code remains intact** - Ready for when you have API key
- All Apollo client code unchanged
- ProviderManager supports Apollo as fallback
- Easy to switch priority when budget allows

## Next Steps

1. ✅ Integration complete with safety features
2. ✅ Test key configured and working
3. ✅ Dry-run mode enabled by default
4. ⏭️ When ready: Replace test key with real key
5. ⏭️ Test with 1-2 real permits
6. ⏭️ Monitor credit usage
7. ⏭️ Adjust `MAX_CREDITS_PER_RUN` if needed

## Safety Checklist

Before using real credits:
- [ ] Verified dry-run mode works (check test output)
- [ ] Test key returns expected dummy data
- [ ] Credit guard stops at limit
- [ ] Scheduler slices permits correctly
- [ ] Real API key added to `.env`
- [ ] Dry-run disabled (`ENRICHMENT_DRY_RUN=false`)
- [ ] Tested with 1-2 real permits first

