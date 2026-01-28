# Waterfall Enrichment Plan (Person + Domain Resolution)

**Goal:** Resolve the "Missing Person Name + Domain" gap by adding a staged, low-cost waterfall that uses government data first, then cheap domain discovery, then LLM parsing of search snippets, and finally Hunter email discovery.

## Phase 1 (Immediate, Fast-to-Impact)

### Objective
Prove we can generate emails by adding two low-cost steps:
1) **Domain discovery** via Clearbit autocomplete (fallback to Apollo).
2) **Person discovery** via LLM parsing of search snippets when we have a domain but no person.

### Scope (Phase 1)
1. **Search Snippet Retrieval**
   - Use Google Custom Search (CSE) to fetch top results for:
     - `"[Company Name]" owner OR president OR director`
     - `"[Company Name]" "[City]" owner`
   - Store snippets and URLs.

2. **LLM Snippet Parsing**
   - Prompt an LLM to extract a decision-maker name + title + source URL.
   - Require strict JSON output.
   - Apply confidence threshold (e.g., `>= 0.75`) before use.

3. **Email Discovery**
   - If `person_name + domain` exists, call Hunter Email Finder.
   - Track source and confidence in logs.

### Success Criteria
- At least one email found in the CKAN test batch.
- Logs show which waterfall stage produced the person name and domain.

### Phase 1 Deliverables
- `search_snippet_client.py` (Google CSE)
- `snippet_llm_parser.py` (LLM extraction)
- Integration into enrichment pipeline (`find_decision_maker`)
- Updated E2E test logs confirming results

---

## Phase 2 (Government Sources, High Confidence)

### Objective
Use authoritative records to find people:
- SBA Small Business Search (SBS)
- Texas Comptroller (PIR officers) for TX permits

### Deliverables
- `sbs_client.py`
- `tx_comptroller_client.py`
- Integration into waterfall (before LLM snippet parsing)

---

## Phase 3 (Geo Bridge + Scale)

### Objective
Resolve business name from address and scale coverage:
- Nominatim/Geoapify POI resolution
- Local contractor datasets (Arlington, Dallas)

### Deliverables
- `geo_business_lookup.py`
- CKAN/Socrata-specific pipelines for contractor lists

---

## Waterfall Order (Final Target)

1. **Gov sources:** SBS → TX Comptroller  
2. **Domain:** Apollo → Clearbit → domain guess  
3. **Person:** Gov officers → LLM snippet extraction  
4. **Hunter:** Email finder + verifier  

---

## Tracking & Observability

Add `source_trace` and `confidence` to enrichment output, e.g.:

```json
{
  "person_name": "Jane Doe",
  "domain": "example.com",
  "source_trace": {
    "domain": "clearbit",
    "person": "llm_snippet"
  },
  "confidence": 0.78
}
```

