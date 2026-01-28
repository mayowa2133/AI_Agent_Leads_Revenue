"""Find working Accela cities by testing various city codes and configurations."""

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

# Common Accela city codes to test
CITIES_TO_TEST = [
    # Texas
    ("COSA", "San Antonio, TX", ["Fire", "Building", "DSD"]),
    ("DAL", "Dallas, TX", ["Fire", "Building"]),
    ("AUSTIN", "Austin, TX", ["Fire", "Building"]),
    ("HOUSTON", "Houston, TX", ["Fire", "Building"]),
    ("FORTWORTH", "Fort Worth, TX", ["Fire", "Building"]),
    ("ARLINGTON", "Arlington, TX", ["Fire", "Building"]),
    ("ELPASO", "El Paso, TX", ["Fire", "Building"]),
    
    # California
    ("SANDIEGO", "San Diego, CA", ["DSD", "Fire", "Building"]),
    ("SACRAMENTO", "Sacramento, CA", ["Fire", "Building"]),
    ("FRESNO", "Fresno, CA", ["Fire", "Building"]),
    ("SANJOSE", "San Jose, CA", ["Fire", "Building"]),
    ("OAKLAND", "Oakland, CA", ["Fire", "Building"]),
    
    # Arizona
    ("PHOENIX", "Phoenix, AZ", ["Fire", "Building"]),
    ("TUCSON", "Tucson, AZ", ["Fire", "Building"]),
    ("MESA", "Mesa, AZ", ["Fire", "Building"]),
    
    # Florida
    ("MIAMI", "Miami, FL", ["Fire", "Building"]),
    ("TAMPA", "Tampa, FL", ["Fire", "Building"]),
    ("JACKSONVILLE", "Jacksonville, FL", ["Fire", "Building"]),
    
    # North Carolina
    ("CHARLOTTE", "Charlotte, NC", ["Fire", "Building"]),
    ("RALEIGH", "Raleigh, NC", ["Fire", "Building"]),
    
    # Colorado
    ("DENVER", "Denver, CO", ["Fire", "Building"]),
    
    # Washington
    ("SEATTLE", "Seattle, WA", ["Fire", "Building"]),
    
    # Oregon
    ("PORTLAND", "Portland, OR", ["Fire", "Building"]),
    
    # Nevada
    ("LASVEGAS", "Las Vegas, NV", ["Fire", "Building"]),
    
    # Tennessee
    ("NASHVILLE", "Nashville, TN", ["Fire", "Building"]),
    
    # Indiana
    ("INDIANAPOLIS", "Indianapolis, IN", ["Fire", "Building"]),
    
    # Ohio
    ("COLUMBUS", "Columbus, OH", ["Fire", "Building"]),
    ("CLEVELAND", "Cleveland, OH", ["Fire", "Building"]),
    
    # Georgia
    ("ATLANTA", "Atlanta, GA", ["Fire", "Building"]),
    
    # Massachusetts
    ("BOSTON", "Boston, MA", ["Fire", "Building"]),
    
    # Maryland
    ("BALTIMORE", "Baltimore, MD", ["Fire", "Building"]),
    
    # Wisconsin
    ("MILWAUKEE", "Milwaukee, WI", ["Fire", "Building"]),
    
    # Minnesota
    ("MINNEAPOLIS", "Minneapolis, MN", ["Fire", "Building"]),
    
    # Missouri
    ("KANSASCITY", "Kansas City, MO", ["Fire", "Building"]),
    
    # Oklahoma
    ("OKLAHOMACITY", "Oklahoma City, OK", ["Fire", "Building"]),
    ("TULSA", "Tulsa, OK", ["Fire", "Building"]),
    
    # Louisiana
    ("NEWORLEANS", "New Orleans, LA", ["Fire", "Building"]),
    
    # Nebraska
    ("OMAHA", "Omaha, NE", ["Fire", "Building"]),
    
    # New Mexico
    ("ALBUQUERQUE", "Albuquerque, NM", ["Fire", "Building"]),
]


