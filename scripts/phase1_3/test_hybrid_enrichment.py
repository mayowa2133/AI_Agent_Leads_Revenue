"""Test the hybrid Apollo + Hunter.io enrichment pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.enrichment.provider_manager import ProviderManager
from src.signal_engine.models import PermitData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_hybrid_workflow():
    """Test the complete hybrid workflow: Apollo (domain) → Hunter.io (email)."""
    logger.info("=" * 60)
    logger.info("Hybrid Enrichment Pipeline Test")
    logger.info("Apollo (domain lookup) → Hunter.io (email finder)")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()
    tenant_id = "test"

    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE: No credits will be used")
    else:
        logger.warning("⚠ REAL API MODE: Credits will be used!")
        logger.warning("   Apollo: Up to 10 credits per run (free tier: 110/month)")
        logger.warning("   Hunter: Up to 3 credits per run (free tier: 50/month)")

    logger.info("")

    # Test with permits that have company names (not person names)
    # This simulates real permits where applicant_name is a company
    test_permits = [
        PermitData(
            source="test_mecklenburg",
            permit_id="HYBRID-001",
            permit_type="Fire Alarm Installation",
            address="600 Tryon St, Charlotte, NC 28202",
            building_type="Commercial Office",
            status="Issued",
            applicant_name="Mecklenburg Electric LLC",  # Company name
            issued_date=datetime.now(tz=timezone.utc),
        ),
        PermitData(
            source="test_mecklenburg",
            permit_id="HYBRID-002",
            permit_type="Sprinkler System",
            address="100 W Houston St, San Antonio, TX 78205",
            building_type="Retail",
            status="Issued",
            applicant_name="Standard Fire Sprinklers Inc",  # Company name
            issued_date=datetime.now(tz=timezone.utc),
        ),
    ]

    logger.info(f"Testing hybrid workflow with {len(test_permits)} permits")
    logger.info("")
    logger.info("Workflow:")
    logger.info("1. Extract company name from permit")
    logger.info("2. Use Apollo organizations/search to find domain (FREE)")
    logger.info("3. Use Hunter.io email-finder to find email (1 credit if found)")
    logger.info("")

    enriched_leads = []

    for i, permit in enumerate(test_permits, 1):
        logger.info(f"Permit {i}/{len(test_permits)}: {permit.permit_id}")
        logger.info(f"  → Company: {permit.applicant_name}")
        logger.info("")

        try:
            logger.info(f"  Step 1: Enriching permit...")
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
                logger.warning("  → Hunter.io cannot search without domain")

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
                if not lead.company.website:
                    logger.info("     Reason: No domain available for Hunter.io")

        except RuntimeError as e:
            logger.warning(f"  ⚠ Credit limit reached: {e}")
            logger.warning("  Stopping enrichment to protect credits")
            break
        except Exception as e:
            logger.error(f"  ✗ Enrichment failed: {e}", exc_info=True)

        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("Hybrid Workflow Test Summary")
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


async def test_apollo_domain_lookup():
    """Test Apollo domain lookup separately."""
    logger.info("=" * 60)
    logger.info("Testing Apollo Domain Lookup")
    logger.info("=" * 60)
    logger.info("")

    settings = get_settings()

    if not settings.apollo_api_key:
        logger.warning("⚠ Apollo API key not set - skipping domain lookup test")
        logger.info("   Add APOLLO_API_KEY to .env to test this feature")
        return

    provider_manager = ProviderManager(
        apollo_api_key=settings.apollo_api_key,
        dry_run=settings.enrichment_dry_run,
        max_apollo_credits_per_run=5,  # Allow more for testing
    )

    test_companies = [
        ("Microsoft", "Redmond, WA"),
        ("Apple Inc", "Cupertino, CA"),
    ]

    for company_name, location in test_companies:
        logger.info(f"Looking up domain for: {company_name} ({location})")
        try:
            domain = await provider_manager.find_company_domain(
                company_name=company_name, location=location
            )
            if domain:
                logger.info(f"  ✓ Found domain: {domain}")
                if settings.enrichment_dry_run:
                    logger.warning("     ⚠ DRY-RUN: No Apollo credit used")
                else:
                    logger.info("     ✅ REAL API: 1 Apollo credit used")
            else:
                logger.info("  → No domain found")
        except RuntimeError as e:
            logger.warning(f"  ⚠ Credit limit reached: {e}")
            break
        except Exception as e:
            logger.error(f"  ✗ Lookup failed: {e}")

        logger.info("")


async def main():
    """Run hybrid enrichment tests."""
    logger.info("Hybrid Apollo + Hunter.io Enrichment Test")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This tests the complete hybrid workflow:")
    logger.info("1. Apollo organizations/search → Find company domain (FREE)")
    logger.info("2. Hunter.io email-finder → Find email (1 credit if found)")
    logger.info("")
    logger.info("Credit Usage:")
    logger.info("- Apollo: organizations/search (free tier endpoint)")
    logger.info("- Hunter: email-finder (1 credit per email found)")
    logger.info("")

    settings = get_settings()

    if not settings.apollo_api_key:
        logger.warning("⚠ Apollo API key not configured")
        logger.warning("   The hybrid workflow needs Apollo to find domains")
        logger.warning("   Add APOLLO_API_KEY to .env to enable this feature")
        logger.info("")

    await test_apollo_domain_lookup()
    await test_hybrid_workflow()

    logger.info("=" * 60)
    logger.info("Test Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

