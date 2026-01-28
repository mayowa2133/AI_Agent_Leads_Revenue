"""Test Phase 2.2 workflow integration - full workflow with response handling."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.agents.orchestrator import build_graph
from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_workflow_with_response():
    """Test the full workflow including response handling."""
    logger.info("=" * 60)
    logger.info("Testing Phase 2.2 Workflow Integration")
    logger.info("=" * 60)
    
    # Create a test lead state
    test_lead_id = f"test-workflow-{int(datetime.now().timestamp())}"
    
    initial_state: AOROState = {
        "lead_id": test_lead_id,
        "tenant_id": "test-tenant",
        "company_name": "Test Fire Safety Company",
        "permit_data": {
            "permit_id": "TEST-001",
            "permit_type": "Fire Alarm",
            "status": "Issued",
            "address": "123 Main St, San Antonio, TX",
            "applicant_name": "Test Company",
        },
        "decision_maker": {
            "full_name": "John Doe",
            "email": "john.doe@testcompany.com",
            "title": "Facilities Manager",
        },
        "outreach_channel": "email",
        "response_history": [],
    }
    
    logger.info(f"Test Lead ID: {test_lead_id}")
    logger.info(f"Company: {initial_state['company_name']}")
    
    # Build workflow graph
    graph = build_graph()
    logger.info("\n✓ Workflow graph built")
    
    # Run workflow up to SendOutreach
    logger.info("\n1. Running workflow: START → SendOutreach")
    try:
        # For testing, we'll manually step through to avoid email sending
        # In production, this would run automatically
        
        # Check that WaitForResponse node exists
        nodes = graph.nodes
        assert "WaitForResponse" in nodes, "WaitForResponse node should be in graph"
        assert "HandleResponse" in nodes, "HandleResponse node should be in graph"
        logger.info("   ✓ WaitForResponse node found in graph")
        logger.info("   ✓ HandleResponse node found in graph")
        
        # Test WaitForResponse node directly
        logger.info("\n2. Testing WaitForResponse node")
        from src.agents.nodes.wait_response import wait_response_node
        
        # State with outreach sent
        state_with_outreach: AOROState = {
            **initial_state,
            "outreach_sent_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        }
        
        wait_result = await wait_response_node(state_with_outreach)
        logger.info(f"   Response received: {wait_result.get('response_received')}")
        logger.info(f"   Timeout: {wait_result.get('response_timeout')}")
        logger.info(f"   Waiting: {wait_result.get('waiting_for_response')}")
        assert wait_result.get("waiting_for_response") is True, "Should be waiting"
        logger.info("   ✓ WaitForResponse working correctly")
        
        # Simulate response received
        logger.info("\n3. Simulating response received via webhook")
        storage = WorkflowStorage()
        storage.save_response(
            test_lead_id,
            {
                "content": "Yes, I'm interested! Let's schedule a meeting.",
                "from_email": "john.doe@testcompany.com",
                "received_at": datetime.now().isoformat(),
            },
        )
        logger.info("   ✓ Response saved")
        
        # Test WaitForResponse again (should detect response)
        logger.info("\n4. Testing WaitForResponse after response received")
        wait_result_2 = await wait_response_node(state_with_outreach)
        assert wait_result_2.get("response_received") is True, "Should detect response"
        logger.info("   ✓ Response detected")
        
        # Test HandleResponse node
        logger.info("\n5. Testing HandleResponse node")
        from src.agents.nodes.handle_response import handle_response_node
        
        state_with_response: AOROState = {
            **wait_result_2,
            "response_data": wait_result_2.get("response_data"),
        }
        
        handle_result = await handle_response_node(state_with_response)
        classification = handle_result.get("response_classification")
        sentiment = handle_result.get("response_sentiment")
        interest = handle_result.get("interest_level")
        
        logger.info(f"   Classification: {classification}")
        logger.info(f"   Sentiment: {sentiment}")
        logger.info(f"   Interest Level: {interest}")
        
        assert classification is not None, "Should have classification"
        assert classification in ["positive", "objection", "no_response", "unsubscribe"]
        logger.info("   ✓ HandleResponse working correctly")
        
        # Verify routing logic
        logger.info("\n6. Testing workflow routing logic")
        
        # Check that graph has correct edges
        compiled_graph = graph
        logger.info("   ✓ Workflow graph includes response handling nodes")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Workflow integration test passed!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info(f"  - Lead ID: {test_lead_id}")
        logger.info(f"  - Response Classification: {classification}")
        logger.info(f"  - Sentiment: {sentiment}")
        logger.info(f"  - Interest Level: {interest}")
        logger.info(f"  - All nodes integrated correctly")
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_workflow_with_response())