async def test_city_module(
    city_code: str,
    city_name: str,
    module: str,
    days_back: int = 365,
) -> tuple[bool, int, list[Any]]:
    """Test a single city/module combination."""
    try:
        scraper = create_accela_scraper(
            city_code=city_code,
            module=module,
            record_type=None,  # All permits
            days_back=days_back,
            extract_applicant=False,  # Faster
            max_pages=1,
        )
        
        permits = await scraper.scrape()
        return True, len(permits), permits
            
    except Exception as e:
        error_msg = str(e)
        # Check if it's a connection/portal issue
        if "404" in error_msg or "not found" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, 0, []  # Portal doesn't exist
        return False, 0, []


async def find_working_cities():
    """Find cities that actually work and return permits."""
    logger.info("=" * 80)
    logger.info("FINDING WORKING ACCELA CITIES")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing cities to find at least 2 more that work (besides San Antonio)")
    logger.info("")
    
    working_cities = {}  # {city_name: {module: permit_count}}
    total_tested = 0
    
    # Test with limited concurrency
    semaphore = asyncio.Semaphore(3)  # 3 concurrent tests
    
    async def test_with_limit(city_code, city_name, module):
        async with semaphore:
            result = await test_city_module(city_code, city_name, module)
            return city_code, city_name, module, result
    
    # Create all test tasks
    tasks = []
    for city_code, city_name, modules in CITIES_TO_TEST:
        for module in modules:
            tasks.append(test_with_limit(city_code, city_name, module))
            total_tested += 1
    
    logger.info(f"Testing {total_tested} city/module combinations...")
    logger.info("This will take 20-40 minutes...")
    logger.info("")
    logger.info("Progress will be shown as working cities are found:")
    logger.info("")
    
    # Process in batches to show progress
    batch_size = 15
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} tests)...")
        
        results = await asyncio.gather(*batch, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            city_code, city_name, module, (success, count, permits) = result
            
            if success and count > 0:
                if city_name not in working_cities:
                    working_cities[city_name] = {"city_code": city_code, "modules": {}}
                
                working_cities[city_name]["modules"][module] = count
                logger.info(f"  ✅ {city_name} ({city_code}) - {module}: {count} permits")
        
        logger.info(f"  Found {len(working_cities)} working cities so far...")
        logger.info("")
        
        # If we found 3+ working cities, we can stop early
        if len(working_cities) >= 3:
            logger.info("Found 3+ working cities! Stopping early.")
            break
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("RESULTS")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Total city/module combinations tested: {total_tested}")
    logger.info(f"Working cities found: {len(working_cities)}")
    logger.info("")
    
    if working_cities:
        logger.info("Working Cities:")
        for city_name, data in sorted(working_cities.items()):
            city_code = data["city_code"]
            modules = data["modules"]
            total_permits = sum(modules.values())
            logger.info(f"  ✅ {city_name} ({city_code}): {total_permits} total permits")
            for module, count in modules.items():
                logger.info(f"     - {module}: {count} permits")
    
    logger.info("")
    logger.info("=" * 80)
    
    if len(working_cities) >= 3:
        logger.info("🎉 SUCCESS: Found 3+ working cities!")
        logger.info("")
        logger.info("The scraper works for multiple cities!")
        logger.info("Ready to demonstrate 1000+ permits with multiple cities!")
    elif len(working_cities) >= 2:
        logger.info("✅ Found 2+ working cities (plus San Antonio = 3 total)")
        logger.info("")
        logger.info("The scraper works for multiple cities!")
    else:
        logger.warning("⚠️  Only found 1 working city")
        logger.info("")
        logger.info("May need to:")
        logger.info("  - Try different date ranges")
        logger.info("  - Try different modules")
        logger.info("  - Check if city codes are correct")
    
    return working_cities


if __name__ == "__main__":
    working = asyncio.run(find_working_cities())
    print(f"\n✅ Test complete: Found {len(working)} working cities")
    if len(working) >= 2:
        print("🎉 Success! Found 2+ working cities (plus San Antonio = 3 total)")
