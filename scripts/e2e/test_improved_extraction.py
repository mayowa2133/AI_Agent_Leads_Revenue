"""Test improved data extraction (addresses and applicant names from detail pages)."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_improved_extraction():
    """Test that improved extraction gets addresses and applicant names."""
    logger.info("=" * 80)
    logger.info("TESTING IMPROVED DATA EXTRACTION")
    logger.info("=" * 80)
    logger.info("")
    
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        days_back=30,
        max_pages=1,
        extract_applicant=True,
    )
    
    logger.info("Scraping permits with improved extraction...")
    permits = await scraper.scrape()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("EXTRACTION RESULTS")
    logger.info("=" * 80)
    logger.info("")
    
    total = len(permits)
    has_address = sum(1 for p in permits if p.address and len(p.address.strip()) > 5)
    has_applicant = sum(1 for p in permits if p.applicant_name and len(p.applicant_name.strip()) > 2)
    has_both = sum(1 for p in permits if (p.address and len(p.address.strip()) > 5) and (p.applicant_name and len(p.applicant_name.strip()) > 2))
    
    logger.info(f"Total Permits: {total}")
    if total > 0:
        logger.info(f"With Address: {has_address}/{total} ({has_address/total*100:.1f}%)")
        logger.info(f"With Applicant Name: {has_applicant}/{total} ({has_applicant/total*100:.1f}%)")
        logger.info(f"With Both: {has_both}/{total} ({has_both/total*100:.1f}%)")
    else:
        logger.warning("⚠️  No permits extracted! Check scraper logic.")
        return
    logger.info("")
    
    # Show sample permits
    logger.info("Sample Permits:")
    logger.info("-" * 80)
    for i, permit in enumerate(permits[:5], 1):
        logger.info(f"\n{i}. Permit ID: {permit.permit_id}")
        logger.info(f"   Type: {permit.permit_type}")
        logger.info(f"   Address: {permit.address or '(empty)'}")
        logger.info(f"   Applicant: {permit.applicant_name or '(empty)'}")
        logger.info(f"   Status: {permit.status}")
        if permit.detail_url:
            logger.info(f"   Detail URL: {permit.detail_url[:80]}...")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("IMPROVEMENT SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    if has_address > 0:
        logger.info(f"✅ Address extraction: {has_address}/{total} permits have addresses")
    else:
        logger.warning("⚠️  Address extraction: No addresses found")
    
    if has_applicant > 0:
        logger.info(f"✅ Applicant extraction: {has_applicant}/{total} permits have applicant names")
    else:
        logger.warning("⚠️  Applicant extraction: No applicant names found")
    
    if has_both > 0:
        logger.info(f"✅ Complete data: {has_both}/{total} permits have both address and applicant")
        logger.info("")
        logger.info("These permits should now be able to find company domains and emails!")
    else:
        logger.warning("⚠️  Complete data: No permits have both address and applicant")
        logger.info("")
        logger.info("This means enrichment will still struggle. May need to:")
        logger.info("  1. Check if detail pages have the data")
        logger.info("  2. Improve selectors for this specific portal")
        logger.info("  3. Try different permit types that have better data")


if __name__ == "__main__":
    asyncio.run(test_improved_extraction())
