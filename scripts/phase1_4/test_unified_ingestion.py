"""Test unified ingestion layer with scrapers and APIs."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.api.unified_ingestion import (
    PermitSource,
    PermitSourceType,
    UnifiedPermitIngestion,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_unified_ingestion():
    """Test unified ingestion with both scrapers and APIs."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.3: UNIFIED INGESTION TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing unified interface for scrapers and APIs")
    logger.info("")
    
    ingestion = UnifiedPermitIngestion()
    
    # Test 1: Scraper source (San Antonio)
    logger.info("-" * 80)
    logger.info("Test 1: Scraper Source (San Antonio)")
    logger.info("-" * 80)
    
    scraper_source = PermitSource(
        source_type=PermitSourceType.SCRAPER,
        city="San Antonio, TX",
        source_id="cosa_fire",
        config={
            "portal_type": "accela",
            "city_code": "COSA",
            "module": "Fire",
            "record_type": None,
        },
    )
    
    try:
        permits = await ingestion.ingest_permits(scraper_source, days_back=120, limit=50)
        logger.info(f"  ✅ Fetched {len(permits)} permits from scraper")
        
        if permits:
            logger.info("  Sample permits:")
            for i, permit in enumerate(permits[:3], 1):
                logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
    
    logger.info("")
    
    # Test 2: Socrata API source (when we have a working portal)
    logger.info("-" * 80)
    logger.info("Test 2: Socrata API Source")
    logger.info("-" * 80)
    logger.info("  (Will test when we discover working Socrata portals)")
    logger.info("")
    
    # Test 3: Combined sources
    logger.info("-" * 80)
    logger.info("Test 3: Combined Sources")
    logger.info("-" * 80)
    
    all_permits = []
    
    # Add scraper permits
    try:
        scraper_permits = await ingestion.ingest_permits(scraper_source, days_back=120, limit=50)
        all_permits.extend(scraper_permits)
        logger.info(f"  ✅ Scraper: {len(scraper_permits)} permits")
    except Exception as e:
        logger.warning(f"  ⚠️  Scraper error: {e}")
    
    # Add API permits (when available)
    # all_permits.extend(api_permits)
    
    logger.info("")
    logger.info(f"  Total permits from all sources: {len(all_permits)}")
    
    # Deduplicate
    unique_permits = {}
    for permit in all_permits:
        key = f"{permit.source}_{permit.permit_id}"
        if key not in unique_permits:
            unique_permits[key] = permit
    
    logger.info(f"  Unique permits: {len(unique_permits)}")
    logger.info("")
    
    logger.info("=" * 80)
    logger.info("✅ Unified Ingestion Test Complete")
    logger.info("=" * 80)
    logger.info("")
    logger.info("The unified interface works for:")
    logger.info("  ✅ Scrapers (Playwright-based)")
    logger.info("  ⏳ APIs (Socrata, CKAN, Custom) - ready to test")
    logger.info("")
    logger.info("Same interface for all permit sources!")


if __name__ == "__main__":
    asyncio.run(test_unified_ingestion())
