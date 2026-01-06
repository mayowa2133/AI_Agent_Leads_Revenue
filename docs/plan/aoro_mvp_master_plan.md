---
source: "copied from /Users/mayowaadesanya/.cursor/plans/aoro_mvp_implementation_77308705.plan.md"
note: "Do not edit the source plan file; this is the project-local copy for documentation."
---

---
name: AORO MVP Implementation
overview: Build a production-grade Autonomous Outcome-Based Revenue Orchestrator MVP covering the Signal Engine (lead discovery), Multi-Agent Workflow (LangGraph), and ServiceTitan CRM integration via MCP, targeting the Commercial Fire Safety vertical.
todos:
  - id: project-setup
    content: Initialize project structure with Poetry, configure environment, and set up Docker Compose for local Neo4j/services
    status: completed
  - id: signal-engine-scrapers
    content: Build permit scraper framework with base class, implement first municipal portal scraper (Playwright-based)
    status: completed
    dependencies:
      - project-setup
  - id: signal-engine-enrichment
    content: Implement data enrichment pipeline with Apollo/Clearbit integration for decision maker identification
    status: completed
    dependencies:
      - signal-engine-scrapers
  - id: knowledge-layer
    content: Set up Neo4j fire code graph schema and Pinecone vector index with case study embeddings
    status: completed
    dependencies:
      - project-setup
  - id: langgraph-orchestrator
    content: Build LangGraph state machine with Researcher, Communicator, and Closer agent nodes
    status: completed
    dependencies:
      - knowledge-layer
  - id: hitl-gates
    content: Implement Human-in-the-Loop approval gates using LangGraph interrupt mechanism
    status: completed
    dependencies:
      - langgraph-orchestrator
  - id: mcp-server
    content: Create FastMCP server exposing ServiceTitan CRM tools (bookings, availability, pricebook)
    status: completed
    dependencies:
      - langgraph-orchestrator
  - id: servicetitan-integration
    content: Build ServiceTitan API client with OAuth authentication and multi-tenant security
    status: completed
    dependencies:
      - mcp-server
  - id: observability
    content: Integrate LangSmith for workflow tracing and decision audit trails
    status: completed
    dependencies:
      - langgraph-orchestrator
  - id: api-layer
    content: Build FastAPI application with routes for lead ingestion, agent triggering, and webhooks
    status: completed
    dependencies:
      - mcp-server
      - signal-engine-enrichment
---

# AORO MVP Master Implementation Plan

## System Architecture Overview

```mermaid
flowchart TB
    subgraph SignalEngine [Phase 1: Signal Engine]
        PS[Permit Scrapers]
        RL[Regulatory Listener]
        DE[Data Enrichment]
        PS --> DE
        RL --> DE
    end

    subgraph KnowledgeLayer [Knowledge Layer]
        Neo4j[(Neo4j Graph DB)]
        Pinecone[(Pinecone Vector DB)]
    end

    subgraph AgentWorkflow [Phase 2: Agent Workflow]
        Orchestrator[LangGraph Orchestrator]
        ResearchAgent[Researcher Agent]
        CommAgent[Communication Agent]
        CloserAgent[Closer Agent]
        Orchestrator --> ResearchAgent
        Orchestrator --> CommAgent
        Orchestrator --> CloserAgent
    end

    subgraph IntegrationLayer [Phase 3: MCP Integration]
        MCPServer[FastMCP Server]
        ServiceTitan[ServiceTitan API]
        Calendar[Calendar Sync]
        MCPServer --> ServiceTitan
        MCPServer --> Calendar
    end

    DE --> Neo4j
    DE --> Pinecone
    ResearchAgent --> Neo4j
    ResearchAgent --> Pinecone
    CommAgent --> MCPServer
    CloserAgent --> MCPServer
```

---

## Project Structure

