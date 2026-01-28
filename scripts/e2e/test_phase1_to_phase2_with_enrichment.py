"""End-to-end test: Real permit → Enrichment → Phase 2 workflow."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from src.core.config import get_settings
from src.core.security import tenant_scoped_session
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.models import PermitData, Company, DecisionMaker
from src.signal_engine.scrapers.permit_scraper import SanAntonioFireScraper
from src.signal_engine.storage.lead_storage import LeadStorage
from src.agents.orchestrator import build_graph
from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def get_real_permit() -> PermitData | None:
    """Get a real permit from San Antonio."""
    logger.info("Scraping real permit from San Antonio...")
    
    scraper = SanAntonioFireScraper(
        record_type="Fire Alarm",
        days_back=30,
    )

    try:
        permits = await scraper.scrape()
        if permits:
            permit = permits[0]
            logger.info(f"✓ Found permit: {permit.permit_id}")
            logger.info(f"  Type: {permit.permit_type}")
            logger.info(f"  Address: {permit.address}")
            return permit
    except Exception as e:
        logger.error(f"Scraping failed: {e}")

    return None


async def enrich_with_known_company(permit: PermitData, tenant_id: str):
    """Enrich permit with a known company domain to increase chance of finding email."""
    logger.info("\nEnriching permit with company matching...")
    
    # Enrich the permit
    lead = await enrich_permit_to_lead(
        EnrichmentInputs(tenant_id=tenant_id, permit=permit)
    )
    
    logger.info(f"✓ Enriched lead: {lead.lead_id}")
    logger.info(f"  Company: {lead.company.name}")
    
    # If no decision maker found, try to manually set a company with known domain
    # This simulates what would happen if Apollo found a domain
    if not lead.decision_maker or not lead.decision_maker.email:
        logger.info("  No decision maker found - this is expected for testing")
        logger.info("  For full E2E test, we'll proceed with the lead as-is")
    
    # Save the lead
    storage = LeadStorage()
    storage.save_lead(lead)
    logger.info("  ✓ Saved to storage")
    
    return lead


def convert_lead_to_state(lead) -> AOROState:
    """Convert enriched lead to workflow state."""
    return AOROState(
        lead_id=lead.lead_id,
        tenant_id=lead.tenant_id,
        company_name=lead.company.name or lead.permit.applicant_name or "Unknown Company",
        decision_maker={
            "full_name": lead.decision_maker.full_name if lead.decision_maker else None,
            "email": lead.decision_maker.email if lead.decision_maker else None,
            "title": lead.decision_maker.title if lead.decision_maker else None,
        },
        permit_data={
            "permit_id": lead.permit.permit_id,
            "permit_type": lead.permit.permit_type,
            "address": lead.permit.address,
            "status": lead.permit.status,
            "applicant_name": lead.permit.applicant_name,
        },
        outreach_channel="email",
        response_history=[],
    )


async def test_phase2_workflow(lead) -> dict:
    """Test Phase 2 workflow with enriched lead."""
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2: Testing Workflow")
    logger.info("=" * 70)
    logger.info(f"Lead ID: {lead.lead_id}")
    logger.info(f"Company: {lead.company.name}")
    logger.info(f"Decision Maker: {lead.decision_maker.full_name if lead.decision_maker else 'None'}")
    logger.info(f"Email: {lead.decision_maker.email if lead.decision_maker and lead.decision_maker.email else 'None'}")

    graph = build_graph()
    storage = WorkflowStorage()
    state = convert_lead_to_state(lead)

    start_time = datetime.now()

    try:
        logger.info("\n[Running Workflow]")
        result = await graph.ainvoke(state)

        execution_time = (datetime.now() - start_time).total_seconds()

        qualification_score = result.get("qualification_score", 0.0)
        compliance_urgency = result.get("compliance_urgency_score", 0.0)
        outreach_sent = result.get("outreach_sent_at") is not None
        workflow_status = result.get("workflow_status")
        workflow_complete = result.get("workflow_complete", False)
        human_approved = result.get("human_approved", False)

        logger.info(f"\n[Results]")
        logger.info(f"  Qualification Score: {qualification_score:.2f}")
        logger.info(f"  Compliance Urgency: {compliance_urgency:.2f}")
        logger.info(f"  Human Approved: {human_approved}")
        logger.info(f"  Outreach Sent: {outreach_sent}")
        logger.info(f"  Workflow Status: {workflow_status}")
        logger.info(f"  Workflow Complete: {workflow_complete}")
        logger.info(f"  Execution Time: {execution_time:.2f}s")

        if result.get("outreach_draft"):
            logger.info(f"\n  Outreach Draft Preview:")
            draft = result.get("outreach_draft", "")
            preview = draft[:200] + "..." if len(draft) > 200 else draft
            logger.info(f"  {preview}")

        if result.get("lead_id"):
            storage.save_workflow_state(result["lead_id"], result)

        return {
            "lead_id": lead.lead_id,
            "success": True,
            "qualification_score": qualification_score,
            "compliance_urgency": compliance_urgency,
            "human_approved": human_approved,
            "outreach_sent": outreach_sent,
            "workflow_status": workflow_status,
            "workflow_complete": workflow_complete,
            "execution_time": execution_time,
        }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Workflow execution failed: {e}", exc_info=True)

        return {
            "lead_id": lead.lead_id,
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
        }


async def main():
    """Run complete end-to-end test."""
    logger.info("\n" + "=" * 70)
    logger.info("END-TO-END TEST: Phase 1 → Phase 2 with Real Permit")
    logger.info("=" * 70)
    logger.info("\nThis will:")
    logger.info("1. Scrape a real permit from San Antonio")
    logger.info("2. Enrich it with company/decision maker data")
    logger.info("3. Run Phase 2 workflow on the enriched lead")
    logger.info("4. Show complete results")
    logger.info("")

    settings = get_settings()
    tenant_id = os.environ.get("TENANT_ID", "test")

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: Credits will be used!")

    logger.info("")

    async with tenant_scoped_session(tenant_id):
        # Step 1: Get real permit
        permit = await get_real_permit()
        if not permit:
            logger.error("✗ Could not get real permit. Cannot continue.")
            return

        # Step 2: Enrich permit
        lead = await enrich_with_known_company(permit, tenant_id)

        # Step 3: Test Phase 2 workflow
        result = await test_phase2_workflow(lead)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("END-TO-END TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Permit ID: {permit.permit_id}")
        logger.info(f"Permit Type: {permit.permit_type}")
        logger.info(f"Address: {permit.address}")
        logger.info(f"Lead ID: {lead.lead_id}")
        logger.info(f"Company: {lead.company.name}")
        logger.info(f"Decision Maker: {lead.decision_maker.full_name if lead.decision_maker else 'None'}")
        logger.info(f"Email: {lead.decision_maker.email if lead.decision_maker and lead.decision_maker.email else 'None'}")
        logger.info("")

        if result.get("success"):
            logger.info("✓ WORKFLOW TEST PASSED")
            logger.info(f"  Qualification Score: {result.get('qualification_score', 0):.2f}")
            logger.info(f"  Outreach Sent: {result.get('outreach_sent', False)}")
            logger.info(f"  Workflow Status: {result.get('workflow_status', 'N/A')}")
        else:
            logger.error("✗ WORKFLOW TEST FAILED")
            logger.error(f"  Error: {result.get('error')}")

        logger.info("\n" + "=" * 70)
        logger.info("TEST COMPLETE!")
        logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
