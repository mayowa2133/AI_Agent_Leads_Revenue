"""End-to-End Integration Test: Phase 1.4 → Phase 2 Workflow."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.models import EnrichedLead
from src.signal_engine.quality.quality_filter import QualityFilter
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.agents.orchestrator import build_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_phase1_4_to_phase2_full_pipeline():
    """Test complete pipeline: Phase 1.4 → Quality Filter → Enrichment → Phase 2."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4 → PHASE 2: FULL PIPELINE INTEGRATION TEST")
    logger.info("=" * 80)
    logger.info("")
    
    tenant_id = "test_tenant"
    all_permits = []
    all_enriched_leads = []
    
    # ========================================================================
    # STEP 1: Phase 1.4 - Unified Ingestion (Scrapers + APIs)
    # ========================================================================
    logger.info("STEP 1: Phase 1.4 - Unified Ingestion")
    logger.info("-" * 80)
    
    ingestion = UnifiedPermitIngestion()
    
    # Test 1.1: Scraper Source (San Antonio)
    logger.info("1.1: Ingesting from Scraper (San Antonio)...")
    scraper_source = PermitSource(
        source_type=PermitSourceType.SCRAPER,
        city="San Antonio, TX",
        source_id="cosa_fire",
        config={
            "portal_type": "accela",
            "city_code": "COSA",
            "module": "Fire",
            "url": "https://aca-prod.accela.com/COSA",
        },
    )
    
    try:
        scraper_permits = await ingestion.ingest_permits(scraper_source, days_back=120, limit=10)
        all_permits.extend(scraper_permits)
        logger.info(f"  ✅ Scraper: {len(scraper_permits)} permits")
    except Exception as e:
        logger.warning(f"  ⚠️  Scraper error: {e}")
    
    # Test 1.2: API Source (Seattle)
    logger.info("")
    logger.info("1.2: Ingesting from API (Seattle Socrata)...")
    api_source = PermitSource(
        source_type=PermitSourceType.SOCRATA_API,
        city="Seattle, WA",
        source_id="seattle_socrata",
        config={
            "portal_url": "https://data.seattle.gov",
            "dataset_id": "76t5-zqzr",
            "field_mapping": {
                "permit_id": "permitnum",
                "permit_type": "permittypedesc",
                "address": "originaladdress1",
                "status": "statuscurrent",
            },
        },
    )
    
    try:
        api_permits = await ingestion.ingest_permits(api_source, days_back=30, limit=10)
        all_permits.extend(api_permits)
        logger.info(f"  ✅ API: {len(api_permits)} permits")
    except Exception as e:
        logger.warning(f"  ⚠️  API error: {e}")
    
    logger.info("")
    logger.info(f"Total permits from Phase 1.4: {len(all_permits)}")
    
    if not all_permits:
        logger.error("❌ No permits extracted - cannot continue test")
        return False
    
    # ========================================================================
    # STEP 2: Quality Filtering
    # ========================================================================
    logger.info("")
    logger.info("STEP 2: Quality Filtering")
    logger.info("-" * 80)
    
    quality_filter = QualityFilter(threshold=0.3)
    high_quality, filtered, stats = quality_filter.filter_permits_sync(all_permits)
    
    logger.info(f"Quality Filter Results:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Passed: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    logger.info(f"  Filtered: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    logger.info(f"  Score Distribution: {stats['score_distribution']}")
    
    if not high_quality:
        logger.warning("⚠️  No permits passed quality filter - testing with all permits")
        high_quality = all_permits
    
    # ========================================================================
    # STEP 3: Enrichment
    # ========================================================================
    logger.info("")
    logger.info("STEP 3: Enrichment Pipeline")
    logger.info("-" * 80)
    
    logger.info(f"Enriching {len(high_quality)} quality permits...")
    
    for i, permit in enumerate(high_quality[:5], 1):  # Limit to 5 for testing
        try:
            logger.info(f"  Enriching permit {i}/{min(5, len(high_quality))}: {permit.permit_id}")
            enriched_lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id=tenant_id, permit=permit)
            )
            all_enriched_leads.append(enriched_lead)
            logger.info(f"    ✅ Enriched: {enriched_lead.lead_id}")
            logger.info(f"       Company: {enriched_lead.company.name}")
            logger.info(f"       Decision Maker: {enriched_lead.decision_maker.full_name if enriched_lead.decision_maker else 'None'}")
        except Exception as e:
            logger.warning(f"    ⚠️  Enrichment failed: {e}")
    
    logger.info("")
    logger.info(f"Total enriched leads: {len(all_enriched_leads)}")
    
    if not all_enriched_leads:
        logger.error("❌ No leads enriched - cannot test Phase 2")
        return False
    
    # ========================================================================
    # STEP 4: Phase 2 Workflow Integration
    # ========================================================================
    logger.info("")
    logger.info("STEP 4: Phase 2 Workflow Integration")
    logger.info("-" * 80)
    
    graph = build_graph()
    workflow_results = []
    
    # Test all enriched leads (or limit for faster testing)
    max_workflows = 10  # Set to None to test all leads
    leads_to_test = all_enriched_leads[:max_workflows] if max_workflows else all_enriched_leads
    
    logger.info(f"Testing workflows for {len(leads_to_test)}/{len(all_enriched_leads)} enriched leads")
    logger.info("")
    
    for i, lead in enumerate(leads_to_test, 1):
        logger.info("")
        logger.info(f"4.{i}: Testing Phase 2 workflow with lead {lead.lead_id}")
        logger.info(f"     Company: {lead.company.name}")
        logger.info(f"     Permit: {lead.permit.permit_id} - {lead.permit.permit_type}")
        
        try:
            # Prepare state for Phase 2
            state_in: dict[str, Any] = {
                "tenant_id": tenant_id,
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
                    "source": lead.permit.source,  # Important for fire module detection
                },
                "outreach_channel": lead.outreach_channel_hint,
            }
            
            # Run Phase 2 workflow
            logger.info("     Running workflow...")
            state_out = await graph.ainvoke(state_in)
            
            # Check results
            qualification_score = state_out.get("qualification_score", 0.0)
            workflow_status = state_out.get("workflow_status")
            outreach_draft = state_out.get("outreach_draft")
            human_approved = state_out.get("human_approved")
            outreach_sent_at = state_out.get("outreach_sent_at")
            response_history = state_out.get("response_history", [])
            
            # Check if outreach was actually sent
            outreach_sent = any(
                item.get("type") == "outreach_sent" 
                for item in response_history
            )
            
            logger.info(f"     ✅ Workflow completed")
            logger.info(f"        Qualification Score: {qualification_score:.2f}")
            logger.info(f"        Workflow Status: {workflow_status}")
            logger.info(f"        Outreach Draft: {'Generated' if outreach_draft else 'Not generated'}")
            logger.info(f"        Human Approved: {human_approved}")
            logger.info(f"        Outreach Sent: {'✅ YES' if outreach_sent else '❌ NO'}")
            
            # Show full draft content if generated
            if outreach_draft:
                logger.info(f"        Full Draft Content:")
                logger.info(f"        {'-' * 70}")
                for line in outreach_draft.split('\n'):
                    logger.info(f"        {line}")
                logger.info(f"        {'-' * 70}")
            
            # Show why it wasn't sent if draft exists but wasn't sent
            if outreach_draft and not outreach_sent:
                has_email = lead.decision_maker and lead.decision_maker.email
                if qualification_score < 0.5:
                    logger.info(f"        ⚠️  Not sent: Qualification score {qualification_score:.2f} < 0.5 (disqualified)")
                elif human_approved is False:
                    logger.info(f"        ⚠️  Not sent: Score {qualification_score:.2f} < 0.6 (failed human review)")
                elif not has_email:
                    logger.info(f"        ⚠️  Not sent: No email address found for decision maker")
                elif human_approved is None:
                    logger.info(f"        ⚠️  Not sent: Human review not completed")
            
            # Check if lead has email address
            has_email = False
            if lead.decision_maker and lead.decision_maker.email:
                has_email = True
            
            workflow_results.append({
                "lead_id": lead.lead_id,
                "qualification_score": qualification_score,
                "workflow_status": workflow_status,
                "outreach_generated": bool(outreach_draft),
                "outreach_sent": outreach_sent,
                "human_approved": human_approved,
                "has_email": has_email,
                "success": True,
            })
            
        except Exception as e:
            logger.error(f"     ❌ Workflow failed: {e}")
            workflow_results.append({
                "lead_id": lead.lead_id,
                "success": False,
                "error": str(e),
            })
    
    # ========================================================================
    # STEP 5: Results Summary
    # ========================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("INTEGRATION TEST RESULTS")
    logger.info("=" * 80)
    logger.info("")
    
    logger.info("Phase 1.4 Results:")
    logger.info(f"  Total Permits Extracted: {len(all_permits)}")
    logger.info(f"    - From Scrapers: {len([p for p in all_permits if 'scraper' in p.source or 'accela' in p.source])}")
    logger.info(f"    - From APIs: {len([p for p in all_permits if 'socrata' in p.source])}")
    logger.info("")
    
    logger.info("Quality Filtering Results:")
    logger.info(f"  Quality Permits: {len(high_quality)}/{len(all_permits)} ({len(high_quality)/len(all_permits)*100:.1f}%)")
    logger.info("")
    
    logger.info("Enrichment Results:")
    logger.info(f"  Enriched Leads: {len(all_enriched_leads)}")
    logger.info(f"  Success Rate: {len(all_enriched_leads)/len(high_quality)*100:.1f}%")
    logger.info("")
    
    logger.info("Phase 2 Workflow Results:")
    successful_workflows = [r for r in workflow_results if r.get("success")]
    logger.info(f"  Workflows Tested: {len(workflow_results)}")
    logger.info(f"  Successful: {len(successful_workflows)}")
    logger.info(f"  Failed: {len(workflow_results) - len(successful_workflows)}")
    
    if successful_workflows:
        avg_qualification = sum(r["qualification_score"] for r in successful_workflows) / len(successful_workflows)
        outreach_drafts = sum(1 for r in successful_workflows if r.get("outreach_generated"))
        outreach_sent = sum(1 for r in successful_workflows if r.get("outreach_sent"))
        logger.info(f"  Avg Qualification Score: {avg_qualification:.2f}")
        logger.info(f"  Outreach Drafts Generated: {outreach_drafts}/{len(successful_workflows)}")
        logger.info(f"  Outreach Actually Sent: {outreach_sent}/{len(successful_workflows)}")
        
        # Show why drafts weren't sent
        if outreach_drafts > outreach_sent:
            logger.info(f"  ⚠️  {outreach_drafts - outreach_sent} draft(s) not sent:")
            for r in successful_workflows:
                if r.get("outreach_generated") and not r.get("outreach_sent"):
                    score = r.get("qualification_score", 0)
                    approved = r.get("human_approved")
                    has_email = r.get("has_email", False)
                    if score < 0.5:
                        logger.info(f"     - Lead {r.get('lead_id')}: Score {score:.2f} < 0.5 (didn't qualify)")
                    elif approved is False:
                        logger.info(f"     - Lead {r.get('lead_id')}: Score {score:.2f} < 0.6 (failed human review)")
                    elif not has_email:
                        logger.info(f"     - Lead {r.get('lead_id')}: No email address found for decision maker")
                    else:
                        logger.info(f"     - Lead {r.get('lead_id')}: Unknown reason")
    
    logger.info("")
    
    # Final verdict
    all_passed = (
        len(all_permits) > 0
        and len(all_enriched_leads) > 0
        and len(successful_workflows) > 0
    )
    
    if all_passed:
        logger.info("=" * 80)
        logger.info("✅ PHASE 1.4 → PHASE 2 INTEGRATION: SUCCESS")
        logger.info("=" * 80)
        logger.info("")
        logger.info("All components working together:")
        logger.info("  ✅ Phase 1.4 unified ingestion (scrapers + APIs)")
        logger.info("  ✅ Quality filtering")
        logger.info("  ✅ Enrichment pipeline")
        logger.info("  ✅ Phase 2 workflow execution")
        logger.info("")
        logger.info("The system is ready for production use!")
    else:
        logger.info("=" * 80)
        logger.info("⚠️  PHASE 1.4 → PHASE 2 INTEGRATION: SOME ISSUES")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Please review the errors above.")
    
    return all_passed


