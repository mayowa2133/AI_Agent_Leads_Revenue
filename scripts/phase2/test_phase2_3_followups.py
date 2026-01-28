"""Test Phase 2.3: Follow-ups & Objection Management."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from src.agents.nodes.book_meeting import book_meeting_node
from src.agents.nodes.followup import followup_node
from src.agents.nodes.update_crm import update_crm_node
from src.agents.state import AOROState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_followup_node():
    """Test FollowUp node with max attempts."""
    logger.info("=" * 60)
    logger.info("Test 1: FollowUp Node")
    logger.info("=" * 60)
    
    # Test case 1: First follow-up
    logger.info("Test 1a: First follow-up")
    state_1: AOROState = {
        "lead_id": "test-followup-001",
        "company_name": "Test Company",
        "permit_data": {"permit_id": "TEST-001", "permit_type": "Fire Alarm"},
        "compliance_gaps": ["Missing sprinkler system"],
        "followup_count": 0,
        "outreach_channel": "email",
    }
    
    result_1 = await followup_node(state_1)
    assert result_1.get("followup_count") == 1, "Follow-up count should increment"
    assert result_1.get("outreach_draft") is not None, "Should generate follow-up draft"
    assert result_1.get("followup_scheduled_at") is not None, "Should schedule follow-up"
    logger.info(f"  ✓ Follow-up count: {result_1.get('followup_count')}")
    logger.info(f"  ✓ Draft generated: {len(result_1.get('outreach_draft', ''))} chars")
    
    # Test case 2: Second follow-up
    logger.info("Test 1b: Second follow-up")
    state_2: AOROState = {
        **state_1,
        "followup_count": 1,
    }
    
    result_2 = await followup_node(state_2)
    assert result_2.get("followup_count") == 2, "Follow-up count should increment"
    logger.info(f"  ✓ Follow-up count: {result_2.get('followup_count')}")
    
    # Test case 3: Max attempts reached
    logger.info("Test 1c: Max attempts reached")
    state_3: AOROState = {
        **state_1,
        "followup_count": 2,  # Max is 2
    }
    
    result_3 = await followup_node(state_3)
    assert result_3.get("workflow_complete") is True, "Should mark workflow as complete"
    assert result_3.get("workflow_status") == "no_response", "Status should be no_response"
    logger.info(f"  ✓ Workflow complete: {result_3.get('workflow_complete')}")
    logger.info(f"  ✓ Status: {result_3.get('workflow_status')}")
    
    logger.info("✓ Test 1 passed\n")


async def test_book_meeting_node():
    """Test BookMeeting node."""
    logger.info("=" * 60)
    logger.info("Test 2: BookMeeting Node")
    logger.info("=" * 60)
    
    state: AOROState = {
        "lead_id": "test-booking-001",
        "company_name": "Test Company",
        "decision_maker": {
            "full_name": "John Doe",
            "email": "john@testcompany.com",
            "title": "Facilities Manager",
        },
        "permit_data": {
            "permit_id": "TEST-001",
            "permit_type": "Fire Alarm",
            "address": "123 Main St",
            "status": "Issued",
        },
        "response_data": {
            "content": "Yes, I'm interested! Can we schedule a call next week? I'm available Monday or Tuesday morning.",
            "from_email": "john@testcompany.com",
        },
        "response_classification": "positive",
        "compliance_gaps": ["Missing sprinkler system"],
        "applicable_codes": ["NFPA 13"],
    }
    
    result = await book_meeting_node(state)
    
    assert result.get("booking_ready") is True, "Booking should be ready"
    assert result.get("booking_payload") is not None, "Should have booking payload"
    assert result.get("meeting_preferences") is not None, "Should extract meeting preferences"
    
    booking_payload = result.get("booking_payload", {})
    assert booking_payload.get("lead_id") == "test-booking-001", "Lead ID should match"
    assert booking_payload.get("company_name") == "Test Company", "Company name should match"
    assert booking_payload.get("meeting_type") == "consultation", "Meeting type should be consultation"
    
    logger.info(f"  ✓ Booking ready: {result.get('booking_ready')}")
    logger.info(f"  ✓ Meeting preferences: {result.get('meeting_preferences', {}).get('preferred_times', [])}")
    logger.info(f"  ✓ Booking payload prepared")
    
    logger.info("✓ Test 2 passed\n")


async def test_update_crm_node():
    """Test UpdateCRM node."""
    logger.info("=" * 60)
    logger.info("Test 3: UpdateCRM Node")
    logger.info("=" * 60)
    
    booking_payload = {
        "lead_id": "test-crm-001",
        "company_name": "Test Company",
        "decision_maker": {
            "full_name": "John Doe",
            "email": "john@testcompany.com",
        },
        "meeting_type": "consultation",
        "meeting_preferences": {
            "preferred_times": ["morning"],
            "preferred_dates": ["next week"],
        },
    }
    
    state: AOROState = {
        "lead_id": "test-crm-001",
        "company_name": "Test Company",
        "booking_payload": booking_payload,
        "booking_ready": True,
    }
    
    result = await update_crm_node(state)
    
    assert result.get("crm_update_status") == "ready", "CRM status should be ready"
    assert result.get("workflow_complete") is True, "Workflow should be complete"
    assert result.get("workflow_status") == "booking_ready", "Status should be booking_ready"
    
    logger.info(f"  ✓ CRM status: {result.get('crm_update_status')}")
    logger.info(f"  ✓ Workflow complete: {result.get('workflow_complete')}")
    logger.info(f"  ✓ Workflow status: {result.get('workflow_status')}")
    
    logger.info("✓ Test 3 passed\n")


async def test_objection_handling_cycle():
    """Test objection handling with cycle tracking."""
    logger.info("=" * 60)
    logger.info("Test 4: Objection Handling Cycle")
    logger.info("=" * 60)
    
    from src.agents.nodes.closer import closer_node
    
    state: AOROState = {
        "lead_id": "test-objection-001",
        "company_name": "Test Company",
        "current_objection": "We already have a vendor",
        "extracted_objections": ["We already have a vendor"],
        "objection_handling_count": 0,
        "applicable_codes": ["NFPA 13"],
        "compliance_gaps": ["Missing sprinkler system"],
    }
    
    result = await closer_node(state)
    
    assert result.get("objection_handling_count") == 1, "Objection count should increment"
    assert result.get("outreach_draft") is not None, "Should generate revised outreach"
    assert result.get("current_objection") is not None, "Should track objection"
    
    logger.info(f"  ✓ Objection handling count: {result.get('objection_handling_count')}")
    logger.info(f"  ✓ Revised outreach generated: {len(result.get('outreach_draft', ''))} chars")
    
    logger.info("✓ Test 4 passed\n")


async def main():
    """Run all Phase 2.3 tests."""
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.3: Follow-ups & Objection Management Tests")
    logger.info("=" * 60 + "\n")
    
    try:
        await test_followup_node()
        await test_book_meeting_node()
        await test_update_crm_node()
        await test_objection_handling_cycle()
        
        logger.info("=" * 60)
        logger.info("✓ All Phase 2.3 tests passed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
