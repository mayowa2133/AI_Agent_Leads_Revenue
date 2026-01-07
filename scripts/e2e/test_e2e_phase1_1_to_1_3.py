"""End-to-end test: Phase 1.1 (Scraping) → Phase 1.3 (Enrichment)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.jobs.scraper_scheduler import ScraperScheduler
from src.signal_engine.models import PermitData
from src.signal_engine.storage.lead_storage import LeadStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_e2e_flow():
    """Test complete flow: Scrape → Enrich → Store."""
    logger.info("=" * 70)
    logger.info("End-to-End Test: Phase 1.1 → Phase 1.3")
    logger.info("Scrape Real Permits → Auto-Enrich → Store Leads")
    logger.info("=" * 70)
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

    # Step 1: Scrape real permits (Phase 1.1)
    logger.info("=" * 70)
    logger.info("STEP 1: Scraping Real Permits (Phase 1.1)")
    logger.info("=" * 70)
    logger.info("")

    permits: list[PermitData] = []

    try:
        # Scrape 1-2 permits from Mecklenburg
        logger.info("Scraping Mecklenburg County permits...")
        logger.info("Search: 'Building' (specific search to avoid timeouts)")
        logger.info("")

        from src.signal_engine.scrapers.permit_scraper import MecklenburgPermitScraper

        scraper = MecklenburgPermitScraper(
            search_type="project_name",
            search_value="Building",
            extract_applicant=True,  # Get applicant names
        )

        scraped_permits = await scraper.scrape()
        # Only use first 2 permits for testing to save credits
        permits.extend(scraped_permits[:2])

        logger.info(f"✓ Scraped {len(scraped_permits)} permits from Mecklenburg")
        logger.info("")

        # Show scraped permits
        for i, permit in enumerate(scraped_permits, 1):
            logger.info(f"Permit {i}:")
            logger.info(f"  → ID: {permit.permit_id}")
            logger.info(f"  → Type: {permit.permit_type}")
            logger.info(f"  → Address: {permit.address}")
            logger.info(f"  → Applicant: {permit.applicant_name or 'N/A'}")
            logger.info(f"  → Status: {permit.status}")
            logger.info("")

        if not permits:
            logger.warning("⚠ No permits scraped - cannot test enrichment")
            logger.warning("   This might be due to portal changes or network issues")
            return

    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}", exc_info=True)
        logger.error("   Cannot continue with enrichment test")
        return

    # Step 2: Enrich permits (Phase 1.3)
    logger.info("=" * 70)
    logger.info("STEP 2: Enriching Permits (Phase 1.3)")
    logger.info("=" * 70)
    logger.info("")

    logger.info("Enrichment Pipeline:")
    logger.info("  1. Geocode address → Get coordinates + jurisdiction")
    logger.info("  2. Match company → Extract from applicant_name")
    logger.info("  3. Find domain → Apollo organizations/search")
    logger.info("  4. Find email → Hunter.io email-finder (if domain found)")
    logger.info("  5. Match regulatory updates → Correlate with permits")
    logger.info("  6. Store enriched lead → Save to lead storage")
    logger.info("")

    enriched_leads = []
    lead_storage = LeadStorage()

    for i, permit in enumerate(permits, 1):
        logger.info(f"Enriching Permit {i}/{len(permits)}: {permit.permit_id}")
        logger.info(f"  → Address: {permit.address}")
        logger.info(f"  → Applicant: {permit.applicant_name or 'N/A'}")
        logger.info("")

        try:
            # Run enrichment
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id=tenant_id, permit=permit)
            )

            enriched_leads.append(lead)

            # Show enrichment results
            logger.info(f"  ✓ Enriched Lead: {lead.lead_id}")
            logger.info(f"  → Company: {lead.company.name}")

            # Geocoding results
            if hasattr(lead, 'location') and lead.location:
                logger.info(f"  → Location: {lead.location.latitude}, {lead.location.longitude}")
                if hasattr(lead.location, 'jurisdiction') and lead.location.jurisdiction:
                    logger.info(f"  → Jurisdiction: {lead.location.jurisdiction}")

            # Company domain
            if lead.company.website:
                logger.info(f"  → Website: {lead.company.website}")
                logger.info("  → Domain found! ✅")
            else:
                logger.info("  → No website/domain found")

            # Decision maker
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
                if lead.decision_maker.title:
                    logger.info(f"  → Title: {lead.decision_maker.title}")
            else:
                logger.info("  → No decision maker found")

            # Regulatory matches
            if hasattr(lead, 'compliance_context') and lead.compliance_context and lead.compliance_context.regulatory_updates:
                logger.info(
                    f"  → Regulatory Matches: {len(lead.compliance_context.regulatory_updates)}"
                )
            else:
                logger.info("  → No regulatory matches")

            # Store the lead
            lead_storage.save_lead(lead)
            logger.info("  → Saved to lead storage ✅")

        except RuntimeError as e:
            logger.warning(f"  ⚠ Credit limit reached: {e}")
            logger.warning("  Stopping enrichment to protect credits")
            break
        except Exception as e:
            logger.error(f"  ✗ Enrichment failed: {e}", exc_info=True)

        logger.info("")

    # Step 3: Summary
    logger.info("=" * 70)
    logger.info("STEP 3: End-to-End Test Summary")
    logger.info("=" * 70)
    logger.info("")

    logger.info("Phase 1.1 (Scraping):")
    logger.info(f"  → Permits scraped: {len(permits)}")
    logger.info(f"  → With applicant names: {sum(1 for p in permits if p.applicant_name)}")
    logger.info("")

    logger.info("Phase 1.3 (Enrichment):")
    logger.info(f"  → Leads enriched: {len(enriched_leads)}")
    logger.info(f"  → With geocoding: {sum(1 for l in enriched_leads if hasattr(l, 'location') and l.location)}")
    logger.info(f"  → With domains: {sum(1 for l in enriched_leads if l.company.website)}")
    logger.info(
        f"  → With emails: {sum(1 for l in enriched_leads if l.decision_maker and l.decision_maker.email)}"
    )
    logger.info(
        f"  → With regulatory matches: {sum(1 for l in enriched_leads if hasattr(l, 'compliance_context') and l.compliance_context and l.compliance_context.regulatory_updates)}"
    )
    logger.info("")

    # Verify pipeline
    logger.info("Pipeline Verification:")
    if len(permits) > 0:
        logger.info("  ✅ Phase 1.1: Permit scraping working")
    if len(enriched_leads) > 0:
        logger.info("  ✅ Phase 1.3: Enrichment pipeline working")
    if any(l.company.website for l in enriched_leads):
        logger.info("  ✅ Apollo domain lookup working")
    if any(l.decision_maker and l.decision_maker.email for l in enriched_leads):
        logger.info("  ✅ Hunter.io email finder working")
    if any(hasattr(l, 'location') and l.location for l in enriched_leads):
        logger.info("  ✅ Geocoding working")
    logger.info("")

    if settings.enrichment_dry_run:
        logger.info("⚠ DRY-RUN MODE: No credits were used")
    else:
        logger.info("✅ REAL API MODE: Check dashboards for credit usage")
        logger.info("   Apollo: https://app.apollo.io/#/settings/integrations/api")
        logger.info("   Hunter: https://hunter.io/dashboard")

    logger.info("")
    logger.info("=" * 70)
    logger.info("End-to-End Test Complete!")
    logger.info("=" * 70)


async def main():
    """Run end-to-end test."""
    await test_e2e_flow()


if __name__ == "__main__":
    asyncio.run(main())

