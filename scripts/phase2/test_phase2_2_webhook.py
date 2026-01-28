"""Test Phase 2.2 webhook endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def test_webhook_endpoint():
    """Test the email response webhook endpoint."""
    logger.info("=" * 60)
    logger.info("Testing Phase 2.2 Webhook Endpoint")
    logger.info("=" * 60)
    
    # Test payload
    test_payload = {
        "lead_id": f"test-webhook-{int(datetime.now().timestamp())}",
        "from_email": "customer@example.com",
        "to_email": "noreply@aoro.ai",
        "subject": "Re: Fire Safety Consultation",
        "content": "Yes, I'm interested in learning more about fire safety compliance. Can we schedule a call?",
        "received_at": datetime.now().isoformat(),
        "source": "email",
    }
    
    logger.info(f"Test Lead ID: {test_payload['lead_id']}")
    logger.info(f"Test Content: {test_payload['content'][:50]}...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test webhook endpoint
            logger.info("\n1. Testing POST /webhooks/email-response")
            response = await client.post(
                f"{BASE_URL}/webhooks/email-response",
                json=test_payload,
            )
            
            logger.info(f"   Status Code: {response.status_code}")
            logger.info(f"   Response: {json.dumps(response.json(), indent=2)}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            result = response.json()
            assert result.get("ok") is True, "Response should have ok=true"
            assert result.get("lead_id") == test_payload["lead_id"], "Lead ID should match"
            
            logger.info("   ✓ Webhook endpoint working correctly")
            
            # Verify response was saved
            logger.info("\n2. Verifying response was saved to storage")
            from src.agents.storage.workflow_storage import WorkflowStorage
            
            storage = WorkflowStorage()
            saved_response = storage.get_latest_response(test_payload["lead_id"])
            
            assert saved_response is not None, "Response should be saved"
            assert saved_response["content"] == test_payload["content"], "Content should match"
            logger.info(f"   ✓ Response saved: {saved_response['content'][:50]}...")
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Webhook endpoint test passed!")
            logger.info("=" * 60)
            
    except httpx.ConnectError:
        logger.error("\n✗ Could not connect to API server")
        logger.error("   Please start the API server first:")
        logger.error("   poetry run uvicorn src.api.main:app --reload")
        raise
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_webhook_endpoint())
