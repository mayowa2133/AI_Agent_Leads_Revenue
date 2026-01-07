"""End-to-end test of hybrid Apollo + Hunter.io workflow with known companies."""

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
    """Test end-to-end hybrid workflow with known companies."""
    logger.info("=" * 60)
    logger.info("End-to-End Hybrid Workflow Test")
    logger.info("Apollo (domain) → Hunter.io (email)")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()
    tenant_id = "test"

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: Credits will be used!")
        logger.warning("   Apollo: Up to 2 credits (domain lookup)")
        logger.warning("   Hunter: Up to 2 credits (email finder)")

    logger.info("")

    # Test with known companies that are likely in Apollo's database
    test_permits = [
        PermitData(
            source="test",
            permit_id="E2E-001",
            permit_type="Fire Alarm Installation",
            address="1 Microsoft Way, Redmond, WA 98052",
            building_type="Commercial Office",
            status="Issued",
            applicant_name="Satya Nadella",  # Person name + known company
            issued_date=datetime.now(tz=timezone.utc),
        ),
        PermitData(
            source="test",
            permit_id="E2E-002",
            permit_type="Sprinkler System",
            address="1 Apple Park Way, Cupertino, CA 95014",
            building_type="Commercial Office",
            status="Issued",
            applicant_name="Tim Cook",  # Person name + known company
            issued_date=datetime.now(tz=timezone.utc),
        ),
    ]

    logger.info(f"Testing with {len(test_permits)} permits (known companies)")
    logger.info("")

    enriched_leads = []
    lead_storage = LeadStorage()

    for i, permit in enumerate(test_permits, 1):
        logger.info(f"Permit {i}/{len(test_permits)}: {permit.permit_id}")
        logger.info(f"  → Address: {permit.address}")
        logger.info(f"  → Applicant: {permit.applicant_name}")
        logger.info("")

        try:
            logger.info("  Enriching permit...")
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id=tenant_id, permit=permit)
            )

            enriched_leads.append(lead)

            logger.info(f"  ✓ Enriched lead: {lead.lead_id}")
            logger.info(f"  → Company: {lead.company.name}")

            if lead.company.website:
                logger.info(f"  → Website: {lead.company.website}")
                logger.info("  → Domain found! ✅")
            else:
                logger.warning("  → No website/domain found")

            if lead.decision_maker:
                logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
                if lead.decision_maker.email:
                    logger.info(f"  → Email: {lead.decision_maker.email}")
                    if settings.enrichment_dry_run:
                        logger.warning("     ⚠ DRY-RUN: No credit used")
                    else:
                        logger.info("     ✅ REAL API: 1 Hunter credit used")
                else:
                    logger.info("  → No email found")
                    if not settings.enrichment_dry_run:
                        logger.info("     (No Hunter credit charged)")
            else:
                logger.info("  → No decision maker found")

            # Store the lead
            lead_storage.save_lead(lead)
            logger.info(f"  → Saved to lead storage")

        except RuntimeError as e:
            logger.warning(f"  ⚠ Credit limit reached: {e}")
            break
        except Exception as e:
            logger.error(f"  ✗ Enrichment failed: {e}", exc_info=True)

        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("End-to-End Test Summary")
    logger.info("=" * 60)
    logger.info(f"Permits processed: {len(test_permits)}")
    logger.info(f"Leads enriched: {len(enriched_leads)}")
    logger.info(f"Domains found: {sum(1 for l in enriched_leads if l.company.website)}")
    logger.info(
        f"Emails found: {sum(1 for l in enriched_leads if l.decision_maker and l.decision_maker.email)}"
    )
    logger.info("")

    if settings.enrichment_dry_run:
        logger.info("⚠ DRY-RUN MODE: No credits were used")
    else:
        logger.info("✅ REAL API MODE: Check dashboards for credit usage")
        logger.info("   Apollo: https://app.apollo.io/#/settings/integrations/api")
        logger.info("   Hunter: https://hunter.io/dashboard")

    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())

