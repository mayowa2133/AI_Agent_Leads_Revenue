"""Test script for Phase 1.4.1: Portal Discovery Service."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.signal_engine.discovery.portal_discovery import (
    PortalDiscoveryService,
    PortalType,
)
from src.signal_engine.discovery.portal_storage import PortalStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_portal_discovery():
    """Test portal discovery with a few cities."""
    logger.info("=" * 70)
    logger.info("Phase 1.4.1: Testing Portal Discovery Service")
    logger.info("=" * 70)

    # Test cities (top 10 by population)
    test_cities = [
        "New York",
        "Los Angeles",
        "Chicago",
        "Houston",
        "Phoenix",
        "Philadelphia",
        "San Antonio",
        "San Diego",
        "Dallas",
        "San Jose",
    ]

    discovery = PortalDiscoveryService()

    if not discovery.api_key or not discovery.engine_id:
        logger.warning("=" * 70)
        logger.warning("Google Custom Search API not configured!")
        logger.warning("=" * 70)
        logger.warning("To enable portal discovery:")
        logger.warning("1. Go to https://programmablesearchengine.google.com/")
        logger.warning("2. Create a custom search engine")
        logger.warning("3. Configure to search only .gov domains (optional)")
        logger.warning("4. Get API key from https://console.cloud.google.com/")
        logger.warning("5. Add to .env:")
        logger.warning("   GOOGLE_CUSTOM_SEARCH_API_KEY=your_key")
        logger.warning("   GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_engine_id")
        logger.warning("")
        logger.warning("Testing with mock data instead...")
        return test_with_mock_data()

    logger.info(f"Discovering portals for {len(test_cities)} cities...")
    logger.info("")

    portals = await discovery.discover_portals(
        cities=test_cities,
        max_results_per_city=5,  # Limit per city to stay within free tier
    )

    logger.info("")
    logger.info("=" * 70)
    logger.info("Discovery Results")
    logger.info("=" * 70)
    logger.info(f"Total portals discovered: {len(portals)}")

    # Group by system type
    by_type: dict[PortalType, list] = {}
    for portal in portals:
        if portal.system_type not in by_type:
            by_type[portal.system_type] = []
        by_type[portal.system_type].append(portal)

    logger.info("")
    logger.info("Portals by System Type:")
    for system_type, portal_list in sorted(by_type.items()):
        logger.info(f"  {system_type.value}: {len(portal_list)}")

    # Show top portals
    logger.info("")
    logger.info("Top Portals (by confidence):")
    sorted_portals = sorted(portals, key=lambda p: p.confidence_score, reverse=True)
    for i, portal in enumerate(sorted_portals[:10], 1):
        logger.info(f"  {i}. {portal.city} - {portal.system_type.value}")
        logger.info(f"     URL: {portal.url}")
        logger.info(f"     Confidence: {portal.confidence_score:.2f}")
        logger.info(f"     Title: {portal.title or 'N/A'}")
        logger.info("")

    # Validate a few portals
    logger.info("=" * 70)
    logger.info("Validating Top Portals")
    logger.info("=" * 70)

    for portal in sorted_portals[:5]:
        logger.info(f"Validating: {portal.url}")
        is_valid = await discovery.validate_portal(portal)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        logger.info(f"  {status}")
        logger.info("")

    return portals


def test_with_mock_data():
    """Test with mock data when API is not configured."""
    logger.info("=" * 70)
    logger.info("Mock Portal Discovery Test")
    logger.info("=" * 70)

    from src.signal_engine.discovery.portal_discovery import PortalInfo

    # Mock portals for testing
    mock_portals = [
        PortalInfo(
            url="https://aca-prod.accela.com/COSA/Cap/CapHome.aspx?module=Fire",
            city="San Antonio",
            system_type=PortalType.ACCELA,
            confidence_score=0.9,
            title="San Antonio Fire Permits",
        ),
        PortalInfo(
            url="https://webpermit.mecklenburgcountync.gov/",
            city="Charlotte",
            system_type=PortalType.MECKLENBURG,
            confidence_score=0.95,
            title="Mecklenburg County WebPermit",
        ),
        PortalInfo(
            url="https://aca-prod.accela.com/DAL/Cap/CapHome.aspx?module=Fire",
            city="Dallas",
            system_type=PortalType.ACCELA,
            confidence_score=0.85,
            title="Dallas Building Permits",
        ),
    ]

    logger.info(f"Mock portals: {len(mock_portals)}")
    for portal in mock_portals:
        logger.info(f"  - {portal.city}: {portal.system_type.value} ({portal.url})")

    return mock_portals


async def main():
    """Run portal discovery test."""
    portals = await test_portal_discovery()

    # Save discovered portals
    storage = PortalStorage()
    storage.add_portals(portals)
    storage.save()

    # Show statistics
    stats = storage.get_statistics()
    logger.info("")
    logger.info("=" * 70)
    logger.info("Portal Storage Statistics")
    logger.info("=" * 70)
    logger.info(f"Total portals stored: {stats['total']}")
    logger.info(f"Validated: {stats['validated']}")
    logger.info(f"Unvalidated: {stats['unvalidated']}")
    logger.info("")
    logger.info("Portals by System Type:")
    for system_type, count in sorted(stats["by_system_type"].items()):
        logger.info(f"  {system_type}: {count}")
    logger.info("")
    logger.info("Portals by City:")
    for city, count in sorted(stats["by_city"].items()):
        logger.info(f"  {city}: {count}")

    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Complete!")
    logger.info("=" * 70)
    logger.info(f"Discovered {len(portals)} portals")
    logger.info(f"Saved to: data/discovered_portals.json")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Review discovered portals in data/discovered_portals.json")
    logger.info("2. Validate more portals manually if needed")
    logger.info("3. Add validated portals to scraper registry")
    logger.info("4. Proceed to Phase 1.4.2: Scraper Standardization")


if __name__ == "__main__":
    asyncio.run(main())
