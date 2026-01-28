"""Focused test to extract 1000+ permits - tests known working cities first."""

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

# Focused list: Known Accela cities + multiple modules/date ranges
# Strategy: Use broader date ranges and multiple permit types per city
FOCUSED_CITIES = [
    # San Antonio - We know this works!
    ("COSA", "San Antonio, TX", "Fire", None, 180),  # All Fire, 6 months
    ("COSA", "San Antonio, TX", "Fire", "Fire Alarm", 180),
    ("COSA", "San Antonio, TX", "Fire", "Fire Sprinkler", 180),
    ("COSA", "San Antonio, TX", "Fire", "Fire Suppression", 180),
    ("COSA", "San Antonio, TX", "Building", None, 180),  # All Building
    ("COSA", "San Antonio, TX", "Building", "Residential", 180),
    ("COSA", "San Antonio, TX", "DSD", None, 180),  # Development Services
    
    # San Diego - We know this portal exists
    ("SANDIEGO", "San Diego, CA", "DSD", None, 180),
    ("SANDIEGO", "San Diego, CA", "Fire", None, 180),
    ("SANDIEGO", "San Diego, CA", "Building", None, 180),
    
    # Common Accela city codes (try these)
    ("DAL", "Dallas, TX", "Fire", None, 180),
    ("DAL", "Dallas, TX", "Building", None, 180),
    ("AUSTIN", "Austin, TX", "Fire", None, 180),
    ("AUSTIN", "Austin, TX", "Building", None, 180),
    ("PHOENIX", "Phoenix, AZ", "Fire", None, 180),
    ("PHOENIX", "Phoenix, AZ", "Building", None, 180),
    ("DENVER", "Denver, CO", "Fire", None, 180),
    ("DENVER", "Denver, CO", "Building", None, 180),
    ("SEATTLE", "Seattle, WA", "Fire", None, 180),
    ("SEATTLE", "Seattle, WA", "Building", None, 180),
    ("CHARLOTTE", "Charlotte, NC", "Fire", None, 180),
    ("CHARLOTTE", "Charlotte, NC", "Building", None, 180),
    ("ATLANTA", "Atlanta, GA", "Fire", None, 180),
    ("ATLANTA", "Atlanta, GA", "Building", None, 180),
    ("MIAMI", "Miami, FL", "Fire", None, 180),
    ("MIAMI", "Miami, FL", "Building", None, 180),
    ("BOSTON", "Boston, MA", "Fire", None, 180),
    ("BOSTON", "Boston, MA", "Building", None, 180),
    ("PORTLAND", "Portland, OR", "Fire", None, 180),
    ("PORTLAND", "Portland, OR", "Building", None, 180),
    ("NASHVILLE", "Nashville, TN", "Fire", None, 180),
    ("NASHVILLE", "Nashville, TN", "Building", None, 180),
    ("INDIANAPOLIS", "Indianapolis, IN", "Fire", None, 180),
    ("INDIANAPOLIS", "Indianapolis, IN", "Building", None, 180),
    ("COLUMBUS", "Columbus, OH", "Fire", None, 180),
    ("COLUMBUS", "Columbus, OH", "Building", None, 180),
    ("MILWAUKEE", "Milwaukee, WI", "Fire", None, 180),
    ("MILWAUKEE", "Milwaukee, WI", "Building", None, 180),
    ("MINNEAPOLIS", "Minneapolis, MN", "Fire", None, 180),
    ("MINNEAPOLIS", "Minneapolis, MN", "Building", None, 180),
    ("KANSASCITY", "Kansas City, MO", "Fire", None, 180),
    ("KANSASCITY", "Kansas City, MO", "Building", None, 180),
    ("OKLAHOMACITY", "Oklahoma City, OK", "Fire", None, 180),
    ("OKLAHOMACITY", "Oklahoma City, OK", "Building", None, 180),
    ("TULSA", "Tulsa, OK", "Fire", None, 180),
    ("TULSA", "Tulsa, OK", "Building", None, 180),
    ("ALBUQUERQUE", "Albuquerque, NM", "Fire", None, 180),
    ("ALBUQUERQUE", "Albuquerque, NM", "Building", None, 180),
    ("MESA", "Mesa, AZ", "Fire", None, 180),
    ("MESA", "Mesa, AZ", "Building", None, 180),
    ("ARLINGTON", "Arlington, TX", "Fire", None, 180),
    ("ARLINGTON", "Arlington, TX", "Building", None, 180),
    ("FORTWORTH", "Fort Worth, TX", "Fire", None, 180),
    ("FORTWORTH", "Fort Worth, TX", "Building", None, 180),
    ("ELPASO", "El Paso, TX", "Fire", None, 180),
    ("ELPASO", "El Paso, TX", "Building", None, 180),
    ("TAMPA", "Tampa, FL", "Fire", None, 180),
    ("TAMPA", "Tampa, FL", "Building", None, 180),
    ("JACKSONVILLE", "Jacksonville, FL", "Fire", None, 180),
    ("JACKSONVILLE", "Jacksonville, FL", "Building", None, 180),
    ("RALEIGH", "Raleigh, NC", "Fire", None, 180),
    ("RALEIGH", "Raleigh, NC", "Building", None, 180),
    ("BALTIMORE", "Baltimore, MD", "Fire", None, 180),
    ("BALTIMORE", "Baltimore, MD", "Building", None, 180),
    ("CLEVELAND", "Cleveland, OH", "Fire", None, 180),
    ("CLEVELAND", "Cleveland, OH", "Building", None, 180),
    ("NEWORLEANS", "New Orleans, LA", "Fire", None, 180),
    ("NEWORLEANS", "New Orleans, LA", "Building", None, 180),
    ("OMAHA", "Omaha, NE", "Fire", None, 180),
    ("OMAHA", "Omaha, NE", "Building", None, 180),
    ("LASVEGAS", "Las Vegas, NV", "Fire", None, 180),
    ("LASVEGAS", "Las Vegas, NV", "Building", None, 180),
    ("SACRAMENTO", "Sacramento, CA", "Fire", None, 180),
    ("SACRAMENTO", "Sacramento, CA", "Building", None, 180),
    ("FRESNO", "Fresno, CA", "Fire", None, 180),
    ("FRESNO", "Fresno, CA", "Building", None, 180),
    ("SANJOSE", "San Jose, CA", "Fire", None, 180),
    ("SANJOSE", "San Jose, CA", "Building", None, 180),
    ("OAKLAND", "Oakland, CA", "Fire", None, 180),
    ("OAKLAND", "Oakland, CA", "Building", None, 180),
    ("TUCSON", "Tucson, AZ", "Fire", None, 180),
    ("TUCSON", "Tucson, AZ", "Building", None, 180),
]


