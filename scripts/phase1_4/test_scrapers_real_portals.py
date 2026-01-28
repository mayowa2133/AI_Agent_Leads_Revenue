"""Test standardized scrapers with real discovered portals."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.signal_engine.discovery.portal_discovery import PortalType
from src.signal_engine.discovery.portal_storage import PortalStorage
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.signal_engine.scrapers.registry import ScraperRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_accela_scraper_direct():
    """Test 1: Direct Accela scraper with known working portal."""
    logger.info("=" * 70)
    logger.info("Test 1: Direct Accela Scraper (San Antonio - Known Working)")
    logger.info("=" * 70)
    
    logger.info("Creating San Antonio Fire scraper...")
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        record_type="Fire Alarm",
        days_back=120,  # Use golden search period (Sept-Oct 2025)
    )
    
    logger.info(f"Scraper: {scraper.source}")
    logger.info(f"URL: {scraper.start_url}")
    logger.info("")
    logger.info("Scraping permits (this may take 30-60 seconds)...")
    
    try:
        permits = await scraper.scrape()
        logger.info(f"✅ Successfully scraped {len(permits)} permits")
        
        if permits:
            logger.info("")
            logger.info("Sample permits:")
            for i, permit in enumerate(permits[:5], 1):
                logger.info(f"  {i}. Permit ID: {permit.permit_id}")
                logger.info(f"     Type: {permit.permit_type}")
                logger.info(f"     Address: {permit.address}")
                logger.info(f"     Status: {permit.status}")
                if permit.applicant_name:
                    logger.info(f"     Applicant: {permit.applicant_name}")
                if permit.detail_url:
                    logger.info(f"     Detail URL: {permit.detail_url[:80]}...")
                logger.info("")
            
            return True, len(permits)
        else:
            logger.warning("⚠️  No permits found (may be normal if no permits in date range)")
            return True, 0  # Scraper worked, just no data
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, 0


async def test_registry_with_discovered_portals():
    """Test 2: Registry with discovered portals."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 2: Registry with Discovered Portals")
    logger.info("=" * 70)
    
    # Load discovered portals
    storage = PortalStorage()
    portals = storage.get_all_portals()
    
    logger.info(f"Found {len(portals)} portals in storage")
    
    # Find Accela portals
    accela_portals = [p for p in portals if p.system_type == PortalType.ACCELA]
    
    if not accela_portals:
        logger.warning("No Accela portals found in storage")
        logger.info("Creating test Accela portal...")
        
        from src.signal_engine.discovery.portal_discovery import PortalInfo
        
        # Create test portal for San Diego (we know this exists)
        test_portal = PortalInfo(
            url="https://aca-prod.accela.com/SANDIEGO/Cap/CapHome.aspx?module=DSD",
            city="San Diego",
            system_type=PortalType.ACCELA,
            confidence_score=0.8,
            title="San Diego Accela Portal",
            validated=True,
            config={
                "city_code": "SANDIEGO",
                "module": "DSD",  # Development Services Department
            },
        )
        accela_portals = [test_portal]
    
    logger.info(f"Found {len(accela_portals)} Accela portal(s)")
    logger.info("")
    
    results = []
    for portal in accela_portals[:2]:  # Test first 2 to avoid rate limits
        logger.info(f"Testing portal: {portal.city}")
        logger.info(f"  URL: {portal.url}")
        logger.info(f"  System Type: {portal.system_type.value}")
        logger.info("")
        
        try:
            # Create scraper via registry
            logger.info("  Creating scraper via registry...")
            scraper = ScraperRegistry.create_scraper(portal, days_back=7)  # Short range for testing
            logger.info(f"  ✅ Scraper created: {scraper.source}")
            logger.info(f"  Scraper type: {type(scraper).__name__}")
            
            # Test scraping (with shorter timeout for testing)
            logger.info("  Scraping permits (this may take 30-60 seconds)...")
            permits = await scraper.scrape()
            
            logger.info(f"  ✅ Successfully scraped {len(permits)} permits")
            
            if permits:
                logger.info("  Sample permits:")
                for i, permit in enumerate(permits[:3], 1):
                    logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
                    logger.info(f"       Address: {permit.address}")
            
            results.append({
                "portal": portal.city,
                "success": True,
                "permit_count": len(permits),
            })
        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            results.append({
                "portal": portal.city,
                "success": False,
                "error": str(e),
            })
        
        logger.info("")
    
    return results


