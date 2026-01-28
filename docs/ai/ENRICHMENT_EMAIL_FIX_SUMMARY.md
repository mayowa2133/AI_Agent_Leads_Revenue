# Email Discovery Issue - Root Cause & Fix Summary

## 🔍 Root Cause Analysis

### Diagnostic Results
✅ **Configuration**: All good
- Dry-run mode: **DISABLED** (real API calls enabled)
- Hunter.io API key: **SET**
- Apollo API key: **SET**
- Enrichment enabled: **YES**

❌ **Data Quality**: The problem
- **Address**: Empty for test permit
- **Applicant Name**: Empty for test permit
- **Result**: Company matching fails → No domain → No emails

### The Problem Chain
```
Missing Address/Applicant Name
    ↓
Company Matching Fails (Unknown Org)
    ↓
No Company Domain Found
    ↓
Hunter.io Can't Find Emails (needs domain)
    ↓
No Decision Maker Found
    ↓
No Email Addresses
```

## ✅ Immediate Fixes (Do These First)

### 1. Improve Address Extraction
**Problem**: Address column is empty for many permits

**Solution**: Extract address from detail page as fallback
- Current: Only extracts from results table column 5
- Fix: If address is empty, visit detail page and extract full address
- Location: `src/signal_engine/scrapers/accela_scraper.py`

### 2. Improve Applicant Name Extraction  
**Problem**: Applicant names not found on detail pages

**Solution**: Enhanced detail page extraction
- Current: Basic selectors, may miss applicant info
- Fix: Add more selectors, try multiple strategies
- Location: `src/signal_engine/scrapers/permit_scraper.py` → `_extract_applicant_from_detail`

### 3. Enhanced Company Matching
**Problem**: Falls back to "Unknown Org" when data is missing

**Solution**: Add fallback strategies
- Use permit type to infer company type
- Use building type if available
- Search by address + city if company name missing
- Location: `src/signal_engine/enrichment/company_enricher.py`

## 📋 Implementation Checklist

### Phase 1: Quick Wins (1-2 hours)
- [ ] Add address extraction from detail pages
- [ ] Improve applicant name selectors
- [ ] Add logging to see what's being extracted

### Phase 2: Enhanced Matching (2-3 hours)
- [ ] Add permit type → company type inference
- [ ] Add address-based company search fallback
- [ ] Improve domain lookup with multiple strategies

### Phase 3: Testing & Optimization (1-2 hours)
- [ ] Test with real permits that have addresses
- [ ] Test with real permits that have applicant names
- [ ] Monitor email discovery rate
- [ ] Optimize credit usage

## 🎯 Expected Results

### Before Fixes
- Email Discovery Rate: **0%** (0/5 leads)
- Company Match Rate: **0%** (all "Unknown Org")
- Domain Discovery Rate: **0%**

### After Phase 1 Fixes
- Email Discovery Rate: **20-40%** (1-2/5 leads)
- Company Match Rate: **40-60%** (2-3/5 leads)
- Domain Discovery Rate: **30-50%**

### After Phase 2 Fixes
- Email Discovery Rate: **60-80%** (3-4/5 leads)
- Company Match Rate: **80-90%** (4-5/5 leads)
- Domain Discovery Rate: **70-85%**

## 🚀 Next Steps

1. **Run diagnostic** (already done):
   ```bash
   poetry run python scripts/e2e/diagnose_enrichment_issues.py
   ```

2. **Implement Phase 1 fixes**:
   - Improve address extraction
   - Improve applicant extraction
   - Add better logging

3. **Test with real permits**:
   - Use permits with known addresses
   - Verify applicant names are extracted
   - Check email discovery rate

4. **Implement Phase 2 fixes**:
   - Enhanced company matching
   - Fallback strategies
   - Better domain lookup

5. **Monitor and optimize**:
   - Track email discovery rate
   - Monitor credit usage
   - Optimize for best results

## 📊 Success Metrics

Track these metrics to measure improvement:
- **Email Discovery Rate**: % of leads with email addresses
- **Company Match Rate**: % of leads with valid company names (not "Unknown Org")
- **Domain Discovery Rate**: % of companies with domains found
- **Credit Efficiency**: Emails found per credit used

## 💡 Key Insights

1. **Configuration is correct** - The system is ready, just needs better data
2. **Data quality is the bottleneck** - Missing addresses/applicant names prevent enrichment
3. **Detail pages are key** - Most information is on detail pages, not results tables
4. **Fallback strategies needed** - Can't rely on single data source

## 🔗 Related Files

- `docs/ai/ENRICHMENT_EMAIL_FIX_PLAN.md` - Detailed fix plan
- `scripts/e2e/diagnose_enrichment_issues.py` - Diagnostic script
- `src/signal_engine/scrapers/accela_scraper.py` - Scraper to improve
- `src/signal_engine/enrichment/company_enricher.py` - Company matching to enhance
