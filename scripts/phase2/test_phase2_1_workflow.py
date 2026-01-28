"""Test script for Phase 2.1: Core Workflow & Outreach Generation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.agents.orchestrator import build_graph
from src.agents.state import AOROState
from src.signal_engine.storage.lead_storage import LeadStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_workflow_with_enriched_lead():
    """Test Phase 2.1 workflow with a real enriched lead from Phase 1."""
    logger.info("=" * 60)
    logger.info("Testing Phase 2.1: Core Workflow & Outreach Generation")
    logger.info("=" * 60)

    # Load an enriched lead from Phase 1
    storage = LeadStorage()
    leads = storage.get_recent(days=30)

    if not leads:
        logger.warning("No enriched leads found. Please run Phase 1.3 enrichment first.")
        logger.info("Creating a test lead for demonstration...")
        
        # Create a minimal test lead
        from src.signal_engine.models import EnrichedLead, PermitData, Company, DecisionMaker
        
        test_permit = PermitData(
            source="test",
            permit_id="TEST-001",
            permit_type="Fire Alarm",
            address="123 Test St, Charlotte, NC",
            building_type="Commercial",
            status="Issued",
            applicant_name="Test Company",
        )
        
        test_lead = EnrichedLead(
            lead_id="test-lead-001",
            tenant_id="demo",
            permit=test_permit,
            company=Company(name="Test Company", website="test.com"),
            decision_maker=DecisionMaker(
                full_name="John Doe",
                title="Facilities Manager",
                email="john.doe@test.com",
            ),
        )
        
        leads = [test_lead]
        logger.info("Using test lead for demonstration")

    # Use the first lead
    lead = leads[0]
    logger.info(f"Testing with lead: {lead.lead_id}")
    logger.info(f"  Company: {lead.company.name}")
    logger.info(f"  Decision Maker: {lead.decision_maker.full_name if lead.decision_maker else 'None'}")
    logger.info(f"  Permit: {lead.permit.permit_type} - {lead.permit.status}")

    # Build initial state from enriched lead
    initial_state: AOROState = {
        "lead_id": lead.lead_id,
        "tenant_id": lead.tenant_id,
        "company_name": lead.company.name,
        "decision_maker": lead.decision_maker.model_dump() if lead.decision_maker else {},
        "permit_data": lead.permit.model_dump(),
        "outreach_channel": "email",
    }

    # Build and run workflow
    graph = build_graph()
    
    logger.info("\n" + "=" * 60)
    logger.info("Running workflow...")
    logger.info("=" * 60)

    try:
        # Run workflow
        final_state = await graph.ainvoke(initial_state)
        
        logger.info("\n" + "=" * 60)
        logger.info("Workflow completed!")
        logger.info("=" * 60)
        
        # Display results
        logger.info(f"\nQualification Score: {final_state.get('qualification_score', 0):.2f}")
        logger.info(f"Compliance Urgency: {final_state.get('compliance_urgency_score', 0):.2f}")
        logger.info(f"Human Approved: {final_state.get('human_approved', False)}")
        logger.info(f"Applicable Codes: {len(final_state.get('applicable_codes', []))}")
        logger.info(f"Compliance Gaps: {len(final_state.get('compliance_gaps', []))}")
        logger.info(f"Case Studies: {len(final_state.get('case_studies', []))}")
        
        if final_state.get("outreach_draft"):
            logger.info("\n" + "-" * 60)
            logger.info("Outreach Draft:")
            logger.info("-" * 60)
            logger.info(final_state.get("outreach_draft"))
        
        if final_state.get("response_history"):
            logger.info("\n" + "-" * 60)
            logger.info("Response History:")
            logger.info("-" * 60)
            for entry in final_state.get("response_history", []):
                logger.info(f"  - {entry.get('type')}: {entry.get('channel', 'N/A')}")
                if entry.get("email_id"):
                    logger.info(f"    Email ID: {entry.get('email_id')}")
        
        logger.info("\n✅ Phase 2.1 workflow test completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_workflow_with_enriched_lead())
    exit(0 if success else 1)
