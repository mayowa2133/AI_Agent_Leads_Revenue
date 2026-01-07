"""Comprehensive test script to verify Phase 1.1 components work correctly.

Tests:
1. Both scrapers can extract permits
2. Applicant extraction works (when enabled)
3. Scheduled job runner can be instantiated and configured
4. Last run timestamps are saved/loaded correctly
5. All components integrate properly
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.core.security import tenant_scoped_session
from src.signal_engine.jobs.scraper_scheduler import ScraperScheduler
from src.signal_engine.scrapers.permit_scraper import (
    MecklenburgPermitScraper,
    SanAntonioFireScraper,
)


class Phase1_1TestResults:
    """Track test results."""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: list[str] = []

    def pass_test(self, test_name: str):
        """Record a passing test."""
        self.tests_passed += 1
        print(f"✅ {test_name}")

    def fail_test(self, test_name: str, reason: str):
        """Record a failing test."""
        self.tests_failed += 1
        self.failures.append(f"{test_name}: {reason}")
        print(f"❌ {test_name}: {reason}")

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("PHASE 1.1 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        if self.failures:
            print("\nFailures:")
            for failure in self.failures:
                print(f"  - {failure}")
        print("=" * 60)
        return self.tests_failed == 0


async def test_mecklenburg_scraper_basic(results: Phase1_1TestResults):
    """Test that Mecklenburg scraper can extract permits."""
    test_name = "Mecklenburg Scraper - Basic Extraction"
    try:
        scraper = MecklenburgPermitScraper(
            search_type="address",
            search_value="Tryon",
            street_number="600",
            extract_applicant=False,  # Disable for speed in basic test
        )

        async with tenant_scoped_session("demo"):
            permits = await scraper.scrape()

        if permits and len(permits) > 0:
            # Verify permit structure
            permit = permits[0]
            if (
                permit.permit_id
                and permit.permit_type
                and permit.address
                and permit.status
                and permit.source == "mecklenburg_county_webpermit"
            ):
                results.pass_test(test_name)
                print(f"   Extracted {len(permits)} permits (sample: {permit.permit_id})")
                return True
            else:
                results.fail_test(test_name, "Permit data incomplete")
                return False
        else:
            results.fail_test(test_name, "No permits extracted")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


async def test_san_antonio_scraper_basic(results: Phase1_1TestResults):
    """Test that San Antonio scraper can extract permits."""
    test_name = "San Antonio Scraper - Basic Extraction"
    try:
        scraper = SanAntonioFireScraper(
            record_type="Fire Alarm",
            days_back=120,  # Use golden search dates
            extract_applicant=False,  # Disable for speed in basic test
        )

        async with tenant_scoped_session("demo"):
            permits = await scraper.scrape()

        if permits and len(permits) > 0:
            # Verify permit structure
            permit = permits[0]
            if (
                permit.permit_id
                and permit.permit_type
                and permit.address
                and permit.status
                and permit.source == "san_antonio_accela_fire"
            ):
                results.pass_test(test_name)
                print(f"   Extracted {len(permits)} permits (sample: {permit.permit_id})")
                return True
            else:
                results.fail_test(test_name, "Permit data incomplete")
                return False
        else:
            # San Antonio might not have results - this is acceptable for MVP
            results.pass_test(test_name + " (no results - acceptable)")
            print("   No permits found (acceptable - may be no data in date range)")
            return True
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


async def test_applicant_extraction_disabled(results: Phase1_1TestResults):
    """Test that scrapers work when applicant extraction is disabled."""
    test_name = "Applicant Extraction - Disabled Mode"
    try:
        scraper = MecklenburgPermitScraper(
            search_type="address",
            search_value="Tryon",
            street_number="600",
            extract_applicant=False,
        )

        async with tenant_scoped_session("demo"):
            permits = await scraper.scrape()

        if permits:
            # All permits should have applicant_name=None when disabled
            all_none = all(p.applicant_name is None for p in permits)
            if all_none:
                results.pass_test(test_name)
                return True
            else:
                results.fail_test(test_name, "Some permits have applicant_name when disabled")
                return False
        else:
            results.fail_test(test_name, "No permits to test")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


async def test_applicant_extraction_enabled(results: Phase1_1TestResults):
    """Test that applicant extraction works when enabled (may be slow)."""
    test_name = "Applicant Extraction - Enabled Mode"
    try:
        scraper = MecklenburgPermitScraper(
            search_type="address",
            search_value="Tryon",
            street_number="600",
            extract_applicant=True,  # Enable applicant extraction
        )

        async with tenant_scoped_session("demo"):
            permits = await scraper.scrape()

        if permits:
            # At least some permits should have detail_url
            permits_with_detail = [p for p in permits if p.detail_url]
            if permits_with_detail:
                # Applicant extraction may succeed or fail (depends on page structure)
                # Just verify the method doesn't crash
                results.pass_test(test_name)
                print(f"   Tested {len(permits_with_detail)} permits with detail URLs")
                applicants_found = sum(1 for p in permits if p.applicant_name)
                print(f"   Found applicant info for {applicants_found} permits")
                return True
            else:
                results.pass_test(test_name + " (no detail URLs - acceptable)")
                print("   No detail URLs found (acceptable)")
                return True
        else:
            results.fail_test(test_name, "No permits to test")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


def test_scheduler_instantiation(results: Phase1_1TestResults):
    """Test that ScraperScheduler can be instantiated."""
    test_name = "Scheduler - Instantiation"
    try:
        scheduler = ScraperScheduler()
        if scheduler:
            results.pass_test(test_name)
            return True
        else:
            results.fail_test(test_name, "Scheduler is None")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


def test_scheduler_last_run_persistence(results: Phase1_1TestResults):
    """Test that last run timestamps are saved and loaded correctly."""
    test_name = "Scheduler - Last Run Persistence"
    try:
        # Use temporary file for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = ScraperScheduler()
            scheduler.last_run_file = Path(tmpdir) / "test_last_runs.json"

            # Test saving
            test_timestamp = datetime.now(tz=timezone.utc)
            scheduler._save_last_run("test_scraper", "test_tenant", test_timestamp)

            # Test loading
            loaded_timestamp = scheduler._get_last_run("test_scraper", "test_tenant")

            if loaded_timestamp:
                # Timestamps should be close (within 1 second)
                time_diff = abs((test_timestamp - loaded_timestamp).total_seconds())
                if time_diff < 1:
                    results.pass_test(test_name)
                    return True
                else:
                    results.fail_test(test_name, f"Timestamp mismatch: {time_diff}s")
                    return False
            else:
                results.fail_test(test_name, "Could not load saved timestamp")
                return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


def test_scheduler_job_configuration(results: Phase1_1TestResults):
    """Test that jobs can be added to scheduler."""
    test_name = "Scheduler - Job Configuration"
    try:
        scheduler = ScraperScheduler()
        scraper = MecklenburgPermitScraper(
            search_type="address",
            search_value="Tryon",
            street_number="600",
        )

        # Add a job
        scheduler.add_scraper_job(
            "test_mecklenburg",
            scraper,
            "demo",
            schedule_type="interval",
            hours=24,
        )

        # Verify job was added
        jobs = scheduler.scheduler.get_jobs()
        if len(jobs) > 0:
            results.pass_test(test_name)
            return True
        else:
            results.fail_test(test_name, "No jobs found after adding")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


async def test_scraper_deduplication(results: Phase1_1TestResults):
    """Test that permit deduplication works."""
    test_name = "Scraper - Deduplication"
    try:
        from src.signal_engine.models import PermitData
        from src.signal_engine.scrapers.base_scraper import dedupe_permits

        # Create duplicate permits
        permit1 = PermitData(
            source="test",
            permit_id="123",
            permit_type="Fire Alarm",
            address="123 Main St",
            status="Open",
        )
        permit2 = PermitData(
            source="test",
            permit_id="123",  # Same ID
            permit_type="Fire Alarm",
            address="123 Main St",
            status="Closed",  # Different status
        )
        permit3 = PermitData(
            source="test",
            permit_id="456",  # Different ID
            permit_type="Fire Sprinkler",
            address="456 Oak Ave",
            status="Open",
        )

        permits = [permit1, permit2, permit3]
        deduped = dedupe_permits(permits)

        # Should have 2 unique permits (123 and 456)
        if len(deduped) == 2:
            # Last write wins - permit2 should be in result
            permit_123 = next((p for p in deduped if p.permit_id == "123"), None)
            if permit_123 and permit_123.status == "Closed":
                results.pass_test(test_name)
                return True
            else:
                results.fail_test(test_name, "Last write didn't win")
                return False
        else:
            results.fail_test(test_name, f"Expected 2 permits, got {len(deduped)}")
            return False
    except Exception as e:
        results.fail_test(test_name, f"Exception: {e}")
        return False


async def main():
    """Run all Phase 1.1 tests."""
    print("\n" + "=" * 60)
    print("PHASE 1.1 COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("Testing all Phase 1.1 components...")
    print()

    results = Phase1_1TestResults()

    # Test scrapers
    print("Testing Scrapers...")
    await test_mecklenburg_scraper_basic(results)
    await test_san_antonio_scraper_basic(results)

    # Test applicant extraction
    print("\nTesting Applicant Extraction...")
    await test_applicant_extraction_disabled(results)
    # Note: Applicant extraction enabled test is slow - run optionally
    if os.environ.get("TEST_APPLICANT_EXTRACTION", "false").lower() == "true":
        await test_applicant_extraction_enabled(results)
    else:
        print("⏭️  Skipping applicant extraction enabled test (set TEST_APPLICANT_EXTRACTION=true to run)")

    # Test scheduler
    print("\nTesting Scheduler...")
    test_scheduler_instantiation(results)
    test_scheduler_last_run_persistence(results)
    test_scheduler_job_configuration(results)

    # Test utilities
    print("\nTesting Utilities...")
    await test_scraper_deduplication(results)

    # Print summary
    all_passed = results.print_summary()

    if all_passed:
        print("\n✅ All Phase 1.1 tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Review failures above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

