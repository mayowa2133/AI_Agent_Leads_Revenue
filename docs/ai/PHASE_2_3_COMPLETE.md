# Phase 2.3: Follow-ups & Objection Management - Complete

**Status:** ✅ Complete  
**Date:** January 2026

## Overview

Phase 2.3 implements follow-up sequences, objection handling integration, meeting booking preparation, and CRM integration preparation. This completes the response management workflow with automated follow-ups and booking preparation.

## Components Implemented

### 1. FollowUp Node ✅
- **File:** `src/agents/nodes/followup.py`
- **Functionality:**
  - Tracks follow-up attempts (max 2 by default, configurable)
  - Generates follow-up messages using OpenAI GPT-4o-mini
  - Different messaging strategy per attempt:
    - **First follow-up (3 days):** Gentle reminder, add value (case study, code update)
    - **Second follow-up (7 days):** Final attempt, soft close
  - Schedules follow-ups with increasing intervals
  - Marks workflow as complete with "no_response" status after max attempts
  - Routes back to SendOutreach to send follow-up message

### 2. ObjectionHandling Integration ✅
- **File:** `src/agents/nodes/closer.py` (enhanced)
- **Functionality:**
  - Enhanced to track objection handling cycles
  - Generates revised outreach messages addressing objections
  - Routes back to DraftOutreach with revised message
  - Max cycles enforced by orchestrator routing (default: 3)
  - Prevents infinite objection handling loops

### 3. BookMeeting Node ✅
- **File:** `src/agents/nodes/book_meeting.py`
- **Functionality:**
  - Extracts meeting preferences from response using OpenAI
  - Preferences include: preferred times, dates, meeting format, timezone, constraints, urgency
  - Prepares booking payload for CRM integration
  - Includes lead information, decision maker, permit data, compliance gaps
  - Routes to UpdateCRM node

### 4. UpdateCRM Node ✅
- **File:** `src/agents/nodes/update_crm.py`
- **Functionality:**
  - Placeholder for Phase 3 CRM integration (ServiceTitan MCP)
  - Logs booking request
  - Marks booking as ready for CRM
  - Stores booking payload in state
  - Ends workflow with "booking_ready" status
  - **Future:** Will call ServiceTitan MCP tool to create booking in Phase 3

### 5. Workflow Resumption ✅
- **File:** `src/api/routes/webhooks.py` (enhanced)
- **Functionality:**
  - Checks if workflow is waiting for response when webhook receives response
  - Updates workflow state with response data
  - Saves updated state for resumption
  - Returns confirmation that workflow resumption was triggered
  - **Note:** In production with checkpointer, would use `graph.resume()`

### 6. State Schema Updates ✅
- **File:** `src/agents/state.py`
- **New Fields:**
  - `followup_count: int` - Number of follow-up attempts
  - `followup_scheduled_at: str | None` - ISO timestamp for next follow-up
  - `workflow_complete: bool` - True if workflow is complete
  - `workflow_status: str | None` - "no_response", "booking_ready", "objection_loop_max", etc.
  - `objection_handling_count: int` - Number of objection handling cycles
  - `booking_payload: dict | None` - Booking data for CRM
  - `booking_ready: bool` - True if booking is ready for CRM
  - `meeting_preferences: dict | None` - Extracted meeting preferences
  - `crm_update_status: str | None` - "ready", "failed", "completed"
  - `crm_ready_at: str | None` - ISO timestamp when CRM update was ready

### 7. Configuration ✅
- **File:** `src/core/config.py`
- **New Settings:**
  - `max_followup_attempts: int = 2` - Maximum number of follow-up attempts
  - `max_objection_handling_cycles: int = 3` - Maximum objection handling cycles

### 8. Workflow Integration ✅
- **File:** `src/agents/orchestrator.py`
- **Changes:**
  - Added `FollowUp`, `BookMeeting`, `UpdateCRM` nodes to graph
  - Updated routing logic:
    - `WaitForResponse` → `FollowUp` (on timeout)
    - `HandleResponse` → `BookMeeting` (on positive response)
    - `HandleResponse` → `FollowUp` (on no_response)
    - `FollowUp` → `SendOutreach` (if not max attempts) or `END` (if max attempts)
    - `ObjectionHandling` → `DraftOutreach` (if not max cycles) or `END` (if max cycles)
    - `BookMeeting` → `UpdateCRM` → `END`

