# Phase 2.2: Response Handling & Classification - Complete

**Status:** ✅ Complete  
**Date:** January 2026

## Overview

Phase 2.2 implements response tracking, classification, and routing for the agentic workflow. This enables the system to receive, classify, and route email responses appropriately.

## Components Implemented

### 1. Response Storage ✅
- **File:** `src/agents/storage/workflow_storage.py`
- **Status:** Already existed, verified working
- **Methods:**
  - `save_response()` - Save response to JSON storage
  - `get_latest_response()` - Retrieve most recent response for a lead
  - `load_all_responses()` - Load all responses

### 2. WaitForResponse Node ✅
- **File:** `src/agents/nodes/wait_response.py`
- **Functionality:**
  - Checks for responses via workflow storage (populated by webhook)
  - Detects timeout (configurable, default 7 days)
  - Routes to HandleResponse if response received
  - Routes to FollowUp (Phase 2.3) if timeout reached
  - Marks as waiting if still within timeout window

### 3. HandleResponse Node ✅
- **File:** `src/agents/nodes/handle_response.py`
- **Functionality:**
  - Classifies responses using OpenAI GPT-4o-mini
  - Classification types: `positive`, `objection`, `no_response`, `unsubscribe`
  - Extracts sentiment: `positive`, `neutral`, `negative`
  - Extracts interest level: `high`, `medium`, `low`, `none`
  - Extracts objections from response text
  - Routes to appropriate next node based on classification

### 4. Webhook Handler ✅
- **File:** `src/api/routes/webhooks.py`
- **Endpoint:** `POST /webhooks/email-response`
- **Functionality:**
  - Accepts email response webhooks from SendGrid, AWS SES, or generic format
  - Extracts lead_id from payload or metadata
  - Saves response to workflow storage
  - Returns confirmation
  - **Future:** Will trigger workflow resumption in Phase 2.3+

### 5. State Schema Updates ✅
- **File:** `src/agents/state.py`
- **New Fields:**
  - `response_received: bool` - True if response was received
  - `response_timeout: bool` - True if timeout reached
  - `response_data: dict | None` - Response data from webhook
  - `response_classification: str | None` - Classification result
  - `response_sentiment: str | None` - Sentiment analysis
  - `interest_level: str | None` - Interest level assessment
  - `extracted_objections: list[str]` - List of objections found
  - `waiting_for_response: bool` - True if currently waiting

### 6. Workflow Integration ✅
- **File:** `src/agents/orchestrator.py`
- **Changes:**
  - Added `WaitForResponse` node after `SendOutreach`
  - Added `HandleResponse` node after `WaitForResponse`
  - Added conditional routing:
    - `WaitForResponse` → `HandleResponse` (if response received)
    - `WaitForResponse` → `END` (if timeout, will route to FollowUp in Phase 2.3)
    - `HandleResponse` → `ObjectionHandling` (if objection)
    - `HandleResponse` → `END` (if positive/no_response/unsubscribe, will route to BookMeeting in Phase 2.3)

### 7. Configuration ✅
- **File:** `src/core/config.py`
- **New Setting:**
  - `response_timeout_days: int = 7` - Days to wait for response before follow-up

## Testing

### Test Script
- **File:** `scripts/phase2/test_phase2_2_response_handling.py`
- **Coverage:**
  1. Response storage (save/retrieve)
  2. WaitForResponse node (response received, timeout, still waiting)
  3. HandleResponse node (positive, objection, empty responses)
  4. Webhook integration (simulated)
  5. End-to-end response flow

### Test Results
```
✓ All Phase 2.2 tests passed!
- Test 1: Response Storage ✅
- Test 2: WaitForResponse Node ✅
- Test 3: HandleResponse Node (Classification) ✅
- Test 4: Webhook Integration ✅
- Test 5: End-to-End Response Flow ✅
```

## Workflow Flow

```
SendOutreach → WaitForResponse → HandleResponse → [Route based on classification]
                                    ↓
                            ┌───────┴───────┐
                            │              │
                    [positive]      [objection]
                            │              │
                    [BookMeeting]  [ObjectionHandling]
                            │              │
                            └──────┬───────┘
                                   ↓
                              [DraftOutreach]
```

## API Endpoints

### POST /webhooks/email-response
**Purpose:** Receive email response webhooks

**Request Body:**
```json
{
  "lead_id": "lead-123",
  "from_email": "customer@example.com",
  "to_email": "noreply@aoro.ai",
  "subject": "Re: Fire Safety Consultation",
  "content": "I'm interested!",
  "received_at": "2026-01-07T12:00:00Z",
  "source": "email"
}
```

**Response:**
```json
{
  "ok": true,
  "lead_id": "lead-123",
  "message": "Response saved"
}
```

## Next Steps (Phase 2.3)

1. **FollowUp Node** - Automated follow-up sequences
2. **ObjectionHandling Integration** - Enhanced objection handling
3. **BookMeeting Node** - Meeting scheduling
4. **Workflow Resumption** - Trigger workflow continuation from webhook
5. **UpdateCRM Node** - CRM integration (Phase 3 prep)

## Notes

- **Interrupt Mechanism:** Currently, `WaitForResponse` doesn't use LangGraph's interrupt mechanism. For MVP, it marks as waiting and the workflow completes. In production with checkpointer, this will interrupt and resume when response is received.
- **Webhook Triggering:** The webhook currently only saves responses. In Phase 2.3+, it will trigger workflow resumption if the workflow is in a waiting state.
- **Classification Accuracy:** Uses GPT-4o-mini for classification. Can be fine-tuned with examples in Phase 2.4.
