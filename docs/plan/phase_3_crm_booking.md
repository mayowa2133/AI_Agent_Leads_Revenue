# Phase 3 Master Plan: CRM + Booking Integration (Free-First)

## Goals
- Convert `booking_ready` into a concrete CRM record.
- Keep costs at zero/low by default (CSV + optional Airtable free tier).
- Preserve existing Phase 2 behavior (no scheduling automation required).

## Scope
1. **CRM Export** (free-by-default)
   - CSV export already exists and is the fallback source of truth.
2. **CRM Provider Integration**
   - Add Airtable integration (free tier) as the primary no-cost CRM option.
3. **Operational Readiness**
   - Config-driven provider selection.
   - Basic error logging and status fields in workflow state.
4. **Verification**
   - Dry-run workflow and webhook simulation still pass.
   - Airtable call works when credentials are provided.

## Implementation Steps
1. **Add CRM provider configuration**
   - `CRM_PROVIDER` (`csv` default, `airtable` optional)
   - `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`
2. **Create CRM client**
   - Interface for `create_booking(payload)` and provider-based behavior.
3. **Update `UpdateCRM` node**
   - Always write CSV if enabled (source of truth).
   - Optionally write to Airtable if configured.
   - Set status fields (`crm_update_status`, `crm_error`).
4. **Documentation**
   - README update for CRM provider config.

## Acceptance Criteria
- With no CRM config, CSV export continues to work.
- With Airtable config, a booking row is created in Airtable.
- Workflow completes even if CRM write fails (error recorded).

## Verification Checklist
- Run Phase 2 e2e in dry-run mode (emails not sent).
- Simulate inbound reply → booking export generated.
- (Optional) Airtable insert succeeds and record appears in table.

## Rollout Notes
- Keep `CRM_PROVIDER=csv` until Airtable is confirmed.
- Airtable free tier is sufficient for MVP.
