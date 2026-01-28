"""Test enhanced qualification scoring with new factors."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from src.agents.orchestrator import build_graph
from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.quality.quality_filter import QualityFilter
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_enhanced_scoring():
    """Test enhanced qualification scoring with all new factors."""
    logger.info("=" * 80)
    logger.info("ENHANCED QUALIFICATION SCORING TEST")
    logger.info("=" * 80)
    logger.info("")
    
    logger.info("New Scoring Factors:")
    logger.info("  ✅ Lowered auto-approval threshold: 0.8 → 0.6")
    logger.info("  ✅ Added compliance urgency: +0.15 (weighted)")
    logger.info("  ✅ Added building type risk: +0.1 (high-risk types)")
    logger.info("  ✅ Added permit recency: +0.05 (issued within 30 days)")
    logger.info("")
    
    # Get real permits
    logger.info("Step 1: Getting real permits...")
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    permits = await scraper.scrape()
    logger.info(f"  Found {len(permits)} permits")
    
    if not permits:
        logger.warning("No permits found, cannot test")
        return
    
    # Quality filter
    logger.info("")
    logger.info("Step 2: Quality filtering...")
    quality_filter = QualityFilter(threshold=0.3)
    high_quality, filtered_out, stats = await quality_filter.filter_permits(permits)
    logger.info(f"  Quality permits: {len(high_quality)}/{len(permits)}")
    
    if not high_quality:
        logger.warning("No quality permits, cannot test")
        return
    
    # Enrich a few leads
    logger.info("")
    logger.info("Step 3: Enriching leads...")
    enriched_leads = []
    for permit in high_quality[:5]:
        try:
            inputs = EnrichmentInputs(
                permit=permit,
                tenant_id="test-tenant",
            )
            lead = await enrich_permit_to_lead(inputs)
            enriched_leads.append(lead)
        except Exception as e:
            logger.warning(f"  Enrichment failed: {e}")
    
    logger.info(f"  Enriched leads: {len(enriched_leads)}")
    
    if not enriched_leads:
        logger.warning("No enriched leads, cannot test")
        return
    
    # Test workflow with enhanced scoring
    logger.info("")
    logger.info("Step 4: Testing Phase 2 workflow with enhanced scoring...")
    logger.info("")
    
    graph = build_graph()
    results = []
    
    for i, lead in enumerate(enriched_leads, 1):
        logger.info(f"Lead {i}: {lead.lead_id}")
        logger.info(f"  Company: {lead.company.name}")
        logger.info(f"  Permit: {lead.permit.permit_id} - {lead.permit.permit_type}")
        logger.info(f"  Status: {lead.permit.status}")
        logger.info(f"  Building Type: {lead.permit.building_type or 'None'}")
        logger.info(f"  Issued Date: {lead.permit.issued_date or 'None'}")
        
        # Prepare state
        state_in = {
            "tenant_id": "test-tenant",
            "lead_id": lead.lead_id,
            "company_name": lead.company.name,
            "decision_maker": (
                {
                    "full_name": lead.decision_maker.full_name,
                    "email": lead.decision_maker.email,
                    "title": lead.decision_maker.title,
                }
                if lead.decision_maker
                else {}
            ),
            "permit_data": {
                "permit_id": lead.permit.permit_id,
                "permit_type": lead.permit.permit_type,
                "address": lead.permit.address,
                "status": lead.permit.status,
                "applicant_name": lead.permit.applicant_name,
                "issued_date": lead.permit.issued_date.isoformat() if lead.permit.issued_date else None,
                "source": lead.permit.source,
                "building_type": lead.permit.building_type,
            },
            "outreach_channel": lead.outreach_channel_hint,
        }
        
        # Run workflow through Researcher (to get compliance urgency)
        logger.info("  Running workflow through Researcher...")
        state_after_research = await graph.ainvoke(state_in)
        
        # Check compliance urgency
        compliance_urgency = state_after_research.get("compliance_urgency_score", 0.0)
        logger.info(f"  Compliance Urgency Score: {compliance_urgency:.2f}")
        
        # Run qualification check
        logger.info("  Running qualification check...")
        state_after_qual = await graph.ainvoke(state_after_research)
        
        qualification_score = state_after_qual.get("qualification_score", 0.0)
        human_approved = state_after_qual.get("human_approved")
        
        logger.info(f"  Qualification Score: {qualification_score:.2f}")
        logger.info(f"  Human Approved: {human_approved}")
        logger.info(f"  Auto-Approved: {'✅ YES' if human_approved else '❌ NO'}")
        logger.info("")
        
        results.append({
            "lead_id": lead.lead_id,
            "qualification_score": qualification_score,
            "compliance_urgency": compliance_urgency,
            "human_approved": human_approved,
            "auto_approved": human_approved,
        })
    
    # Summary
    logger.info("=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    avg_score = sum(r["qualification_score"] for r in results) / len(results)
    max_score = max(r["qualification_score"] for r in results)
    min_score = min(r["qualification_score"] for r in results)
    auto_approved_count = sum(1 for r in results if r["auto_approved"])
    passing_count = sum(1 for r in results if r["qualification_score"] >= 0.5)
    
    logger.info(f"Total Leads Tested: {len(results)}")
    logger.info(f"Average Qualification Score: {avg_score:.2f}")
    logger.info(f"Max Score: {max_score:.2f}")
    logger.info(f"Min Score: {min_score:.2f}")
    logger.info("")
    logger.info(f"Passing (>=0.5): {passing_count}/{len(results)} ({passing_count/len(results)*100:.1f}%)")
    logger.info(f"Auto-Approved (>=0.6): {auto_approved_count}/{len(results)} ({auto_approved_count/len(results)*100:.1f}%)")
    logger.info("")
    
    # Show score breakdown
    logger.info("Score Distribution:")
    score_ranges = [
        (0.0, 0.3, "Low (0.0-0.3)"),
        (0.3, 0.5, "Medium (0.3-0.5)"),
        (0.5, 0.6, "Good (0.5-0.6)"),
        (0.6, 0.8, "High (0.6-0.8)"),
        (0.8, 1.0, "Very High (0.8-1.0)"),
    ]
    
    for min_range, max_range, label in score_ranges:
        count = sum(1 for r in results if min_range <= r["qualification_score"] < max_range)
        logger.info(f"  {label}: {count} leads")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ ENHANCED SCORING TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_enhanced_scoring())
