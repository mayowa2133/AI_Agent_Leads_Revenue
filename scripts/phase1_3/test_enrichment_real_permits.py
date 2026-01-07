"""Test enrichment pipeline with 1-2 real permits from scrapers."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from src.core.config import get_settings
from src.core.security import tenant_scoped_session
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.scrapers.permit_scraper import (
    MecklenburgPermitScraper,
    SanAntonioFireScraper,
)
from src.signal_engine.storage.lead_storage import LeadStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def scrape_mecklenburg_permits(limit: int = 2) -> list:
    """Scrape a few permits from Mecklenburg County."""
    logger.info("=" * 60)
    logger.info("Scraping Mecklenburg County Permits")
    logger.info("=" * 60)

    # Try project name search to get more permits with applicant data
    scraper = MecklenburgPermitScraper(
        search_type="project_name",
        search_value="Building",  # Broader search to get more results
        extract_applicant=True,  # Get applicant names from detail pages
    )

    try:
        permits = await scraper.scrape()
        logger.info(f"✓ Scraped {len(permits)} permits from Mecklenburg")
        
        # Return only the first N permits
        return permits[:limit]
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}", exc_info=True)
        return []


async def scrape_san_antonio_permits(limit: int = 2) -> list:
    """Scrape a few permits from San Antonio."""
    logger.info("=" * 60)
    logger.info("Scraping San Antonio Fire Permits")
    logger.info("=" * 60)

    scraper = SanAntonioFireScraper(
        record_type="Fire Alarm",
        days_back=30,
    )

    try:
        permits = await scraper.scrape()
        logger.info(f"✓ Scraped {len(permits)} permits from San Antonio")
        
        # Return only the first N permits
        return permits[:limit]
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}", exc_info=True)
        return []


async def test_enrichment_with_real_permits():
    """Test enrichment with 1-2 real permits."""
    logger.info("=" * 60)
    logger.info("Testing Enrichment with Real Permits")
    logger.info("=" * 60)

    settings = get_settings()
    tenant_id = os.environ.get("TENANT_ID", "demo")

    # Check if dry-run is enabled
    if settings.enrichment_dry_run:
        logger.warning("⚠ DRY-RUN MODE IS ENABLED")
        logger.warning("   Set ENRICHMENT_DRY_RUN=false in .env to use real API calls")
        logger.info("")
        logger.info("Proceeding with dry-run mode (no credits will be used)...")
        logger.info("")

    # Choose which scraper to use
    use_mecklenburg = os.environ.get("USE_MECKLENBURG", "true").lower() == "true"
    
    async with tenant_scoped_session(tenant_id):
        # Scrape 1-2 permits
        if use_mecklenburg:
            permits = await scrape_mecklenburg_permits(limit=2)
        else:
            permits = await scrape_san_antonio_permits(limit=2)

        if not permits:
            logger.error("✗ No permits scraped. Cannot test enrichment.")
            return

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Enriching {len(permits)} Permit(s)")
        logger.info("=" * 60)
        logger.info("")

        enriched_leads = []
        lead_storage = LeadStorage()

        for i, permit in enumerate(permits, 1):
            logger.info(f"Permit {i}/{len(permits)}: {permit.permit_id}")
            logger.info(f"  → Type: {permit.permit_type}")
            logger.info(f"  → Address: {permit.address}")
            logger.info(f"  → Applicant: {permit.applicant_name or 'N/A'}")
            logger.info("")

            try:
                # Enrich the permit
                logger.info(f"  Enriching permit {permit.permit_id}...")
                lead = await enrich_permit_to_lead(
                    EnrichmentInputs(tenant_id=tenant_id, permit=permit)
                )

                enriched_leads.append(lead)

                # Display results
                logger.info(f"  ✓ Enriched lead created: {lead.lead_id}")
                logger.info(f"  → Company: {lead.company.name}")
                if lead.company.website:
                    logger.info(f"  → Website: {lead.company.website}")
                if lead.company.employee_count:
                    logger.info(f"  → Employees: {lead.company.employee_count}")

                if lead.decision_maker:
                    logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
                    if lead.decision_maker.email:
                        logger.info(f"  → Email: {lead.decision_maker.email}")
                        if settings.enrichment_dry_run:
                            logger.warning("     ⚠ DRY-RUN: This is a test, no credit used")
                        else:
                            logger.info("     ✅ REAL API: Credit used if email found")
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
        logger.info("Enrichment Test Summary")
        logger.info("=" * 60)
        logger.info(f"Permits processed: {len(permits)}")
        logger.info(f"Leads enriched: {len(enriched_leads)}")
        logger.info(f"Leads with emails: {sum(1 for l in enriched_leads if l.decision_maker and l.decision_maker.email)}")
        logger.info("")

        if settings.enrichment_dry_run:
            logger.info("⚠ DRY-RUN MODE: No credits were used")
            logger.info("   To use real API: Set ENRICHMENT_DRY_RUN=false in .env")
        else:
            logger.info("✅ Real API mode: Check Hunter.io dashboard for credit usage")
            logger.info("   Dashboard: https://hunter.io/dashboard")

        logger.info("")


async def main():
    """Run enrichment test with real permits."""
    logger.info("Real Permit Enrichment Test")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This will:")
    logger.info("1. Scrape 1-2 real permits from Mecklenburg or San Antonio")
    logger.info("2. Enrich them with Hunter.io")
    logger.info("3. Show results and credit usage")
    logger.info("")
    logger.info("Safety:")
    logger.info("- Only processes 1-2 permits")
    logger.info("- Credit limit: 3 credits max")
    logger.info("- Dry-run mode can be enabled/disabled in .env")
    logger.info("")

    settings = get_settings()
    if settings.enrichment_dry_run:
        logger.warning("⚠ Currently in DRY-RUN mode (safe)")
        logger.warning("   Set ENRICHMENT_DRY_RUN=false to use real API")
    else:
        logger.warning("⚠ REAL API MODE - Credits will be used!")
        logger.warning("   Max credits: 3 (safety limit)")
        logger.warning("   Only processing 1-2 permits")

    logger.info("")
    logger.info("Starting test...")
    logger.info("")

    await test_enrichment_with_real_permits()

    logger.info("=" * 60)
    logger.info("Test Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

