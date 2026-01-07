"""Safe test script for real Hunter.io API with minimal credit usage."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.hunter_client import HunterClient
from src.signal_engine.enrichment.provider_manager import ProviderManager
from src.signal_engine.models import PermitData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_real_api_key():
    """Test that the real API key is configured and working."""
    logger.info("=" * 60)
    logger.info("Testing Real Hunter.io API Key")
    logger.info("=" * 60)

    settings = get_settings()
    hunter_key = settings.hunter_api_key

    if not hunter_key:
        logger.error("✗ HUNTER_API_KEY not found in environment")
        return False

    if hunter_key == "test-api-key":
        logger.warning("⚠ Still using test-api-key. Update .env with your real key.")
        return False

    logger.info(f"✓ API key found: {hunter_key[:10]}...{hunter_key[-4:]}")
    logger.info("")
    return True


async def test_dry_run_first():
    """Test in dry-run mode first to verify configuration."""
    logger.info("=" * 60)
    logger.info("Step 1: Dry-Run Test (Zero Credits)")
    logger.info("=" * 60)

    settings = get_settings()

    # Force dry-run mode for safety
    client = HunterClient(api_key=settings.hunter_api_key, dry_run=True)
    try:
        logger.info("Testing dry-run mode with real API key...")
        result = await client.find_email(
            first_name="John",
            last_name="Doe",
            domain="example.com",
        )
        logger.info("✓ Dry-run test completed (no credits used)")
        logger.info("  → Check logs above to verify URL and params are correct")
    finally:
        await client.aclose()

    logger.info("")


async def test_single_real_call():
    """Make ONE real API call to verify it works."""
    logger.info("=" * 60)
    logger.info("Step 2: Single Real API Call (1 Credit)")
    logger.info("=" * 60)

    settings = get_settings()

    # Use a well-known company for better chance of finding email
    # This is a test - use a real company you know exists
    test_domain = "hunter.io"  # Hunter.io itself - should have public emails
    test_first_name = "Franck"
    test_last_name = "Dupont"  # Hunter.io founder

    logger.info(f"Attempting to find: {test_first_name} {test_last_name} @ {test_domain}")
    logger.warning("⚠ This will use 1 credit if email is found!")
    logger.info("")

    # Disable dry-run for this single test
    client = HunterClient(api_key=settings.hunter_api_key, dry_run=False)
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
            logger.info(f"  → Sources: {len(result.sources or [])} sources found")
            logger.info("")
            logger.info("✅ Real API is working! 1 credit used.")
            return True
        else:
            logger.info("✓ API call successful but no email found (no credit charged)")
            logger.info("  → This is normal - Hunter only charges when email is found")
            return True

    except Exception as e:
        logger.error(f"✗ API call failed: {e}", exc_info=True)
        return False
    finally:
        await client.aclose()

    logger.info("")


async def test_with_real_permit():
    """Test enrichment with a single real permit (safely)."""
    logger.info("=" * 60)
    logger.info("Step 3: Test with Real Permit (1 Credit Max)")
    logger.info("=" * 60)

    settings = get_settings()

    # Create a test permit with a person name
    # Replace with a real permit from your data if available
    permit = PermitData(
        source="test",
        permit_id="TEST-REAL-001",
        permit_type="Fire Alarm",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="John Smith",  # Person name
        issued_date=datetime.now(tz=timezone.utc),
    )

    logger.info(f"Testing permit: {permit.permit_id}")
    logger.info(f"Applicant: {permit.applicant_name}")
    logger.warning("⚠ This will use up to 1 credit if email is found!")
    logger.info("")

    # Use provider manager with credit limit
    provider_manager = ProviderManager(
        hunter_api_key=settings.hunter_api_key,
        dry_run=False,  # Real API call
        max_credits_per_run=1,  # Only allow 1 credit for this test
    )

    try:
        # We need a company with a domain for Hunter to work
        # For this test, we'll use a placeholder domain
        # In real usage, you'd extract domain from company website
        test_domain = "example.com"  # Replace with real domain from permit

        name_parts = permit.applicant_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else None
        last_name = name_parts[1] if len(name_parts) > 1 else None

        decision_maker = await provider_manager.find_decision_maker_email(
            first_name=first_name,
            last_name=last_name,
            full_name=permit.applicant_name,
            company_domain=test_domain,
        )

        if decision_maker and decision_maker.email:
            logger.info("✓ Decision maker found!")
            logger.info(f"  → Name: {decision_maker.full_name}")
            logger.info(f"  → Email: {decision_maker.email}")
            logger.info(f"  → Credits used: {provider_manager.get_credits_used()}/1")
        else:
            logger.info("✓ No email found (no credit charged)")
            logger.info(f"  → Credits used: {provider_manager.get_credits_used()}/1")

    except RuntimeError as e:
        logger.warning(f"Credit limit reached: {e}")
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)

    logger.info("")


async def main():
    """Run safe real API tests."""
    logger.info("Hunter.io Real API Test - Safe Mode")
    logger.info("=" * 60)
    logger.info("")

    # Step 1: Verify API key
    if not await test_real_api_key():
        logger.error("Please configure your API key in .env first")
        return

    # Step 2: Dry-run test (zero credits)
    await test_dry_run_first()

    # Ask user if they want to proceed with real calls
    logger.info("=" * 60)
    logger.info("Ready for Real API Test")
    logger.info("=" * 60)
    logger.info("Next steps will use real credits:")
    logger.info("  - Step 2: 1 credit (single API call)")
    logger.info("  - Step 3: 1 credit max (permit enrichment)")
    logger.info("")
    logger.info("Total potential credits: 2 credits")
    logger.info("")
    logger.info("Proceeding with real API tests...")
    logger.info("")

    # Step 3: Single real call
    success = await test_single_real_call()

    if success:
        # Step 4: Test with permit (optional)
        # Uncomment to test with a real permit
        # await test_with_real_permit()
        pass

    logger.info("=" * 60)
    logger.info("Test Complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Check Hunter.io dashboard for credit usage")
    logger.info("2. If successful, you can now use enrichment in production")
    logger.info("3. Remember: MAX_CREDITS_PER_RUN=3 is still enforced")
    logger.info("4. Scheduler will auto-slice permits to credit limit")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

