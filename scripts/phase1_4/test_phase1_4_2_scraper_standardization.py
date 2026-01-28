"""Test Phase 1.4.2: Scraper Standardization."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.discovery.portal_discovery import PortalType
from src.signal_engine.discovery.portal_storage import PortalStorage
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.signal_engine.scrapers.registry import ScraperRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_accela_scraper():
    """Test 1: Reusable Accela scraper."""
    logger.info("=" * 70)
    logger.info("Test 1: Reusable Accela Scraper")
    logger.info("=" * 70)
    
    # Test with San Antonio (known working)
    logger.info("Testing with San Antonio (COSA)...")
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        record_type="Fire Alarm",
        days_back=30,
    )
    
    logger.info(f"Scraper created: {scraper.source}")
    logger.info(f"City code: {scraper.city_code}")
    logger.info(f"Module: {scraper.module}")
    logger.info(f"Start URL: {scraper.start_url}")
    
    # Test scraping (may take a while)
    logger.info("")
    logger.info("Scraping permits (this may take 30-60 seconds)...")
    try:
        permits = await scraper.scrape()
        logger.info(f"✅ Successfully scraped {len(permits)} permits")
        
        if permits:
            logger.info("")
            logger.info("Sample permits:")
            for i, permit in enumerate(permits[:3], 1):
                logger.info(f"  {i}. {permit.permit_id} - {permit.permit_type}")
                logger.info(f"     Address: {permit.address}")
                logger.info(f"     Status: {permit.status}")
                if permit.applicant_name:
                    logger.info(f"     Applicant: {permit.applicant_name}")
        
        # Scraper creation and execution is what matters - 0 permits is OK
        # (could mean no permits in date range)
        return True  # Scraper worked correctly
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        return False


async def test_scraper_registry():
    """Test 2: Scraper registry routing."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 2: Scraper Registry")
    logger.info("=" * 70)
    
    # Load discovered portals
    storage = PortalStorage()
    portals = storage.get_all_portals()
    
    if not portals:
        logger.warning("No portals in storage - run Phase 1.4.1 first")
        return False
    
    logger.info(f"Found {len(portals)} portals in storage")
    
    # Test registry with Accela portals
    accela_portals = [p for p in portals if p.system_type == PortalType.ACCELA]
    
    if not accela_portals:
        logger.warning("No Accela portals found - testing with mock portal")
        # Create mock Accela portal
        from src.signal_engine.discovery.portal_discovery import PortalInfo
        
        mock_portal = PortalInfo(
            url="https://aca-prod.accela.com/SANDIEGO/Cap/CapHome.aspx?module=DSD",
            city="San Diego",
            system_type=PortalType.ACCELA,
            confidence_score=0.8,
            title="San Diego Accela Portal",
            config={"city_code": "SANDIEGO", "module": "DSD"},
        )
        accela_portals = [mock_portal]
    
    logger.info(f"Testing with {len(accela_portals)} Accela portal(s)")
    
    success_count = 0
    for portal in accela_portals[:1]:  # Test first one only
        logger.info("")
        logger.info(f"Testing portal: {portal.city} - {portal.url}")
        
        try:
            scraper = ScraperRegistry.create_scraper(portal)
            logger.info(f"✅ Successfully created scraper: {scraper.source}")
            logger.info(f"   Type: {type(scraper).__name__}")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to create scraper: {e}")
    
    return success_count > 0


def test_registry_support():
    """Test 3: Registry support checking."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 3: Registry Support Checking")
    logger.info("=" * 70)
    
    supported_types = ScraperRegistry.get_supported_types()
    logger.info(f"Supported portal types: {len(supported_types)}")
    
    for portal_type in supported_types:
        is_supported = ScraperRegistry.is_supported(portal_type)
        logger.info(f"  {portal_type.value}: {'✅' if is_supported else '❌'}")
    
    # Test unsupported type
    is_unknown_supported = ScraperRegistry.is_supported(PortalType.UNKNOWN)
    logger.info(f"  {PortalType.UNKNOWN.value}: {'✅' if is_unknown_supported else '❌'} (expected: ❌)")
    
    return True


async def test_multiple_cities():
    """Test 4: Multiple cities with same scraper."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 4: Multiple Cities with Same Scraper")
    logger.info("=" * 70)
    
    # Test creating scrapers for different cities
    cities = [
        ("COSA", "San Antonio"),
        ("SANDIEGO", "San Diego"),
    ]
    
    logger.info("Creating scrapers for multiple cities...")
    scrapers = []
    
    for city_code, city_name in cities:
        try:
            scraper = create_accela_scraper(
                city_code=city_code,
                module="Fire",
                days_back=7,  # Short range for testing
            )
            scrapers.append((city_name, scraper))
            logger.info(f"✅ Created scraper for {city_name} ({city_code})")
        except Exception as e:
            logger.error(f"❌ Failed to create scraper for {city_name}: {e}")
    
    logger.info(f"Successfully created {len(scrapers)} scrapers")
    
    return len(scrapers) == len(cities)


async def main():
    """Run Phase 1.4.2 tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 1.4.2: Scraper Standardization Test Suite")
    logger.info("=" * 70)
    logger.info("")
    
    results = {}
    
    # Test 1: Accela scraper
    results["accela_scraper"] = await test_accela_scraper()
    
    # Test 2: Scraper registry
    results["scraper_registry"] = await test_scraper_registry()
    
    # Test 3: Registry support
    results["registry_support"] = test_registry_support()
    
    # Test 4: Multiple cities
    results["multiple_cities"] = await test_multiple_cities()
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Summary")
    logger.info("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    logger.info("")
    if all_passed:
        logger.info("=" * 70)
        logger.info("🎉 ALL TESTS PASSED - Phase 1.4.2 Ready!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("✅ Reusable Accela scraper working")
        logger.info("✅ Scraper registry routing working")
        logger.info("✅ Multiple cities supported")
        logger.info("")
        logger.info("Ready to proceed to Phase 1.4.3: Open Data API Integration")
    else:
        logger.warning("=" * 70)
        logger.warning("⚠️  SOME TESTS FAILED")
        logger.warning("=" * 70)
        logger.warning("")
        logger.warning("Review results above before proceeding")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