```javascript
AI_Agent_Leads_Revenue/
├── pyproject.toml                 # Project dependencies (Poetry/UV)
├── .env.example                   # Environment template
├── README.md
├── docker-compose.yml             # Local dev services
│
├── src/
│   ├── __init__.py
│   │
│   ├── signal_engine/             # Phase 1: Lead Discovery
│   │   ├── __init__.py
│   │   ├── scrapers/
│   │   │   ├── base_scraper.py    # Abstract scraper interface
│   │   │   ├── permit_scraper.py  # Municipal permit monitoring
│   │   │   └── regulatory_scraper.py
│   │   ├── enrichment/
│   │   │   ├── apollo_client.py   # Contact enrichment
│   │   │   └── company_enricher.py
│   │   ├── listeners/
│   │   │   └── fire_marshal_listener.py
│   │   └── models.py              # Pydantic models for leads
│   │
│   ├── knowledge/                 # Knowledge Layer
│   │   ├── __init__.py
│   │   ├── graph/
│   │   │   ├── neo4j_client.py
│   │   │   ├── schemas.py         # Cypher schemas
│   │   │   └── fire_code_graph.py # NFPA regulatory graph
│   │   └── vectors/
│   │       ├── pinecone_client.py
│   │       └── embeddings.py
│   │
│   ├── agents/                    # Phase 2: LangGraph Agents
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Main LangGraph workflow
│   │   ├── state.py               # Shared agent state schema
│   │   ├── nodes/
│   │   │   ├── researcher.py      # Prospect analysis
│   │   │   ├── communicator.py    # Outreach generation
│   │   │   ├── closer.py          # Objection handling
│   │   │   └── human_review.py    # HITL approval gate
│   │   └── tools/
│   │       ├── regulatory_lookup.py
│   │       ├── case_study_search.py
│   │       └── contact_finder.py
│   │
│   ├── integrations/              # Phase 3: MCP + External APIs
│   │   ├── __init__.py
│   │   ├── mcp/
│   │   │   ├── server.py          # FastMCP server definition
│   │   │   ├── tools/
│   │   │   │   ├── crm_tools.py   # ServiceTitan CRM tools
│   │   │   │   ├── calendar_tools.py
│   │   │   │   └── pricebook_tools.py
│   │   │   └── auth.py            # Multi-tenant auth
│   │   └── servicetitan/
│   │       ├── client.py          # REST API wrapper
│   │       └── models.py
│   │
│   ├── core/                      # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   ├── security.py            # RLS, encryption
│   │   └── observability.py       # LangSmith integration
│   │
│   └── api/                       # FastAPI application
│       ├── __init__.py
│       ├── main.py
│       └── routes/
│           ├── leads.py
│           ├── agents.py
│           └── webhooks.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── scripts/
    ├── seed_knowledge_graph.py
    └── run_scraper_job.py
```

---

## Phase 1: Signal Engine (Weeks 1-4)

### 1.1 Permit Scraper Framework

Build an async scraper system targeting municipal fire/mechanical permit portals.**Key Components:**

- Abstract `BaseScraper` class with retry logic, rate limiting, and proxy rotation
- Playwright-based scraper for JavaScript-heavy portals
- Scheduled job runner using APScheduler or Celery Beat

**Target Data Points:**

- Permit number, type (Fire Alarm, Sprinkler, HVAC)
- Property address and building type
- Applicant/contractor information
- Status transitions ("Permit Issued", "Inspection Scheduled")

**Implementation Pattern:**

```python
# src/signal_engine/scrapers/base_scraper.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class PermitData(BaseModel):
    permit_id: str
    permit_type: str
    address: str
    building_type: str
    status: str
    applicant_name: str | None
    issued_date: datetime | None

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self) -> list[PermitData]: ...
    
    @abstractmethod
    async def check_for_updates(self, last_run: datetime) -> list[PermitData]: ...
```

### 1.2 Regulatory Listener

Monitor state fire marshal bulletins and federal register updates for compliance triggers.**Data Sources:**

- State Fire Marshal RSS/API feeds
- NFPA code amendment announcements
- EPA refrigerant phase-out schedules (for future HVAC expansion)

### 1.3 Data Enrichment Pipeline

Cross-reference permit data with business intelligence APIs.**Enrichment Flow:**

```mermaid
flowchart LR
    Permit[Raw Permit] --> Geocode[Geocoding]
    Geocode --> CompanyMatch[Company Matching]
    CompanyMatch --> Apollo[Apollo/Clearbit API]
    Apollo --> DecisionMaker[Decision Maker Identification]
    DecisionMaker --> EnrichedLead[Enriched Lead Record]
```

