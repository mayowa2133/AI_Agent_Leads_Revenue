# Extraction Improvements Evaluation & Implementation

**Date:** January 15, 2026  
**Status:** ✅ **XPath Fix Implemented** | Other solutions evaluated and prioritized

## Executive Summary

I understand the advice and have evaluated each solution. The recommendations are **highly valuable** and directly address our cascade failure problems. Here's the evaluation and implementation status:

---

## Solution Evaluation

### 1. ✅ **XPath Following-Sibling Fix (Step 3)** - **IMPLEMENTED**

**Problem:** Extracting labels ("Location:") instead of values ("123 Main St")

**Solution:** Use XPath `following-sibling` axis to find value elements that follow label elements

**Status:** ✅ **IMPLEMENTED**

**Implementation:**
- Added XPath-based extraction as **Strategy 0** (highest priority) in `_extract_address_from_detail()`
- Uses `document.evaluate()` with XPath to find:
  - Labels containing "address" or "location" → following sibling `span`, `div`, `input`, or `textarea`
  - Table cells (`td`) containing "address" or "location" → following sibling `td`
- Validates extracted text to ensure it's not a label and looks like an address

**File:** `src/signal_engine/scrapers/permit_scraper.py` (lines ~616-660)

**Expected Impact:** Should significantly improve address extraction by correctly finding values instead of labels

**Next Step:** Test with real permits to verify improvement

---

### 2. ⏳ **State-Based Waits (Detail Page Navigation)** - **PARTIALLY IMPLEMENTED**

**Problem:** Hard timeouts (15s) causing navigation failures

**Solution:** Use `wait_for_load_state("networkidle")` and `wait_for_selector()` instead of fixed sleeps

**Status:** ⚠️ **PARTIALLY IMPLEMENTED** - We already use `networkidle` but could improve

**Current Implementation:**
- Already using `page.wait_for_load_state("networkidle")` in many places
- Already using `page.wait_for_timeout()` as fallback
- Could improve by waiting for specific data elements instead of generic `networkidle`

**Priority:** **MEDIUM** - Current implementation works but could be more robust

**Next Step:** Add `wait_for_selector()` for specific data elements (e.g., `wait_for_selector('[id*="address"]')`)

---

### 3. ⏳ **LLM-Based Company Name Extraction (Step 4)** - **EVALUATED**

**Problem:** 9% success rate with regex patterns

**Solution:** Use Few-Shot LLM prompting to extract company names from messy HTML

**Status:** ⚠️ **EVALUATED** - High value but adds cost

**Evaluation:**
- **Pros:**
  - Handles messy HTML better than regex
  - Can learn from examples
  - More flexible for different portal structures
- **Cons:**
  - Adds API costs (LLM calls)
  - Slower than regex
  - Requires prompt engineering and examples

**Priority:** **MEDIUM-HIGH** - Good fallback when regex fails

**Recommendation:** 
- Keep regex as primary (fast, free)
- Add LLM extraction as fallback for permits where regex fails
- Use structured output (Pydantic) for validation

**Next Step:** Implement LLM fallback in `_extract_applicant_from_detail()` when regex returns None

---

### 4. ⏳ **SOS APIs for Small LLC Lookup (Step 5 & 6)** - **EVALUATED**

**Problem:** Small LLCs (like "TX Septic Systems LLC") don't have websites, so Apollo fails

**Solution:** Use Secretary of State APIs (Middesk, iDenfy) to find registered agent and principal office address

**Status:** ⚠️ **EVALUATED** - High value for enrichment pipeline

**Evaluation:**
- **Pros:**
  - Solves the "no website" problem
  - Provides registered agent name (person name for Hunter.io!)
  - Provides principal office address
  - More reliable than website lookup for small businesses
- **Cons:**
  - Requires API integration (Middesk, iDenfy)
  - May have costs (need to check free tiers)
  - State-by-state variations

**Priority:** **HIGH** - Directly solves enrichment pipeline blocker

**Recommendation:**
- Research Middesk/iDenfy free tiers
- Implement as fallback when Apollo doesn't find domain
- Use registered agent name for Hunter.io email finding

**Next Step:** Research SOS API options and implement waterfall: Apollo → SOS API → Hunter.io

