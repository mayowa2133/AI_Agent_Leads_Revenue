## Audit Logging (Compliance / Explainability)

This project targets regulated compliance workflows. We keep an **append-only, machine-readable audit log** for:
- key agent decisions
- human approvals (HITL)
- tool calls (MCP) that cause external side effects
- model metadata (when available)

### Format
- **File**: JSONL (one JSON object per line)
- **Schema**: `docs/ai/audit/event.schema.json`

### Default path (dev)
Set:
- `AORO_AUDIT_LOG_PATH=docs/ai/audit/events.jsonl`

In production, route these events to a durable store (DB/S3/SIEM) with retention controls.


