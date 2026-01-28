"""Run Accela scrape + enrichment pipeline using extracted applicant names."""

from __future__ import annotations

import asyncio
import logging

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_accela_enrichment() -> None:
    settings = get_settings()
    logger.info("Starting Accela scrape for enrichment test")
    logger.info(f"Dry Run Mode: {settings.enrichment_dry_run}")

    scraper = create_accela_scraper(city_code="COSA", module="Fire", days_back=30, max_pages=1, extract_applicant=True)
    permits = await scraper.scrape()

    # Filter to quality permits with both address and applicant
    candidates = [
        p
        for p in permits
        if p.address and len(p.address.strip()) > 5 and p.applicant_name and len(p.applicant_name.strip()) > 2
    ]
    logger.info(f"Found {len(candidates)} permits with address + applicant")

    # Limit to avoid API rate limits
    candidates = candidates[:5]
    logger.info(f"Enriching first {len(candidates)} permits")

    enriched = []
    for permit in candidates:
        try:
            lead = await enrich_permit_to_lead(
                EnrichmentInputs(tenant_id="local_test", permit=permit)
            )
            enriched.append(lead)
            logger.info(
                "Enriched lead for %s | company=%s | email=%s",
                permit.permit_id,
                lead.company.name if lead.company else None,
                lead.decision_maker.email if lead.decision_maker else None,
            )
        except Exception as exc:
            logger.warning("Failed enrichment for %s: %s", permit.permit_id, exc)

    logger.info("Enriched %d/%d permits", len(enriched), len(candidates))


if __name__ == "__main__":
    asyncio.run(run_accela_enrichment())
