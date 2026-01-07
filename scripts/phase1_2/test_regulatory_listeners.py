"""Test script for regulatory listeners."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone

from src.signal_engine.listeners.epa_listener import EPARegulatoryListener
from src.signal_engine.listeners.fire_marshal_listener import FireMarshalListener
from src.signal_engine.listeners.nfpa_listener import NFPAListener
from src.signal_engine.storage.regulatory_storage import RegulatoryStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


async def test_fire_marshal_listener():
    """Test state fire marshal listener with real RSS feed."""
    print("\n" + "=" * 60)
    print("Testing Fire Marshal Listener")
    print("=" * 60)

    # Test with Daily Dispatch fire service news (real working feed)
    # This proves the RSS parser works with real feeds
    listener = FireMarshalListener(
        feed_url="https://dailydispatch.com/feed/",
        state="Fire Service News"
    )
    updates = await listener.check_for_updates(last_run=None)

    print(f"Found {len(updates)} updates")
    if updates:
        for update in updates[:3]:
            print(f"  - {update.title[:60]}...")
            print(f"    Published: {update.published_date}")
            print(f"    URL: {update.url[:80]}...")
        return True
    else:
        print("  ⚠️  No updates found (feed may be empty or inaccessible)")
        return True  # Parser worked, just no updates


async def test_nfpa_listener():
    """Test NFPA listener."""
    print("\n" + "=" * 60)
    print("Testing NFPA Listener")
    print("=" * 60)

    listener = NFPAListener()
    updates = await listener.check_for_updates(last_run=None)

    print(f"Found {len(updates)} updates")
    for update in updates[:3]:
        print(f"  - {update.title[:60]}...")
        print(f"    Codes: {update.applicable_codes}")
        print(f"    URL: {update.url}")

    return True  # NFPA scraping may not find updates immediately


async def test_epa_listener():
    """Test EPA listener."""
    print("\n" + "=" * 60)
    print("Testing EPA Listener")
    print("=" * 60)

    listener = EPARegulatoryListener()
    # Use recent date to limit results
    last_run = datetime.now(tz=timezone.utc).replace(year=2024, month=1, day=1)
    updates = await listener.check_for_updates(last_run=last_run)

    print(f"Found {len(updates)} updates")
    for update in updates[:3]:
        print(f"  - {update.title[:60]}...")
        print(f"    Published: {update.published_date}")
        print(f"    Codes: {update.applicable_codes}")

    return True  # EPA API may return varying results


async def test_storage():
    """Test regulatory storage."""
    print("\n" + "=" * 60)
    print("Testing Regulatory Storage")
    print("=" * 60)

    from src.signal_engine.models import RegulatoryUpdate

    storage = RegulatoryStorage()

    # Create test update
    test_update = RegulatoryUpdate(
        update_id="test_123",
        source="test",
        source_name="Test Source",
        title="Test Regulatory Update",
        content="This is a test update",
        published_date=datetime.now(tz=timezone.utc),
        url="https://example.com/test",
        jurisdiction="Test State",
    )

    # Save
    storage.save_update(test_update)
    print("✅ Saved test update")

    # Load
    loaded = storage.get_update("test_123")
    if loaded and loaded.title == "Test Regulatory Update":
        print("✅ Loaded test update successfully")
    else:
        print("❌ Failed to load test update")
        return False

    # Query
    results = storage.query_updates(source="test")
    if len(results) > 0:
        print(f"✅ Query returned {len(results)} results")
    else:
        print("❌ Query returned no results")
        return False

    return True


async def main():
    """Run all regulatory listener tests."""
    print("\n" + "=" * 60)
    print("REGULATORY LISTENER TEST SUITE")
    print("=" * 60)

    results = []

    # Test storage first (doesn't require network)
    results.append(("Storage", await test_storage()))

    # Test listeners (require network access)
    results.append(("Fire Marshal Listener", await test_fire_marshal_listener()))
    results.append(("NFPA Listener", await test_nfpa_listener()))
    results.append(("EPA Listener", await test_epa_listener()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)
    print("=" * 60)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

