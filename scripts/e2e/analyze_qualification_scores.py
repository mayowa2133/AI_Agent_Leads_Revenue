"""Analyze why qualification scores are low."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_qualification_score(permit_data: dict, decision_maker: dict | None) -> dict:
    """Calculate qualification score and show breakdown."""
    status = str(permit_data.get("status") or "").lower()
    ptype = str(permit_data.get("permit_type") or "").lower()
    
    breakdown = {
        "base_score": 0.2,
        "status_issued": 0.0,
        "status_inspection": 0.0,
        "fire_in_type": 0.0,
        "has_decision_maker": 0.0,
    }
    
    score = 0.2  # Base score
    
    # Check status
    if "issued" in status or "approved" in status:
        score += 0.3
        breakdown["status_issued"] = 0.3
    if "inspection" in status or "passed" in status:
        score += 0.2
        breakdown["status_inspection"] = 0.2
    
    # Check permit type
    if "fire" in ptype:
        score += 0.2
        breakdown["fire_in_type"] = 0.2
    
    # Check decision maker
    if decision_maker:
        score += 0.1
        breakdown["has_decision_maker"] = 0.1
    
    breakdown["total_score"] = min(score, 1.0)
    return breakdown


async def main():
    """Analyze qualification scores for real permits."""
    logger.info("=" * 80)
    logger.info("QUALIFICATION SCORE ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    
    logger.info("Phase 2 Qualification Scoring Logic:")
    logger.info("  Base Score: 0.2")
    logger.info("  +0.3 if status contains 'issued' or 'approved'")
    logger.info("  +0.2 if status contains 'inspection' or 'passed'")
    logger.info("  +0.2 if permit_type contains 'fire'")
    logger.info("  +0.1 if decision_maker exists")
    logger.info("  Maximum: 1.0")
    logger.info("")
    
    # Get real permits
    logger.info("=" * 80)
    logger.info("Analyzing Real Permit Data")
    logger.info("=" * 80)
    logger.info("")
    
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    scraper_permits = await scraper.scrape()
    
    logger.info(f"Scraper Permits (San Antonio): {len(scraper_permits)}")
    logger.info("")
    
    for i, permit in enumerate(scraper_permits[:5], 1):
        logger.info(f"Permit {i}: {permit.permit_id}")
        logger.info(f"  Type: '{permit.permit_type}'")
        logger.info(f"  Status: '{permit.status}'")
        logger.info(f"  Address: '{permit.address}'")
        logger.info(f"  Applicant: {permit.applicant_name}")
        logger.info("")
        
        # Calculate score
        permit_data = {
            "permit_id": permit.permit_id,
            "permit_type": permit.permit_type,
            "status": permit.status,
            "address": permit.address,
        }
        
        breakdown = calculate_qualification_score(permit_data, None)
        
        logger.info(f"  Qualification Score Breakdown:")
        logger.info(f"    Base Score: {breakdown['base_score']}")
        logger.info(f"    Status 'issued'/'approved': {breakdown['status_issued']} (checking: '{permit.status}')")
        logger.info(f"    Status 'inspection'/'passed': {breakdown['status_inspection']} (checking: '{permit.status}')")
        logger.info(f"    Type contains 'fire': {breakdown['fire_in_type']} (checking: '{permit.permit_type}')")
        logger.info(f"    Has Decision Maker: {breakdown['has_decision_maker']}")
        logger.info(f"    TOTAL SCORE: {breakdown['total_score']:.2f}")
        logger.info("")
        
        # Explain why score is low
        reasons = []
        if breakdown['status_issued'] == 0.0:
            reasons.append(f"Status '{permit.status}' doesn't contain 'issued' or 'approved'")
        if breakdown['status_inspection'] == 0.0:
            reasons.append(f"Status '{permit.status}' doesn't contain 'inspection' or 'passed'")
        if breakdown['fire_in_type'] == 0.0:
            reasons.append(f"Type '{permit.permit_type}' doesn't contain 'fire'")
        if breakdown['has_decision_maker'] == 0.0:
            reasons.append("No decision maker found")
        
        if reasons:
            logger.info(f"  Why score is low:")
            for reason in reasons:
                logger.info(f"    - {reason}")
        logger.info("")
    
    # Get API permits
    logger.info("=" * 80)
    logger.info("API Permits (Seattle)")
    logger.info("=" * 80)
    logger.info("")
    
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
    api_permits = await client.get_permits(days_back=30, limit=5)
    
    logger.info(f"API Permits: {len(api_permits)}")
    logger.info("")
    
    for i, permit in enumerate(api_permits[:3], 1):
        logger.info(f"Permit {i}: {permit.permit_id}")
        logger.info(f"  Type: '{permit.permit_type}'")
        logger.info(f"  Status: '{permit.status}'")
        logger.info(f"  Address: '{permit.address}'")
        logger.info("")
        
        permit_data = {
            "permit_id": permit.permit_id,
            "permit_type": permit.permit_type,
            "status": permit.status,
            "address": permit.address,
        }
        
        breakdown = calculate_qualification_score(permit_data, None)
        
        logger.info(f"  Qualification Score: {breakdown['total_score']:.2f}")
        logger.info(f"    Base: {breakdown['base_score']}")
        logger.info(f"    Status check: {breakdown['status_issued']} (status: '{permit.status}')")
        logger.info(f"    Fire check: {breakdown['fire_in_type']} (type: '{permit.permit_type}')")
        logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("ROOT CAUSE ANALYSIS")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Why scores are low (0.20):")
    logger.info("")
    logger.info("1. PERMIT TYPES don't contain 'fire':")
    logger.info("   - 'State License Registration Application' ❌")
    logger.info("   - 'MEP Trade Permits Application' ❌")
    logger.info("   - 'Residential Improvements Permit Application' ❌")
    logger.info("   - 'Environmentally Critical Area Exemption' ❌")
    logger.info("   → Even though they're from Fire module, types don't say 'fire'")
    logger.info("")
    logger.info("2. STATUS VALUES are weird/invalid:")
    logger.info("   - '34845' (number, not a status) ❌")
    logger.info("   - 'Tunnel' (not a status) ❌")
    logger.info("   - 'RITA GHOSE' (person name, not status) ❌")
    logger.info("   - 'Canceled' (doesn't match 'issued'/'approved') ❌")
    logger.info("   → Status field contains wrong data")
    logger.info("")
    logger.info("3. NO DECISION MAKERS:")
    logger.info("   - Enrichment couldn't find decision makers")
    logger.info("   - No applicant names in permits")
    logger.info("   → Missing +0.1")
    logger.info("")
    logger.info("SOLUTION:")
    logger.info("  Option 1: Improve qualification scoring to be more lenient")
    logger.info("    - Check source field for 'fire' module (like quality filter does)")
    logger.info("    - Accept more status variations")
    logger.info("    - Give partial credit for permit types")
    logger.info("")
    logger.info("  Option 2: Improve data quality")
    logger.info("    - Fix scraper to extract correct status values")
    logger.info("    - Extract applicant names from detail pages")
    logger.info("    - Use better permit type mapping")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
