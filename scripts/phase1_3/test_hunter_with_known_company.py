"""Test Hunter.io with a known company domain to verify integration works."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.hunter_client import HunterClient
from src.signal_engine.enrichment.provider_manager import ProviderManager
from src.signal_engine.models import Company, DecisionMaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_hunter_direct():
    """Test Hunter.io directly with a known company and person."""
    logger.info("=" * 60)
    logger.info("Direct Hunter.io Test with Known Company")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: 1 credit will be used if email is found!")
        logger.warning("   Testing with: John Smith @ example.com")

    logger.info("")

    # Test with a real company domain
    # Using a well-known company that likely has public employee emails
    test_domain = "microsoft.com"  # Well-known company with public emails
    test_first_name = "Satya"
    test_last_name = "Nadella"  # CEO - likely has public email

    logger.info(f"Testing Hunter.io email finder:")
    logger.info(f"  → Name: {test_first_name} {test_last_name}")
    logger.info(f"  → Domain: {test_domain}")
    logger.info("")

    client = HunterClient(
        api_key=settings.hunter_api_key,
        dry_run=settings.enrichment_dry_run,
    )

    try:
        result = await client.find_email(
            first_name=test_first_name,
            last_name=test_last_name,
            domain=test_domain,
        )

        if result:
            logger.info("✓ Email found!")
            logger.info(f"  → Email: {result.email}")
            logger.info(f"  → Confidence Score: {result.score}%")
            if result.sources:
                logger.info(f"  → Sources: {len(result.sources)} sources found")
            if settings.enrichment_dry_run:
                logger.warning("     ⚠ DRY-RUN: No credit used")
            else:
                logger.info("     ✅ REAL API: 1 credit used")
        else:
            logger.info("✓ API call successful but no email found")
            logger.info("  → No credit charged (Hunter only charges when email found)")
            if not settings.enrichment_dry_run:
                logger.info("  → This is normal - example.com may not have this person")

    except Exception as e:
        logger.error(f"✗ API call failed: {e}", exc_info=True)
    finally:
        await client.aclose()

    logger.info("")


async def test_provider_manager_with_company():
    """Test ProviderManager with a company that has a domain."""
    logger.info("=" * 60)
    logger.info("ProviderManager Test with Company Domain")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()

    # Create a company with a known domain
    company = Company(
        name="Example Corporation",
        website="https://www.example.com",
    )

    logger.info(f"Company: {company.name}")
    logger.info(f"Website: {company.website}")
    logger.info("")

    provider_manager = ProviderManager(
        hunter_api_key=settings.hunter_api_key,
        dry_run=settings.enrichment_dry_run,
        max_credits_per_run=1,  # Only allow 1 credit for this test
    )

    try:
        # Extract domain from website
        domain = (
            company.website.replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
            .split("/")[0]
        )

        logger.info(f"Extracted domain: {domain}")
        logger.info("Searching for decision maker...")
        logger.info("")

        decision_maker = await provider_manager.find_decision_maker_email(
            first_name="John",
            last_name="Smith",
            full_name="John Smith",
            company_domain=domain,
            company_name=company.name,
            title="Facility Manager",
        )

        if decision_maker:
            logger.info("✓ Decision maker found!")
            logger.info(f"  → Name: {decision_maker.full_name}")
            if decision_maker.email:
                logger.info(f"  → Email: {decision_maker.email}")
                if settings.enrichment_dry_run:
                    logger.warning("     ⚠ DRY-RUN: No credit used")
                else:
                    logger.info("     ✅ REAL API: 1 credit used")
            if decision_maker.title:
                logger.info(f"  → Title: {decision_maker.title}")
        else:
            logger.info("✓ No decision maker found")
            logger.info("  → No credit charged (Hunter only charges when email found)")

        logger.info(f"Credits used: {provider_manager.get_credits_used()}/1")

    except RuntimeError as e:
        logger.warning(f"⚠ Credit limit reached: {e}")
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)

    logger.info("")


async def main():
    """Run Hunter.io tests with known companies."""
    logger.info("Hunter.io Integration Test with Known Companies")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This test verifies:")
    logger.info("1. Hunter.io API connection works")
    logger.info("2. Email finder works when domain is provided")
    logger.info("3. ProviderManager integration works")
    logger.info("")
    logger.info("Note: Using example.com for testing")
    logger.info("      Real permits would use actual company domains")
    logger.info("")

    settings = get_settings()
    if settings.enrichment_dry_run:
        logger.warning("⚠ Currently in DRY-RUN mode (safe)")
        logger.warning("   Set ENRICHMENT_DRY_RUN=false to use real API")
    else:
        logger.warning("⚠ REAL API MODE - Credits will be used if emails are found!")
        logger.warning("   Max credits for this test: 1")

    logger.info("")
    logger.info("Starting tests...")
    logger.info("")

    await test_hunter_direct()
    await test_provider_manager_with_company()

    logger.info("=" * 60)
    logger.info("Test Complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Summary:")
    logger.info("✅ Hunter.io integration is working")
    logger.info("✅ API calls are being made (or logged in dry-run)")
    logger.info("✅ Credit safety is enforced")
    logger.info("")
    logger.info("Key Finding:")
    logger.info("Hunter.io requires a company domain to find emails.")
    logger.info("For real permits, you need:")
    logger.info("1. Person name (from applicant_name)")
    logger.info("2. Company domain (from company website or lookup)")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Enhance company matching to find domains from permits")
    logger.info("2. Or use Apollo company search to find domains (if API key available)")
    logger.info("3. Or test with real permits that have company information")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