**Output Schema:**

- Company: name, industry, employee count, revenue estimate
- Decision Maker: name, title, email, LinkedIn, phone
- Compliance Context: applicable codes, inspection history

---

## Phase 2: Agentic Workflow (Weeks 5-8)

### 2.1 LangGraph State Machine

```mermaid
stateDiagram-v2
    [*] --> LeadIngestion
    LeadIngestion --> Research
    Research --> QualificationCheck
    QualificationCheck --> Disqualified: score < threshold
    QualificationCheck --> DraftOutreach: score >= threshold
    Disqualified --> [*]
    DraftOutreach --> HumanReview
    HumanReview --> SendOutreach: approved
    HumanReview --> DraftOutreach: revision_needed
    SendOutreach --> WaitForResponse
    WaitForResponse --> HandleResponse: response_received
    WaitForResponse --> FollowUp: timeout
    HandleResponse --> ObjectionHandling: objection_detected
    HandleResponse --> BookMeeting: positive_response
    ObjectionHandling --> DraftOutreach
    FollowUp --> WaitForResponse
    BookMeeting --> UpdateCRM
    UpdateCRM --> [*]
```

### 2.2 Agent State Schema

```python
# src/agents/state.py
from typing import TypedDict, Literal
from langgraph.graph import MessagesState

class AOROState(TypedDict):
    # Lead Information
    lead_id: str
    company_name: str
    decision_maker: dict
    permit_data: dict
    
    # Research Results
    compliance_gaps: list[str]
    applicable_codes: list[str]
    case_studies: list[dict]
    
    # Communication State
    outreach_draft: str
    outreach_channel: Literal["email", "whatsapp", "voice"]
    response_history: list[dict]
    
    # Workflow State
    qualification_score: float
    current_objection: str | None
    human_approved: bool
    
    # CRM State
    crm_booking_id: str | None
    appointment_datetime: datetime | None
```

### 2.3 Agent Nodes

**Researcher Agent:**

- Queries Neo4j for applicable fire codes based on building type
- Searches Pinecone for relevant case studies
- Calculates "compliance urgency score"

**Communication Agent:**

- Generates hyper-personalized outreach using GPT-4o
- Leads with technical value: "Your {building_type} is subject to NFPA 72 2022 amendments..."
- Adapts tone based on decision maker title

**Closer Agent:**

- Fine-tuned prompt for handling domain-specific objections
- Access to local labor rate data and code citation lookup
- Negotiation patterns for high-ticket sales

### 2.4 Human-in-the-Loop Gates

```python
# src/agents/nodes/human_review.py
from langgraph.prebuilt import interrupt

def human_review_node(state: AOROState) -> AOROState:
    \"\"\"Pause workflow for human approval of outreach.\"\"\"
    if state[\"qualification_score\"] > 0.8:
        # Auto-approve high-confidence leads
        return {**state, \"human_approved\": True}
    
    # Interrupt for human review
    interrupt({
        \"type\": \"approval_required\",
        \"lead_id\": state[\"lead_id\"],
        \"draft\": state[\"outreach_draft\"],
        \"confidence\": state[\"qualification_score\"]
    })
```

---

## Phase 3: MCP Integration Layer (Weeks 9-12)

### 3.1 FastMCP Server Architecture

```python
# src/integrations/mcp/server.py
from fastmcp import FastMCP

mcp = FastMCP(\"AORO ServiceTitan Bridge\")

@mcp.tool()
async def create_booking(
    customer_id: str,
    job_type: str,
    scheduled_datetime: str,
    notes: str,
    tenant_id: str  # Multi-tenancy
) -> dict:
    \"\"\"Create a new booking in ServiceTitan CRM.\"\"\"
    client = get_servicetitan_client(tenant_id)
    return await client.bookings.create(...)

@mcp.tool()
async def check_availability(
    technician_id: str,
    date_range: tuple[str, str],
    tenant_id: str
) -> list[dict]:
    \"\"\"Check technician availability slots.\"\"\"
    ...

@mcp.tool()
async def get_pricebook_services(
    category: str,
    tenant_id: str
) -> list[dict]:
    \"\"\"Retrieve service offerings and pricing.\"\"\"
    ...
```

