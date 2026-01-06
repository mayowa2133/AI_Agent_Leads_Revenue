## Plan–Act–Reflect (PAR) Workflow

This repo uses a Plan–Act–Reflect loop to keep AI-assisted work traceable.

### Plan
Before coding, create a short plan containing:
- objective and non-goals
- files to change
- risks (security/compliance/integration)
- test/verification steps

### Act
Implement in small chunks:
- keep diffs reviewable
- add docstrings/comments
- keep tests deterministic (no network)

### Reflect
After implementation:
- summarize what changed
- note what remains
- append a short entry to `docs/ai/WORKLOG.md`
- update `docs/ai/CHANGELOG.md` if the change is user-visible


