# Email Address Discovery Fix Plan

## Problem Analysis

### Current Situation
- **0/5 leads have email addresses** in the integration test
- All companies are showing as "Unknown Org (Unknown)" or "Unknown Org (10 ft tunnel)"
- Decision makers are `None` for all leads
- Emails cannot be sent because no email addresses are found

### Root Causes

1. **Dry-Run Mode Enabled** ⚠️
   - `ENRICHMENT_DRY_RUN=true` in config
   - System is not making real API calls to find emails
   - This is a safety feature but prevents actual enrichment

2. **Company Matching Failing** 🔴
   - Many permits have missing/invalid `applicant_name` fields
   - Addresses are poor quality ("10 ft tunnel", empty strings)
   - Without valid company names, Apollo can't find domains
   - Without domains, Hunter.io can't find emails

3. **Data Quality Issues** 🔴
   - Applicant names not extracted from detail pages
   - Addresses are incomplete or invalid
   - Company information missing from permit data

4. **API Keys May Be Missing** ⚠️
   - Hunter.io API key may not be configured
   - Apollo API key may not be configured
   - Without API keys, enrichment cannot work

## Solution Strategy

### Phase 1: Immediate Fixes (Enable Real Enrichment)

1. **Disable Dry-Run Mode**
   - Set `ENRICHMENT_DRY_RUN=false` in `.env`
   - This allows real API calls to Hunter.io and Apollo

2. **Verify API Keys**
   - Check if `HUNTER_API_KEY` is set in `.env`
   - Check if `APOLLO_API_KEY` is set in `.env`
   - Add keys if missing

3. **Improve Data Collection**
   - Ensure applicant extraction is enabled (already done)
   - Improve address extraction from permit detail pages
   - Add fallback strategies for company matching

### Phase 2: Enhanced Company Matching

1. **Better Applicant Name Extraction**
   - Already enabled by default in `AccelaScraper`
   - Verify it's working correctly
   - Add logging to see what's being extracted

2. **Improved Address Validation**
   - Filter out invalid addresses (too short, no street number)
   - Use address normalization before geocoding
   - Add fallback to use city/state if address fails

3. **Enhanced Company Matching Logic**
   - Use permit type to infer company type
   - Use building type to narrow search
   - Add fallback to search by address + city
   - Use Apollo's enhanced search with more fields

### Phase 3: Fallback Strategies

1. **Multi-Strategy Email Finding**
   - Strategy 1: Applicant name + domain (Hunter.io)
   - Strategy 2: Company name + title (Apollo)
   - Strategy 3: Address-based company search (Apollo)
   - Strategy 4: Permit type + location search

2. **Better Title Matching**
   - Expand list of facility-related titles
   - Use permit type to infer relevant titles
   - Search for multiple titles in parallel

## Implementation Steps

### Step 1: Check Current Configuration

```bash
# Check if API keys are set
grep -E "HUNTER_API_KEY|APOLLO_API_KEY" .env

# Check dry-run mode
grep "ENRICHMENT_DRY_RUN" .env
```

### Step 2: Enable Real Enrichment

Update `.env`:
```env
# Disable dry-run mode
ENRICHMENT_DRY_RUN=false

# Ensure API keys are set
HUNTER_API_KEY=your_hunter_key_here
APOLLO_API_KEY=your_apollo_key_here  # Optional but recommended
```

### Step 3: Improve Data Collection

1. **Verify Applicant Extraction**
   - Check if `extract_applicant=True` is set in scrapers
   - Add logging to see extracted applicant names
   - Test with real permits

2. **Improve Address Extraction**
   - Add address validation in scrapers
   - Extract full addresses from detail pages
   - Use multiple address fields if available

### Step 4: Enhanced Company Matching

1. **Add Fallback Strategies**
   - Search by address + city if company name missing
   - Use permit type to infer company type
   - Use building type to narrow search

2. **Better Domain Lookup**
   - Use Apollo's enhanced search
   - Try multiple company name variations
   - Use location to narrow results

### Step 5: Testing

1. **Test with Real Permits**
   - Use permits with known company names
   - Verify applicant names are extracted
   - Check if domains are found
   - Verify emails are discovered

2. **Monitor Credit Usage**
   - Track Hunter.io credits used
   - Track Apollo credits used
   - Ensure limits are respected

## Expected Outcomes

### After Phase 1 (Immediate Fixes)
- Dry-run mode disabled
- Real API calls enabled
- API keys verified
- **Expected: 20-40% of leads get emails**

### After Phase 2 (Enhanced Matching)
- Better company matching
- Improved address validation
- **Expected: 40-60% of leads get emails**

### After Phase 3 (Fallback Strategies)
- Multiple enrichment strategies
- Better title matching
- **Expected: 60-80% of leads get emails**

## Success Metrics

- **Email Discovery Rate**: % of leads with email addresses
- **Company Match Rate**: % of leads with valid company names
- **Domain Discovery Rate**: % of companies with domains found
- **Credit Efficiency**: Emails found per credit used

## Next Steps

1. ✅ Create diagnostic script to check current state
2. ✅ Update configuration to enable real enrichment
3. ✅ Improve data collection (applicant names, addresses)
4. ✅ Enhance company matching logic
5. ✅ Add fallback strategies
6. ✅ Test with real permits
7. ✅ Monitor and optimize
