"""Test extraction with Building permits which might have better data."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_building_permits():
    """Test extraction with Building module permits."""
    logger.info("Testing extraction with Building permits (may have better data structure)")
    
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Building",  # Try Building instead of Fire
        days_back=30,
        max_pages=1,
        extract_applicant=True,
    )
    
    logger.info("Scraping Building permits...")
    permits = await scraper.scrape()
    
    logger.info(f"\n{'='*80}")
    logger.info("EXTRACTION RESULTS")
    logger.info(f"{'='*80}\n")
    
    total = len(permits)
    has_address = sum(1 for p in permits if p.address and len(p.address.strip()) > 5)
    has_applicant = sum(1 for p in permits if p.applicant_name and len(p.applicant_name.strip()) > 2)
    has_both = sum(1 for p in permits if (p.address and len(p.address.strip()) > 5) and (p.applicant_name and len(p.applicant_name.strip()) > 2))
    
    logger.info(f"Total Permits: {total}")
    if total > 0:
        logger.info(f"With Address: {has_address}/{total} ({has_address/total*100:.1f}%)")
        logger.info(f"With Applicant Name: {has_applicant}/{total} ({has_applicant/total*100:.1f}%)")
        logger.info(f"With Both: {has_both}/{total} ({has_both/total*100:.1f}%)")
        
        # Show sample permits with data
        logger.info(f"\nSample Permits with Data:")
        for i, permit in enumerate([p for p in permits if (p.address and len(p.address.strip()) > 5) or (p.applicant_name and len(p.applicant_name.strip()) > 2)][:5], 1):
            logger.info(f"\n{i}. Permit ID: {permit.permit_id}")
            logger.info(f"   Type: {permit.permit_type}")
            logger.info(f"   Address: {permit.address or '(empty)'}")
            logger.info(f"   Applicant: {permit.applicant_name or '(empty)'}")
            logger.info(f"   Status: {permit.status}")
    else:
        logger.warning("No permits extracted!")


if __name__ == "__main__":
    asyncio.run(test_building_permits())
