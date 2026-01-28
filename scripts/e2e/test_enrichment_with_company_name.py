"""Test enrichment pipeline with extracted company name."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.enrichment.apollo_client import ApolloClient
from src.signal_engine.enrichment.hunter_client import HunterClient
from src.signal_engine.enrichment.company_enricher import match_company, find_decision_maker
from src.signal_engine.enrichment.geocoder import geocode_address
from src.signal_engine.models import PermitData
from src.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_enrichment():
    """Test enrichment with a company name we extracted."""
    logger.info("Testing enrichment pipeline with extracted company name")
    logger.info("Company: TX Septic Systems LLC\n")
    
    config = get_settings()
    
    # Check if APIs are configured
    if not config.apollo_api_key:
        logger.warning("⚠️  Apollo API key not configured - will use mock/dry-run mode")
    if not config.hunter_api_key:
        logger.warning("⚠️  Hunter API key not configured - will use mock/dry-run mode")
    
    company_name = "TX Septic Systems LLC"
    
    # Create a test permit with the company name we extracted
    test_permit = PermitData(
        source="test",
        permit_id="TEST-001",
        permit_type="Test Permit",
        address="",  # No address for this test
        building_type=None,
        status="issued",
        applicant_name=company_name,  # This is what we extracted
        issued_date=None,
        detail_url=None,
    )
    
    logger.info(f"Test Permit: {test_permit.permit_id}")
    logger.info(f"Company Name: {test_permit.applicant_name}\n")
    
    # Test Step 1: Company Matching (uses Apollo to find domain)
    logger.info("="*80)
    logger.info("STEP 1: COMPANY MATCHING (Apollo Domain Lookup)")
    logger.info("="*80)
    try:
        geocode_result = None  # No address, so no geocoding
        company = await match_company(test_permit, geocode_result)
        logger.info(f"✅ Company Matched: {company.name}")
        if company.website:
            logger.info(f"   Website: {company.website}")
            logger.info(f"   Domain: {company.website.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]}")
        else:
            logger.warning("   ⚠️  No website/domain found")
    except Exception as e:
        logger.error(f"❌ Company matching error: {e}")
        company = None
    
    # Test Step 2: Decision Maker Finding (uses Hunter.io to find email)
    if company and company.website:
        logger.info("\n" + "="*80)
        logger.info("STEP 2: DECISION MAKER FINDING (Hunter.io Email Lookup)")
        logger.info("="*80)
        try:
            decision_maker = await find_decision_maker(company, geocode_result, test_permit)
            if decision_maker:
                logger.info(f"✅ Decision Maker Found:")
                logger.info(f"   Name: {decision_maker.name}")
                logger.info(f"   Email: {decision_maker.email or '(not found)'}")
                logger.info(f"   Title: {decision_maker.title or '(not found)'}")
                logger.info(f"   Phone: {decision_maker.phone or '(not found)'}")
            else:
                logger.warning("⚠️  No decision maker found")
        except Exception as e:
            logger.error(f"❌ Decision maker finding error: {e}")
    else:
        logger.info("\n⏭️  Skipping decision maker finding (no domain available)")
    
    logger.info("\n" + "="*80)
    logger.info("ENRICHMENT TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Company Name: {company_name}")
    logger.info(f"Apollo Configured: {bool(config.apollo_api_key)}")
    logger.info(f"Hunter Configured: {bool(config.hunter_api_key)}")
    logger.info(f"Dry Run Mode: {config.enrichment_dry_run}")
    logger.info("\n💡 Pipeline Status:")
    logger.info("   1. Company name extraction ✅ (we have this)")
    logger.info("   2. Company matching (Apollo) {'✅' if company and company.website else '⚠️'}")
    logger.info("   3. Decision maker finding (Hunter) {'✅' if company and company.website else '⏭️'}")
    logger.info("\n📝 Note: With dry_run=True, no real API calls are made")
    logger.info("   Set enrichment_dry_run=False in config to test with real APIs")


if __name__ == "__main__":
    asyncio.run(test_enrichment())
