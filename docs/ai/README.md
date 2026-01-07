## AI Documentation (Project Memory)

This folder is the project’s “audit trail” for how the system evolves.

### Where to look
- **Status**: `docs/ai/STATUS.md` (current implementation status and handoff notes)
- **Plan**: `docs/plan/aoro_mvp_master_plan.md`
- **Changelog**: `docs/ai/CHANGELOG.md` (high-level human-readable changes)
- **Worklog**: `docs/ai/WORKLOG.md` (chronological engineering notes)
- **Architecture Decisions (ADRs)**: `docs/ai/adr/` (why we made key choices)
- **Multi-agent contract**: `docs/ai/multi_agent_responsibilities.md` (handoffs + HITL rules)
- **Audit logging**: `docs/ai/audit/README.md` (machine-readable, compliance-oriented)
- **Workflows**: `docs/ai/workflows/plan_act_reflect.md`

### Process (lightweight, but consistent)
- For any non-trivial change: add a short entry to `CHANGELOG.md`
- For any architectural decision: add an ADR in `docs/ai/adr/`
- For every work session: append 3-10 bullets to `WORKLOG.md`

### Documentation gate (CI-style)
We enforce doc updates on significant changes:
- Script: `scripts/docs_gate.py`
- CI: `.github/workflows/docs-gate.yml`

### Plan–Act–Reflect (PAR)
Use the templates in `docs/ai/workflows/`:
- `docs/ai/workflows/plan_act_reflect.md`
- `docs/ai/workflows/task_template.md`