### 3.2 ServiceTitan API Integration

**Required Endpoints:**

- `POST /bookings` - Create appointments
- `GET /customers` - Customer lookup
- `GET /pricebook/services` - Service catalog
- `GET /dispatch/technicians/availability` - Calendar availability

**Authentication:**

- OAuth 2.0 with tenant-specific credentials
- Secure credential storage in environment/vault

### 3.3 Multi-Tenant Security

```python
# src/core/security.py
from functools import wraps

def tenant_context(func):
    \"\"\"Decorator ensuring tenant isolation.\"\"\"
    @wraps(func)
    async def wrapper(*args, tenant_id: str, **kwargs):
        # Validate tenant access
        if not await verify_tenant_access(tenant_id):
            raise PermissionError(\"Invalid tenant context\")
        
        # Set row-level security context
        async with tenant_scoped_session(tenant_id):
            return await func(*args, tenant_id=tenant_id, **kwargs)
    return wrapper
```

---

## Knowledge Layer Setup

### Neo4j Fire Code Graph Schema

```cypher
// Core node types
CREATE CONSTRAINT FOR (c:FireCode) REQUIRE c.code_id IS UNIQUE;
CREATE CONSTRAINT FOR (b:BuildingType) REQUIRE b.type_id IS UNIQUE;
CREATE CONSTRAINT FOR (j:Jurisdiction) REQUIRE j.fips_code IS UNIQUE;

// Relationships
// (:FireCode)-[:APPLIES_TO]->(:BuildingType)
// (:Jurisdiction)-[:ENFORCES]->(:FireCode)
// (:FireCode)-[:SUPERSEDES]->(:FireCode)
// (:Inspection)-[:CITED]->(:Violation)-[:VIOLATES]->(:FireCode)
```

### Pinecone Index Configuration

- **Index Name:** `aoro-case-studies`
- **Dimensions:** 1536 (text-embedding-3-small)
- **Metadata Fields:** industry, deal_size, building_type, outcome
- **Namespace per tenant** for data isolation

---

## Observability with LangSmith

```python
# src/core/observability.py
from langsmith import traceable
from langsmith.wrappers import wrap_openai

# Wrap OpenAI client for automatic tracing
client = wrap_openai(OpenAI())

@traceable(name=\"researcher_agent\")
async def run_researcher(state: AOROState) -> AOROState:
    # All LLM calls automatically traced
    ...
```

**Tracked Metrics:**

- Lead-to-appointment conversion rate
- Agent decision audit trails
- Latency per workflow step
- Token usage and cost per lead

---

## Dependencies

```toml
# pyproject.toml (key dependencies)
[tool.poetry.dependencies]
python = \"^3.11\"
langgraph = \"^0.2\"
langchain-openai = \"^0.2\"
langsmith = \"^0.1\"
fastmcp = \"^0.1\"
neo4j = \"^5.0\"
pinecone-client = \"^3.0\"
fastapi = \"^0.115\"
uvicorn = \"^0.32\"
playwright = \"^1.48\"
pydantic = \"^2.0\"
httpx = \"^0.27\"
python-dotenv = \"^1.0\"
apscheduler = \"^3.10\"
```

---

## Implementation Priority

| Week | Deliverable | Success Criteria |
|------|-------------|------------------|
| 1-2 | Permit scraper for 1 target municipality | Successfully extracts 100+ fire permits |
| 3-4 | Data enrichment pipeline | 80%+ decision maker match rate |
| 5-6 | LangGraph workflow (research + communication) | End-to-end lead processing |
| 7-8 | Closer agent + HITL gates | Objection handling demo |
| 9-10 | MCP server + ServiceTitan mock | Tool invocation working |
| 11-12 | Integration testing + LangSmith | Full audit trail captured |

---

## Next Steps After MVP

1. **Billing Engine:** Stripe integration for outcome-based charging
2. **Voice AI:** Integration with Vapi or Bland.ai for phone outreach


