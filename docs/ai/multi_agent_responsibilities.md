## Multi-Agent Responsibilities and Handoffs (MAS Contract)

This document defines **who does what**, **when the system must pause for human approval**, and **how agents communicate** to prevent runaway logic.

### Shared definitions
- **Lead**: an `EnrichedLead` (permit + company + decision maker + compliance context)
- **Workflow state**: `AOROState` (`src/agents/state.py`)
- **HITL**: human-in-the-loop approval gate (interrupt)

### Agent roles (current MVP)

#### Researcher Agent (`src/agents/nodes/researcher.py`)
- **Inputs**: permit metadata, company name, optional decision maker data
- **Responsibilities**:
  - Determine **applicable codes** (via Neo4j lookup)
  - Identify **compliance gaps / urgency signals** (heuristics in MVP)
  - Retrieve **relevant case studies** (vector search)
- **Outputs**:
  - `applicable_codes`
  - `compliance_gaps`
  - `case_studies`

#### Communication Agent (`src/agents/nodes/communicator.py`)
- **Inputs**: research outputs + decision maker context
- **Responsibilities**:
  - Draft **technical-first outreach** (email/WhatsApp/voice later)
  - Keep language concise, credible, non-hype
- **Outputs**:
  - `outreach_draft`
  - `outreach_channel`

#### Closer Agent (`src/agents/nodes/closer.py`)
- **Inputs**: objection text + research outputs
- **Responsibilities**:
  - Provide **short technical rebuttals** and propose next step (scheduling)
  - Avoid legal claims; cite codes only when helpful
- **Outputs**:
  - appended `response_history` entries (objection replies)

### Human-in-the-loop (HITL) checkpoints

#### Approval gate (`src/agents/nodes/human_review.py`)
- **Auto-approve** if `qualification_score >= 0.8`
- **Otherwise**: trigger an interrupt with payload:
  - `type=approval_required`
  - `lead_id`
  - `draft`
  - `confidence`

**Rule**: no outbound outreach occurs unless `human_approved == True` (or an explicitly defined future “auto-send” policy).

### Communication patterns and safety
- Agents communicate **only via `AOROState`** (no side channels).
- External side effects (CRM writes, booking creation) must be behind:
  - MCP tools
  - tenant validation
  - audit logging
  - optional HITL approval

### Preventing runaway logic
- Any loop (follow-ups, objection handling) must enforce:
  - max attempts
  - max time window
  - explicit stop conditions
- If ambiguity is detected (missing decision maker, missing permit details), prefer:
  - enrichment retry
  - human review
  - or graceful disqualification


