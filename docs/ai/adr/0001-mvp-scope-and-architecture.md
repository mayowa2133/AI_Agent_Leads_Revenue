## 0001 - MVP scope and architecture

- **Status**: accepted
- **Date**: 2026-01-02

### Context
We need an MVP that demonstrates the full AORO loop for the Commercial Fire Safety niche:
signal detection → enrichment → regulatory reasoning → outreach drafting → HITL gate → CRM tooling.

### Decision
- Use **LangGraph** for orchestration (stateful graph + interrupts).
- Use **Neo4j** for regulatory relationships (codes ↔ building types).
- Use **Pinecone** for tenant-namespaced semantic retrieval (case studies).
- Use **FastMCP** as the standardized tool bridge to **ServiceTitan** endpoints.
- Use **OpenAI** models for generation + embeddings, with optional LangSmith tracing.

### Consequences
- MVP uses placeholders/mocks in some areas (e.g., outbound delivery, full response handling).
- Credentials and tenant mapping require hardening (vault/DB + RLS) before production.


