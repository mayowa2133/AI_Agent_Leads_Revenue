## AORO (Autonomous Outcome-Based Revenue Orchestrator)

A stateful multi-agent system that discovers high-intent compliance triggers (permits, inspections, code updates), generates technical outreach, handles objections with regulatory context, and books qualified appointments into ServiceTitan via MCP.

### Documentation

- **Master plan**: `docs/plan/aoro_mvp_master_plan.md`
- **AI engineering audit trail**: `docs/ai/README.md` (includes changelog, worklog, ADRs)

### Local development

- **Prereqs**: Python 3.11+, Poetry, Docker
- **Services**: Neo4j + Postgres via `docker-compose.yml`

### Test Phase 1.1 (Permit Scraper) locally (no internet)

This uses a local HTML fixture and Playwright to validate the scraper end-to-end:

```bash
poetry run playwright install chromium
poetry run python scripts/run_scraper_fixture.py
```

### Environment

Copy `.env.example` to `.env` and fill in values.

### Run services

```bash
docker compose up -d
```

### Run API (dev)

```bash
poetry install
poetry run uvicorn src.api.main:app --reload --port 8000
```


