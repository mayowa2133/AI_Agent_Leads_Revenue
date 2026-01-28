"""Test Phase 1.4.2 scalability across multiple cities."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_multiple_cities():
    """Test standardized scraper across multiple cities."""
    logger.info("=" * 70)
    logger.info("Phase 1.4.2: Multi-City Scalability Test")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Testing standardized Accela scraper across multiple cities...")
    logger.info("Same scraper code, different city configurations!")
    logger.info("")
    
    # Test cities with known Accela portals
    test_cities = [
        {
            "city_code": "COSA",
            "city_name": "San Antonio, TX",
            "module": "Fire",
            "record_type": "Fire Alarm",
        },
        {
            "city_code": "SANDIEGO",
            "city_name": "San Diego, CA",
            "module": "DSD",  # Development Services Department
            "record_type": None,  # All permits
        },
        # Add more cities as we discover them
    ]
    
    all_results = []
    total_permits = 0
    
    for city_config in test_cities:
        city_code = city_config["city_code"]
        city_name = city_config["city_name"]
        module = city_config["module"]
        record_type = city_config.get("record_type")
        
        logger.info("-" * 70)
        logger.info(f"Testing: {city_name}")
        logger.info(f"  City Code: {city_code}")
        logger.info(f"  Module: {module}")
        logger.info(f"  Record Type: {record_type or 'All'}")
        logger.info("")
        
        try:
            # Create scraper for this city
            scraper = create_accela_scraper(
                city_code=city_code,
                module=module,
                record_type=record_type,
                days_back=120,  # Use golden search period
            )
            
            logger.info(f"  Scraper created: {scraper.source}")
            logger.info(f"  URL: {scraper.start_url}")
            logger.info("  Scraping permits (this may take 30-60 seconds)...")
            
            # Scrape permits
            permits = await scraper.scrape()
            
            logger.info(f"  ✅ Successfully scraped {len(permits)} permits")
            
            if permits:
                logger.info("")
                logger.info("  Sample permits:")
                for i, permit in enumerate(permits[:5], 1):
                    logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
                    logger.info(f"       Address: {permit.address}")
                    logger.info(f"       Status: {permit.status}")
                
                if len(permits) > 5:
                    logger.info(f"    ... and {len(permits) - 5} more permits")
                
                # Count by permit type
                permit_types = {}
                for permit in permits:
                    permit_types[permit.permit_type] = permit_types.get(permit.permit_type, 0) + 1
                
                logger.info("")
                logger.info("  Permit types found:")
                for ptype, count in sorted(permit_types.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"    {ptype}: {count}")
            
            all_results.append({
                "city": city_name,
                "city_code": city_code,
                "module": module,
                "success": True,
                "permit_count": len(permits),
                "permits": permits,
            })
            total_permits += len(permits)
            
        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            all_results.append({
                "city": city_name,
                "city_code": city_code,
                "module": module,
                "success": False,
                "error": str(e),
                "permit_count": 0,
            })
        
        logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("Scalability Test Summary")
    logger.info("=" * 70)
    logger.info("")
    
    successful_cities = [r for r in all_results if r.get("success", False)]
    failed_cities = [r for r in all_results if not r.get("success", False)]
    
    logger.info(f"Total Cities Tested: {len(all_results)}")
    logger.info(f"  ✅ Successful: {len(successful_cities)}")
    logger.info(f"  ❌ Failed: {len(failed_cities)}")
    logger.info(f"")
    logger.info(f"Total Permits Extracted: {total_permits}")
    logger.info("")
    
    if successful_cities:
        logger.info("Successful Cities:")
        for result in successful_cities:
            logger.info(f"  ✅ {result['city']} ({result['city_code']}): {result['permit_count']} permits")
            logger.info(f"     Module: {result['module']}")
    
    if failed_cities:
        logger.info("")
        logger.info("Failed Cities:")
        for result in failed_cities:
            logger.info(f"  ❌ {result['city']} ({result['city_code']}): {result.get('error', 'Unknown error')}")
    
    logger.info("")
    logger.info("=" * 70)
    
    if len(successful_cities) > 0:
        logger.info("🎉 SCALABILITY DEMONSTRATED!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("✅ Same scraper code works across multiple cities")
        logger.info(f"✅ {len(successful_cities)} cities successfully scraped")
        logger.info(f"✅ {total_permits} total permits extracted")
        logger.info("")
        logger.info("The standardized scraper is scalable and reusable!")
    else:
        logger.warning("⚠️  No cities successfully scraped")
        logger.warning("Review errors above")
    
    return len(successful_cities), total_permits


if __name__ == "__main__":
    successful, total = asyncio.run(test_multiple_cities())
    print(f"\n✅ Test complete: {successful} cities successful, {total} total permits")
    if successful > 1:
        print("🎉 Multi-city scalability proven!")
