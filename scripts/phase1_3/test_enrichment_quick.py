"""Quick test with sample permits that have applicant names."""

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
    """Test enrichment with sample permits that have applicant names."""
    logger.info("=" * 60)
    logger.info("Quick Enrichment Test with Sample Permits")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()
    tenant_id = "test"

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: Credits will be used if emails are found!")
        logger.warning("   Max credits: 3 (safety limit)")
        logger.warning("   Only testing 2 permits")

    logger.info("")

    # Create sample permits with applicant names (person names)
    # These simulate real permits that would have person names as applicants
    test_permits = [
        PermitData(
            source="test_mecklenburg",
            permit_id="TEST-001",
            permit_type="Fire Alarm Installation",
            address="600 Tryon St, Charlotte, NC 28202",
            building_type="Commercial Office",
            status="Issued",
            applicant_name="John Smith",  # Person name - will trigger Hunter email finder
            issued_date=datetime.now(tz=timezone.utc),
        ),
        PermitData(
            source="test_mecklenburg",
            permit_id="TEST-002",
            permit_type="Sprinkler System",
            address="100 W Houston St, San Antonio, TX 78205",
            building_type="Retail",
            status="Issued",
            applicant_name="Jane Doe",  # Person name - will trigger Hunter email finder
            issued_date=datetime.now(tz=timezone.utc),
        ),
    ]

    logger.info(f"Testing with {len(test_permits)} sample permits")
    logger.info("")

    enriched_leads = []
    lead_storage = LeadStorage()

    for i, permit in enumerate(test_permits, 1):
        logger.info(f"Permit {i}/{len(test_permits)}: {permit.permit_id}")
        logger.info(f"  → Type: {permit.permit_type}")
        logger.info(f"  → Address: {permit.address}")
        logger.info(f"  → Applicant: {permit.applicant_name}")
        logger.info("")

        try:
            logger.info(f"  Enriching permit {permit.permit_id}...")
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id=tenant_id, permit=permit)
            )

            enriched_leads.append(lead)

            logger.info(f"  ✓ Enriched lead: {lead.lead_id}")
            logger.info(f"  → Company: {lead.company.name}")

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
                if lead.decision_maker.title:
                    logger.info(f"  → Title: {lead.decision_maker.title}")
            else:
                logger.info("  → No decision maker found")
                if settings.enrichment_dry_run:
                    logger.info("     (Dry-run mode - no real API call made)")
                else:
                    logger.info("     (No email found or API call failed)")

            # Store the lead
            lead_storage.save_lead(lead)
            logger.info(f"  → Saved to lead storage")

        except RuntimeError as e:
            logger.warning(f"  ⚠ Credit limit reached: {e}")
            logger.warning("  Stopping enrichment to protect credits")
            break
        except Exception as e:
            logger.error(f"  ✗ Enrichment failed: {e}", exc_info=True)

        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Permits processed: {len(test_permits)}")
    logger.info(f"Leads enriched: {len(enriched_leads)}")
    logger.info(
        f"Leads with emails: {sum(1 for l in enriched_leads if l.decision_maker and l.decision_maker.email)}"
    )
    logger.info("")

    if settings.enrichment_dry_run:
        logger.info("⚠ DRY-RUN MODE: No credits were used")
        logger.info("   To use real API: Set ENRICHMENT_DRY_RUN=false in .env")
    else:
        logger.info("✅ REAL API MODE: Check Hunter.io dashboard for credit usage")
        logger.info("   Dashboard: https://hunter.io/dashboard")
        logger.info("   Note: Hunter only charges when email is found")

    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

