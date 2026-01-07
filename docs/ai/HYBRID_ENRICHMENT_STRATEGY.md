# Hybrid Enrichment Strategy: Apollo + Hunter.io

## Overview

This document explains the **"Free Tier Hybrid Pipeline"** that uses Apollo's free endpoints to find company domains, then Hunter.io to find emails. This strategy allows Phase 1.3 to work without paid plans.

## The Problem

Hunter.io requires a **company domain** to find emails, but permits don't always have company websites. We need a way to find domains from company names.

## The Solution: Hybrid Pipeline

Use **Apollo's free tier endpoints** as a "bridge" to find domains, then use **Hunter.io** to find emails.

### Workflow

```mermaid
flowchart LR
    Permit[Permit Data] -->|Extract| CompanyName[Company Name]
    CompanyName -->|Apollo Free| Apollo[organizations/search]
    Apollo -->|Returns| Domain[Company Domain]
    Domain -->|Hunter.io| Hunter[email-finder]
    Hunter -->|Returns| Email[Email Address]
```

### Step-by-Step Process

| Step | Platform | Endpoint | Cost | Purpose |
|------|----------|----------|------|---------|
| **1. Extract** | - | - | Free | Get company name from `applicant_name` |
| **2. Find Domain** | Apollo | `organizations/search` | **0 Credits** (Free tier) | Convert company name → domain |
| **3. Find Email** | Hunter.io | `email-finder` | **1 Credit** (if found) | Get email with name + domain |

## Apollo Free Tier Endpoints Used

### 1. `organizations/search` (The "Gold Mine")

**Purpose:** Convert company name to website domain

**Endpoint:** `POST /api/v1/organizations/search`

**Request:**
```json
{
  "api_key": "your_key",
  "q_organization_name": "Mecklenburg Electric LLC",
  "q_location": "Charlotte, NC",
  "page": 1,
  "per_page": 1
}
```

**Response:**
```json
{
  "organizations": [{
    "name": "Mecklenburg Electric LLC",
    "website_url": "https://www.meckelec.com",
    "primary_domain": "meckelec.com",
    ...
  }]
}
```

**Cost:** 0 credits (free tier endpoint)

**Usage:** Extract `website_url` or `primary_domain` → pass to Hunter.io

### 2. `organization_top_people` (Optional)

**Purpose:** Get names of owners/managers at a company

**Endpoint:** `POST /api/v1/mixed_people/organization_top_people`

**Cost:** 0 credits (free tier, read-only)

**Usage:** Get decision maker names, then use Hunter.io to find their emails

**Note:** Emails are hidden on free tier (`[email hidden]`), but names are available.

## Implementation

### Code Flow

1. **Company Matching** (`match_company()`):
   - Extracts company name from permit
   - Calls Apollo `organizations/search` to find domain
   - Returns `Company` object with `website` field

2. **Decision Maker Finding** (`find_decision_maker()`):
   - If company has domain + permit has person name → Use Hunter.io
   - If no domain → Try Apollo to find domain first
   - Falls back gracefully if no domain found

3. **Provider Manager** (`ProviderManager`):
   - Manages both Apollo and Hunter.io credits separately
   - Apollo: Max 10 credits per run (free tier: 110/month)
   - Hunter: Max 3 credits per run (free tier: 50/month)

## Credit Management

### Apollo Credits (Free Tier: 110/month)

- `organizations/search`: **0 credits** (free tier endpoint)
- `organization_top_people`: **0 credits** (free tier endpoint)
- Other endpoints: May use credits (check Apollo docs)

**Safety:** `max_apollo_credits_per_run=10` (configurable)

### Hunter.io Credits (Free Tier: 50/month)

- `email-finder`: **1 credit** (only if email found)
- No email found (404): **0 credits**

**Safety:** `max_credits_per_run=3` (configurable)

## Configuration

### `.env` Settings

```env
# Apollo (Free Tier: 110 credits/month)
APOLLO_API_KEY=your_apollo_key_here

# Hunter.io (Free Tier: 50 credits/month)
HUNTER_API_KEY=your_hunter_key_here

# Safety Limits
MAX_CREDITS_PER_RUN=3          # Hunter.io credits
MAX_APOLLO_CREDITS_PER_RUN=10  # Apollo credits

# Provider Priority
ENRICHMENT_PROVIDER_PRIORITY=auto  # Use hybrid strategy
ENRICHMENT_DRY_RUN=false           # Set to true for testing
```

## Testing

### Test Hybrid Workflow

```bash
# Test the complete hybrid pipeline
poetry run python scripts/test_hybrid_enrichment.py
```

This will:
1. Test Apollo domain lookup
2. Test full enrichment with Apollo → Hunter.io
3. Show credit usage for both providers

### Test with Real Permits

```bash
# Test with 1-2 real permits
poetry run python scripts/test_enrichment_real_permits.py
```

## Success Criteria

✅ **Phase 1.3 Complete When:**
- Apollo finds domains from company names
- Hunter.io finds emails using name + domain
- Both credit limits are enforced
- System works end-to-end with real permits

## Credit Usage Example

For **1 permit** with company name:

1. **Apollo `organizations/search`**: 0 credits (free tier)
   - Input: "Mecklenburg Electric LLC"
   - Output: `meckelec.com`

2. **Hunter.io `email-finder`**: 1 credit (if email found)
   - Input: "John Smith" + "meckelec.com"
   - Output: `john.smith@meckelec.com`

**Total:** 1 Hunter credit per successful email find

## Limitations

1. **Apollo Free Tier:**
   - 110 credits/month limit
   - Some endpoints may not work on free tier
   - Emails hidden on free tier (`[email hidden]`)

2. **Hunter.io Free Tier:**
   - 50 credits/month limit
   - Requires domain to search
   - Only charges when email found

3. **Domain Finding:**
   - Apollo may not find domain for all companies
   - Small/local companies may not be in Apollo database
   - Fallback: Manual research for high-value leads

## Best Practices

1. **Start Small:**
   - Test with 1-2 permits first
   - Verify domains are found correctly
   - Check credit usage in dashboards

2. **Monitor Credits:**
   - Apollo: Check https://app.apollo.io/#/settings/integrations/api
   - Hunter: Check https://hunter.io/dashboard
   - Adjust limits if needed

3. **Prioritize Leads:**
   - Use enrichment on high-value permits first
   - Skip permits without company names
   - Manual research for critical leads

4. **Credit Conservation:**
   - Apollo domain lookup is free - use it first
   - Only use Hunter.io when domain is found
   - Skip if no domain (saves Hunter credits)

## Next Steps

1. ✅ Hybrid strategy implemented
2. ⏭️ Test with Apollo API key (when available)
3. ⏭️ Verify domain lookup works
4. ⏭️ Test end-to-end with real permits
5. ⏭️ Monitor credit usage
6. ⏭️ Adjust limits as needed

---

**Status:** ✅ Implementation Complete
**Ready for:** Testing with Apollo API key