async def test_multiple_accela_cities():
    """Test 3: Multiple Accela cities with same scraper."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 3: Multiple Accela Cities")
    logger.info("=" * 70)
    
    # Test cities (known Accela cities)
    test_cities = [
        ("COSA", "San Antonio", "Fire"),
        ("SANDIEGO", "San Diego", "DSD"),
    ]
    
    results = []
    
    for city_code, city_name, module in test_cities:
        logger.info(f"Testing {city_name} ({city_code}) - {module} module...")
        
        try:
            scraper = create_accela_scraper(
                city_code=city_code,
                module=module,
                days_back=7,  # Short range for testing
            )
            
            logger.info(f"  Scraper created: {scraper.source}")
            logger.info(f"  URL: {scraper.start_url}")
            
            # Test scraping
            logger.info("  Scraping permits...")
            permits = await scraper.scrape()
            
            logger.info(f"  ✅ Scraped {len(permits)} permits")
            
            if permits:
                logger.info(f"  Sample: {permits[0].permit_id} - {permits[0].permit_type}")
            
            results.append({
                "city": city_name,
                "city_code": city_code,
                "module": module,
                "success": True,
                "permit_count": len(permits),
            })
        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")
            results.append({
                "city": city_name,
                "city_code": city_code,
                "module": module,
                "success": False,
                "error": str(e),
            })
        
        logger.info("")
    
    return results


async def main():
    """Run comprehensive real portal tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Standardized Scrapers with Real Portals")
    logger.info("=" * 70)
    logger.info("")
    
    all_results = {}
    
    # Test 1: Direct Accela scraper (known working)
    logger.info("Starting Test 1: Direct Accela Scraper...")
    success, permit_count = await test_accela_scraper_direct()
    all_results["direct_accela"] = {
        "success": success,
        "permit_count": permit_count,
    }
    
    # Test 2: Registry with discovered portals
    logger.info("")
    logger.info("Starting Test 2: Registry with Discovered Portals...")
    registry_results = await test_registry_with_discovered_portals()
    all_results["registry"] = registry_results
    
    # Test 3: Multiple cities
    logger.info("")
    logger.info("Starting Test 3: Multiple Accela Cities...")
    multi_city_results = await test_multiple_accela_cities()
    all_results["multiple_cities"] = multi_city_results
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Summary")
    logger.info("=" * 70)
    
    # Test 1 summary
    if all_results["direct_accela"]["success"]:
        logger.info("✅ Test 1: Direct Accela Scraper - PASSED")
        logger.info(f"   Permits scraped: {all_results['direct_accela']['permit_count']}")
    else:
        logger.error("❌ Test 1: Direct Accela Scraper - FAILED")
    
    # Test 2 summary
    logger.info("")
    logger.info("Test 2: Registry with Discovered Portals")
    registry_success = sum(1 for r in registry_results if r.get("success", False))
    logger.info(f"   Success: {registry_success}/{len(registry_results)} portals")
    for result in registry_results:
        if result.get("success"):
            logger.info(f"   ✅ {result['portal']}: {result.get('permit_count', 0)} permits")
        else:
            logger.info(f"   ❌ {result['portal']}: {result.get('error', 'Unknown error')}")
    
    # Test 3 summary
    logger.info("")
    logger.info("Test 3: Multiple Accela Cities")
    multi_success = sum(1 for r in multi_city_results if r.get("success", False))
    logger.info(f"   Success: {multi_success}/{len(multi_city_results)} cities")
    for result in multi_city_results:
        if result.get("success"):
            logger.info(f"   ✅ {result['city']} ({result['city_code']}): {result.get('permit_count', 0)} permits")
        else:
            logger.info(f"   ❌ {result['city']}: {result.get('error', 'Unknown error')}")
    
    # Overall assessment
    logger.info("")
    logger.info("=" * 70)
    
    total_tests = 1 + len(registry_results) + len(multi_city_results)
    passed_tests = (
        (1 if all_results["direct_accela"]["success"] else 0) +
        registry_success +
        multi_success
    )
    
    if passed_tests == total_tests:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("✅ Standardized scrapers are working with real portals")
        logger.info("✅ Registry successfully routes portals to scrapers")
        logger.info("✅ Multiple cities supported")
        logger.info("")
        logger.info("Ready to proceed to Phase 1.4.3!")
    elif passed_tests > 0:
        logger.warning(f"⚠️  {passed_tests}/{total_tests} TESTS PASSED")
        logger.info("=" * 70)
        logger.info("")
        logger.warning("Some tests passed, but review failures above")
        logger.info("Scrapers are functional but may need refinement")
    else:
        logger.error("❌ ALL TESTS FAILED")
        logger.info("=" * 70)
        logger.info("")
        logger.error("Review errors above - scrapers need debugging")
    
    return 0 if passed_tests == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