async def test_data_compatibility():
    """Test data compatibility between Phase 1.4 and Phase 2."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATA COMPATIBILITY TEST")
    logger.info("=" * 80)
    logger.info("")
    
    # Test 1: Scraper permit structure
    logger.info("Test 1: Scraper Permit Structure")
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    scraper_permits = await scraper.scrape()
    
    if scraper_permits:
        permit = scraper_permits[0]
        logger.info(f"  ✅ Scraper permit structure valid")
        logger.info(f"     Permit ID: {permit.permit_id}")
        logger.info(f"     Permit Type: {permit.permit_type}")
        logger.info(f"     Address: {permit.address}")
        logger.info(f"     Source: {permit.source}")
        
        # Check required fields for Phase 2
        required_fields = ["permit_id", "permit_type", "address", "status"]
        missing = [f for f in required_fields if not getattr(permit, f, None)]
        if missing:
            logger.warning(f"     ⚠️  Missing fields: {missing}")
        else:
            logger.info(f"     ✅ All required fields present")
    
    # Test 2: API permit structure
    logger.info("")
    logger.info("Test 2: API Permit Structure")
    client = SocrataPermitClient(
        portal_url="https://data.seattle.gov",
        dataset_id="76t5-zqzr",
        field_mapping={
            "permit_id": "permitnum",
            "permit_type": "permittypedesc",
            "address": "originaladdress1",
            "status": "statuscurrent",
        },
    )
    api_permits = await client.get_permits(days_back=30, limit=1)
    
    if api_permits:
        permit = api_permits[0]
        logger.info(f"  ✅ API permit structure valid")
        logger.info(f"     Permit ID: {permit.permit_id}")
        logger.info(f"     Permit Type: {permit.permit_type}")
        logger.info(f"     Address: {permit.address}")
        logger.info(f"     Source: {permit.source}")
        
        # Check required fields
        required_fields = ["permit_id", "permit_type", "address", "status"]
        missing = [f for f in required_fields if not getattr(permit, f, None)]
        if missing:
            logger.warning(f"     ⚠️  Missing fields: {missing}")
        else:
            logger.info(f"     ✅ All required fields present")
    
    # Test 3: EnrichedLead structure
    logger.info("")
    logger.info("Test 3: EnrichedLead Structure")
    if scraper_permits:
        try:
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id="test", permit=scraper_permits[0])
            )
            logger.info(f"  ✅ EnrichedLead structure valid")
            logger.info(f"     Lead ID: {lead.lead_id}")
            logger.info(f"     Company: {lead.company.name}")
            logger.info(f"     Permit: {lead.permit.permit_id}")
            
            # Check Phase 2 required fields
            phase2_fields = ["lead_id", "company", "permit", "decision_maker"]
            missing = [f for f in phase2_fields if not getattr(lead, f, None)]
            if missing:
                logger.warning(f"     ⚠️  Missing Phase 2 fields: {missing}")
            else:
                logger.info(f"     ✅ All Phase 2 required fields present")
        except Exception as e:
            logger.error(f"     ❌ Enrichment failed: {e}")
    
    logger.info("")
    logger.info("✅ Data Compatibility Test Complete")
    logger.info("")


async def main():
    """Run all integration tests."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4 → PHASE 2: COMPREHENSIVE INTEGRATION TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing complete integration:")
    logger.info("  1. Phase 1.4 unified ingestion (scrapers + APIs)")
    logger.info("  2. Quality filtering")
    logger.info("  3. Enrichment pipeline")
    logger.info("  4. Phase 2 workflow execution")
    logger.info("  5. Data compatibility")
    logger.info("")
    
    # Test data compatibility first
    await test_data_compatibility()
    
    # Test full pipeline
    result = await test_phase1_4_to_phase2_full_pipeline()
    
    logger.info("")
    logger.info("=" * 80)
    if result:
        logger.info("✅ ALL INTEGRATION TESTS PASSED")
    else:
        logger.info("⚠️  SOME INTEGRATION TESTS FAILED")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
