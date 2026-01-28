# Phase 2 Qualification Scoring Enhancement V2

**Date:** January 14, 2026  
**Status:** ✅ **ENHANCED**

## Overview

This document describes the second round of enhancements to the Phase 2 qualification scoring system, addressing the issues identified in the initial analysis:
1. Auto-approval threshold too high (0.8)
2. Missing scoring factors (compliance urgency, building risk, recency)
3. Need for better data collection

## Changes Implemented

### 1. Lowered Auto-Approval Threshold ✅

**File:** `src/agents/nodes/human_review.py`

**Change:**
- **Before:** Auto-approve if `qualification_score >= 0.8`
- **After:** Auto-approve if `qualification_score >= 0.6`

**Rationale:**
- Previous threshold (0.8) was at theoretical maximum
- With enhanced scoring, 0.6 is more realistic and achievable
- Still maintains quality bar while allowing more leads to auto-approve

### 2. Enhanced Qualification Scoring ✅

**File:** `src/agents/orchestrator.py` - `qualification_check_node()`

**New Scoring Factors Added:**

#### Factor 5: Compliance Urgency (+0.15 weighted)
- Uses `compliance_urgency_score` from Researcher node
- Weighted by 0.15 (urgency score 0.0-1.0 × 0.15)
- Based on permit status, type, applicable codes, compliance gaps, building risk
- **Impact:** Adds up to +0.15 points for high-urgency permits

#### Factor 6: Building Type Risk (+0.1)
- High-risk building types get bonus points
- Types: hospital, data_center, school, nursing, care, assisted living, skilled nursing
- **Impact:** Adds +0.1 for high-risk facilities

#### Factor 7: Permit Recency (+0.05)
- Recently issued permits (within 30 days) get bonus
- Uses `issued_date` from permit data
- **Impact:** Adds +0.05 for time-sensitive permits

## Complete Scoring Logic

```python
score = 0.2  # Base score

# Factor 1: Good status (+0.3)
if status contains "issued", "approved", "active", "completed", "in progress":
    score += 0.3

# Factor 2: Progress status (+0.2)
if status contains "inspection", "passed", "scheduled", "ready":
    score += 0.2

# Factor 3: Fire-related (+0.2)
if permit_type contains fire keywords OR source contains "fire":
    score += 0.2
# MEP permits: +0.1 partial credit, then +0.2 fire-related

# Factor 4: Decision maker (+0.1)
if decision_maker exists:
    score += 0.1

# Factor 5: Compliance urgency (+0.15 weighted) NEW
compliance_urgency = state.get("compliance_urgency_score", 0.0)
score += compliance_urgency * 0.15

# Factor 6: Building type risk (+0.1) NEW
if building_type in high_risk_types:
    score += 0.1

# Factor 7: Permit recency (+0.05) NEW
if issued_date and (now - issued_date).days <= 30:
    score += 0.05

# Cap at 1.0
score = min(score, 1.0)
```

## Maximum Possible Score

**Before Enhancement:**
- Maximum: 0.2 + 0.3 + 0.2 + 0.2 + 0.1 = 1.0 (theoretical, rarely achieved)
- Typical: 0.2 + 0.3 + 0.2 = 0.7 (without decision maker)

**After Enhancement:**
- Maximum: 0.2 + 0.3 + 0.2 + 0.2 + 0.1 + 0.15 + 0.1 + 0.05 = 1.0
- More achievable paths to higher scores
- Better differentiation between leads

## Expected Impact

### Auto-Approval Rate
- **Before:** ~0% (threshold 0.8, max realistic score ~0.7)
- **After:** Expected 20-40% (threshold 0.6, more achievable)

### Score Distribution
- **Before:** Most leads 0.2-0.5
- **After:** More leads 0.5-0.7, some 0.7-0.9

### Lead Quality
- Better prioritization of high-urgency permits
- Recognition of high-risk building types
- Time-sensitive permits get boost

## Testing

**Test Script:** `scripts/e2e/test_enhanced_qualification_scoring.py`

**To Run:**
```bash
poetry run python scripts/e2e/test_enhanced_qualification_scoring.py
```

**What It Tests:**
- Enhanced scoring with all new factors
- Auto-approval threshold (0.6)
- Score distribution
- Compliance urgency integration
- Building type risk detection
- Permit recency calculation

## Data Collection Improvements Needed

While scoring is enhanced, data quality improvements are still recommended:

### High Priority
1. **Status Field Extraction**
   - Fix scrapers to extract correct status values
   - Map weird values ("34845", "Tunnel") to standard statuses
   - **Impact:** Enables Factor 1 & 2 scoring

2. **Applicant Name Extraction**
   - Enable `extract_applicant=True` in scraper configs
   - Improve detail page parsing
   - **Impact:** Enables decision maker finding (+0.1)

3. **Building Type Extraction**
   - Extract from permit detail pages
   - Map permit types to building categories
   - **Impact:** Enables Factor 6 scoring (+0.1)

4. **Issued Date Extraction**
   - Extract from permit data
   - Parse various date formats
   - **Impact:** Enables Factor 7 scoring (+0.05)

### Medium Priority
5. **Permit Value/Scope**
   - Extract project value if available
   - Use for prioritization
   - **Impact:** Could add value-based scoring

6. **Historical Context**
   - Track repeat customers
   - Previous permit history
   - **Impact:** Could add loyalty/relationship scoring

## Alignment with Phase 1.4

The enhanced scoring aligns with Phase 1.4 quality filter:
- ✅ Both check source field for "fire" module
- ✅ Both are lenient with real-world data
- ✅ Both handle data quality issues gracefully
- ✅ Quality filter (0.3 threshold) feeds into qualification (0.5 threshold)

## Next Steps

1. **Test with Real Data**
   - Run enhanced scoring test
   - Verify auto-approval rates
   - Check score distributions

2. **Monitor Performance**
   - Track qualification scores over time
   - Monitor auto-approval rates
   - Adjust thresholds if needed

3. **Improve Data Collection**
   - Fix status extraction
   - Enable applicant extraction
   - Extract building types
   - Extract issued dates

4. **Iterate**
   - Based on real-world results
   - Adjust scoring weights
   - Fine-tune thresholds

## Conclusion

✅ **Enhanced qualification scoring is implemented and ready for testing!**

- Auto-approval threshold lowered to realistic level (0.6)
- Three new scoring factors added
- Better differentiation between leads
- More achievable paths to higher scores
- Ready for production use after testing

---

**Enhancement Completed:** January 14, 2026  
**Status:** ✅ IMPLEMENTED  
**Testing:** ⏳ PENDING
