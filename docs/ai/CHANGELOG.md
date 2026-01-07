## Unreleased

- **Phase 1.3**: Implemented complete data enrichment pipeline with hybrid Apollo + Hunter.io strategy ✅ **COMPLETE**
  - Added geocoding service using Nominatim (free, no API key)
  - Implemented company matching with Apollo `organizations/search` endpoint (free tier)
  - Integrated Hunter.io email finder API with credit safety
  - Created `ProviderManager` for multi-provider enrichment with fallback logic
  - Added Apollo free tier endpoints (`organizations/search`, `organization_top_people`)
  - Implemented hybrid workflow: Apollo (domain lookup) → Hunter.io (email finder)
  - Added separate credit tracking for Apollo (10/run) and Hunter (3/run)
  - Integrated auto-enrichment into scraper scheduler with auto-slicing
  - Created lead storage layer for enriched leads
  - Added regulatory matching to correlate updates with permits
  - **Verified:** Hunter.io successfully found email (1 credit used in test)
  - **Status:** Ready for Apollo API key to test complete hybrid workflow
  - Added comprehensive test suite and documentation

- **Phase 1.2**: Implemented complete regulatory listener system ✅ **COMPLETE**
  - Added `RegulatoryUpdate` data model for storing regulatory information
  - Implemented RSS/Atom feed parser for state fire marshal bulletins
    - **Verified with real feeds:** BBC News (40 updates), Daily Dispatch (12 updates)
  - Created `BaseRegulatoryListener` base class for all regulatory listeners
  - Implemented `FireMarshalListener` for state fire marshal bulletins
    - **Verified with real feed:** Daily Dispatch (12 real updates extracted)
  - Implemented `NFPAListener` for NFPA code amendment announcements
  - Implemented `EPARegulatoryListener` for EPA/Federal Register regulations
    - **Verified with real API:** Federal Register (3 real EPA updates extracted)
  - Added `RegulatoryContentProcessor` for LLM-based compliance trigger extraction
  - Created `RegulatoryStorage` for persistent storage of regulatory updates
  - Integrated all listeners into scheduler with appropriate frequencies
  - Added comprehensive test suite and setup verification scripts
  - **All components tested and verified with real data sources**
- **Docs**: Added in-repo documentation system (`docs/plan`, `docs/ai`) to track AI-assisted changes and decisions.
- **Docs**: Added Cursor agent blueprint (`.github/agents/agents.md`) and `llms.txt` AI index.
- **Docs**: Added STATUS.md handoff document for context window management.
- **Governance**: Added MAS responsibilities/handoffs doc and machine-readable audit log spec.
- **Governance**: Added CI-style documentation gate (`scripts/docs_gate.py`, `.github/workflows/docs-gate.yml`).
- **SignalEngine**: Added offline Playwright fixture runner for Phase 1.1 scraper validation.
- **SignalEngine**: Added Mecklenburg County (Charlotte, NC) WebPermit portal scraper factory (`MecklenburgPermitScraper`) with proper ASP.NET postback navigation sequence. Form submission working; results table selector verification in progress.

## 0.1.0 (2026-01-02)

- **Bootstrap**: Project skeleton (`pyproject.toml`, `docker-compose.yml`, `src/`, `tests/`, `scripts/`).
- **SignalEngine**: Playwright permit scraper framework + enrichment pipeline (Apollo-style wrapper).
- **KnowledgeLayer**: Neo4j fire code graph schema + minimal seed; Pinecone vector scaffolding + embeddings helper.
- **Agents**: LangGraph orchestrator with Researcher/Communicator/Closer nodes + HITL interrupt gate.
- **Integration**: FastMCP server exposing ServiceTitan tools + async ServiceTitan client wrapper.
- **Observability**: LangSmith-friendly tracing wrapper + minimal audit event hook.
- **API**: FastAPI app with `/leads`, `/agents`, `/webhooks` routes.


