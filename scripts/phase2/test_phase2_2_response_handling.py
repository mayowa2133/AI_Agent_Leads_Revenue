"""Test Phase 2.2: Response Handling & Classification."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.agents.nodes.handle_response import handle_response_node
from src.agents.nodes.wait_response import wait_response_node
from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_response_storage():
    """Test saving and retrieving responses."""
    logger.info("=" * 60)
    logger.info("Test 1: Response Storage")
    logger.info("=" * 60)
    
    storage = WorkflowStorage()
    test_lead_id = "test-lead-response-001"
    
    # Save a test response
    test_response = {
        "content": "Yes, I'm interested in learning more about fire safety compliance.",
        "from_email": "decision.maker@example.com",
        "to_email": "noreply@aoro.ai",
        "subject": "Re: Fire Safety Compliance Consultation",
        "received_at": datetime.now().isoformat(),
        "source": "email",
    }
    
    storage.save_response(test_lead_id, test_response)
    logger.info(f"✓ Saved response for lead {test_lead_id}")
    
    # Retrieve latest response
    latest = storage.get_latest_response(test_lead_id)
    assert latest is not None, "Should retrieve saved response"
    assert latest["content"] == test_response["content"], "Content should match"
    logger.info(f"✓ Retrieved latest response: {latest['content'][:50]}...")
    
    logger.info("✓ Test 1 passed\n")


async def test_wait_response_node():
    """Test WaitForResponse node."""
    logger.info("=" * 60)
    logger.info("Test 2: WaitForResponse Node")
    logger.info("=" * 60)
    
    storage = WorkflowStorage()
    test_lead_id = "test-lead-wait-001"
    
    # Test case 1: Response received
    logger.info("Test 2a: Response received")
    outreach_time = (datetime.now() - timedelta(hours=2)).isoformat()
    state: AOROState = {
        "lead_id": test_lead_id,
        "outreach_sent_at": outreach_time,
        "outreach_channel": "email",
    }
    
    # Save a response that's newer than outreach
    storage.save_response(
        test_lead_id,
        {
            "content": "I'm interested!",
            "received_at": datetime.now().isoformat(),
        },
    )
    
    result = await wait_response_node(state)
    assert result.get("response_received") is True, "Should detect response"
    logger.info(f"✓ Response detected: {result.get('response_received')}")
    
    # Test case 2: Timeout
    logger.info("Test 2b: Timeout reached")
    old_outreach_time = (datetime.now() - timedelta(days=8)).isoformat()
    state_timeout: AOROState = {
        "lead_id": "test-lead-timeout-001",
        "outreach_sent_at": old_outreach_time,
        "outreach_channel": "email",
    }
    
    result = await wait_response_node(state_timeout)
    assert result.get("response_timeout") is True, "Should detect timeout"
    logger.info(f"✓ Timeout detected: {result.get('response_timeout')}")
    
    # Test case 3: Still waiting
    logger.info("Test 2c: Still waiting")
    recent_outreach_time = (datetime.now() - timedelta(hours=1)).isoformat()
    state_waiting: AOROState = {
        "lead_id": "test-lead-waiting-001",
        "outreach_sent_at": recent_outreach_time,
        "outreach_channel": "email",
    }
    
    result = await wait_response_node(state_waiting)
    assert result.get("waiting_for_response") is True, "Should be waiting"
    logger.info(f"✓ Still waiting: {result.get('waiting_for_response')}")
    
    logger.info("✓ Test 2 passed\n")


async def test_handle_response_node():
    """Test HandleResponse node classification."""
    logger.info("=" * 60)
    logger.info("Test 3: HandleResponse Node (Classification)")
    logger.info("=" * 60)
    
    # Test case 1: Positive response
    logger.info("Test 3a: Positive response")
    state_positive: AOROState = {
        "lead_id": "test-lead-positive-001",
        "response_data": {
            "content": "Yes, I'd like to schedule a consultation. When are you available?",
            "from_email": "decision.maker@example.com",
        },
    }
    
    result = await handle_response_node(state_positive)
    classification = result.get("response_classification")
    sentiment = result.get("response_sentiment")
    interest = result.get("interest_level")
    
    logger.info(f"  Classification: {classification}")
    logger.info(f"  Sentiment: {sentiment}")
    logger.info(f"  Interest Level: {interest}")
    assert classification in ["positive", "objection", "no_response", "unsubscribe"]
    logger.info("✓ Positive response classified")
    
    # Test case 2: Objection response
    logger.info("Test 3b: Objection response")
    state_objection: AOROState = {
        "lead_id": "test-lead-objection-001",
        "response_data": {
            "content": "We already have a vendor for fire safety. Thanks but no thanks.",
            "from_email": "decision.maker@example.com",
        },
    }
    
    result = await handle_response_node(state_objection)
    classification = result.get("response_classification")
    objections = result.get("extracted_objections", [])
    
    logger.info(f"  Classification: {classification}")
    logger.info(f"  Extracted Objections: {objections}")
    assert classification in ["positive", "objection", "no_response", "unsubscribe"]
    logger.info("✓ Objection response classified")
    
    # Test case 3: No response / empty
    logger.info("Test 3c: Empty response")
    state_empty: AOROState = {
        "lead_id": "test-lead-empty-001",
        "response_data": {
            "content": "",
            "from_email": "decision.maker@example.com",
        },
    }
    
    result = await handle_response_node(state_empty)
    classification = result.get("response_classification")
    assert classification == "no_response", "Empty should be no_response"
    logger.info(f"✓ Empty response classified as: {classification}")
    
    logger.info("✓ Test 3 passed\n")


async def test_webhook_integration():
    """Test webhook endpoint integration (simulated)."""
    logger.info("=" * 60)
    logger.info("Test 4: Webhook Integration (Simulated)")
    logger.info("=" * 60)
    
    storage = WorkflowStorage()
    test_lead_id = "test-lead-webhook-001"
    
    # Simulate webhook payload
    webhook_payload = {
        "lead_id": test_lead_id,
        "from_email": "customer@example.com",
        "to_email": "noreply@aoro.ai",
        "subject": "Re: Fire Safety Consultation",
        "content": "I'm interested in learning more. Can we schedule a call?",
        "received_at": datetime.now().isoformat(),
        "source": "email",
    }
    
    # Save via storage (simulating webhook handler)
    storage.save_response(test_lead_id, webhook_payload)
    logger.info(f"✓ Simulated webhook saved response for {test_lead_id}")
    
    # Verify it's retrievable
    latest = storage.get_latest_response(test_lead_id)
    assert latest is not None, "Webhook response should be saved"
    assert latest["content"] == webhook_payload["content"], "Content should match"
    logger.info(f"✓ Verified response retrieval: {latest['content'][:50]}...")
    
    logger.info("✓ Test 4 passed\n")


async def test_end_to_end_response_flow():
    """Test end-to-end response handling flow."""
    logger.info("=" * 60)
    logger.info("Test 5: End-to-End Response Flow")
    logger.info("=" * 60)
    
    storage = WorkflowStorage()
    # Use a unique lead_id with timestamp to avoid conflicts
    import time
    test_lead_id = f"test-lead-e2e-{int(time.time())}"
    
    # Step 1: Initial state with outreach sent
    outreach_time = (datetime.now() - timedelta(hours=3)).isoformat()
    initial_state: AOROState = {
        "lead_id": test_lead_id,
        "company_name": "Test Company",
        "outreach_sent_at": outreach_time,
        "outreach_channel": "email",
        "response_history": [],
    }
    
    logger.info("Step 1: Initial state (outreach sent)")
    
    # Step 2: Wait for response (no response yet)
    logger.info("Step 2: WaitForResponse (no response yet)")
    # Ensure no response exists for this lead
    wait_state = await wait_response_node(initial_state)
    assert wait_state.get("waiting_for_response") is True, "Should be waiting"
    logger.info("  → Still waiting for response")
    
    # Step 3: Simulate response received via webhook
    logger.info("Step 3: Response received via webhook")
    storage.save_response(
        test_lead_id,
        {
            "content": "Yes, I'm interested! Let's schedule a meeting.",
            "from_email": "decision.maker@example.com",
            "received_at": datetime.now().isoformat(),
        },
    )
    
    # Step 4: Wait for response again (should detect it)
    logger.info("Step 4: WaitForResponse (response detected)")
    wait_state_2 = await wait_response_node(initial_state)
    assert wait_state_2.get("response_received") is True, "Should detect response"
    logger.info("  → Response detected!")
    
    # Step 5: Handle response (classify)
    logger.info("Step 5: HandleResponse (classify)")
    handle_state: AOROState = {
        **wait_state_2,
        "response_data": wait_state_2.get("response_data"),
    }
    classified_state = await handle_response_node(handle_state)
    
    classification = classified_state.get("response_classification")
    sentiment = classified_state.get("response_sentiment")
    interest = classified_state.get("interest_level")
    
    logger.info(f"  → Classification: {classification}")
    logger.info(f"  → Sentiment: {sentiment}")
    logger.info(f"  → Interest Level: {interest}")
    
    assert classification is not None, "Should have classification"
    logger.info("✓ End-to-end flow completed successfully")
    
    logger.info("✓ Test 5 passed\n")


async def main():
    """Run all Phase 2.2 tests."""
    logger.info("\n" + "=" * 60)
    logger.info("Phase 2.2: Response Handling & Classification Tests")
    logger.info("=" * 60 + "\n")
    
    try:
        await test_response_storage()
        await test_wait_response_node()
        await test_handle_response_node()
        await test_webhook_integration()
        await test_end_to_end_response_flow()
        
        logger.info("=" * 60)
        logger.info("✓ All Phase 2.2 tests passed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
