"""Component validation test for Phase 2.1 (no email sending)."""

from __future__ import annotations

import asyncio
import logging

from src.agents.nodes.communicator import communicator_node, generate_email_outreach
from src.agents.nodes.researcher import calculate_compliance_urgency, researcher_node
from src.agents.orchestrator import build_graph
from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage
from src.agents.infrastructure.email_sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_workflow_storage():
    """Test workflow storage layer."""
    logger.info("=" * 60)
    logger.info("Testing Workflow Storage")
    logger.info("=" * 60)

    storage = WorkflowStorage()
    
    # Create test state
    test_state: AOROState = {
        "lead_id": "test-storage-001",
        "tenant_id": "demo",
        "company_name": "Test Company",
        "qualification_score": 0.75,
        "outreach_draft": "Test draft",
    }
    
    # Save state
    storage.save_workflow_state("test-storage-001", test_state)
    logger.info("✓ Saved workflow state")
    
    # Load state
    loaded_state = storage.load_workflow_state("test-storage-001")
    if loaded_state:
        logger.info("✓ Loaded workflow state")
        logger.info(f"  Lead ID: {loaded_state.get('lead_id')}")
        logger.info(f"  Score: {loaded_state.get('qualification_score')}")
    else:
        logger.error("✗ Failed to load workflow state")
        return False
    
    # Test outreach storage
    storage.save_outreach("test-storage-001", {
        "channel": "email",
        "subject": "Test Subject",
        "body": "Test body",
    })
    logger.info("✓ Saved outreach")
    
    # Test response storage
    storage.save_response("test-storage-001", {
        "content": "Test response",
        "source": "email",
    })
    logger.info("✓ Saved response")
    
    logger.info("")
    return True


async def test_researcher_urgency_scoring():
    """Test compliance urgency scoring."""
    logger.info("=" * 60)
    logger.info("Testing Compliance Urgency Scoring")
    logger.info("=" * 60)

    # Test case 1: High urgency (inspection scheduled)
    high_urgency_state: AOROState = {
        "permit_data": {
            "status": "Inspection Scheduled",
            "permit_type": "Fire Alarm",
            "building_type": "Hospital",
        },
        "applicable_codes": ["NFPA_72", "NFPA_101"],
        "compliance_gaps": ["Inspection deadline approaching"],
    }
    
    urgency = await calculate_compliance_urgency(high_urgency_state)
    logger.info(f"High urgency case: {urgency:.2f}")
    assert urgency >= 0.6, f"Expected high urgency (≥0.6), got {urgency}"
    logger.info("✓ High urgency scoring works")
    
    # Test case 2: Low urgency (pending)
    low_urgency_state: AOROState = {
        "permit_data": {
            "status": "Pending",
            "permit_type": "General",
            "building_type": "Unknown",
        },
        "applicable_codes": [],
        "compliance_gaps": [],
    }
    
    urgency = await calculate_compliance_urgency(low_urgency_state)
    logger.info(f"Low urgency case: {urgency:.2f}")
    assert urgency < 0.5, f"Expected low urgency (<0.5), got {urgency}"
    logger.info("✓ Low urgency scoring works")
    
    logger.info("")
    return True


async def test_communicator_channels():
    """Test multi-channel communicator."""
    logger.info("=" * 60)
    logger.info("Testing Multi-Channel Communicator")
    logger.info("=" * 60)

    test_state: AOROState = {
        "lead_id": "test-comm-001",
        "company_name": "Test Company",
        "decision_maker": {
            "full_name": "John Doe",
            "title": "Facilities Manager",
        },
        "permit_data": {
            "permit_type": "Fire Alarm",
            "status": "Issued",
            "address": "123 Test St",
        },
        "applicable_codes": ["NFPA_72"],
        "compliance_gaps": ["Inspection required"],
        "outreach_channel": "email",
    }
    
    # Test email channel
    email_state = {**test_state, "outreach_channel": "email"}
    result = await communicator_node(email_state)
    if result.get("outreach_draft"):
        logger.info("✓ Email outreach generated")
        logger.info(f"  Length: {len(result.get('outreach_draft', ''))} chars")
    else:
        logger.error("✗ Failed to generate email outreach")
        return False
    
    # Test WhatsApp channel
    whatsapp_state = {**test_state, "outreach_channel": "whatsapp"}
    result = await communicator_node(whatsapp_state)
    if result.get("outreach_draft"):
        logger.info("✓ WhatsApp outreach generated")
        logger.info(f"  Length: {len(result.get('outreach_draft', ''))} chars")
    else:
        logger.error("✗ Failed to generate WhatsApp outreach")
        return False
    
    # Test voice channel
    voice_state = {**test_state, "outreach_channel": "voice"}
    result = await communicator_node(voice_state)
    if result.get("outreach_draft"):
        logger.info("✓ Voice script generated")
        logger.info(f"  Length: {len(result.get('outreach_draft', ''))} chars")
    else:
        logger.error("✗ Failed to generate voice script")
        return False
    
    logger.info("")
    return True


async def test_email_sender_init():
    """Test email sender initialization."""
    logger.info("=" * 60)
    logger.info("Testing Email Sender Initialization")
    logger.info("=" * 60)

    # Test SMTP initialization
    smtp_sender = EmailSender(provider="smtp")
    logger.info("✓ SMTP sender initialized")
    
    # Test SendGrid initialization (if key configured)
    try:
        sendgrid_sender = EmailSender(provider="sendgrid")
        logger.info("✓ SendGrid sender initialized")
    except Exception as e:
        logger.warning(f"⚠ SendGrid not configured: {e}")
    
    # Test SES initialization (if configured)
    try:
        ses_sender = EmailSender(provider="ses")
        logger.info("✓ SES sender initialized")
    except Exception as e:
        logger.warning(f"⚠ SES not configured: {e}")
    
    logger.info("")
    return True


async def test_workflow_graph():
    """Test workflow graph construction."""
    logger.info("=" * 60)
    logger.info("Testing Workflow Graph Construction")
    logger.info("=" * 60)

    try:
        graph = build_graph()
        logger.info("✓ Workflow graph built successfully")
        
        # Check that graph has expected nodes
        # (LangGraph doesn't expose node list directly, so we just verify it compiles)
        logger.info("✓ Graph compilation successful")
    except Exception as e:
        logger.error(f"✗ Failed to build workflow graph: {e}")
        return False
    
    logger.info("")
    return True


async def main():
    """Run all component tests."""
    logger.info("=" * 70)
    logger.info("Phase 2.1 Component Validation Tests")
    logger.info("=" * 70)
    logger.info("")

    tests = [
        ("Workflow Storage", test_workflow_storage),
        ("Compliance Urgency Scoring", test_researcher_urgency_scoring),
        ("Multi-Channel Communicator", test_communicator_channels),
        ("Email Sender Initialization", test_email_sender_init),
        ("Workflow Graph Construction", test_workflow_graph),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ {test_name} failed: {e}", exc_info=True)
            results.append((test_name, False))

    # Summary
    logger.info("=" * 70)
    logger.info("Test Summary")
    logger.info("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("")
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✅ All Phase 2.1 components validated!")
        return True
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
