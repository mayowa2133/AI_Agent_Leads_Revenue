## Unreleased

- **Docs**: Added in-repo documentation system (`docs/plan`, `docs/ai`) to track AI-assisted changes and decisions.
- **Docs**: Added Cursor agent blueprint (`.github/agents/agents.md`) and `llms.txt` AI index.
- **Governance**: Added MAS responsibilities/handoffs doc and machine-readable audit log spec.
- **Governance**: Added CI-style documentation gate (`scripts/docs_gate.py`, `.github/workflows/docs-gate.yml`).
- **SignalEngine**: Added offline Playwright fixture runner for Phase 1.1 scraper validation.

## 0.1.0 (2026-01-02)

- **Bootstrap**: Project skeleton (`pyproject.toml`, `docker-compose.yml`, `src/`, `tests/`, `scripts/`).
- **SignalEngine**: Playwright permit scraper framework + enrichment pipeline (Apollo-style wrapper).
- **KnowledgeLayer**: Neo4j fire code graph schema + minimal seed; Pinecone vector scaffolding + embeddings helper.
- **Agents**: LangGraph orchestrator with Researcher/Communicator/Closer nodes + HITL interrupt gate.
- **Integration**: FastMCP server exposing ServiceTitan tools + async ServiceTitan client wrapper.
- **Observability**: LangSmith-friendly tracing wrapper + minimal audit event hook.
- **API**: FastAPI app with `/leads`, `/agents`, `/webhooks` routes.


