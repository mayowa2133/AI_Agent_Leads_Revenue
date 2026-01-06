# AORO (Autonomous Outcome-Based Revenue Orchestrator)

A stateful multi-agent system that discovers high-intent compliance triggers (permits, inspections, code updates), generates technical outreach, handles objections with regulatory context, and books qualified appointments into ServiceTitan via MCP.

## 🎯 Overview

AORO is an AI-powered revenue orchestration platform designed for compliance-driven industrial services, with an initial focus on **Commercial Fire Safety**. The system autonomously:

- **Discovers** high-intent leads through permit scraping and regulatory monitoring
- **Enriches** lead data with company information and decision-maker identification
- **Researches** applicable fire codes and compliance requirements
- **Generates** technical, compliance-focused outreach messages
- **Handles** objections with regulatory context and case studies
- **Books** qualified appointments directly into ServiceTitan CRM

## ✨ Features

### Signal Engine (Lead Discovery)
- **Permit Scrapers**: Playwright-based scrapers for municipal permit portals
- **Regulatory Listeners**: Monitor code updates and regulatory changes
- **Data Enrichment**: Apollo/Clearbit integration for company and decision-maker data
- **Qualification Scoring**: Automated lead scoring based on permit status and type

### Multi-Agent Workflow (LangGraph)
- **Researcher Agent**: Identifies applicable fire codes, compliance gaps, and relevant case studies
- **Communicator Agent**: Drafts technical, non-hype outreach messages
- **Closer Agent**: Handles objections with regulatory context and proposes next steps
- **Human-in-the-Loop (HITL)**: Approval gates for quality control and safety

### Knowledge Layer
- **Neo4j Graph Database**: Fire code relationships and compliance rules
- **Pinecone Vector Store**: Semantic search for case studies and regulatory context
- **Embeddings**: OpenAI-based embeddings for knowledge retrieval

### Integrations
- **ServiceTitan CRM**: OAuth-authenticated API client for booking appointments
- **MCP (Model Context Protocol)**: FastMCP server exposing CRM tools to agents
- **Calendar Sync**: Integration with calendar systems for availability

### Observability & Security
- **LangSmith Tracing**: Workflow observability and decision audit trails
- **Multi-Tenant Security**: Tenant-scoped sessions and data isolation
- **Audit Logging**: Comprehensive event logging for compliance

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Signal Engine (Phase 1)                 │
│  Permit Scrapers → Data Enrichment → Qualification Scoring  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Layer                           │
│         Neo4j (Graph)    │    Pinecone (Vectors)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Multi-Agent Workflow (Phase 2)                  │
│  Researcher → Communicator → HITL Gate → Closer             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP Integration (Phase 3)                       │
│         ServiceTitan CRM │ Calendar Sync                    │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
AI_Agent_Leads_Revenue/
├── pyproject.toml              # Poetry dependencies
├── poetry.lock                 # Locked dependencies
├── docker-compose.yml          # Local dev services (Neo4j, Postgres)
├── .env.example                # Environment variables template
├── README.md                   # This file
│
├── src/
│   ├── signal_engine/          # Phase 1: Lead Discovery
│   │   ├── scrapers/          # Permit & regulatory scrapers
│   │   │   ├── base_scraper.py
│   │   │   ├── permit_scraper.py
│   │   │   └── regulatory_scraper.py
│   │   ├── enrichment/        # Data enrichment pipeline
│   │   │   ├── company_enricher.py
│   │   │   └── apollo_client.py
│   │   └── models.py          # Data models
│   │
│   ├── knowledge/             # Knowledge Layer
│   │   ├── graph/             # Neo4j fire code graph
│   │   │   ├── fire_code_graph.py
│   │   │   ├── neo4j_client.py
│   │   │   └── schemas.py
│   │   └── vectors/           # Pinecone vector store
│   │       ├── pinecone_client.py
│   │       └── embeddings.py
│   │
│   ├── agents/                # Phase 2: Multi-Agent Workflow
│   │   ├── orchestrator.py   # LangGraph state machine
│   │   ├── state.py          # AOROState definition
│   │   ├── nodes/            # Agent nodes
│   │   │   ├── researcher.py
│   │   │   ├── communicator.py
│   │   │   ├── closer.py
│   │   │   └── human_review.py
│   │   └── tools/            # Agent tools
│   │       ├── case_study_search.py
│   │       ├── contact_finder.py
│   │       └── regulatory_lookup.py
│   │
│   ├── integrations/         # Phase 3: External Integrations
│   │   ├── mcp/              # MCP server
│   │   │   ├── server.py
│   │   │   ├── auth.py
│   │   │   └── tools/
│   │   │       ├── crm_tools.py
│   │   │       ├── calendar_tools.py
│   │   │       └── pricebook_tools.py
│   │   └── servicetitan/     # ServiceTitan API client
│   │       ├── client.py
│   │       └── models.py
│   │
│   ├── api/                  # FastAPI application
│   │   ├── main.py           # App factory
│   │   └── routes/
│   │       ├── leads.py      # Lead ingestion endpoints
│   │       ├── agents.py     # Agent workflow triggers
│   │       └── webhooks.py   # Webhook handlers
│   │
│   └── core/                 # Core utilities
│       ├── config.py         # Settings management
│       ├── security.py       # Multi-tenant security
│       ├── observability.py  # LangSmith integration
│       └── audit_log.py      # Audit logging
│
├── scripts/
│   ├── run_scraper_fixture.py    # Test scraper with local fixture
│   ├── run_scraper_job.py         # Run scraper job
│   ├── seed_knowledge_graph.py    # Seed Neo4j with fire codes
│   └── docs_gate.py               # Documentation gate check
│
├── tests/
│   ├── unit/                # Unit tests
│   └── fixtures/            # Test fixtures
│
└── docs/
    ├── plan/
    │   └── aoro_mvp_master_plan.md    # Master implementation plan
    └── ai/                            # AI engineering docs
        ├── README.md                  # Documentation hub
        ├── CHANGELOG.md               # Change log
        ├── WORKLOG.md                 # Work log
        ├── adr/                       # Architecture Decision Records
        ├── audit/                     # Audit schemas
        └── workflows/                 # Workflow documentation
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Poetry** (dependency management)
- **Docker & Docker Compose** (for local services)
- **Playwright** (for web scraping)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mayowa2133/AI_Agent_Leads_Revenue.git
   cd AI_Agent_Leads_Revenue
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Install Playwright browser**
   ```bash
   poetry run playwright install chromium
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your API keys and configuration
   ```