---

### 5. ✅ **Open Data APIs (Municipal APIs)** - **ALREADY IMPLEMENTED!**

**Problem:** Scraping is brittle, labels vs values, timeouts, etc.

**Solution:** Use municipal Open Data APIs (Socrata, CKAN, ArcGIS) for structured JSON data

**Status:** ✅ **ALREADY IMPLEMENTED** (Phase 1.4.3)

**Current Implementation:**
- ✅ `SocrataPermitClient` - For 100+ cities using Socrata
- ✅ `CKANPermitClient` - For 50+ cities using CKAN  
- ✅ `CustomAPIPermitClient` - For custom REST APIs
- ✅ `UnifiedPermitIngestion` - Single interface for scrapers + APIs
- ✅ **Tested:** Seattle Socrata API (47 permits extracted) ✅

**Files:**
- `src/signal_engine/api/socrata_client.py`
- `src/signal_engine/api/ckan_client.py`
- `src/signal_engine/api/unified_ingestion.py`

**Recommendation for San Antonio:**
- **Check if San Antonio has Open Data API** (Socrata, CKAN, or custom)
- If yes, **switch from scraping to API** - this would instantly solve all extraction problems!
- If no, continue with improved scraping (XPath fix)

**Next Step:** Research San Antonio Open Data portal and switch if available

---

## Implementation Priority

### ✅ **Completed (High Priority)**
1. ✅ **XPath Following-Sibling Fix** - Implemented in `_extract_address_from_detail()`

### 🔄 **In Progress (High Priority)**
2. ⏳ **Check San Antonio Open Data API** - Research and switch if available
3. ⏳ **SOS API Integration** - Research Middesk/iDenfy and implement waterfall

### 📋 **Planned (Medium Priority)**
4. ⏳ **LLM Fallback for Company Names** - Add when regex fails
5. ⏳ **Improved State-Based Waits** - Add `wait_for_selector()` for specific elements

---

## Expected Impact

### Immediate (XPath Fix)
- **Address Extraction:** Should improve from 0/11 (0%) to potentially 5-8/11 (45-73%)
- **Root Cause:** Directly addresses "extracting labels instead of values" problem

### Short-term (Open Data API Switch)
- **If San Antonio has API:** 100% success rate (structured JSON, no scraping issues)
- **All Problems Solved:** No labels vs values, no timeouts, no DOM navigation

### Medium-term (SOS APIs)
- **Enrichment Pipeline:** Should improve from 0/11 emails to 3-5/11 (27-45%)
- **Root Cause:** Provides registered agent names and addresses when Apollo fails

---

## Next Actions

1. **Test XPath Fix** (Immediate)
   ```bash
   poetry run python scripts/e2e/test_improved_extraction.py
   ```
   - Verify address extraction improved
   - Check if we're now extracting values instead of labels

2. **Research San Antonio Open Data** (High Priority)
   - Check: https://data.sanantonio.gov (Socrata)
   - Check: https://www.sanantonio.gov/opendata (if exists)
   - If found, switch `AccelaScraper` to use API instead

3. **Research SOS APIs** (High Priority)
   - Check Middesk free tier
   - Check iDenfy pricing
   - Implement waterfall: Apollo → SOS → Hunter.io

4. **Implement LLM Fallback** (Medium Priority)
   - Add to `_extract_applicant_from_detail()` when regex returns None
   - Use structured output (Pydantic) for validation

---

## Conclusion

**The advice is excellent and directly addresses our problems:**

1. ✅ **XPath Fix** - **IMPLEMENTED** - Should solve label vs value extraction
2. ✅ **Open Data APIs** - **ALREADY IMPLEMENTED** - Should use for San Antonio if available
3. ⏳ **SOS APIs** - **HIGH VALUE** - Should implement as enrichment fallback
4. ⏳ **LLM Extraction** - **GOOD FALLBACK** - Should add when regex fails
5. ⏳ **State-Based Waits** - **IMPROVEMENT** - Current works but could be better

**The cascade failure can be broken by:**
- **Immediate:** XPath fix (implemented) + Open Data API switch (if available)
- **Short-term:** SOS API integration for enrichment
- **Long-term:** LLM fallbacks for edge cases