## Testing

### Test Scripts
- **File:** `scripts/phase2/test_phase2_3_followups.py` - Component tests
- **File:** `scripts/phase2/test_phase2_3_workflow_integration.py` - Integration tests

### Test Results
```
✓ All Phase 2.3 tests passed!
- Test 1: FollowUp Node ✅
  - First follow-up ✅
  - Second follow-up ✅
  - Max attempts reached ✅
- Test 2: BookMeeting Node ✅
- Test 3: UpdateCRM Node ✅
- Test 4: Objection Handling Cycle ✅
- Test 5: Full Workflow - Follow-up Path ✅
- Test 6: Full Workflow - Booking Path ✅
- Test 7: Objection Handling Workflow ✅
- Test 8: Max Attempts Enforcement ✅
```

## Workflow Flow

```
SendOutreach → WaitForResponse → HandleResponse → [Route based on classification]
                                    ↓
                            ┌───────┴───────┬───────────┐
                            │              │           │
                    [positive]      [objection]  [no_response]
                            │              │           │
                    [BookMeeting]  [ObjectionHandling] [FollowUp]
                            │              │           │
                    [UpdateCRM]    [DraftOutreach]  [SendOutreach]
                            │              │           │
                            └──────────────┴───────────┘
                                   ↓
                              [WaitForResponse]
```

## Follow-up Strategy

### First Follow-up (3 days after initial outreach)
- **Tone:** Friendly, value-focused
- **Content:** 
  - Gentle reminder
  - Add value (case study, code update)
  - Non-pushy approach
- **Subject:** "Re: Fire Safety Compliance Consultation - [Value Add]"

### Second Follow-up (7 days after initial outreach)
- **Tone:** Respectful, soft close
- **Content:**
  - Final attempt
  - Offer one last opportunity
  - Respect decision if not interested
- **Subject:** "Final Follow-up: Fire Safety Compliance Consultation"

### After Max Attempts
- Workflow marked as complete
- Status: "no_response"
- No further follow-ups

## Objection Handling Strategy

1. **Extract Objections:** From response classification
2. **Generate Reply:** Address objection with technical authority
3. **Revise Outreach:** Create new outreach message addressing objection
4. **Route Back:** Send revised message via DraftOutreach → SendOutreach
5. **Cycle Limit:** Max 3 cycles to prevent infinite loops

## Meeting Booking Flow

1. **Extract Preferences:** From positive response using LLM
   - Preferred times (morning, afternoon, specific times)
   - Preferred dates (next week, Monday, specific dates)
   - Meeting format (phone, video, in-person)
   - Timezone and constraints
   - Urgency level

2. **Prepare Payload:** Booking data for CRM
   - Lead information
   - Decision maker details
   - Permit data
   - Meeting preferences
   - Compliance gaps and codes

3. **Mark Ready:** UpdateCRM node marks as ready for Phase 3 integration

## API Endpoints

### POST /webhooks/email-response (Enhanced)

**Phase 2.3 Enhancement:**
- Now checks if workflow is waiting for response
- Triggers workflow resumption if waiting
- Updates workflow state with response data

**Response (with resumption):**
```json
{
  "ok": true,
  "lead_id": "lead-123",
  "message": "Response saved and workflow resumption triggered",
  "workflow_resumed": true
}
```

## Next Steps (Phase 2.4)

1. **End-to-End Testing** - Comprehensive tests with real enriched leads
2. **Workflow Monitoring** - LangSmith integration for observability
3. **Performance Optimization** - Optimize LLM calls and workflow execution
4. **Error Handling** - Enhanced error handling and recovery

## Notes

- **Workflow Resumption:** Currently saves state for scheduler to handle. In production with LangGraph checkpointer, would use `graph.resume()` for immediate resumption.
- **CRM Integration:** UpdateCRM node is a placeholder. Actual CRM booking will be implemented in Phase 3 using ServiceTitan MCP integration.
- **Follow-up Scheduling:** Follow-ups are scheduled but not automatically executed. In production, a scheduler would check `followup_scheduled_at` and trigger follow-up execution.
- **Max Attempts:** Configurable via `max_followup_attempts` and `max_objection_handling_cycles` settings.
