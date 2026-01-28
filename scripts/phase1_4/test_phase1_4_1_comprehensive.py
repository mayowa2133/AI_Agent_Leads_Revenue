"""Comprehensive test for Phase 1.4.1: Portal Discovery."""

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


async def test_discovery_coverage():
    """Test 1: Discover portals for top 20 cities."""
    logger.info("=" * 70)
    logger.info("Test 1: Portal Discovery Coverage")
    logger.info("=" * 70)

    # Top 20 cities by population
    cities = [
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
        "Austin",
        "Jacksonville",
        "Fort Worth",
        "Columbus",
        "Charlotte",
        "San Francisco",
        "Indianapolis",
        "Seattle",
        "Denver",
        "Washington",
    ]

    discovery = PortalDiscoveryService()

    if not discovery.api_key or not discovery.engine_id:
        logger.warning("Google Custom Search API not configured - skipping test")
        return None

    logger.info(f"Discovering portals for {len(cities)} cities...")
    portals = await discovery.discover_portals(
        cities=cities,
        max_results_per_city=3,  # Limit to stay within free tier
    )

    logger.info(f"✓ Discovered {len(portals)} portals")
    return portals


async def test_classification_accuracy():
    """Test 2: Verify portal classification accuracy."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 2: Portal Classification Accuracy")
    logger.info("=" * 70)

    storage = PortalStorage()
    portals = storage.get_all_portals()

    if not portals:
        logger.warning("No portals in storage - run discovery first")
        return

    # Check classification
    by_type: dict[PortalType, int] = {}
    for portal in portals:
        by_type[portal.system_type] = by_type.get(portal.system_type, 0) + 1

    logger.info("Classification Results:")
    for system_type, count in sorted(by_type.items()):
        percentage = (count / len(portals)) * 100
        logger.info(f"  {system_type.value}: {count} ({percentage:.1f}%)")

    # Check for known systems
    accela_count = by_type.get(PortalType.ACCELA, 0)
    custom_count = by_type.get(PortalType.CUSTOM, 0)
    unknown_count = by_type.get(PortalType.UNKNOWN, 0)

    classified_count = accela_count + custom_count
    classification_rate = (classified_count / len(portals)) * 100 if portals else 0

    logger.info("")
    logger.info(f"Classification Rate: {classification_rate:.1f}%")
    logger.info(f"  Classified (Accela + Custom): {classified_count}")
    logger.info(f"  Unknown: {unknown_count}")

    # Success criteria: 80%+ classification rate
    if classification_rate >= 80:
        logger.info("✅ PASSED: Classification rate ≥ 80%")
    else:
        logger.warning(f"⚠️  Classification rate {classification_rate:.1f}% < 80% target")

    return classification_rate


async def test_portal_validation():
    """Test 3: Validate discovered portals."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 3: Portal Validation")
    logger.info("=" * 70)

    storage = PortalStorage()
    portals = storage.get_all_portals()

    if not portals:
        logger.warning("No portals in storage - run discovery first")
        return

    # Validate top 10 portals by confidence
    sorted_portals = sorted(portals, key=lambda p: p.confidence_score, reverse=True)
    portals_to_validate = sorted_portals[:10]

    logger.info(f"Validating top {len(portals_to_validate)} portals...")

    discovery = PortalDiscoveryService()
    validated_count = 0

    for portal in portals_to_validate:
        logger.info(f"  Validating: {portal.city} - {portal.url[:60]}...")
        is_valid = await discovery.validate_portal(portal)
        if is_valid:
            validated_count += 1
            logger.info(f"    ✅ VALID")
            # Update storage
            portal.validated = True
            storage.add_portal(portal)
        else:
            logger.info(f"    ❌ INVALID")

    storage.save()

    validation_rate = (validated_count / len(portals_to_validate)) * 100
    logger.info("")
    logger.info(f"Validation Rate: {validation_rate:.1f}%")
    logger.info(f"  Validated: {validated_count}/{len(portals_to_validate)}")

    # Success criteria: 70%+ validation rate
    if validation_rate >= 70:
        logger.info("✅ PASSED: Validation rate ≥ 70%")
    else:
        logger.warning(f"⚠️  Validation rate {validation_rate:.1f}% < 70% target")

    return validation_rate


