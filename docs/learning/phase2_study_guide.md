# Phase 2 Study Guide: Complete Background Knowledge

**Purpose:** This guide provides comprehensive background knowledge required to fully understand and work with Phase 2 (Agentic Workflow) implementation.

**Estimated Study Time:** 4-6 weeks (depending on prior experience)

**Last Updated:** 2025-01-27

---

## Table of Contents

1. [Core Concepts](#1-core-concepts)
2. [Database Technologies](#2-database-technologies)
3. [LLM Integration](#3-llm-integration)
4. [Agent Architecture](#4-agent-architecture-patterns)
5. [Software Architecture](#5-software-architecture)
6. [Data Modeling](#6-data-modeling)
7. [Workflow Patterns](#7-workflow-patterns)
8. [Integration Patterns](#8-integration-patterns)
9. [Testing & Debugging](#9-testing--debugging)
10. [Domain Knowledge](#10-domain-knowledge)
11. [Learning Path](#11-recommended-learning-path)
12. [Hands-On Exercises](#12-hands-on-exercises)

---

## 1. Core Concepts

### 1.1 LangGraph Fundamentals

#### What is LangGraph?

LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain by adding:

- **Stateful workflows:** Maintain state across multiple steps
- **Graph-based execution:** Define workflows as directed graphs
- **Conditional routing:** Make decisions based on state
- **Human-in-the-loop:** Pause workflows for human approval
- **Persistence:** Save and resume workflows

#### Key Concepts

**StateGraph:**
```python
from langgraph.graph import StateGraph, START, END

# Define your state type
class MyState(TypedDict):
    data: str
    count: int

# Create a graph
graph = StateGraph(MyState)

# Add nodes (functions that process state)
def process_node(state: MyState) -> MyState:
    return {"count": state.get("count", 0) + 1}

graph.add_node("process", process_node)

# Add edges (connections between nodes)
graph.add_edge(START, "process")
graph.add_edge("process", END)

# Compile to executable workflow
app = graph.compile()
```

**Nodes:**
- Functions that take state as input and return updated state
- Can be async: `async def my_node(state) -> State:`
- Should be pure: No side effects (or minimal, controlled ones)
- Return partial state updates (only changed fields)

**Edges:**
- **Unconditional:** Always follow this path
  ```python
  graph.add_edge("NodeA", "NodeB")
  ```
- **Conditional:** Route based on state
  ```python
  def route_logic(state: MyState) -> str:
      if state.get("count") > 10:
          return "EndNode"
      return "ContinueNode"
  
  graph.add_conditional_edges("NodeA", route_logic)
  ```

**State:**
- TypedDict for type safety
- Immutable updates (return new dict, don't mutate)
- Partial updates allowed (only specify changed fields)
- Shared across all nodes

**Compilation:**
```python
# Compile the graph
app = graph.compile()

# Run the workflow
result = await app.ainvoke({"data": "test", "count": 0})
```

#### Resources

- **Official Docs:** https://langchain-ai.github.io/langgraph/
- **Tutorial:** https://langchain-ai.github.io/langgraph/tutorials/
- **Concepts:** https://langchain-ai.github.io/langgraph/concepts/
- **State Management:** https://langchain-ai.github.io/langgraph/concepts/low_level/#state

#### Practice Exercise

Create a simple 3-node workflow:
1. "Start" node: Initialize state
2. "Process" node: Transform data
3. "End" node: Finalize and return

Add conditional routing: if processed data is empty, skip to end.

---

### 1.2 State Management Patterns

#### TypedDict for Type Safety

**What is TypedDict?**
- Python's way to define dictionary structures with types
- Provides type hints for IDE autocomplete and type checking
- Doesn't enforce types at runtime (use Pydantic for that)

**Example:**
```python
from typing import TypedDict, Literal

class AOROState(TypedDict, total=False):
    # total=False means all fields are optional
    lead_id: str
    company_name: str
    qualification_score: float
    outreach_channel: Literal["email", "whatsapp", "voice"]
```

**Why TypedDict?**
- Type safety without runtime overhead
- IDE autocomplete
- Clear contract for state structure
- Works with LangGraph's state system

#### Immutable State Updates

**Principle:** Never mutate state directly. Always return new dictionaries.

**Bad:**
```python
def bad_node(state: AOROState) -> AOROState:
    state["count"] = state.get("count", 0) + 1  # ❌ Mutation
    return state
```

**Good:**
```python
def good_node(state: AOROState) -> AOROState:
    return {
        **state,  # Spread existing state
        "count": state.get("count", 0) + 1  # ✅ New dict
    }
```

**Partial Updates:**
```python
# You only need to return fields that changed
def update_score(state: AOROState) -> AOROState:
    return {"qualification_score": 0.85}  # Only this field
    # LangGraph merges with existing state
```

#### Context Variables vs Global State

**Context Variables (`contextvars`):**
- Thread-local storage for async code
- Perfect for multi-tenant isolation
- Each async task has its own context

**Example:**
```python
from contextvars import ContextVar

_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)

def set_tenant(tenant_id: str):
    _tenant_id.set(tenant_id)

def get_tenant() -> str | None:
    return _tenant_id.get()
```

**Why not global variables?**
- Global state breaks in async/multi-tenant environments
- Context variables are isolated per async task
- Safe for concurrent operations

#### Resources

- **TypedDict Docs:** https://docs.python.org/3/library/typing.html#typing.TypedDict
- **Context Variables:** https://docs.python.org/3/library/contextvars.html
- **Functional State Management:** https://redux.js.org/understanding/thinking-in-redux/three-principles

---

### 1.3 Asynchronous Programming in Python

#### Async/Await Basics

**What is async/await?**
- Allows functions to pause and resume execution
- Enables concurrent I/O operations without threads
- More efficient than threads for I/O-bound tasks

**Basic Syntax:**
```python
import asyncio

async def fetch_data():
    # Simulate I/O operation
    await asyncio.sleep(1)
    return "data"

async def main():
    result = await fetch_data()
    print(result)

# Run async code
asyncio.run(main())
```

**Why async in Phase 2?**
- Database queries (Neo4j, Pinecone) are I/O-bound
- API calls (OpenAI, Apollo) are I/O-bound
- Multiple agents can run concurrently
- Better resource utilization

#### Async Context Managers

**Pattern:** Use `async with` for resource management

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def database_session():
    session = await create_session()
    try:
        yield session
    finally:
        await session.close()

# Usage
async def query_data():
    async with database_session() as session:
        result = await session.query("MATCH (n) RETURN n")
        return result
```

**Real Example from Code:**
```python
@asynccontextmanager
async def tenant_scoped_session(tenant_id: str):
    token = _tenant_id_ctx.set(tenant_id)
    try:
        yield
    finally:
        _tenant_id_ctx.reset(token)
```

#### Async Function Composition

**Chaining async operations:**
```python
async def step1():
    return await fetch_data()

async def step2(data):
    return await process_data(data)

async def step3(processed):
    return await save_data(processed)

# Compose
async def pipeline():
    data = await step1()
    processed = await step2(data)
    result = await step3(processed)
    return result
```

**Concurrent execution:**
```python
import asyncio

async def fetch_multiple():
    # Run multiple operations concurrently
    results = await asyncio.gather(
        fetch_data_1(),
        fetch_data_2(),
        fetch_data_3()
    )
    return results
```

#### Async HTTP Clients

**HTTPX (async HTTP client):**
```python
import httpx

async def fetch_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()
```

**OpenAI Async Client:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="...")

async def generate_text():
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
    return response.choices[0].message.content
```

#### Common Patterns

**Error Handling:**
```python
async def safe_operation():
    try:
        result = await risky_operation()
        return result
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return None  # Graceful degradation
```

**Timeouts:**
```python
import asyncio

async def fetch_with_timeout():
    try:
        return await asyncio.wait_for(
            slow_operation(),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        return None
```

#### Resources

- **Python AsyncIO Docs:** https://docs.python.org/3/library/asyncio.html
- **Real Python Async Guide:** https://realpython.com/async-io-python/
- **HTTPX Docs:** https://www.python-httpx.org/
- **Async Patterns:** https://docs.python.org/3/library/asyncio-task.html

---

## 2. Database Technologies

### 2.1 Neo4j Graph Database

#### What is a Graph Database?

**Traditional Relational DB:**
- Tables with rows and columns
- Joins to connect related data
- Good for structured, tabular data

**Graph Database:**
- Nodes (entities) and relationships (connections)
- Direct connections, no joins needed
- Excellent for connected data

**Why Graph for Fire Codes?**
- Fire codes apply to building types (many-to-many)
- Jurisdictions enforce codes
- Codes supersede other codes
- Natural fit for graph structure

#### Core Concepts

**Nodes:**
- Entities in your domain
- Have labels (types): `FireCode`, `BuildingType`
- Have properties: `{code_id: "NFPA_72", name: "..."}`

**Relationships:**
- Connections between nodes
- Have types: `APPLIES_TO`, `ENFORCES`
- Can have properties: `{since: "2022"}`

**Example Graph:**
```
(FireCode:NFPA_72)-[:APPLIES_TO]->(BuildingType:hospital)
(FireCode:NFPA_72)-[:APPLIES_TO]->(BuildingType:data_center)
(Jurisdiction:NC)-[:ENFORCES]->(FireCode:NFPA_72)
```

#### Cypher Query Language

**Basic Patterns:**

**MATCH (find nodes):**
```cypher
MATCH (c:FireCode)
RETURN c
```

**WHERE (filter):**
```cypher
MATCH (c:FireCode)
WHERE c.code_id = "NFPA_72"
RETURN c
```

**Relationships:**
```cypher
MATCH (c:FireCode)-[:APPLIES_TO]->(b:BuildingType)
RETURN c, b
```

**Pattern Matching:**
```cypher
// Find all codes that apply to hospitals
MATCH (c:FireCode)-[:APPLIES_TO]->(b:BuildingType {type_id: "hospital"})
RETURN c.code_id, c.name, c.edition
```

**MERGE (create or update):**
```cypher
MERGE (c:FireCode {code_id: "NFPA_72"})
SET c.name = "National Fire Alarm Code",
    c.edition = "2022"
```

**CREATE (always create):**
```cypher
CREATE (c:FireCode {
    code_id: "NFPA_72",
    name: "National Fire Alarm Code"
})
```

**Creating Relationships:**
```cypher
MATCH (c:FireCode {code_id: "NFPA_72"})
MATCH (b:BuildingType {type_id: "hospital"})
MERGE (c)-[:APPLIES_TO]->(b)
```

#### Python Driver Usage

**Connection:**
```python
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)
```

**Sessions:**
```python
async with driver.session() as session:
    result = await session.run(
        "MATCH (n) RETURN n LIMIT 10"
    )
    records = await result.data()
```

**Parameterized Queries:**
```python
query = """
MATCH (c:FireCode)-[:APPLIES_TO]->(b:BuildingType {type_id: $type_id})
RETURN c.code_id, c.name, c.edition
"""

result = await session.run(query, type_id="hospital")
rows = await result.data()
```

**Real Example from Code:**
```python
async def get_applicable_codes(building_type_id: str) -> list[dict]:
    driver = get_neo4j_driver()
    query = """
    MATCH (c:FireCode)-[:APPLIES_TO]->(b:BuildingType {type_id: $building_type_id})
    RETURN c.code_id AS code_id, c.name AS name, c.edition AS edition
    ORDER BY c.code_id
    """
    async with driver.session() as session:
        res = await session.run(query, building_type_id=building_type_id)
        rows = await res.data()
    return rows
```

#### Schema Design

**Constraints:**
```cypher
CREATE CONSTRAINT fire_code_id IF NOT EXISTS 
FOR (c:FireCode) REQUIRE c.code_id IS UNIQUE;

CREATE CONSTRAINT building_type_id IF NOT EXISTS 
FOR (b:BuildingType) REQUIRE b.type_id IS UNIQUE;
```

**Best Practices:**
- Use meaningful labels: `FireCode`, not `FC`
- Index frequently queried properties
- Use relationships for connections, not properties
- Keep property names consistent

#### Resources

- **Neo4j Docs:** https://neo4j.com/docs/
- **Cypher Manual:** https://neo4j.com/docs/cypher-manual/
- **Python Driver:** https://neo4j.com/docs/python-manual/
- **Graph Database Concepts:** https://neo4j.com/developer/graph-database/
- **Cypher Cheat Sheet:** https://neo4j.com/docs/cypher-cheat-sheet/

#### Practice Exercise

1. Create nodes for 3 fire codes (NFPA_72, NFPA_25, NFPA_101)
2. Create nodes for 2 building types (hospital, data_center)
3. Create relationships: NFPA_72 applies to both building types
4. Query: Find all codes that apply to hospitals
5. Query: Find all building types that NFPA_72 applies to

---

### 2.2 Pinecone Vector Database

#### What are Vector Embeddings?

**Text → Numbers:**
- Convert text into a list of numbers (vector)
- Example: "hospital fire safety" → `[0.123, -0.456, 0.789, ...]`
- Typically 1536 numbers for OpenAI embeddings

**Why Embeddings?**
- Capture semantic meaning, not just keywords
- Similar meanings → similar vectors
- Enables semantic search

**Example:**
```python
"hospital fire safety" → [0.1, 0.2, -0.3, ...]
"medical facility compliance" → [0.12, 0.19, -0.28, ...]
# These are similar, so vectors are close
```

#### Semantic Search

**Traditional Search:**
- Keyword matching: "hospital" matches "hospital"
- Misses: "medical facility", "healthcare building"

**Semantic Search:**
- Meaning matching: "hospital" matches "medical facility"
- Understands synonyms and context
- Finds conceptually similar content

**How it Works:**
1. Convert query to vector
2. Compare query vector to all stored vectors
3. Return most similar (highest similarity score)

#### Cosine Similarity

**What is it?**
- Measures angle between two vectors
- Range: -1 to 1 (1 = identical, 0 = orthogonal, -1 = opposite)
- Used to rank search results

**Formula:**
```
similarity = (A · B) / (||A|| × ||B||)
```

**In Practice:**
```python
query_vector = [0.1, 0.2, -0.3]
stored_vector = [0.12, 0.19, -0.28]
similarity = 0.95  # Very similar!
```

#### Pinecone Basics

**What is Pinecone?**
- Managed vector database service
- Handles storage, indexing, and search
- Scales automatically

**Key Concepts:**
- **Index:** Container for vectors
- **Namespace:** Logical partition (for multi-tenancy)
- **Metadata:** Additional data stored with vectors
- **Dimension:** Size of vectors (1536 for OpenAI)

#### Python Integration

**Setup:**
```python
from pinecone import Pinecone

pc = Pinecone(api_key="your-api-key")
index = pc.Index("your-index-name")
```

**Upsert (store vectors):**
```python
vectors = [
    {
        "id": "case-study-1",
        "values": [0.1, 0.2, ...],  # 1536 numbers
        "metadata": {
            "building_type": "hospital",
            "outcome": "Closed $500k deal"
        }
    }
]
index.upsert(vectors=vectors, namespace="tenant-1")
```

**Query (search):**
```python
query_vector = [0.1, 0.2, ...]  # From embedding

results = index.query(
    vector=query_vector,
    top_k=5,  # Return top 5 matches
    include_metadata=True,
    namespace="tenant-1"
)

# Results:
# {
#   "matches": [
#     {
#       "id": "case-study-1",
#       "score": 0.92,  # Similarity score
#       "metadata": {...}
#     }
#   ]
# }
```

**Real Example from Code:**
```python
async def search_case_studies(query: str, top_k: int = 5):
    # 1. Convert query to vector
    vec = await embed_text(query)
    
    # 2. Search Pinecone
    index = get_index()
    ns = tenant_namespace(current_tenant_id())
    res = index.query(
        vector=vec,
        top_k=top_k,
        include_metadata=True,
        namespace=ns
    )
    
    # 3. Extract results
    matches = res.get("matches", [])
    return [
        {
            "id": m.get("id"),
            "score": m.get("score"),
            "metadata": m.get("metadata")
        }
        for m in matches
    ]
```

#### Embedding Generation

**OpenAI Embeddings:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="...")

async def embed_text(text: str) -> list[float]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding  # 1536 numbers
```

**Batch Embedding:**
```python
async def embed_texts(texts: list[str]) -> list[list[float]]:
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]
```

#### Multi-Tenancy with Namespaces

**Why Namespaces?**
- Isolate data per tenant
- Same index, different logical partitions
- Efficient and secure

**Usage:**
```python
def tenant_namespace(tenant_id: str) -> str:
    return tenant_id  # "tenant-1", "tenant-2", etc.

# Store in tenant namespace
index.upsert(vectors=vectors, namespace=tenant_namespace("tenant-1"))

# Query from tenant namespace
index.query(vector=vec, namespace=tenant_namespace("tenant-1"))
```

#### Best Practices

1. **Consistent Dimensions:** Always use same dimension (1536)
2. **Metadata Filtering:** Use metadata for additional filtering
3. **Batch Operations:** Upsert multiple vectors at once
4. **Namespace Isolation:** Always specify namespace for multi-tenant
5. **Error Handling:** Handle API failures gracefully

#### Resources

- **Pinecone Docs:** https://docs.pinecone.io/
- **Vector Database Guide:** https://www.pinecone.io/learn/vector-database/
- **Embeddings Guide:** https://www.pinecone.io/learn/embeddings/
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings

#### Practice Exercise

1. Generate embeddings for 5 case study texts
2. Store them in Pinecone with metadata
3. Query with a similar text
4. Verify top results are semantically similar
5. Test namespace isolation (create two namespaces)

---

## 3. LLM Integration

### 3.1 OpenAI API Patterns

#### Chat Completions API

**Basic Structure:**
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="...")

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write an email about fire safety."}
    ],
    temperature=0.7
)

content = response.choices[0].message.content
```

**Message Roles:**
- **system:** Instructions for the model's behavior
- **user:** User input/requests
- **assistant:** Model's previous responses (for conversation)

**Parameters:**
- **model:** Which model to use (`gpt-4o-mini`, `gpt-4`, etc.)
- **temperature:** Creativity (0.0 = deterministic, 1.0 = creative)
- **max_tokens:** Maximum response length
- **top_p:** Nucleus sampling parameter

**Real Example from Code:**
```python
async def communicator_node(state: AOROState) -> AOROState:
    client = get_openai_client()
    
    system = (
        "You are a technical sales outreach assistant for commercial fire safety services. "
        "Be concise, credible, and specific. Avoid hype. Use code citations only if relevant."
    )
    user = f"""
    Draft a first-touch email to a facility decision maker.
    
    Context:
    - Company: {company}
    - Decision maker: {dm.get('full_name')} ({dm.get('title')})
    - Permit type: {permit.get('permit_type')}
    - Applicable codes: {codes}
    
    Constraints:
    - 120-160 words
    - Subject line included
    - Offer a 15-minute call
    """
    
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.4
    )
    
    draft = resp.choices[0].message.content or ""
    return {**state, "outreach_draft": draft}
```

#### Embeddings API

**Text to Vector:**
```python
response = await client.embeddings.create(
    model="text-embedding-3-small",
    input=["hospital fire safety case study"]
)

embedding = response.data[0].embedding  # 1536 numbers
```

**Batch Processing:**
```python
texts = ["text 1", "text 2", "text 3"]
response = await client.embeddings.create(
    model="text-embedding-3-small",
    input=texts
)

embeddings = [item.embedding for item in response.data]
```

#### Error Handling

**Rate Limits:**
```python
import asyncio
from openai import RateLimitError

async def safe_llm_call():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.chat.completions.create(...)
        except RateLimitError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

**API Errors:**
```python
from openai import APIError

try:
    response = await client.chat.completions.create(...)
except APIError as e:
    logger.error(f"OpenAI API error: {e}")
    return None  # Graceful degradation
```

#### Cost Management

**Token Counting:**
- Input tokens: ~$0.15 per 1M tokens (gpt-4o-mini)
- Output tokens: ~$0.60 per 1M tokens
- Embeddings: ~$0.02 per 1M tokens

**Optimization:**
- Use `gpt-4o-mini` for simple tasks
- Limit `max_tokens` for responses
- Cache embeddings when possible
- Batch embedding requests

#### Resources

- **OpenAI API Docs:** https://platform.openai.com/docs/api-reference
- **Models:** https://platform.openai.com/docs/models
- **Pricing:** https://openai.com/api/pricing/
- **Best Practices:** https://platform.openai.com/docs/guides/gpt-best-practices

---

### 3.2 Prompt Engineering

#### System vs User Prompts

**System Prompt:**
- Defines the model's role and behavior
- Sets tone, style, constraints
- Should be stable across requests

**Example:**
```python
system = (
    "You are a technical sales outreach assistant for commercial fire safety services. "
    "Be concise, credible, and specific. Avoid hype. Use code citations only if relevant."
)
```

**User Prompt:**
- Contains the specific task and context
- Changes per request
- Includes dynamic data

**Example:**
```python
user = f"""
Draft a first-touch email to a facility decision maker.

Context:
- Company: {company_name}
- Permit type: {permit_type}
- Applicable codes: {codes}

Constraints:
- 120-160 words
- Subject line included
"""
```

#### Context Injection

**Include Relevant Data:**
```python
user = f"""
Context:
- Company: {state.get('company_name')}
- Decision maker: {dm.get('full_name')} ({dm.get('title')})
- Permit type: {permit.get('permit_type')}
- Applicable codes: {state.get('applicable_codes')}
- Case studies: {format_case_studies(state.get('case_studies'))}
"""
```

**Format Complex Data:**
```python
def format_case_studies(case_studies: list[dict]) -> str:
    if not case_studies:
        return "None available"
    
    formatted = []
    for cs in case_studies[:3]:  # Top 3
        formatted.append(
            f"- {cs['metadata'].get('outcome', 'N/A')} "
            f"({cs['metadata'].get('building_type', 'N/A')})"
        )
    return "\n".join(formatted)
```

#### Constraint Specification

**Be Explicit:**
```python
constraints = """
Constraints:
- 120-160 words
- Subject line included
- Offer a 15-minute call and propose 2 time windows
- Lead with technical value (inspection readiness, code alignment, risk reduction)
- No generic sales language
"""
```

#### Few-Shot Examples

**Show, Don't Tell:**
```python
system = """
You are a fire safety outreach assistant. Here are examples of good emails:

Example 1:
Subject: NFPA 72 Compliance for Your Hospital
[Email content...]

Example 2:
Subject: Fire Alarm Inspection Readiness
[Email content...]

Now draft a similar email for the given context.
"""
```

#### Temperature Selection

**Low Temperature (0.0-0.3):**
- Deterministic, consistent
- Good for: Technical content, structured output
- Use case: Code citations, compliance information

**Medium Temperature (0.4-0.7):**
- Balanced creativity and consistency
- Good for: Sales emails, outreach
- Use case: Communicator agent

**High Temperature (0.8-1.0):**
- Creative, varied
- Good for: Brainstorming, ideation
- Use case: Not typically used in Phase 2

#### Resources

- **OpenAI Prompt Guide:** https://platform.openai.com/docs/guides/prompt-engineering
- **Prompt Engineering Guide:** https://www.promptingguide.ai/
- **Best Practices:** https://platform.openai.com/docs/guides/gpt-best-practices

---

## 4. Agent Architecture Patterns

### 4.1 Multi-Agent Systems

#### Agent Roles

**Researcher Agent:**
- **Purpose:** Gather information about the lead
- **Tools:** Regulatory lookup, case study search
- **Output:** Applicable codes, compliance gaps, case studies

**Communicator Agent:**
- **Purpose:** Generate outreach content
- **Input:** Research results, lead data
- **Output:** Drafted email/WhatsApp/voice script

**Closer Agent:**
- **Purpose:** Handle objections and responses
- **Input:** Objection text, context
- **Output:** Reply to objection

**Human Review Agent:**
- **Purpose:** Approval gate
- **Logic:** Auto-approve high confidence, interrupt for low confidence
- **Output:** Approval flag

#### Agent Communication

**State-Based Communication:**
- Agents don't call each other directly
- They read from and write to shared state
- State flows through the graph

**Example Flow:**
```python
# Researcher writes to state
state = {
    "applicable_codes": ["NFPA_72", "NFPA_25"],
    "case_studies": [...]
}

# Communicator reads from state
codes = state.get("applicable_codes")
case_studies = state.get("case_studies")

# Communicator writes to state
state = {
    **state,
    "outreach_draft": "Subject: ..."
}
```

#### Sequential vs Parallel Execution

**Sequential (Current Implementation):**
```python
# Nodes execute one after another
LeadIngestion → Research → QualificationCheck → DraftOutreach
```

**Parallel (Future Enhancement):**
```python
# Multiple agents can run simultaneously
Research → [Regulatory Lookup, Case Study Search] (parallel)
```

#### Resources

- **Multi-Agent Systems:** https://en.wikipedia.org/wiki/Multi-agent_system
- **Agent Patterns:** https://langchain-ai.github.io/langgraph/concepts/multi-agent/

---

### 4.2 Human-in-the-Loop (HITL) Patterns

#### Interrupt Mechanism

**LangGraph Interrupt:**
```python
from langgraph.prebuilt import interrupt

async def human_review_node(state: AOROState) -> AOROState:
    score = float(state.get("qualification_score") or 0.0)
    
    if score >= 0.8:
        # Auto-approve high confidence
        return {**state, "human_approved": True}
    
    # Interrupt for human review
    interrupt({
        "type": "approval_required",
        "lead_id": state.get("lead_id"),
        "draft": state.get("outreach_draft"),
        "confidence": score
    })
    
    # Resume after human approval
    return {**state, "human_approved": bool(state.get("human_approved", False))}
```

**How It Works:**
1. Workflow pauses at interrupt
2. External system (API, UI) shows approval request
3. Human approves/rejects
4. Workflow resumes with updated state

#### Auto-Approval Thresholds

**Confidence-Based Routing:**
```python
def route_after_review(state: AOROState) -> str:
    if state.get("human_approved") is True:
        return "SendOutreach"
    return END  # Rejected or pending
```

**Scoring Logic:**
```python
score = 0.2  # Base score
if "issued" in status:
    score += 0.3
if "fire" in permit_type:
    score += 0.2
if decision_maker:
    score += 0.1

# Auto-approve if score >= 0.8
```

#### Approval Workflow

**State Machine:**
```
DraftOutreach → HumanReview → [Approved?] → SendOutreach
                              [Rejected?] → END
```

**Resume After Approval:**
```python
# After human approves via API
updated_state = {
    **current_state,
    "human_approved": True
}

# Resume workflow
result = await app.ainvoke(updated_state)
```

#### Resources

- **LangGraph Interrupts:** https://langchain-ai.github.io/langgraph/how-tos/interrupts/
- **HITL Patterns:** https://www.patterns.dev/posts/human-in-the-loop/

---

### 4.3 Tool/Function Calling Patterns

#### Tool Definition

**Simple Tool:**
```python
async def lookup_applicable_fire_codes(*, building_type: str | None) -> list[str]:
    """
    Look up fire codes that apply to a building type.
    
    Args:
        building_type: Type of building (e.g., "hospital")
    
    Returns:
        List of applicable fire code IDs
    """
    building_type_id = normalize_building_type(building_type)
    rows = await get_applicable_codes(building_type_id)
    return [f"{r['code_id']} ({r['edition']})" for r in rows]
```

**Tool with Error Handling:**
```python
async def search_case_studies(query: str, *, top_k: int = 5) -> list[dict]:
    try:
        vec = await embed_text(query)
    except Exception:
        return []  # Graceful degradation
    
    try:
        index = get_index()
        ns = tenant_namespace(current_tenant_id())
        res = index.query(vector=vec, top_k=top_k, include_metadata=True, namespace=ns)
    except Exception:
        return []  # Return empty on failure
    
    # Normalize results
    matches = res.get("matches", [])
    return [
        {
            "id": m.get("id"),
            "score": m.get("score"),
            "metadata": m.get("metadata")
        }
        for m in matches
    ]
```

#### Tool Usage in Agents

**Researcher Agent Example:**
```python
async def researcher_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    building_type = permit.get("building_type")
    
    # Call tool 1: Regulatory lookup
    applicable = await lookup_applicable_fire_codes(building_type=building_type)
    
    # Call tool 2: Case study search
    query = f"{state.get('company_name','')} {building_type or ''} fire safety"
    case_studies = await search_case_studies(query, top_k=5)
    
    # Update state with results
    return {
        **state,
        "applicable_codes": applicable,
        "case_studies": case_studies
    }
```

#### Tool Composition

**Chaining Tools:**
```python
# Tool 1: Find company domain
domain = await find_company_domain(company_name)

# Tool 2: Find decision maker (uses domain from tool 1)
decision_maker = await find_decision_maker(domain, company_name)

# Tool 3: Find email (uses domain and name from previous tools)
email = await find_email(domain, decision_maker["name"])
```

#### Resources

- **LangChain Tools:** https://python.langchain.com/docs/modules/tools/
- **Function Calling:** https://platform.openai.com/docs/guides/function-calling

---

## 5. Software Architecture

### 5.1 Multi-Tenancy Patterns

#### Context Variables for Tenant Scoping

**Implementation:**
```python
from contextvars import ContextVar

_tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)

def current_tenant_id() -> str | None:
    return _tenant_id_ctx.get()
```

**Setting Tenant Context:**
```python
@asynccontextmanager
async def tenant_scoped_session(tenant_id: str):
    token = _tenant_id_ctx.set(tenant_id)
    try:
        yield
    finally:
        _tenant_id_ctx.reset(token)
```

**Usage:**
```python
async def process_lead(tenant_id: str, lead_id: str):
    async with tenant_scoped_session(tenant_id):
        # All code here has access to tenant_id via current_tenant_id()
        tenant = current_tenant_id()  # Returns tenant_id
        # Query Pinecone with tenant namespace
        # Query database with tenant filter
        # Log with tenant context
```

#### Namespace Isolation

**Pinecone Namespaces:**
```python
def tenant_namespace(tenant_id: str | None = None) -> str:
    tenant_id = tenant_id or current_tenant_id()
    return tenant_id or "default"

# Store data in tenant namespace
index.upsert(vectors=vectors, namespace=tenant_namespace("tenant-1"))

# Query from tenant namespace
index.query(vector=vec, namespace=tenant_namespace("tenant-1"))
```

**Database Isolation (Future):**
```python
# Row-level security (PostgreSQL example)
# Each query automatically filters by tenant_id
SELECT * FROM leads WHERE tenant_id = current_setting('app.tenant_id')
```

#### Tenant Verification

**Access Control:**
```python
async def verify_tenant_access(tenant_id: str) -> bool:
    settings = get_settings()
    allowed_tenants = settings.tenant_list()  # From env: "tenant1,tenant2"
    return tenant_id in allowed_tenants

@tenant_context
async def process_request(tenant_id: str, data: dict):
    # Decorator ensures tenant is verified and context is set
    # Process request...
    pass
```

#### Resources

- **Multi-Tenancy Patterns:** https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/overview
- **Context Variables:** https://docs.python.org/3/library/contextvars.html

---

### 5.2 Observability and Tracing

#### LangSmith Integration

**Setup:**
```python
from langsmith.wrappers import wrap_openai

client = AsyncOpenAI(api_key="...")
if settings.langsmith_tracing:
    client = wrap_openai(client)
```

**Tracing Functions:**
```python
from langsmith import traceable

@traceable(name="researcher_agent")
async def researcher_node(state: AOROState) -> AOROState:
    # All operations are automatically traced
    # View in LangSmith dashboard
    pass
```

**What Gets Traced:**
- LLM API calls (inputs, outputs, tokens, latency)
- Function executions
- State transitions
- Tool calls

#### Audit Logging

**Structured Events:**
```python
def audit_event(event_type: str, payload: dict[str, Any]) -> None:
    evt = {
        "type": event_type,
        "tenant_id": current_tenant_id(),
        "timestamp": datetime.utcnow().isoformat(),
        **payload
    }
    # Write to log file, database, or monitoring service
    append_audit(event_type, payload, lead_id=payload.get("lead_id"))
```

**Event Types:**
- `outreach_ready`: Outreach draft completed
- `human_approval_required`: Workflow interrupted
- `workflow_completed`: Full workflow finished
- `tool_called`: External tool invoked

#### Resources

- **LangSmith Docs:** https://docs.smith.langchain.com/
- **Observability:** https://docs.smith.langchain.com/tracing

---

### 5.3 API Design with FastAPI

#### RESTful Endpoints

**Basic Structure:**
```python
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

router = APIRouter()

class RunAgentRequest(BaseModel):
    tenant_id: str
    lead_id: str
    company_name: str
    decision_maker: dict | None = None
    permit_data: dict
    outreach_channel: str | None = "email"

@router.post("/run", response_model=dict[str, Any])
async def run_agents(req: RunAgentRequest):
    graph = build_graph()
    
    async with tenant_scoped_session(req.tenant_id):
        state_in: dict[str, Any] = {
            "tenant_id": req.tenant_id,
            "lead_id": req.lead_id,
            "company_name": req.company_name,
            "decision_maker": req.decision_maker or {},
            "permit_data": req.permit_data,
            "outreach_channel": req.outreach_channel or "email",
        }
        
        state_out = await graph.ainvoke(state_in)
    
    return {"ok": True, "state": state_out}
```

#### Request/Response Models

**Pydantic Models:**
```python
from pydantic import BaseModel, Field

class RunAgentRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    lead_id: str = Field(..., description="Unique lead ID")
    company_name: str = Field(..., min_length=1)
    decision_maker: dict | None = Field(None, description="Decision maker info")
    permit_data: dict = Field(..., description="Permit information")
    outreach_channel: Literal["email", "whatsapp", "voice"] = "email"
```

#### Error Handling

**Exception Handling:**
```python
from fastapi import HTTPException

@router.post("/run")
async def run_agents(req: RunAgentRequest):
    try:
        # Validate tenant access
        if not await verify_tenant_access(req.tenant_id):
            raise HTTPException(status_code=403, detail="Invalid tenant")
        
        # Run workflow
        result = await graph.ainvoke(state_in)
        return {"ok": True, "state": result}
    
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### Resources

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Pydantic:** https://docs.pydantic.dev/

---

## 6. Data Modeling

### 6.1 Pydantic Models

#### Basic Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

class EnrichedLead(BaseModel):
    lead_id: str
    tenant_id: str
    company: Company
    decision_maker: DecisionMaker | None
    permit: PermitData
    compliance: ComplianceContext | None
    outreach_channel_hint: Literal["email", "whatsapp", "voice"] = "email"
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### Field Validation

```python
from pydantic import BaseModel, Field, validator

class Company(BaseModel):
    name: str = Field(..., min_length=1)
    domain: str | None = None
    industry: str | None = None
    employee_count: int | None = Field(None, ge=0)
    
    @validator('domain')
    def validate_domain(cls, v):
        if v and not v.startswith('http'):
            return f"https://{v}"
        return v
```

#### Nested Models

```python
class Location(BaseModel):
    address: str
    city: str | None
    state: str | None
    zip_code: str | None
    latitude: float | None
    longitude: float | None

class Company(BaseModel):
    name: str
    location: Location | None
    domain: str | None
```

#### Resources

- **Pydantic Docs:** https://docs.pydantic.dev/
- **Data Validation:** https://docs.pydantic.dev/usage/validators/

---

### 6.2 Graph Data Modeling

#### Node Types

**FireCode Node:**
```cypher
CREATE (c:FireCode {
    code_id: "NFPA_72",
    name: "National Fire Alarm and Signaling Code",
    edition: "2022"
})
```

**BuildingType Node:**
```cypher
CREATE (b:BuildingType {
    type_id: "hospital",
    label: "Hospital"
})
```

#### Relationship Types

**APPLIES_TO:**
```cypher
MATCH (c:FireCode {code_id: "NFPA_72"})
MATCH (b:BuildingType {type_id: "hospital"})
CREATE (c)-[:APPLIES_TO]->(b)
```

**ENFORCES:**
```cypher
MATCH (j:Jurisdiction {fips_code: "37000"})
MATCH (c:FireCode {code_id: "NFPA_72"})
CREATE (j)-[:ENFORCES]->(c)
```

#### Schema Design Principles

1. **Use Labels for Types:** `FireCode`, not `FC`
2. **Index Key Properties:** `code_id`, `type_id`
3. **Relationships for Connections:** Not properties
4. **Properties for Attributes:** Name, edition, etc.

---

## 7. Workflow Patterns

### 7.1 Conditional Routing

#### State-Based Decisions

```python
def route_after_qualification(state: AOROState) -> str:
    score = float(state.get("qualification_score") or 0.0)
    
    if score < 0.5:
        return END  # Disqualified
    return "DraftOutreach"  # Qualified

graph.add_conditional_edges("QualificationCheck", route_after_qualification)
```

#### Multiple Conditions

```python
def route_after_review(state: AOROState) -> str:
    if state.get("human_approved") is True:
        return "SendOutreach"
    elif state.get("revision_requested") is True:
        return "DraftOutreach"  # Loop back for revision
    else:
        return END  # Rejected
```

#### Early Termination

```python
def route_logic(state: AOROState) -> str:
    if state.get("error"):
        return END  # Stop on error
    return "NextNode"
```

---

### 7.2 Error Handling and Resilience

#### Graceful Degradation

```python
async def researcher_node(state: AOROState) -> AOROState:
    # Try to get codes, but don't fail if it errors
    try:
        applicable = await lookup_applicable_fire_codes(...)
    except Exception as e:
        logger.warning(f"Code lookup failed: {e}")
        applicable = []  # Continue with empty list
    
    # Try case studies
    try:
        case_studies = await search_case_studies(...)
    except Exception:
        case_studies = []  # Continue with empty list
    
    return {
        **state,
        "applicable_codes": applicable,
        "case_studies": case_studies
    }
```

#### Retry Patterns

```python
import asyncio

async def retry_operation(max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await risky_operation()
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

---

## 8. Integration Patterns

### 8.1 External API Integration

#### HTTP Client Patterns

```python
import httpx

async def call_external_api(url: str, data: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API call failed: {e}")
            return None
```

#### Rate Limiting

```python
from asyncio import Semaphore

# Limit to 10 concurrent requests
semaphore = Semaphore(10)

async def rate_limited_call():
    async with semaphore:
        return await api_call()
```

---

### 8.2 Database Connection Management

#### Connection Pooling

```python
from neo4j import AsyncGraphDatabase

# Driver manages connection pool
driver = AsyncGraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password"),
    max_connection_lifetime=3600
)

# Sessions are lightweight, use connection pool
async with driver.session() as session:
    result = await session.run("MATCH (n) RETURN n")
```

#### Cleanup

```python
async def cleanup():
    driver = get_neo4j_driver()
    await driver.close()
    get_neo4j_driver.cache_clear()
```

---

## 9. Testing & Debugging

### 9.1 Testing Agent Workflows

#### Unit Testing Nodes

```python
import pytest

@pytest.mark.asyncio
async def test_researcher_node():
    state: AOROState = {
        "permit_data": {"building_type": "hospital"},
        "company_name": "Test Hospital"
    }
    
    result = await researcher_node(state)
    
    assert "applicable_codes" in result
    assert "case_studies" in result
```

#### Mocking External Dependencies

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_researcher_with_mocks():
    with patch('src.agents.tools.regulatory_lookup.lookup_applicable_fire_codes') as mock_lookup:
        mock_lookup.return_value = ["NFPA_72"]
        
        state = {"permit_data": {"building_type": "hospital"}}
        result = await researcher_node(state)
        
        assert result["applicable_codes"] == ["NFPA_72"]
```

#### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_workflow():
    graph = build_graph()
    
    initial_state: AOROState = {
        "tenant_id": "test-tenant",
        "lead_id": "test-lead",
        "company_name": "Test Company",
        "permit_data": {"building_type": "hospital"}
    }
    
    result = await graph.ainvoke(initial_state)
    
    assert "outreach_draft" in result
    assert result.get("qualification_score", 0) > 0
```

---

### 9.2 Debugging

#### State Inspection

```python
async def debug_node(state: AOROState) -> AOROState:
    import json
    print(f"Current state: {json.dumps(state, indent=2, default=str)}")
    return state
```

#### Workflow Visualization

- Use LangSmith to visualize workflow execution
- View state at each node
- See LLM calls and responses
- Identify bottlenecks

---

## 10. Domain Knowledge

### 10.1 Fire Safety Regulations

#### NFPA Codes

**NFPA 72:** National Fire Alarm and Signaling Code
- Requirements for fire alarm systems
- Applies to: Most commercial buildings

**NFPA 25:** Inspection, Testing, and Maintenance of Water-Based Fire Protection Systems
- Maintenance requirements for sprinkler systems
- Applies to: Buildings with sprinkler systems

**NFPA 101:** Life Safety Code
- Egress requirements
- Applies to: All occupied buildings

#### Building Types

- **Hospital:** Healthcare facilities
- **Data Center:** IT facilities
- **Commercial Office:** Office buildings
- **Warehouse:** Storage facilities
- **School:** Educational facilities

#### Code Applicability

- Different codes apply to different building types
- Jurisdictions may enforce different editions
- Codes are updated periodically (every 3 years typically)

#### Resources

- **NFPA Website:** https://www.nfpa.org/
- **Code References:** https://www.nfpa.org/codes-and-standards

---

## 11. Recommended Learning Path

### Week 1: Foundation
- [ ] LangGraph fundamentals (tutorials, docs)
- [ ] Async Python (asyncio, async/await)
- [ ] State management (TypedDict, immutable updates)

**Deliverable:** Build a simple 3-node LangGraph workflow

### Week 2: Databases
- [ ] Neo4j basics (Cypher, graph concepts)
- [ ] Pinecone basics (vectors, semantic search)
- [ ] Graph data modeling

**Deliverable:** 
- Create a Neo4j graph with fire codes and building types
- Index 10 case studies in Pinecone and query them

### Week 3: LLMs and Agents
- [ ] OpenAI API (chat completions, embeddings)
- [ ] Prompt engineering
- [ ] Multi-agent system design

**Deliverable:** Build a simple 2-agent system (researcher + communicator)

### Week 4: Architecture
- [ ] Multi-tenancy patterns
- [ ] Observability (LangSmith)
- [ ] FastAPI basics

**Deliverable:** Add multi-tenant support to your workflow

### Week 5: Advanced Patterns
- [ ] Human-in-the-loop
- [ ] Tool/function calling
- [ ] Conditional routing

**Deliverable:** Add HITL approval to your workflow

### Week 6: Integration and Testing
- [ ] External API integration
- [ ] Database connection management
- [ ] Testing strategies

**Deliverable:** Write tests for your workflow

---

## 12. Hands-On Exercises

### Exercise 1: Simple LangGraph Workflow

**Goal:** Build a 3-node workflow that processes text.

**Steps:**
1. Create a state with `text: str` and `processed: str`
2. Node 1: Normalize text (lowercase, strip)
3. Node 2: Count words
4. Node 3: Format output
5. Add conditional routing: if word count > 10, add "long" tag

### Exercise 2: Neo4j Fire Code Graph

**Goal:** Build a knowledge graph of fire codes.

**Steps:**
1. Create 5 FireCode nodes (NFPA_72, NFPA_25, NFPA_101, etc.)
2. Create 3 BuildingType nodes (hospital, data_center, office)
3. Create APPLIES_TO relationships
4. Query: Find all codes for hospitals
5. Query: Find all buildings that NFPA_72 applies to

### Exercise 3: Pinecone Case Study Search

**Goal:** Index and search case studies.

**Steps:**
1. Write 5 case study texts (about fire safety projects)
2. Generate embeddings for each
3. Store in Pinecone with metadata (building_type, outcome)
4. Query with similar text
5. Verify top results are semantically similar

### Exercise 4: Multi-Agent System

**Goal:** Build a 2-agent workflow.

**Steps:**
1. Researcher agent: Takes company name, returns industry
2. Communicator agent: Takes industry, generates email
3. Connect with LangGraph
4. Test with different company names

### Exercise 5: Human-in-the-Loop

**Goal:** Add approval gate to workflow.

**Steps:**
1. Add confidence scoring to your workflow
2. Add interrupt for low confidence (< 0.7)
3. Test auto-approval (high confidence)
4. Test manual approval (low confidence)

### Exercise 6: Full Phase 2 Workflow

**Goal:** Replicate Phase 2 workflow.

**Steps:**
1. Implement all nodes (LeadIngestion, Research, QualificationCheck, DraftOutreach, HumanReview, SendOutreach)
2. Add conditional routing
3. Integrate Neo4j and Pinecone
4. Add multi-tenant support
5. Test end-to-end

---

## Additional Resources

### Documentation
- **LangGraph:** https://langchain-ai.github.io/langgraph/
- **Neo4j:** https://neo4j.com/docs/
- **Pinecone:** https://docs.pinecone.io/
- **OpenAI:** https://platform.openai.com/docs/
- **FastAPI:** https://fastapi.tiangolo.com/
- **Pydantic:** https://docs.pydantic.dev/

### Tutorials
- **LangGraph Tutorial:** https://langchain-ai.github.io/langgraph/tutorials/
- **Neo4j Cypher Tutorial:** https://neo4j.com/developer/cypher/
- **Pinecone Quickstart:** https://docs.pinecone.io/guides/get-started/quickstart

### Books
- "Designing Data-Intensive Applications" by Martin Kleppmann
- "Building Microservices" by Sam Newman
- "Clean Architecture" by Robert C. Martin

---

## Study Tips

1. **Hands-On First:** Don't just read—build something
2. **Start Small:** Begin with simple examples, then scale up
3. **Read the Code:** Study the actual Phase 2 implementation
4. **Experiment:** Try modifying the code to see what happens
5. **Ask Questions:** Use the codebase as a reference
6. **Iterate:** Build, test, break, fix, repeat

---

**Good luck with your studies! This guide should give you a solid foundation for understanding Phase 2.**

