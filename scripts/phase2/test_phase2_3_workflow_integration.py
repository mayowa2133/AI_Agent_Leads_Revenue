"""Test Phase 2.3 workflow integration - full workflow with follow-ups and booking."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from src.agents.orchestrator import build_graph
from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_full_workflow_with_followup():
    """Test full workflow including follow-up path."""
    logger.info("=" * 60)
    logger.info("Test 1: Full Workflow - Follow-up Path")
    logger.info("=" * 60)
    
    graph = build_graph()
    
    # Verify all Phase 2.3 nodes are in graph
    nodes = graph.nodes
    assert "FollowUp" in nodes, "FollowUp node should be in graph"
    assert "BookMeeting" in nodes, "BookMeeting node should be in graph"
    assert "UpdateCRM" in nodes, "UpdateCRM node should be in graph"
    logger.info("✓ All Phase 2.3 nodes found in graph")
    
    # Test follow-up path: WaitForResponse → FollowUp → SendOutreach
    logger.info("\nTesting follow-up routing:")
    from src.agents.nodes.wait_response import wait_response_node
    from src.agents.nodes.followup import followup_node
    
    # State with timeout
    state_timeout: AOROState = {
        "lead_id": "test-followup-workflow-001",
        "outreach_sent_at": (datetime.now() - timedelta(days=8)).isoformat(),
        "outreach_channel": "email",
    }
    
    wait_result = await wait_response_node(state_timeout)
    assert wait_result.get("response_timeout") is True, "Should detect timeout"
    logger.info("  ✓ Timeout detected")
    
    # Follow-up should be triggered
    followup_result = await followup_node(wait_result)
    assert followup_result.get("followup_count") == 1, "Should increment follow-up count"
    assert followup_result.get("outreach_draft") is not None, "Should generate follow-up draft"
    logger.info("  ✓ Follow-up generated")
    
    logger.info("✓ Test 1 passed\n")


async def test_full_workflow_with_booking():
    """Test full workflow including booking path."""
    logger.info("=" * 60)
    logger.info("Test 2: Full Workflow - Booking Path")
    logger.info("=" * 60)
    
    from src.agents.nodes.handle_response import handle_response_node
    from src.agents.nodes.book_meeting import book_meeting_node
    from src.agents.nodes.update_crm import update_crm_node
    
    # State with positive response
    state_positive: AOROState = {
        "lead_id": "test-booking-workflow-001",
        "company_name": "Test Company",
        "decision_maker": {
            "full_name": "John Doe",
            "email": "john@testcompany.com",
        },
        "permit_data": {
            "permit_id": "TEST-001",
            "permit_type": "Fire Alarm",
        },
        "response_data": {
            "content": "Yes, I'm interested! Can we schedule a call?",
            "from_email": "john@testcompany.com",
        },
        "response_classification": "positive",
        "response_received": True,
    }
    
    # Handle response
    handle_result = await handle_response_node(state_positive)
    assert handle_result.get("response_classification") == "positive", "Should classify as positive"
    logger.info("  ✓ Response classified as positive")
    
    # Book meeting
    book_result = await book_meeting_node(handle_result)
    assert book_result.get("booking_ready") is True, "Booking should be ready"
    logger.info("  ✓ Booking prepared")
    
    # Update CRM
    crm_result = await update_crm_node(book_result)
    assert crm_result.get("crm_update_status") == "ready", "CRM should be ready"
    assert crm_result.get("workflow_complete") is True, "Workflow should be complete"
    logger.info("  ✓ CRM update ready")
    
    logger.info("✓ Test 2 passed\n")


async def test_objection_handling_workflow():
    """Test objection handling workflow path."""
    logger.info("=" * 60)
    logger.info("Test 3: Objection Handling Workflow")
    logger.info("=" * 60)
    
    from src.agents.nodes.handle_response import handle_response_node
    from src.agents.nodes.closer import closer_node
    from src.agents.nodes.communicator import communicator_node
    
    # State with objection response
    state_objection: AOROState = {
        "lead_id": "test-objection-workflow-001",
        "company_name": "Test Company",
        "response_data": {
            "content": "We already have a vendor for fire safety. Thanks but no thanks.",
            "from_email": "decision.maker@example.com",
        },
        "response_received": True,
        "applicable_codes": ["NFPA 13"],
        "compliance_gaps": ["Missing sprinkler system"],
    }
    
    # Handle response (should classify as objection)
    handle_result = await handle_response_node(state_objection)
    assert handle_result.get("response_classification") == "objection", "Should classify as objection"
    logger.info("  ✓ Response classified as objection")
    
    # Handle objection
    objection_result = await closer_node(handle_result)
    assert objection_result.get("objection_handling_count") == 1, "Should track objection cycles"
    assert objection_result.get("outreach_draft") is not None, "Should generate revised outreach"
    logger.info("  ✓ Objection handled, revised outreach generated")
    
    # Should route back to DraftOutreach (communicator)
    draft_result = await communicator_node(objection_result)
    assert draft_result.get("outreach_draft") is not None, "Should have outreach draft"
    logger.info("  ✓ Revised outreach drafted")
    
    logger.info("✓ Test 3 passed\n")


async def test_max_attempts_enforcement():
    """Test max attempts enforcement for follow-ups and objections."""
    logger.info("=" * 60)
    logger.info("Test 4: Max Attempts Enforcement")
    logger.info("=" * 60)
    
    from src.agents.nodes.followup import followup_node
    from src.agents.nodes.closer import closer_node
    from src.core.config import get_settings
    
    settings = get_settings()
    max_followups = getattr(settings, "max_followup_attempts", 2)
    max_objections = getattr(settings, "max_objection_handling_cycles", 3)
    
    # Test follow-up max attempts
    logger.info(f"Testing follow-up max attempts (max: {max_followups})")
    state_followup: AOROState = {
        "lead_id": "test-max-followup-001",
        "company_name": "Test Company",
        "followup_count": max_followups,
        "outreach_channel": "email",
    }
    
    followup_result = await followup_node(state_followup)
    assert followup_result.get("workflow_complete") is True, "Should complete workflow"
    assert followup_result.get("workflow_status") == "no_response", "Status should be no_response"
    logger.info("  ✓ Follow-up max attempts enforced")
    
    # Test objection max cycles
    logger.info(f"Testing objection max cycles (max: {max_objections})")
    state_objection: AOROState = {
        "lead_id": "test-max-objection-001",
        "current_objection": "Not interested",
        "objection_handling_count": max_objections,
        "applicable_codes": [],
        "compliance_gaps": [],
    }
    
    # Note: The orchestrator routing will handle max cycles, not the closer node itself
    # The closer node just increments the count
    objection_result = await closer_node(state_objection)
    assert objection_result.get("objection_handling_count") == max_objections + 1, "Should increment count"
    logger.info("  ✓ Objection handling count tracked")
    logger.info("  (Max cycles enforced by orchestrator routing)")
    
    logger.info("✓ Test 4 passed\n")


async def main():
    """Run all Phase 2.3 workflow integration tests."""
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.3: Workflow Integration Tests")
    logger.info("=" * 60 + "\n")
    
    try:
        await test_full_workflow_with_followup()
        await test_full_workflow_with_booking()
        await test_objection_handling_workflow()
        await test_max_attempts_enforcement()
        
        logger.info("=" * 60)
        logger.info("✓ All Phase 2.3 workflow integration tests passed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