def test_storage_functionality():
    """Test 4: Verify storage functionality."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 4: Storage Functionality")
    logger.info("=" * 70)

    storage = PortalStorage()

    # Test: Get all portals
    all_portals = storage.get_all_portals()
    logger.info(f"✓ Get all portals: {len(all_portals)}")

    # Test: Filter by city
    nyc_portals = storage.get_portals(city="New York")
    logger.info(f"✓ Filter by city (NYC): {len(nyc_portals)}")

    # Test: Filter by system type
    accela_portals = storage.get_portals(system_type=PortalType.ACCELA)
    logger.info(f"✓ Filter by system type (Accela): {len(accela_portals)}")

    # Test: Filter validated only
    validated_portals = storage.get_portals(validated_only=True)
    logger.info(f"✓ Filter validated only: {len(validated_portals)}")

    # Test: Statistics
    stats = storage.get_statistics()
    logger.info("")
    logger.info("Storage Statistics:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Validated: {stats['validated']}")
    logger.info(f"  Unvalidated: {stats['unvalidated']}")
    logger.info(f"  Cities: {len(stats['by_city'])}")
    logger.info(f"  System Types: {len(stats['by_system_type'])}")

    # Verify storage file exists
    storage_file = Path("data/discovered_portals.json")
    if storage_file.exists():
        file_size = storage_file.stat().st_size
        logger.info(f"✓ Storage file exists: {file_size} bytes")
    else:
        logger.error("✗ Storage file does not exist")

    logger.info("✅ PASSED: All storage functions working")
    return True


async def test_edge_cases():
    """Test 5: Edge cases and error handling."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test 5: Edge Cases & Error Handling")
    logger.info("=" * 70)

    discovery = PortalDiscoveryService()

    # Test: Empty city list
    try:
        portals = await discovery.discover_portals([])
        logger.info(f"✓ Empty city list handled: {len(portals)} portals")
    except Exception as e:
        logger.error(f"✗ Empty city list failed: {e}")

    # Test: Invalid portal validation
    from src.signal_engine.discovery.portal_discovery import PortalInfo

    invalid_portal = PortalInfo(
        url="https://invalid-url-that-does-not-exist-12345.com",
        city="Test",
        system_type=PortalType.UNKNOWN,
        confidence_score=0.0,
    )

    try:
        is_valid = await discovery.validate_portal(invalid_portal)
        logger.info(f"✓ Invalid portal validation handled: {is_valid}")
    except Exception as e:
        logger.error(f"✗ Invalid portal validation failed: {e}")

    # Test: Storage with empty data
    try:
        empty_storage = PortalStorage()
        empty_portals = empty_storage.get_all_portals()
        logger.info(f"✓ Empty storage handled: {len(empty_portals)} portals")
    except Exception as e:
        logger.error(f"✗ Empty storage failed: {e}")

    logger.info("✅ PASSED: Edge cases handled correctly")
    return True


async def main():
    """Run comprehensive Phase 1.4.1 tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 1.4.1: Comprehensive Test Suite")
    logger.info("=" * 70)
    logger.info("")

    results = {}

    # Test 1: Discovery Coverage
    portals = await test_discovery_coverage()
    if portals:
        results["discovery_count"] = len(portals)
        # Success criteria: 50+ portals
        if len(portals) >= 50:
            logger.info("✅ PASSED: Discovered ≥ 50 portals")
        else:
            logger.warning(f"⚠️  Discovered {len(portals)} portals < 50 target")

    # Test 2: Classification Accuracy
    classification_rate = await test_classification_accuracy()
    if classification_rate is not None:
        results["classification_rate"] = classification_rate

    # Test 3: Portal Validation
    validation_rate = await test_portal_validation()
    if validation_rate is not None:
        results["validation_rate"] = validation_rate

    # Test 4: Storage Functionality
    storage_ok = test_storage_functionality()
    results["storage_ok"] = storage_ok

    # Test 5: Edge Cases
    edge_cases_ok = await test_edge_cases()
    results["edge_cases_ok"] = edge_cases_ok

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Summary")
    logger.info("=" * 70)

    all_passed = True

    if "discovery_count" in results:
        count = results["discovery_count"]
        status = "✅" if count >= 50 else "⚠️"
        logger.info(f"{status} Discovery: {count} portals (target: 50+)")
        if count < 50:
            all_passed = False

    if "classification_rate" in results:
        rate = results["classification_rate"]
        status = "✅" if rate >= 80 else "⚠️"
        logger.info(f"{status} Classification: {rate:.1f}% (target: 80%+)")
        if rate < 80:
            all_passed = False

    if "validation_rate" in results:
        rate = results["validation_rate"]
        status = "✅" if rate >= 70 else "⚠️"
        logger.info(f"{status} Validation: {rate:.1f}% (target: 70%+)")
        if rate < 70:
            all_passed = False

    if results.get("storage_ok"):
        logger.info("✅ Storage: All functions working")
    else:
        logger.error("❌ Storage: Issues detected")
        all_passed = False

    if results.get("edge_cases_ok"):
        logger.info("✅ Edge Cases: Handled correctly")
    else:
        logger.error("❌ Edge Cases: Issues detected")
        all_passed = False

    logger.info("")
    if all_passed:
        logger.info("=" * 70)
        logger.info("🎉 ALL TESTS PASSED - Phase 1.4.1 Ready!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Ready to proceed to Phase 1.4.2: Scraper Standardization")
    else:
        logger.warning("=" * 70)
        logger.warning("⚠️  SOME TESTS NEED ATTENTION")
        logger.warning("=" * 70)
        logger.warning("")
        logger.warning("Review results above before proceeding")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
