# Phase 2.3: Testing Guide

**Status:** ✅ All Tests Passing  
**Date:** January 2026

## Quick Test Commands

### Run All Phase 2.3 Tests

```bash
# Comprehensive end-to-end test (recommended - tests all scenarios)
poetry run python scripts/phase2/test_phase2_3_comprehensive.py

# Component-level tests
poetry run python scripts/phase2/test_phase2_3_followups.py

# Workflow integration tests
poetry run python scripts/phase2/test_phase2_3_workflow_integration.py
```

### Run Individual Test Suites

```bash
# Test 1: FollowUp Node (follow-up sequences, max attempts)
poetry run python scripts/phase2/test_phase2_3_followups.py

# Test 2: Workflow Integration (all nodes, routing)
poetry run python scripts/phase2/test_phase2_3_workflow_integration.py

# Test 3: Comprehensive Scenarios (end-to-end workflows)
poetry run python scripts/phase2/test_phase2_3_comprehensive.py
```

## Test Coverage

### ✅ Component Tests (`test_phase2_3_followups.py`)

**Test 1: FollowUp Node**
- ✓ First follow-up generation
- ✓ Second follow-up generation
- ✓ Max attempts enforcement (workflow completion)

**Test 2: BookMeeting Node**
- ✓ Meeting preferences extraction
- ✓ Booking payload preparation

**Test 3: UpdateCRM Node**
- ✓ CRM status marking
- ✓ Workflow completion

**Test 4: Objection Handling Cycle**
- ✓ Objection handling count tracking
- ✓ Revised outreach generation

### ✅ Integration Tests (`test_phase2_3_workflow_integration.py`)

**Test 1: Full Workflow - Follow-up Path**
- ✓ Timeout detection
- ✓ Follow-up generation
- ✓ Routing to SendOutreach

**Test 2: Full Workflow - Booking Path**
- ✓ Positive response classification
- ✓ Booking preparation
- ✓ CRM update ready

**Test 3: Objection Handling Workflow**
- ✓ Objection classification
- ✓ Objection handling
- ✓ Revised outreach drafting

**Test 4: Max Attempts Enforcement**
- ✓ Follow-up max attempts
- ✓ Objection max cycles

### ✅ Comprehensive Tests (`test_phase2_3_comprehensive.py`)

**Scenario 1: Positive Response → Booking → CRM**
- ✓ Full workflow execution
- ✓ Response detection
- ✓ Booking preparation
- ✓ CRM update ready

**Scenario 2: Objection → Revised Outreach**
- ✓ Objection classification
- ✓ Objection handling
- ✓ Revised outreach generation

**Scenario 3: Timeout → Follow-up → Max Attempts**
- ✓ Timeout detection
- ✓ First follow-up
- ✓ Second follow-up
- ✓ Max attempts reached

**Scenario 4: Objection Handling Max Cycles**
- ✓ Max cycles enforcement
- ✓ Cycle tracking

**Workflow Graph Structure Verification**
- ✓ All 12 required nodes present
- ✓ Graph structure validated

## Expected Test Results

### Component Tests Output

```
✓ Test 1 passed (FollowUp Node)
✓ Test 2 passed (BookMeeting Node)
✓ Test 3 passed (UpdateCRM Node)
✓ Test 4 passed (Objection Handling Cycle)
✓ All Phase 2.3 tests passed!
```

### Integration Tests Output

```
✓ Test 1 passed (Full Workflow - Follow-up Path)
✓ Test 2 passed (Full Workflow - Booking Path)
✓ Test 3 passed (Objection Handling Workflow)
✓ Test 4 passed (Max Attempts Enforcement)
✓ All Phase 2.3 workflow integration tests passed!
```

### Comprehensive Tests Output

```
✓ PASSED: Workflow Graph Structure
✓ PASSED: Scenario 1: Positive → Booking
✓ PASSED: Scenario 2: Objection → Revised
✓ PASSED: Scenario 3: Follow-up Sequence
✓ PASSED: Scenario 4: Max Objection Cycles

Total: 5/5 tests passed
🎉 ALL PHASE 2.3 COMPREHENSIVE TESTS PASSED!
```

## Manual Testing Steps

### 1. Test Follow-up Sequence

