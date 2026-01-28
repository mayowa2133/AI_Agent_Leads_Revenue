"""End-to-end test: Phase 1 (real permits) → Phase 2 (workflow) with real data."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import get_settings
from src.core.security import tenant_scoped_session
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
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


async def scrape_real_permits_with_applicants(limit: int = 3) -> list:
    """Scrape real permits from San Antonio with applicant extraction enabled."""
    logger.info("=" * 70)
    logger.info("Scraping Real Permits with Applicant Extraction")
    logger.info("=" * 70)

    scraper = SanAntonioFireScraper(
        record_type="Fire Alarm",
        days_back=30,
        extract_applicant=True,  # Enable applicant extraction
    )

    try:
        permits = await scraper.scrape()
        logger.info(f"✓ Scraped {len(permits)} permits from San Antonio")
        
        # Filter to only permits with applicant names
        permits_with_applicants = [p for p in permits if p.applicant_name]
        logger.info(f"✓ Found {len(permits_with_applicants)} permits with applicant names")
        
        return permits_with_applicants[:limit]
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}", exc_info=True)
        return []


async def enrich_permits(permits: list, tenant_id: str) -> list:
    """Enrich permits to leads."""
    logger.info("=" * 70)
    logger.info(f"Enriching {len(permits)} Permit(s)")
    logger.info("=" * 70)

    enriched_leads = []
    lead_storage = LeadStorage()
    settings = get_settings()

    for i, permit in enumerate(permits, 1):
        logger.info(f"\nPermit {i}/{len(permits)}: {permit.permit_id}")
        logger.info(f"  → Type: {permit.permit_type}")
        logger.info(f"  → Address: {permit.address}")
        logger.info(f"  → Applicant: {permit.applicant_name or 'N/A'}")

        try:
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id=tenant_id, permit=permit)
            )

            enriched_leads.append(lead)

            logger.info(f"  ✓ Enriched lead: {lead.lead_id}")
            logger.info(f"  → Company: {lead.company.name}")
            if lead.decision_maker:
                logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
                if lead.decision_maker.email:
                    logger.info(f"  → Email: {lead.decision_maker.email}")
            else:
                logger.info("  → No decision maker found")

            lead_storage.save_lead(lead)
            logger.info(f"  → Saved to storage")

        except Exception as e:
            logger.error(f"  ✗ Enrichment failed: {e}", exc_info=True)

    return enriched_leads


def convert_lead_to_state(lead: dict) -> AOROState:
    """Convert enriched lead to workflow state."""
    permit_data = lead.get("permit") or lead.get("permit_data", {})
    company = lead.get("company", {})
    decision_maker = lead.get("decision_maker") or {}
    location = lead.get("location", {})

    return AOROState(
        lead_id=lead.get("lead_id", f"lead-{int(datetime.now().timestamp())}"),
        tenant_id=lead.get("tenant_id", "test"),
        company_name=company.get("name") or permit_data.get("applicant_name") or "Unknown Company",
        decision_maker={
            "full_name": decision_maker.get("full_name") if decision_maker else None,
            "email": decision_maker.get("email") if decision_maker else None,
            "title": decision_maker.get("title") if decision_maker else None,
        },
        permit_data={
            "permit_id": permit_data.get("permit_id"),
            "permit_type": permit_data.get("permit_type"),
            "address": permit_data.get("address"),
            "status": permit_data.get("status"),
            "applicant_name": permit_data.get("applicant_name"),
        },
        outreach_channel="email",
        response_history=[],
    )


async def test_phase2_workflow(lead: dict) -> dict:
    """Test Phase 2 workflow with an enriched lead."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Phase 2 Workflow")
    logger.info("=" * 70)
    logger.info(f"Lead ID: {lead.get('lead_id')}")
    logger.info(f"Company: {lead.get('company', {}).get('name', 'Unknown')}")

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

        logger.info(f"\n[Results]")
        logger.info(f"  Qualification Score: {qualification_score:.2f}")
        logger.info(f"  Compliance Urgency: {compliance_urgency:.2f}")
        logger.info(f"  Outreach Sent: {outreach_sent}")
        logger.info(f"  Workflow Status: {workflow_status}")
        logger.info(f"  Workflow Complete: {workflow_complete}")
        logger.info(f"  Execution Time: {execution_time:.2f}s")

        if result.get("lead_id"):
            storage.save_workflow_state(result["lead_id"], result)

        return {
            "lead_id": lead.get("lead_id"),
            "success": True,
            "qualification_score": qualification_score,
            "compliance_urgency": compliance_urgency,
            "outreach_sent": outreach_sent,
            "workflow_status": workflow_status,
            "workflow_complete": workflow_complete,
            "execution_time": execution_time,
        }

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Workflow execution failed: {e}", exc_info=True)

        return {
            "lead_id": lead.get("lead_id"),
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
        }


async def main():
    """Run complete end-to-end test: Phase 1 → Phase 2."""
    logger.info("\n" + "=" * 70)
    logger.info("END-TO-END TEST: Phase 1 → Phase 2 with Real Permits")
    logger.info("=" * 70)
    logger.info("\nThis will:")
    logger.info("1. Scrape real permits from San Antonio (with applicant extraction)")
    logger.info("2. Enrich permits with company/decision maker data")
    logger.info("3. Run Phase 2 workflow on enriched leads")
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
        # Step 1: Scrape real permits
        permits = await scrape_real_permits_with_applicants(limit=3)
        
        if not permits:
            logger.error("✗ No permits with applicants found. Cannot continue.")
            return

        # Step 2: Enrich permits
        enriched_leads = await enrich_permits(permits, tenant_id)
        
        if not enriched_leads:
            logger.error("✗ No leads enriched. Cannot continue.")
            return

        # Step 3: Test Phase 2 workflow
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 2: Testing Workflow")
        logger.info("=" * 70)

        results = []
        for lead in enriched_leads:
            # Convert to dict format
            lead_dict = {
                "lead_id": lead.lead_id,
                "tenant_id": lead.tenant_id,
                "company": {
                    "name": lead.company.name,
                    "website": lead.company.website,
                },
                "decision_maker": {
                    "full_name": lead.decision_maker.full_name if lead.decision_maker else None,
                    "email": lead.decision_maker.email if lead.decision_maker else None,
                    "title": lead.decision_maker.title if lead.decision_maker else None,
                } if lead.decision_maker else None,
                "permit": {
                    "permit_id": lead.permit.permit_id,
                    "permit_type": lead.permit.permit_type,
                    "address": lead.permit.address,
                    "status": lead.permit.status,
                    "applicant_name": lead.permit.applicant_name,
                },
            }
            
            result = await test_phase2_workflow(lead_dict)
            results.append(result)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("END-TO-END TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Permits scraped: {len(permits)}")
        logger.info(f"Leads enriched: {len(enriched_leads)}")
        logger.info(f"Leads with emails: {sum(1 for l in enriched_leads if l.decision_maker and l.decision_maker.email)}")
        logger.info(f"Workflow tests: {len(results)}")
        logger.info(f"Successful workflows: {sum(1 for r in results if r.get('success'))}")
        logger.info("")

        for result in results:
            status = "✓ PASSED" if result.get("success") else "✗ FAILED"
            logger.info(f"  {status}: Lead {result.get('lead_id')}")
            if result.get("success"):
                logger.info(f"    Qualification: {result.get('qualification_score', 0):.2f}")
                logger.info(f"    Outreach Sent: {result.get('outreach_sent', False)}")
            else:
                logger.error(f"    Error: {result.get('error')}")

        logger.info("\n" + "=" * 70)
        logger.info("TEST COMPLETE!")
        logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