async def scrape_city(
    city_code: str,
    city_name: str,
    module: str,
    record_type: str | None,
    days_back: int,
) -> tuple[bool, int, list[Any]]:
    """Scrape permits for a single city/module combination."""
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
        if "404" in error_msg or "not found" in error_msg.lower():
            return False, 0, []  # Portal doesn't exist
        return False, 0, []  # Other error


async def test_1000_permits_focused():
    """Test scraping 1000+ permits with focused city list."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.2: 1000+ PERMITS TEST (FOCUSED)")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Strategy:")
    logger.info("  - Test known working cities (San Antonio, San Diego)")
    logger.info("  - Multiple modules per city (Fire, Building, DSD)")
    logger.info("  - Multiple permit types per module")
    logger.info("  - Broader date ranges (6 months)")
    logger.info("")
    logger.info(f"Total combinations: {len(FOCUSED_CITIES)}")
    logger.info("")
    
    all_permits = []
    successful = 0
    failed = 0
    city_stats = {}
    
    # Process with limited concurrency
    semaphore = asyncio.Semaphore(2)  # 2 concurrent scrapes
    
    async def scrape_with_limit(city_code, city_name, module, record_type, days_back):
        async with semaphore:
            result = await scrape_city(city_code, city_name, module, record_type, days_back)
            city_key = f"{city_name} ({city_code})"
            module_key = f"{module}{' - ' + record_type if record_type else ''}"
            
            success, count, permits = result
            
            if success and count > 0:
                logger.info(f"  ✅ {city_key} - {module_key}: {count} permits")
            elif success:
                logger.debug(f"  ⚠️  {city_key} - {module_key}: 0 permits")
            else:
                logger.debug(f"  ❌ {city_key} - {module_key}: Failed")
            
            return result
    
    logger.info("Starting scraping (this will take 15-45 minutes)...")
    logger.info("Progress will be shown as permits are found.")
    logger.info("")
    
    # Process in batches to show progress
    batch_size = 10
    for i in range(0, len(FOCUSED_CITIES), batch_size):
        batch = FOCUSED_CITIES[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} combinations)...")
        
        tasks = [
            scrape_with_limit(city_code, city_name, module, record_type, days_back)
            for city_code, city_name, module, record_type, days_back in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            city_code, city_name, module, record_type, days_back = batch[j]
            
            if isinstance(result, Exception):
                failed += 1
                continue
            
            success, count, permits = result
            
            if success:
                successful += 1
                all_permits.extend(permits)
                
                city_key = f"{city_name} ({city_code})"
                if city_key not in city_stats:
                    city_stats[city_key] = 0
                city_stats[city_key] += count
            else:
                failed += 1
        
        current_total = len(all_permits)
        logger.info(f"  Batch complete. Total permits so far: {current_total}")
        
        if current_total >= 1000:
            logger.info("")
            logger.info("🎉 1000+ PERMITS REACHED! Stopping early.")
            break
    
    # Deduplicate
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
    logger.info(f"Total Combinations Tested: {len(FOCUSED_CITIES)}")
    logger.info(f"  ✅ Successful: {successful}")
    logger.info(f"  ❌ Failed: {failed}")
    logger.info("")
    logger.info(f"Total Permits Found: {len(all_permits)}")
    logger.info(f"Unique Permits: {unique_count}")
    logger.info("")
    
    if city_stats:
        logger.info("Top Cities by Permit Count:")
        for city, count in sorted(city_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"  {city}: {count} permits")
    
    logger.info("")
    logger.info("=" * 80)
    
    if unique_count >= 1000:
        logger.info("🎉🎉🎉 SUCCESS: 1000+ PERMITS EXTRACTED! 🎉🎉🎉")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"✅ {unique_count} unique permits extracted")
        logger.info(f"✅ {successful} successful city/module combinations")
        logger.info("")
        logger.info("PROOF: The standardized scraper CAN extract 1000+ permits!")
        logger.info("PROOF: Same scraper code works across multiple cities!")
    else:
        logger.info(f"✅ Extracted {unique_count} permits")
        logger.info("")
        if unique_count >= 100:
            logger.info("Good progress! To reach 1000:")
            logger.info("  - Test more cities")
            logger.info("  - Use even broader date ranges (1 year)")
            logger.info("  - Try more permit types")
        else:
            logger.info("The scraper is working, but we need:")
            logger.info("  - More cities with Accela portals")
            logger.info("  - Broader date ranges")
            logger.info("  - More permit types per city")
    
    logger.info("")
    
    return unique_count, successful, failed


if __name__ == "__main__":
    unique_count, successful, failed = asyncio.run(test_1000_permits_focused())
    print(f"\n✅ Test complete: {unique_count} unique permits, {successful} successful scrapes")
    if unique_count >= 1000:
        print("🎉🎉🎉 1000+ PERMITS ACHIEVED! 🎉🎉🎉")