```python
# Create a test state with timeout
from src.agents.nodes.wait_response import wait_response_node
from src.agents.nodes.followup import followup_node
from datetime import datetime, timedelta

state = {
    "lead_id": "test-manual-001",
    "outreach_sent_at": (datetime.now() - timedelta(days=8)).isoformat(),
    "outreach_channel": "email",
    "followup_count": 0,
}

# Wait for response (should timeout)
wait_result = await wait_response_node(state)
print(f"Timeout: {wait_result.get('response_timeout')}")

# Generate follow-up
followup_result = await followup_node(wait_result)
print(f"Follow-up count: {followup_result.get('followup_count')}")
print(f"Follow-up draft: {followup_result.get('outreach_draft')[:100]}...")
```

### 2. Test Booking Flow

```python
# Create a test state with positive response
from src.agents.nodes.handle_response import handle_response_node
from src.agents.nodes.book_meeting import book_meeting_node

state = {
    "lead_id": "test-manual-002",
    "response_data": {
        "content": "Yes, I'm interested! Can we schedule a call?",
    },
    "response_received": True,
}

# Handle response
handle_result = await handle_response_node(state)
print(f"Classification: {handle_result.get('response_classification')}")

# Book meeting
book_result = await book_meeting_node(handle_result)
print(f"Booking ready: {book_result.get('booking_ready')}")
print(f"Meeting preferences: {book_result.get('meeting_preferences')}")
```

### 3. Test Objection Handling

```python
# Create a test state with objection
from src.agents.nodes.closer import closer_node

state = {
    "lead_id": "test-manual-003",
    "current_objection": "We already have a vendor",
    "objection_handling_count": 0,
    "applicable_codes": ["NFPA 13"],
    "compliance_gaps": ["Missing sprinkler system"],
}

# Handle objection
result = await closer_node(state)
print(f"Objection count: {result.get('objection_handling_count')}")
print(f"Revised outreach: {result.get('outreach_draft')[:100]}...")
```

## Verification Checklist

After running tests, verify:

- [ ] All test suites pass (5/5 comprehensive tests)
- [ ] FollowUp node generates follow-up messages
- [ ] Max follow-up attempts enforced (default: 2)
- [ ] BookMeeting node extracts meeting preferences
- [ ] UpdateCRM node marks booking as ready
- [ ] Objection handling tracks cycles
- [ ] Max objection cycles enforced (default: 3)
- [ ] Workflow graph contains all 12 nodes
- [ ] Routing logic works for all paths:
  - [ ] Positive response → BookMeeting → UpdateCRM
  - [ ] Objection → ObjectionHandling → DraftOutreach
  - [ ] No response → FollowUp → SendOutreach
  - [ ] Timeout → FollowUp → SendOutreach

## Troubleshooting

### Issue: "OpenAI API error"
**Solution:** Verify OpenAI API key in `.env`:
```bash
grep OPENAI_API_KEY .env
```

### Issue: "Workflow graph missing nodes"
**Solution:** Verify orchestrator imports all nodes:
```bash
grep "from src.agents.nodes" src/agents/orchestrator.py
```

### Issue: "Tests fail with import errors"
**Solution:** Ensure all dependencies installed:
```bash
poetry install
```

### Issue: "State schema errors"
**Solution:** Verify state schema includes Phase 2.3 fields:
```bash
grep "followup_count\|booking_payload\|workflow_complete" src/agents/state.py
```

## Test Data Files

Tests create temporary data in:
- `data/workflow_states.json` - Workflow state snapshots
- `data/workflow_responses.json` - Response data
- `data/workflow_outreachs.json` - Outreach tracking

These files are safe to delete after testing:
```bash
rm data/workflow_*.json
```

## Success Criteria

Phase 2.3 is fully implemented when:

✅ All test suites pass  
✅ FollowUp node works with max attempts  
✅ BookMeeting node extracts preferences  
✅ UpdateCRM node marks booking ready  
✅ Objection handling tracks cycles  
✅ Workflow graph includes all nodes  
✅ Routing logic works for all paths  
✅ Max attempts enforced correctly  

## Next Steps

After Phase 2.3 verification:
- Proceed to Phase 2.4: Testing & Monitoring
- Add LangSmith integration for observability
- Create end-to-end tests with real enriched leads
- Optimize workflow performance
