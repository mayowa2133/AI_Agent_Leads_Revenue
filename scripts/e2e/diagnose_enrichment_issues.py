"""Diagnostic script to identify why email addresses aren't being found."""

from __future__ import annotations

import asyncio
import logging
from src.core.config import get_settings
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def diagnose_enrichment():
    """Diagnose why enrichment isn't finding email addresses."""
    logger.info("=" * 80)
    logger.info("ENRICHMENT DIAGNOSTIC REPORT")
    logger.info("=" * 80)
    logger.info("")
    
    settings = get_settings()
    
    # Check 1: Configuration
    logger.info("1. CONFIGURATION CHECK")
    logger.info("-" * 80)
    logger.info(f"   Enable Enrichment: {settings.enable_enrichment}")
    logger.info(f"   Dry-Run Mode: {settings.enrichment_dry_run}")
    logger.info(f"   Hunter API Key: {'✅ Set' if settings.hunter_api_key else '❌ Missing'}")
    logger.info(f"   Apollo API Key: {'✅ Set' if settings.apollo_api_key else '❌ Missing'}")
    logger.info(f"   Provider Priority: {settings.enrichment_provider_priority}")
    logger.info(f"   Max Credits (Hunter): {settings.max_credits_per_run}")
    logger.info(f"   Max Credits (Apollo): {settings.max_apollo_credits_per_run}")
    logger.info("")
    
    # Check 2: Get real permit data
    logger.info("2. TESTING WITH REAL PERMIT DATA")
    logger.info("-" * 80)
    
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        days_back=30,
        max_pages=1,
    )
    
    permits = await scraper.scrape()
    logger.info(f"   Found {len(permits)} permits")
    
    if not permits:
        logger.warning("   ⚠️  No permits found - cannot test enrichment")
        return
    
    # Test with first permit
    test_permit = permits[0]
    logger.info(f"   Testing with permit: {test_permit.permit_id}")
    logger.info(f"      Permit Type: {test_permit.permit_type}")
    logger.info(f"      Address: {test_permit.address or '(empty)'}")
    logger.info(f"      Applicant Name: {test_permit.applicant_name or '(empty)'}")
    logger.info(f"      Status: {test_permit.status}")
    logger.info("")
    
    # Check 3: Data Quality
    logger.info("3. DATA QUALITY CHECK")
    logger.info("-" * 80)
    has_address = bool(test_permit.address and len(test_permit.address.strip()) > 5)
    has_applicant = bool(test_permit.applicant_name and len(test_permit.applicant_name.strip()) > 2)
    logger.info(f"   Address Quality: {'✅ Valid' if has_address else '❌ Missing/Invalid'}")
    logger.info(f"   Applicant Name: {'✅ Present' if has_applicant else '❌ Missing'}")
    logger.info("")
    
    # Check 4: Run Enrichment
    logger.info("4. RUNNING ENRICHMENT")
    logger.info("-" * 80)
    
    try:
        lead = await enrich_permit_to_lead(EnrichmentInputs(
            tenant_id="diagnostic_test",
            permit=test_permit,
        ))
        
        logger.info(f"   Company Name: {lead.company.name}")
        logger.info(f"   Company Website: {lead.company.website or '(none)'}")
        logger.info(f"   Decision Maker: {'✅ Found' if lead.decision_maker else '❌ Not Found'}")
        
        if lead.decision_maker:
            logger.info(f"      Name: {lead.decision_maker.name}")
            logger.info(f"      Email: {lead.decision_maker.email or '(none)'}")
            logger.info(f"      Title: {lead.decision_maker.title or '(none)'}")
        else:
            logger.warning("   ⚠️  No decision maker found")
            logger.info("")
            logger.info("   REASONS WHY DECISION MAKER NOT FOUND:")
            
            if lead.company.name.startswith("Unknown"):
                logger.info("      - Company name is 'Unknown Org' (company matching failed)")
            if not lead.company.website:
                logger.info("      - No company website/domain found")
            if not has_applicant:
                logger.info("      - No applicant name available")
            if settings.enrichment_dry_run:
                logger.info("      - Dry-run mode enabled (no real API calls)")
            if not settings.hunter_api_key and not settings.apollo_api_key:
                logger.info("      - No API keys configured")
        
        logger.info("")
        
    except Exception as e:
        logger.error(f"   ❌ Enrichment failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("")
    
    # Check 5: Recommendations
    logger.info("5. RECOMMENDATIONS")
    logger.info("-" * 80)
    
    recommendations = []
    
    if settings.enrichment_dry_run:
        recommendations.append("   ⚠️  Disable dry-run mode: Set ENRICHMENT_DRY_RUN=false in .env")
    
    if not settings.hunter_api_key:
        recommendations.append("   ⚠️  Add Hunter.io API key: Set HUNTER_API_KEY in .env")
    
    if not settings.apollo_api_key:
        recommendations.append("   ⚠️  Add Apollo API key (optional but recommended): Set APOLLO_API_KEY in .env")
    
    if not has_address:
        recommendations.append("   ⚠️  Improve address extraction: Many permits have missing/invalid addresses")
    
    if not has_applicant:
        recommendations.append("   ⚠️  Improve applicant name extraction: Many permits have missing applicant names")
    
    if recommendations:
        for rec in recommendations:
            logger.info(rec)
    else:
        logger.info("   ✅ All checks passed! Enrichment should be working.")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_enrichment())
