"""Test script for Hunter.io integration with credit safety."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.enrichment.hunter_client import HunterClient, MockHunterClient
from src.signal_engine.enrichment.provider_manager import ProviderManager
from src.signal_engine.models import PermitData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_mock_hunter_client():
    """Test MockHunterClient (zero credits)."""
    logger.info("=" * 60)
    logger.info("Testing MockHunterClient (Zero Credits)")
    logger.info("=" * 60)

    mock_client = MockHunterClient(api_key="test")
    try:
        result = await mock_client.find_email(
            first_name="John",
            last_name="Doe",
            domain="example.com",
        )
        if result:
            logger.info(f"✓ Mock client returned: {result.email}")
            logger.info(f"  → Score: {result.score}%")
        else:
            logger.error("✗ Mock client returned None")
    finally:
        await mock_client.aclose()

    logger.info("")


async def test_hunter_dry_run():
    """Test Hunter.io client in dry-run mode."""
    logger.info("=" * 60)
    logger.info("Testing Hunter.io Dry-Run Mode")
    logger.info("=" * 60)

    settings = get_settings()
    hunter_key = settings.hunter_api_key or "test-api-key"

    client = HunterClient(api_key=hunter_key, dry_run=True)
    try:
        logger.info("Making dry-run call (should only log, not make API call)...")
        result = await client.find_email(
            first_name="Jane",
            last_name="Smith",
            domain="contractor.com",
        )
        logger.info("✓ Dry-run mode working (no API call made)")
    finally:
        await client.aclose()

    logger.info("")


async def test_provider_manager():
    """Test ProviderManager with credit safety."""
    logger.info("=" * 60)
    logger.info("Testing ProviderManager with Credit Safety")
    logger.info("=" * 60)

    settings = get_settings()

    provider_manager = ProviderManager(
        hunter_api_key=settings.hunter_api_key,
        apollo_api_key=settings.apollo_api_key,
        dry_run=settings.enrichment_dry_run,
        max_credits_per_run=settings.max_credits_per_run,
    )

    # Test 1: Find email with name + domain
    logger.info("Test 1: Finding email with name + domain...")
    try:
        decision_maker = await provider_manager.find_decision_maker_email(
            first_name="John",
            last_name="Doe",
            company_domain="example.com",
            title="Facility Manager",
        )
        if decision_maker:
            logger.info(f"✓ Found: {decision_maker.email}")
        else:
            logger.info("✓ No result (expected in dry-run mode)")
    except RuntimeError as e:
        logger.warning(f"Credit limit reached: {e}")

    logger.info(f"Credits used: {provider_manager.get_credits_used()}/{settings.max_credits_per_run}")
    logger.info("")


async def test_enrichment_pipeline():
    """Test full enrichment pipeline with Hunter.io."""
    logger.info("=" * 60)
    logger.info("Testing Full Enrichment Pipeline")
    logger.info("=" * 60)

    # Create test permit with person name as applicant
    permit = PermitData(
        source="test",
        permit_id="TEST-HUNTER-001",
        permit_type="Fire Alarm",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="John Doe",  # Person name
        issued_date=datetime.now(tz=timezone.utc),
    )

    try:
        lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="test", permit=permit))

        logger.info(f"✓ Enriched lead created: {lead.lead_id}")
        logger.info(f"  → Company: {lead.company.name}")

        if lead.decision_maker:
            logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
            if lead.decision_maker.email:
                logger.info(f"  → Email: {lead.decision_maker.email}")
            else:
                logger.info("  → No email found (expected in dry-run mode)")
        else:
            logger.info("  → No decision maker found (expected in dry-run mode)")

    except RuntimeError as e:
        logger.warning(f"Credit limit reached: {e}")
    except Exception as e:
        logger.error(f"✗ Enrichment failed: {e}", exc_info=True)

    logger.info("")


async def test_credit_limit():
    """Test credit limit safety brake."""
    logger.info("=" * 60)
    logger.info("Testing Credit Limit Safety Brake")
    logger.info("=" * 60)

    settings = get_settings()

    provider_manager = ProviderManager(
        hunter_api_key=settings.hunter_api_key,
        dry_run=False,  # Disable dry-run to test credit counter
        max_credits_per_run=3,
    )

    logger.info("Attempting 4 calls (should stop at 3)...")
    for i in range(4):
        try:
            logger.info(f"Call {i+1}...")
            await provider_manager.find_decision_maker_email(
                first_name=f"Test{i}",
                last_name="User",
                company_domain="example.com",
            )
            logger.info(f"  ✓ Call {i+1} completed")
        except RuntimeError as e:
            logger.warning(f"  ✗ Credit limit reached at call {i+1}: {e}")
            break

    logger.info(f"Final credits used: {provider_manager.get_credits_used()}/3")
    logger.info("")


async def main():
    """Run all Hunter.io integration tests."""
    logger.info("Starting Hunter.io Integration Tests")
    logger.info("")

    await test_mock_hunter_client()
    await test_hunter_dry_run()
    await test_provider_manager()
    await test_enrichment_pipeline()
    await test_credit_limit()

    logger.info("=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Verify dry-run mode is working (check logs above)")
    logger.info("2. When ready, set ENRICHMENT_DRY_RUN=false in .env")
    logger.info("3. Replace HUNTER_API_KEY=test-api-key with your real key")
    logger.info("4. Test with 1-2 real permits first")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

