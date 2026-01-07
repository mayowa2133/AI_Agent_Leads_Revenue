# Hunter.io Setup Complete ✅

## Status

✅ **Real API key configured and verified**
- API key: Configured in `.env` (see HUNTER_API_KEY)
- API connection: ✅ Working
- Test call: ✅ Successful (no credit charged - no email found)

## Current Safety Configuration

Your system is configured with multiple safety layers:

```env
HUNTER_API_KEY=your_hunter_key_here  # Set your actual key in .env (not committed)
ENRICHMENT_DRY_RUN=true          # Still in dry-run mode (safe)
MAX_CREDITS_PER_RUN=3            # Hard limit enforced
ENRICHMENT_PROVIDER_PRIORITY=auto # Hunter first, Apollo fallback
```

## Safety Features Active

1. ✅ **Dry-Run Mode** - Currently enabled (no real API calls)
2. ✅ **Credit Limit** - Max 3 credits per run enforced
3. ✅ **Auto Slicing** - Scheduler only processes first 3 permits
4. ✅ **Credit Guard** - Raises error if limit exceeded
5. ✅ **No-Charge on 404** - Hunter doesn't charge if email not found

## How to Enable Production Mode (When Ready)

### Step 1: Test with 1-2 Real Permits First

Create a test script that processes just 1-2 permits:

```python
# Test with minimal credits
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.models import PermitData

# Use a real permit from your data
permit = PermitData(
    source="mecklenburg",
    permit_id="REAL-PERMIT-001",
    permit_type="Fire Alarm",
    address="Real Address Here",
    building_type="Commercial",
    status="Issued",
    applicant_name="Real Person Name",  # Must be a person name
)

lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="test", permit=permit))
```

### Step 2: Enable Production Mode

When ready to use real credits:

1. **Update `.env`**:
   ```env
   ENRICHMENT_DRY_RUN=false  # Enable real API calls
   MAX_CREDITS_PER_RUN=3     # Keep safety limit
   ```

2. **Test with 1 permit first**:
   - Run enrichment for just 1 permit
   - Verify email is found correctly
   - Check Hunter.io dashboard for credit usage

3. **Monitor credit usage**:
   - Check dashboard: https://hunter.io/dashboard
   - Credits used: Should show 1 credit per successful email find
   - Remaining: Should show 49 credits (if 1 used)

### Step 3: Production Usage

Once verified:
- System will automatically slice permits to 3 per run
- Credit guard will stop at limit
- Scheduler processes permits safely
- No risk of draining all 50 credits

## Credit Usage Notes

- **Hunter only charges when email is found**
  - Successful find = 1 credit
  - No email found (404) = 0 credits
  - This is why the test call didn't use a credit

- **Current limits protect you**:
  - Max 3 credits per scraper run
  - Auto-slicing prevents processing all 500 permits
  - Dry-run mode still enabled (change when ready)

## Next Steps

1. ✅ API key configured
2. ✅ API connection verified
3. ⏭️ Test with 1-2 real permits (when ready)
4. ⏭️ Enable dry_run=false (when ready)
5. ⏭️ Monitor credit usage
6. ⏭️ Adjust MAX_CREDITS_PER_RUN if needed

## Safety Reminders

- **Dry-run is still enabled** - Change to `false` when ready
- **Credit limit is 3** - Protects against runaway loops
- **Auto-slicing active** - Only first 3 permits processed per run
- **Monitor dashboard** - Check credit usage regularly

Your 50 credits are protected! 🛡️

