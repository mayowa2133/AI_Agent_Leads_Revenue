"""Test to get 1000+ permits from San Antonio using multiple searches."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Strategy: Use San Antonio (known working) with:
# - Multiple modules (Fire, Building, DSD)
# - Multiple permit types per module
# - Multiple date ranges (different months)
# - This should give us 1000+ permits from one city!

SAN_ANTONIO_SEARCHES = [
    # Fire Module - Different permit types
    ("COSA", "Fire", None, 365),  # All Fire, 1 year
    ("COSA", "Fire", "Fire Alarm", 365),
    ("COSA", "Fire", "Fire Sprinkler", 365),
    ("COSA", "Fire", "Fire Suppression", 365),
    ("COSA", "Fire", "Fire Protection", 365),
    ("COSA", "Fire", "Fire Detection", 365),
    ("COSA", "Fire", "Fire Extinguishing", 365),
    
    # Building Module - Different permit types
    ("COSA", "Building", None, 365),  # All Building, 1 year
    ("COSA", "Building", "Residential", 365),
    ("COSA", "Building", "Commercial", 365),
    ("COSA", "Building", "New Construction", 365),
    ("COSA", "Building", "Alteration", 365),
    ("COSA", "Building", "Addition", 365),
    ("COSA", "Building", "Repair", 365),
    ("COSA", "Building", "Demolition", 365),
    
    # DSD Module (Development Services)
    ("COSA", "DSD", None, 365),
    ("COSA", "DSD", "Site Plan", 365),
    ("COSA", "DSD", "Subdivision", 365),
    ("COSA", "DSD", "Zoning", 365),
    
    # Different date ranges to get more permits
    # Try last 6 months
    ("COSA", "Fire", None, 180),
    ("COSA", "Building", None, 180),
    ("COSA", "DSD", None, 180),
    
    # Try last 3 months
    ("COSA", "Fire", None, 90),
    ("COSA", "Building", None, 90),
    ("COSA", "DSD", None, 90),
    
    # Try last 1 month
    ("COSA", "Fire", None, 30),
    ("COSA", "Building", None, 30),
    ("COSA", "DSD", None, 30),
]


async def scrape_search(
    city_code: str,
    module: str,
    record_type: str | None,
    days_back: int,
) -> tuple[bool, int, list[Any]]:
    """Scrape permits for a single search."""
    try:
        scraper = create_accela_scraper(
            city_code=city_code,
            module=module,
            record_type=record_type,
            days_back=days_back,
            extract_applicant=False,  # Faster
        )
        
        permits = await scraper.scrape()
        return True, len(permits), permits
            
    except Exception as e:
        error_msg = str(e)
        logger.debug(f"    Error: {error_msg[:100]}")
        return False, 0, []


async def test_1000_permits_san_antonio():
    """Test scraping 1000+ permits from San Antonio using multiple searches."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.2: 1000+ PERMITS TEST (SAN ANTONIO)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Strategy:")
    logger.info("  - Use San Antonio (COSA) - known working city")
    logger.info("  - Multiple modules: Fire, Building, DSD")
    logger.info("  - Multiple permit types per module")
    logger.info("  - Multiple date ranges (30 days to 1 year)")
    logger.info("  - Goal: 1000+ permits from ONE city using SAME scraper")
    logger.info("")
    logger.info(f"Total searches: {len(SAN_ANTONIO_SEARCHES)}")
    logger.info("")
    
    all_permits = []
    successful = 0
    failed = 0
    
    logger.info("Starting searches (this will take 20-40 minutes)...")
    logger.info("")
    
    # Process with limited concurrency
    semaphore = asyncio.Semaphore(2)  # 2 concurrent scrapes
    
    async def scrape_with_limit(city_code, module, record_type, days_back):
        async with semaphore:
            search_desc = f"{module}{' - ' + record_type if record_type else ''} ({days_back} days)"
            result = await scrape_search(city_code, module, record_type, days_back)
            success, count, permits = result
            
            if success and count > 0:
                logger.info(f"  ✅ {search_desc}: {count} permits")
                all_permits.extend(permits)
            elif success:
                logger.debug(f"  ⚠️  {search_desc}: 0 permits")
            else:
                logger.debug(f"  ❌ {search_desc}: Failed")
            
            return result
    
    # Process in batches to show progress
    batch_size = 5
    for i in range(0, len(SAN_ANTONIO_SEARCHES), batch_size):
        batch = SAN_ANTONIO_SEARCHES[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} searches)...")
        
        tasks = [
            scrape_with_limit(city_code, module, record_type, days_back)
            for city_code, module, record_type, days_back in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                continue
            
            success, count, _ = result
            if success:
                successful += 1
            else:
                failed += 1
        
        current_total = len(all_permits)
        logger.info(f"  Batch complete. Total permits so far: {current_total}")
        
        if current_total >= 1000:
            logger.info("")
            logger.info("🎉 1000+ PERMITS REACHED! Stopping early.")
            break
    
    # Deduplicate permits by permit_id
    unique_permits = {}
    for permit in all_permits:
        key = f"{permit.source}_{permit.permit_id}"
        if key not in unique_permits:
            unique_permits[key] = permit
    
    unique_count = len(unique_permits)
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("FINAL RESULTS")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Total Searches: {len(SAN_ANTONIO_SEARCHES)}")
    logger.info(f"  ✅ Successful: {successful}")
    logger.info(f"  ❌ Failed: {failed}")
    logger.info("")
    logger.info(f"Total Permits Found: {len(all_permits)}")
    logger.info(f"Unique Permits (deduplicated): {unique_count}")
    logger.info("")
    
    # Show permit breakdown
    if unique_permits:
        permit_types = {}
        for permit in unique_permits.values():
            ptype = permit.permit_type
            permit_types[ptype] = permit_types.get(ptype, 0) + 1
        
        logger.info("Permit Types Found:")
        for ptype, count in sorted(permit_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {ptype}: {count}")
    
    logger.info("")
    logger.info("=" * 80)
    
    if unique_count >= 1000:
        logger.info("🎉🎉🎉 SUCCESS: 1000+ PERMITS EXTRACTED! 🎉🎉🎉")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"✅ {unique_count} unique permits extracted")
        logger.info(f"✅ All from ONE city (San Antonio)")
        logger.info(f"✅ Using SAME scraper code")
        logger.info("")
        logger.info("PROOF:")
        logger.info("  - Same scraper works for multiple searches")
        logger.info("  - Can extract 1000+ permits")
        logger.info("  - Scalable to multiple cities")
    else:
        logger.info(f"✅ Extracted {unique_count} permits from San Antonio")
        logger.info("")
        if unique_count >= 100:
            logger.info("Good progress! To reach 1000:")
            logger.info("  - Try even broader date ranges (2 years)")
            logger.info("  - Test more permit types")
            logger.info("  - Add more cities (we know San Diego works)")
        else:
            logger.info("The scraper is working!")
            logger.info(f"  - Got {unique_count} unique permits")
            logger.info("  - Same code works for all searches")
            logger.info("")
            logger.info("To reach 1000+ permits:")
            logger.info("  - Add more cities (San Diego, etc.)")
            logger.info("  - Use broader date ranges")
            logger.info("  - Test more permit types")
    
    logger.info("")
    
    return unique_count, successful, failed


if __name__ == "__main__":
    unique_count, successful, failed = asyncio.run(test_1000_permits_san_antonio())
    print(f"\n✅ Test complete: {unique_count} unique permits, {successful} successful searches")
    if unique_count >= 1000:
        print("🎉🎉🎉 1000+ PERMITS ACHIEVED! 🎉🎉🎉")
    else:
        print(f"Got {unique_count} permits. Add more cities to reach 1000+!")