5. **Start local services**
   ```bash
   docker compose up -d
   ```
   This starts:
   - Neo4j on `http://localhost:7474` (web UI) and `bolt://localhost:7687`
   - Postgres on `localhost:5432`

### Configuration

Key environment variables (see `.env.example` for full list):

```bash
# OpenAI / LangSmith
OPENAI_API_KEY=your_key_here
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=aoro

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpassword

# Pinecone
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX=aoro-case-studies

# ServiceTitan
SERVICETITAN_CLIENT_ID=your_client_id
SERVICETITAN_CLIENT_SECRET=your_secret
SERVICETITAN_APP_KEY=your_app_key
SERVICETITAN_BASE_URL=https://api.servicetitan.com
SERVICETITAN_TENANT_ID=your_tenant_id
```

## 💻 Usage

### Run the API Server

```bash
poetry run uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Test Permit Scraper (Local, No Internet)

This uses a local HTML fixture to validate the scraper:

```bash
poetry run python scripts/run_scraper_fixture.py
```

### Seed Knowledge Graph

Populate Neo4j with fire code data:

```bash
poetry run python scripts/seed_knowledge_graph.py
```

### Run Scraper Job

Execute a scraper job:

```bash
poetry run python scripts/run_scraper_job.py
```

## 📡 API Endpoints

### Health Check
```bash
GET /healthz
```

### Lead Ingestion
```bash
POST /leads/ingest
Content-Type: application/json

{
  "tenant_id": "demo",
  "permit": {
    "permit_id": "PER-123",
    "applicant_name": "ABC Company",
    "permit_type": "Fire Safety Inspection",
    "status": "Issued",
    "issue_date": "2024-01-15",
    "address": "123 Main St, City, State"
  }
}
```

### Get Lead
```bash
GET /leads/{lead_id}
```

### Run Agent Workflow
```bash
POST /agents/run
Content-Type: application/json

{
  "tenant_id": "demo",
  "lead_id": "lead-123",
  "company_name": "ABC Company",
  "permit_data": {
    "permit_id": "PER-123",
    "permit_type": "Fire Safety Inspection",
    "status": "Issued"
  },
  "outreach_channel": "email"
}
```

## 🧪 Testing

Run tests:
```bash
poetry run pytest
```

Run with coverage:
```bash
poetry run pytest --cov=src --cov-report=html
```

## 🔧 Development

### Code Quality

- **Linting**: `poetry run ruff check src tests`
- **Type Checking**: `poetry run mypy src`
- **Formatting**: `poetry run ruff format src tests`

### Compile Check

Quick syntax check:
```bash
python -m compileall -q src tests
```

### Documentation Gate

Check documentation changes:
```bash
python scripts/docs_gate.py --show-changes
```

## 📚 Documentation

- **Master Plan**: [`docs/plan/aoro_mvp_master_plan.md`](docs/plan/aoro_mvp_master_plan.md)
- **AI Engineering Hub**: [`docs/ai/README.md`](docs/ai/README.md)
- **Changelog**: [`docs/ai/CHANGELOG.md`](docs/ai/CHANGELOG.md)
- **Work Log**: [`docs/ai/WORKLOG.md`](docs/ai/WORKLOG.md)
- **Architecture Decision Records**: [`docs/ai/adr/`](docs/ai/adr/)
- **Multi-Agent Responsibilities**: [`docs/ai/multi_agent_responsibilities.md`](docs/ai/multi_agent_responsibilities.md)

## 🏛️ Architecture Decisions

Key architectural choices are documented in ADRs:
- **ADR-0001**: MVP Scope and Architecture ([`docs/ai/adr/0001-mvp-scope-and-architecture.md`](docs/ai/adr/0001-mvp-scope-and-architecture.md))

## 🔐 Security

- Multi-tenant isolation via tenant-scoped sessions
- OAuth authentication for ServiceTitan integration
- Environment-based secret management
- Audit logging for compliance

## 🤝 Contributing

1. Follow the code quality standards (ruff, mypy)
2. Update documentation for non-trivial changes
3. Add tests for new features
4. Update `docs/ai/CHANGELOG.md` and `docs/ai/WORKLOG.md`
5. Create ADRs for architectural decisions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [FastMCP](https://github.com/jlowin/fastmcp) - Model Context Protocol server
- [Neo4j](https://neo4j.com/) - Graph database
- [Pinecone](https://www.pinecone.io/) - Vector database
- [Playwright](https://playwright.dev/) - Web automation

---

**Status**: MVP - Active Development

For questions or issues, please open an issue on GitHub.
