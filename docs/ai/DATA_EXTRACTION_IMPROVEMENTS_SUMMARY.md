# Data Extraction Improvements Summary

## Date: January 14, 2026

## Overview
This document summarizes the improvements made to permit data extraction to enable better enrichment and email discovery.

## Problems Identified

### Original Issues
1. **Status Selector Error**: Status was being extracted from wrong column (column 6 instead of column 7)
2. **Address Validation Error**: `PermitData` model requires string, but `None` was being passed
3. **Code Structure Issue**: Detail link extraction code was in wrong location
4. **JavaScript Postback Navigation**: Detail pages were navigating to error pages instead of actual detail pages
5. **Label Extraction**: Extraction functions were capturing label text ("Applicant:", "Location") instead of actual values

## Improvements Implemented

### 1. Fixed Status Selector ✅
- **Before**: `td:nth-child(6)` (Project Name column)
- **After**: `td:nth-child(7)` (Status column, cell index 6)
- **Result**: Status extraction now works correctly

### 2. Fixed Address Validation ✅
- **Before**: Passing `None` for empty addresses (caused Pydantic validation error)
- **After**: Passing empty string `""` for missing addresses
- **Result**: Permits can now be created even when address is missing

### 3. Fixed Code Structure ✅
- **Before**: Detail link extraction code was after a `raise` statement
- **After**: Moved to correct location within extraction block
- **Result**: Detail URLs are now being captured correctly

### 4. Fixed JavaScript Postback Navigation ✅
- **Before**: Clicking detail links navigated to error pages
- **After**: Proper navigation handling with `expect_navigation` and error page detection
- **Result**: Successfully navigating to actual detail pages (`CapDetail.aspx`)

### 5. Enhanced Extraction Functions ✅
- **Added**: Multiple extraction strategies (ID-based, label-based, table-based, DOM-wide search)
- **Added**: Label filtering to skip common label patterns
- **Added**: Better validation to filter out labels and placeholders
- **Added**: Address validation (checks for numbers and street words)
- **Result**: Extraction functions are more robust, but still need refinement for Accela's specific structure

### 6. Implemented Second Pass Extraction ✅
- **Added**: `_extract_detail_page_data()` method for second pass extraction
- **Added**: Proper navigation back to results page after each detail page visit
- **Added**: JavaScript postback link finding on results page
- **Result**: Infrastructure is in place for detail page extraction

## Current Extraction Status

### What's Working ✅
1. **Permit Extraction**: 11/13 permits extracted from results table
2. **Status Extraction**: Working correctly (using correct column)
3. **Detail Page Navigation**: Successfully navigating to detail pages
4. **Extraction Infrastructure**: All extraction functions are running

### What's Not Working Yet ⚠️
1. **Address Extraction**: 0/11 permits have addresses
   - Detail pages are being visited
   - Extraction functions are running
   - But not finding actual address values (finding labels instead)

2. **Applicant Name Extraction**: 0/11 permits have applicant names
   - Detail pages are being visited
   - Extraction functions are running
   - But not finding actual name values (finding labels instead)

3. **Email Extraction**: 0/11 permits have emails
   - **Expected**: Emails come from enrichment APIs (Hunter.io, Apollo), not scraping
   - **Requirement**: Need addresses and applicant names first to enable enrichment

## Root Cause Analysis

### Why Addresses/Names Aren't Being Extracted

The extraction functions are:
1. ✅ Successfully navigating to detail pages
2. ✅ Finding elements with "applicant" or "address" in their IDs/labels
3. ❌ But extracting the label text instead of the associated value

**Possible Reasons**:
1. **HTML Structure**: Accela may use a different structure than expected
2. **Dynamic Content**: Data might be loaded via JavaScript after page load
3. **Tab/Section Navigation**: Data might be in different tabs that need to be clicked
4. **Iframe Content**: Data might be in iframes
5. **Permit Type Variation**: These specific permit types (State License, MEP Trade) might not have addresses/applicants in their detail pages

## Next Steps to Get Names, Addresses, and Emails

### Immediate Actions Needed

1. **Inspect Actual HTML Structure**
   - Manually inspect detail pages to understand the exact HTML structure
   - Identify where addresses and applicant names are actually stored
   - Create specific selectors for Accela's structure

2. **Test Different Permit Types**
   - Try Building permits, Fire permits, or other types that might have better-structured data
   - Some permit types may have addresses/applicants in different locations

3. **Handle Tab Navigation**
   - Accela detail pages often have tabs (General, Contacts, Addresses, etc.)
   - May need to click tabs to access the data

4. **Improve Selectors**
   - Create Accela-specific selectors based on actual HTML structure
   - May need to use more specific CSS selectors or XPath

### Long-term Improvements

1. **Machine Learning Approach**
   - Train a model to identify name/address patterns in HTML
   - More robust than rule-based extraction

2. **Multiple Portal Support**
   - Different cities may structure data differently
   - Need portal-specific extraction strategies

3. **Fallback Strategies**
   - If detail pages don't have data, try other sources
   - Company name inference from permit type
   - Address geocoding from permit location

## Impact on Email Discovery

### Current Pipeline
```
Permit Data → Company Matching → Domain Lookup → Email Discovery
     ↓              ↓                  ↓              ↓
  Missing        Fails            Fails          Fails
Addresses/Names
```

### Required Pipeline
```
Permit Data → Company Matching → Domain Lookup → Email Discovery
     ↓              ↓                  ↓              ↓
Has Address    Company Found      Domain Found    Email Found
Has Name       (via address)      (via Apollo)    (via Hunter)
```

### Why This Matters

1. **Addresses** are needed for:
   - Geocoding to find location
   - Company matching (matching by address)
   - Building type inference

2. **Applicant Names** are needed for:
   - Finding decision makers (person name + company domain)
   - Hunter.io email lookup (requires name + domain)

3. **Emails** come from:
   - **Hunter.io**: Requires person name + company domain
   - **Apollo**: Can find decision makers by company + title, but emails may be hidden on free tier

## Conclusion

### What We've Accomplished ✅
- Fixed critical bugs preventing permit extraction
- Implemented robust detail page navigation
- Created comprehensive extraction infrastructure
- Added label filtering and validation

### What Still Needs Work 🔧
- Refine selectors to extract actual values instead of labels
- Handle Accela's specific HTML structure
- Potentially handle tab navigation on detail pages
- Test with different permit types

### Expected Outcome Once Fixed 🎯
Once we can extract actual addresses and applicant names:
1. **Company Matching** will work (using addresses)
2. **Domain Lookup** will work (Apollo can find domains from company names)
3. **Email Discovery** will work (Hunter.io can find emails with name + domain)
4. **Enrichment Pipeline** will be fully functional

The infrastructure is in place - we just need to refine the selectors to match Accela's actual HTML structure.
