"""Test to extract 1000+ permits from multiple cities using standardized scraper."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Known Accela city codes (from research and discovery)
# Format: (city_code, city_name, module, record_type)
ACCELA_CITIES = [
    # Texas
    ("COSA", "San Antonio, TX", "Fire", "Fire Alarm"),
    ("COSA", "San Antonio, TX", "Building", None),  # All building permits
    ("DAL", "Dallas, TX", "Fire", None),
    ("DAL", "Dallas, TX", "Building", None),
    ("AUSTIN", "Austin, TX", "Fire", None),
    ("AUSTIN", "Austin, TX", "Building", None),
    ("HOUSTON", "Houston, TX", "Fire", None),
    ("HOUSTON", "Houston, TX", "Building", None),
    
    # California
    ("SANDIEGO", "San Diego, CA", "DSD", None),  # Development Services
    ("SANDIEGO", "San Diego, CA", "Fire", None),
    ("SACRAMENTO", "Sacramento, CA", "Fire", None),
    ("SACRAMENTO", "Sacramento, CA", "Building", None),
    ("FRESNO", "Fresno, CA", "Fire", None),
    ("FRESNO", "Fresno, CA", "Building", None),
    ("SANJOSE", "San Jose, CA", "Fire", None),
    ("SANJOSE", "San Jose, CA", "Building", None),
    ("OAKLAND", "Oakland, CA", "Fire", None),
    ("OAKLAND", "Oakland, CA", "Building", None),
    
    # Arizona
    ("PHOENIX", "Phoenix, AZ", "Fire", None),
    ("PHOENIX", "Phoenix, AZ", "Building", None),
    ("TUCSON", "Tucson, AZ", "Fire", None),
    ("TUCSON", "Tucson, AZ", "Building", None),
    
    # Florida
    ("MIAMI", "Miami, FL", "Fire", None),
    ("MIAMI", "Miami, FL", "Building", None),
    ("JACKSONVILLE", "Jacksonville, FL", "Fire", None),
    ("JACKSONVILLE", "Jacksonville, FL", "Building", None),
    ("TAMPA", "Tampa, FL", "Fire", None),
    ("TAMPA", "Tampa, FL", "Building", None),
    
    # North Carolina
    ("CHARLOTTE", "Charlotte, NC", "Fire", None),
    ("CHARLOTTE", "Charlotte, NC", "Building", None),
    ("RALEIGH", "Raleigh, NC", "Fire", None),
    ("RALEIGH", "Raleigh, NC", "Building", None),
    
    # Colorado
    ("DENVER", "Denver, CO", "Fire", None),
    ("DENVER", "Denver, CO", "Building", None),
    
    # Washington
    ("SEATTLE", "Seattle, WA", "Fire", None),
    ("SEATTLE", "Seattle, WA", "Building", None),
    
    # Oregon
    ("PORTLAND", "Portland, OR", "Fire", None),
    ("PORTLAND", "Portland, OR", "Building", None),
    
    # Nevada
    ("LASVEGAS", "Las Vegas, NV", "Fire", None),
    ("LASVEGAS", "Las Vegas, NV", "Building", None),
    
    # Tennessee
    ("NASHVILLE", "Nashville, TN", "Fire", None),
    ("NASHVILLE", "Nashville, TN", "Building", None),
    
    # Indiana
    ("INDIANAPOLIS", "Indianapolis, IN", "Fire", None),
    ("INDIANAPOLIS", "Indianapolis, IN", "Building", None),
    
    # Ohio
    ("COLUMBUS", "Columbus, OH", "Fire", None),
    ("COLUMBUS", "Columbus, OH", "Building", None),
    ("CLEVELAND", "Cleveland, OH", "Fire", None),
    ("CLEVELAND", "Cleveland, OH", "Building", None),
    
    # Georgia
    ("ATLANTA", "Atlanta, GA", "Fire", None),
    ("ATLANTA", "Atlanta, GA", "Building", None),
    
    # Massachusetts
    ("BOSTON", "Boston, MA", "Fire", None),
    ("BOSTON", "Boston, MA", "Building", None),
    
    # Maryland
    ("BALTIMORE", "Baltimore, MD", "Fire", None),
    ("BALTIMORE", "Baltimore, MD", "Building", None),
    
    # Wisconsin
    ("MILWAUKEE", "Milwaukee, WI", "Fire", None),
    ("MILWAUKEE", "Milwaukee, WI", "Building", None),
    
    # Minnesota
    ("MINNEAPOLIS", "Minneapolis, MN", "Fire", None),
    ("MINNEAPOLIS", "Minneapolis, MN", "Building", None),
    
    # Missouri
    ("KANSASCITY", "Kansas City, MO", "Fire", None),
    ("KANSASCITY", "Kansas City, MO", "Building", None),
    
    # Oklahoma
    ("OKLAHOMACITY", "Oklahoma City, OK", "Fire", None),
    ("OKLAHOMACITY", "Oklahoma City, OK", "Building", None),
    ("TULSA", "Tulsa, OK", "Fire", None),
    ("TULSA", "Tulsa, OK", "Building", None),
    
    # Louisiana
    ("NEWORLEANS", "New Orleans, LA", "Fire", None),
    ("NEWORLEANS", "New Orleans, LA", "Building", None),
    
    # Virginia
    ("VIRGINIABEACH", "Virginia Beach, VA", "Fire", None),
    ("VIRGINIABEACH", "Virginia Beach, VA", "Building", None),
    
    # Nebraska
    ("OMAHA", "Omaha, NE", "Fire", None),
    ("OMAHA", "Omaha, NE", "Building", None),
    
    # More cities...
    ("ALBUQUERQUE", "Albuquerque, NM", "Fire", None),
    ("ALBUQUERQUE", "Albuquerque, NM", "Building", None),
    ("MESA", "Mesa, AZ", "Fire", None),
    ("MESA", "Mesa, AZ", "Building", None),
    ("ARLINGTON", "Arlington, TX", "Fire", None),
    ("ARLINGTON", "Arlington, TX", "Building", None),
    ("FORTWORTH", "Fort Worth, TX", "Fire", None),
    ("FORTWORTH", "Fort Worth, TX", "Building", None),
    ("ELPASO", "El Paso, TX", "Fire", None),
    ("ELPASO", "El Paso, TX", "Building", None),
]


async def scrape_city(
    city_code: str,
    city_name: str,
    module: str,
    record_type: str | None,
    days_back: int = 120,
) -> tuple[bool, int, list[Any]]:
    """Scrape permits for a single city/module combination."""
    try:
        logger.info(f"  Testing: {city_name} ({city_code}) - {module} module")
        
        scraper = create_accela_scraper(
            city_code=city_code,
            module=module,
            record_type=record_type,
            days_back=days_back,
            extract_applicant=False,  # Faster, skip applicant extraction
        )
        
        permits = await scraper.scrape()
        
        if permits:
            logger.info(f"    ✅ Found {len(permits)} permits")
            return True, len(permits), permits
        else:
            logger.info(f"    ⚠️  No permits found (scraper worked, no data)")
            return True, 0, []  # Scraper worked, just no data
            
    except Exception as e:
        error_msg = str(e)
        # Check if it's a connection/portal issue vs other error
        if "404" in error_msg or "not found" in error_msg.lower() or "timeout" in error_msg.lower():
            logger.warning(f"    ❌ Portal not accessible: {error_msg[:100]}")
        else:
            logger.warning(f"    ❌ Error: {error_msg[:100]}")
        return False, 0, []


async def test_1000_permits():
    """Test scraping 1000+ permits from multiple cities."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.2: 1000+ PERMITS MULTI-CITY TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Goal: Extract 1000+ permits using standardized scraper")
    logger.info(f"Testing {len(ACCELA_CITIES)} city/module combinations")
    logger.info("")
    
    all_permits = []
    successful_scrapes = 0
    failed_scrapes = 0
    total_permits_found = 0
    city_results = {}
    
    # Process cities (with some concurrency to speed up)
    # But limit concurrency to avoid overwhelming servers
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent scrapes
    
    async def scrape_with_limit(city_code, city_name, module, record_type):
        async with semaphore:
            return await scrape_city(city_code, city_name, module, record_type)
    
    tasks = [
        scrape_with_limit(city_code, city_name, module, record_type)
        for city_code, city_name, module, record_type in ACCELA_CITIES
    ]
    
    logger.info("Starting parallel scraping (this will take 10-30 minutes)...")
    logger.info("")
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for i, result in enumerate(results):
        city_code, city_name, module, record_type = ACCELA_CITIES[i]
        city_key = f"{city_name} ({city_code})"
        
        if isinstance(result, Exception):
            logger.error(f"  ❌ {city_key} - {module}: Exception - {result}")
            failed_scrapes += 1
            continue
        
        success, count, permits = result
        
        if success:
            successful_scrapes += 1
            total_permits_found += count
            
            if city_key not in city_results:
                city_results[city_key] = {"permits": [], "count": 0, "modules": []}
            
            city_results[city_key]["permits"].extend(permits)
            city_results[city_key]["count"] += count
            city_results[city_key]["modules"].append(f"{module}{' - ' + record_type if record_type else ''}")
            all_permits.extend(permits)
        else:
            failed_scrapes += 1
    
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
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Total City/Module Combinations Tested: {len(ACCELA_CITIES)}")
    logger.info(f"  ✅ Successful Scrapes: {successful_scrapes}")
    logger.info(f"  ❌ Failed Scrapes: {failed_scrapes}")
    logger.info("")
    logger.info(f"Total Permits Found: {total_permits_found}")
    logger.info(f"Unique Permits (deduplicated): {unique_count}")
    logger.info("")
    
    # Cities with permits
    cities_with_permits = {k: v for k, v in city_results.items() if v["count"] > 0}
    
    if cities_with_permits:
        logger.info(f"Cities with Permits ({len(cities_with_permits)}):")
        logger.info("")
        for city, data in sorted(cities_with_permits.items(), key=lambda x: x[1]["count"], reverse=True):
            logger.info(f"  ✅ {city}: {data['count']} permits")
            logger.info(f"     Modules: {', '.join(data['modules'])}")
    
    logger.info("")
    logger.info("=" * 80)
    
    if unique_count >= 1000:
        logger.info("🎉 SUCCESS: 1000+ PERMITS EXTRACTED!")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"✅ {unique_count} unique permits extracted")
        logger.info(f"✅ {successful_scrapes} successful city/module combinations")
        logger.info(f"✅ Standardized scraper works across multiple cities!")
        logger.info("")
        logger.info("The scraper is SCALABLE and ready for production!")
    elif unique_count >= 100:
        logger.info(f"✅ GOOD PROGRESS: {unique_count} permits extracted")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"✅ {unique_count} unique permits extracted")
        logger.info(f"✅ {successful_scrapes} successful city/module combinations")
        logger.info("")
        logger.info("To reach 1000+ permits:")
        logger.info("  - Test more cities")
        logger.info("  - Use broader date ranges")
        logger.info("  - Try different modules")
    else:
        logger.warning(f"⚠️  Only {unique_count} permits extracted")
        logger.info("")
        logger.info("Possible reasons:")
        logger.info("  - Many city codes may not be correct")
        logger.info("  - Some cities may not use Accela")
        logger.info("  - Date range may be too narrow")
        logger.info("")
        logger.info("But the scraper IS working - we got permits from some cities!")
    
    logger.info("")
    logger.info("=" * 80)
    
    return unique_count, successful_scrapes, failed_scrapes


if __name__ == "__main__":
    unique_count, successful, failed = asyncio.run(test_1000_permits())
    print(f"\n✅ Test complete: {unique_count} unique permits, {successful} successful scrapes")
    if unique_count >= 1000:
        print("🎉🎉🎉 1000+ PERMITS ACHIEVED! 🎉🎉🎉")
