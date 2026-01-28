"""Test Phase 1.4.2 with broader parameters to get multiple permits."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_broad_search():
    """Test with broader search parameters to get multiple permits."""
    logger.info("=" * 70)
    logger.info("Testing Standardized Accela Scraper - BROAD SEARCH")
    logger.info("=" * 70)
    logger.info("")
    
    # Test 1: All Fire permits (no record_type filter)
    logger.info("Test 1: All Fire Permits (No Filter)")
    logger.info("-" * 70)
    scraper1 = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        record_type=None,  # No filter - get ALL fire permits
        days_back=120,  # Broader date range
    )
    
    logger.info(f"Scraping ALL Fire permits from San Antonio...")
    logger.info(f"Date range: Last 120 days (or Sept-Oct 2025 if >= 120)")
    logger.info("")
    
    permits1 = await scraper1.scrape()
    logger.info(f"✅ Found {len(permits1)} permits")
    
    if permits1:
        logger.info("")
        logger.info("Sample permits:")
        for i, permit in enumerate(permits1[:10], 1):
            logger.info(f"  {i}. {permit.permit_id} - {permit.permit_type}")
            logger.info(f"     Address: {permit.address}")
            logger.info(f"     Status: {permit.status}")
        if len(permits1) > 10:
            logger.info(f"     ... and {len(permits1) - 10} more")
    
    logger.info("")
    logger.info("=" * 70)
    
    # Test 2: Multiple permit types
    logger.info("Test 2: Multiple Permit Types")
    logger.info("-" * 70)
    
    all_permits = permits1.copy() if permits1 else []
    
    # Try different permit types
    permit_types = ["Fire Sprinkler", "Fire Suppression", "Fire Protection"]
    
    for permit_type in permit_types:
        logger.info(f"Searching for: {permit_type}...")
        scraper = create_accela_scraper(
            city_code="COSA",
            module="Fire",
            record_type=permit_type,
            days_back=120,
        )
        
        permits = await scraper.scrape()
        logger.info(f"  Found {len(permits)} permits for {permit_type}")
        
        if permits:
            all_permits.extend(permits)
    
    # Deduplicate
    seen_ids = set()
    unique_permits = []
    for permit in all_permits:
        if permit.permit_id not in seen_ids:
            seen_ids.add(permit.permit_id)
            unique_permits.append(permit)
    
    logger.info("")
    logger.info(f"✅ Total unique permits across all searches: {len(unique_permits)}")
    
    if unique_permits:
        logger.info("")
        logger.info("All unique permits:")
        for i, permit in enumerate(unique_permits[:20], 1):
            logger.info(f"  {i}. {permit.permit_id} - {permit.permit_type}")
            logger.info(f"     Address: {permit.address}")
        if len(unique_permits) > 20:
            logger.info(f"     ... and {len(unique_permits) - 20} more")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Summary")
    logger.info("=" * 70)
    logger.info(f"Total permits found: {len(unique_permits)}")
    if unique_permits:
        permit_types_found = set(p.permit_type for p in unique_permits)
        logger.info(f"Unique permit types: {len(permit_types_found)}")
        logger.info(f"Permit types: {', '.join(sorted(permit_types_found))}")
    
    return len(unique_permits)


if __name__ == "__main__":
    result = asyncio.run(test_broad_search())
    print(f"\n✅ Test complete: Found {result} total permits")
    if result > 1:
        print(f"🎉 SUCCESS: Got {result} permits (not just 1!)")
    else:
        print(f"⚠️  Only got {result} permit(s) - may need different parameters")
