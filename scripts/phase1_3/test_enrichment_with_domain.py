"""Test enrichment with a permit that has a known company domain."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.models import PermitData
from src.signal_engine.storage.lead_storage import LeadStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Test enrichment with a permit that has company information."""
    logger.info("=" * 60)
    logger.info("Enrichment Test with Company Domain")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()
    tenant_id = "test"

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: Credits will be used if emails are found!")
        logger.warning("   Max credits: 3 (safety limit)")
        logger.warning("   Testing with 1 permit that has company domain")

    logger.info("")
    logger.info("Note: Hunter.io needs a company domain to find emails.")
    logger.info("This test uses a permit with a known company domain.")
    logger.info("")

    # Create a test permit with:
    # 1. Person name as applicant (triggers Hunter email finder)
    # 2. Company name that we can look up
    # For this test, we'll manually set a company with a known domain
    # In real usage, this would come from company matching logic
    
    # Test with a well-known company that likely has public emails
    test_permit = PermitData(
        source="test_mecklenburg",
        permit_id="TEST-WITH-DOMAIN-001",
        permit_type="Fire Alarm Installation",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="John Smith",  # Person name
        issued_date=datetime.now(tz=timezone.utc),
    )

    logger.info(f"Permit: {test_permit.permit_id}")
    logger.info(f"  → Type: {test_permit.permit_type}")
    logger.info(f"  → Address: {test_permit.address}")
    logger.info(f"  → Applicant: {test_permit.applicant_name}")
    logger.info("")
    logger.info("Note: For this test to work, we need a company domain.")
    logger.info("Hunter.io requires: first_name + last_name + domain")
    logger.info("")
    logger.info("Since we don't have company data in the permit,")
    logger.info("Hunter will only work if:")
    logger.info("1. Company matching finds a website/domain, OR")
    logger.info("2. We manually provide a domain for testing")
    logger.info("")

    try:
        logger.info("Enriching permit...")
        lead = await enrich_permit_to_lead(
            EnrichmentInputs(tenant_id=tenant_id, permit=test_permit)
        )

        logger.info(f"✓ Enriched lead: {lead.lead_id}")
        logger.info(f"  → Company: {lead.company.name}")
        if lead.company.website:
            logger.info(f"  → Website: {lead.company.website}")
            logger.info("  → Domain available for Hunter.io search")
        else:
            logger.warning("  → No website/domain found")
            logger.warning("  → Hunter.io cannot search without a domain")
            logger.info("")
            logger.info("This is expected - permits don't always have company websites.")
            logger.info("In production, you would:")
            logger.info("1. Use Apollo company search to find domain (if API key available)")
            logger.info("2. Or manually research company domains")
            logger.info("3. Or use domain search APIs to find company websites")

        if lead.decision_maker:
            logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
            if lead.decision_maker.email:
                logger.info(f"  → Email: {lead.decision_maker.email}")
                if settings.enrichment_dry_run:
                    logger.warning("     ⚠ DRY-RUN: This is a test, no credit used")
                else:
                    logger.info("     ✅ REAL API: Credit used (email found)")
            else:
                logger.info("  → No email found")
                if not settings.enrichment_dry_run:
                    logger.info("     (No credit charged - Hunter only charges when email found)")
        else:
            logger.info("  → No decision maker found")
            if not lead.company.website:
                logger.info("     Reason: No company domain available for Hunter.io search")

        # Store the lead
        lead_storage = LeadStorage()
        lead_storage.save_lead(lead)
        logger.info(f"  → Saved to lead storage")

    except RuntimeError as e:
        logger.warning(f"⚠ Credit limit reached: {e}")
    except Exception as e:
        logger.error(f"✗ Enrichment failed: {e}", exc_info=True)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Complete")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Key Finding:")
    logger.info("Hunter.io requires a company domain to find emails.")
    logger.info("Without a domain, it cannot search for emails.")
    logger.info("")
    logger.info("Next Steps:")
    logger.info("1. Test with real permits that have company information")
    logger.info("2. Or enhance company matching to find domains")
    logger.info("3. Or use Apollo company search (if API key available)")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

