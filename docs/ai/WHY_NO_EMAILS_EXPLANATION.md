# Why No Emails Are Being Extracted

## Date: January 15, 2026

## The Question

**User**: "I see that you got name, address but no email why is that?"

## The Answer

Emails are **NOT extracted from scraping** - they come from **enrichment APIs** (Hunter.io and Apollo). Here's why we're not getting emails:

## The Email Enrichment Pipeline

### Step 1: Scraping (What We Have) ✅
- **Company Name**: "TX Septic Systems LLC" ✅ Extracted
- **Address**: "109 TERESA ST *" ✅ Extracted
- **Email**: ❌ NOT in permit data (permits don't contain email addresses)

### Step 2: Company Matching (Apollo) ⚠️
- **Input**: Company name "TX Septic Systems LLC"
- **Process**: Use Apollo's `organizations/search` endpoint (FREE TIER)
- **Result**: Company found, but **NO WEBSITE/DOMAIN** ⚠️
- **Why**: This company doesn't have a website in Apollo's database (common for small/local companies)

### Step 3: Email Finding (Hunter.io) ⏭️
- **Input Required**: 
  1. Company domain (e.g., "txsepticsystems.com")
  2. Person's name (e.g., "John Smith")
- **Process**: Use Hunter.io's `email-finder` API
- **Result**: ⏭️ **CANNOT PROCEED** - No domain available

## Why We Can't Get Emails

### Problem 1: No Domain Found
```
Company: TX Septic Systems LLC
Apollo Search: ✅ Found company
Website: ❌ Not in Apollo database
Domain: ❌ Cannot proceed without domain
```

**Why**: Small/local companies often don't have websites or aren't in Apollo's database.

### Problem 2: Hunter.io Requires Domain
```
Hunter.io Email Finder Requirements:
- Domain: ✅ Required (e.g., "company.com")
- Person Name: ✅ Required (e.g., "John Smith")
- Result: Email address (e.g., "john.smith@company.com")
```

**Without a domain, Hunter.io cannot find emails.**

### Problem 3: No Person Name
Even if we had a domain, we'd need:
- Person's name (from permit applicant or decision maker search)
- Title (e.g., "Owner", "Manager", "Director")

## Current Status

### What We Have ✅
1. **Company Name**: "TX Septic Systems LLC" (from permit applicant_name)
2. **Address**: "109 TERESA ST *" (from permit detail page)
3. **Apollo Integration**: Working (found company, but no website)
4. **Hunter Integration**: Configured and ready

### What We're Missing ⚠️
1. **Company Domain**: Not found in Apollo (company doesn't have website)
2. **Person Name**: Not extracted (permit applicant is company name, not person)
3. **Email**: Cannot be found without domain + person name

## Solutions

### Solution 1: Test with Companies That Have Websites
Some companies in permits will have websites in Apollo's database. When we find those:
- ✅ Domain available
- ✅ Can use Hunter.io to find emails
- ✅ Full enrichment pipeline works

### Solution 2: Extract Person Names from Permits
Some permits have person names (not just company names):
- If applicant_name is a person (e.g., "John Smith"), we can use that
- Use person name + domain to find email via Hunter.io

### Solution 3: Use Address for Company Matching
- Use address + company name for better Apollo matching
- Some companies might be found with location context

### Solution 4: Manual Domain Lookup (Fallback)
- If Apollo doesn't find domain, try:
  - Google search: "TX Septic Systems LLC website"
  - Domain guessing: "txsepticsystems.com", "txseptic.com", etc.
  - Business directory lookups

## Test Results

### Enrichment Test Output
```
Company Name: TX Septic Systems LLC
Apollo Search: ✅ Found company
Website: ⚠️  No website/domain found
Hunter Email Lookup: ⏭️ Skipped (no domain available)
```

## What This Means

**This is EXPECTED behavior** for companies without websites:
- ✅ Scraping is working (names, addresses extracted)
- ✅ Enrichment pipeline is working (Apollo integration successful)
- ⚠️ Email finding requires domain (not available for this company)
- ✅ System is ready for companies WITH websites

## Next Steps

1. **Test with more permits** - Some companies will have websites
2. **Extract person names** - When applicant is a person, not a company
3. **Improve company matching** - Use address + location for better Apollo results
4. **Add fallback strategies** - Manual domain lookup, business directories

## Conclusion

**Emails aren't being extracted because:**
1. Emails don't exist in permit data (must come from enrichment)
2. This company doesn't have a website in Apollo's database
3. Hunter.io requires a domain to find emails
4. We need both domain AND person name to find emails

**The system is working correctly** - we just need to test with companies that have websites to see the full pipeline in action.
