"""Refresh data/enriched_leads.json with newest CKAN results (clean slate)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from pathlib import Path

from src.core.config import get_settings
from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _is_quality_permit(applicant_name: str, address: str, permit_type: str | None) -> bool:
    if not applicant_name or len(applicant_name.strip()) <= 2:
        return False
    if not address or len(address.strip()) <= 5:
        return False
    if permit_type and "garage" in permit_type.lower():
        return False

    company_keywords = [
        "llc",
        "inc",
        "ltd",
        "corp",
        "company",
        "co",
        "group",
        "associates",
        "services",
        "systems",
        "construction",
        "builders",
        "contractor",
        "contractors",
        "architect",
        "architects",
        "engineering",
        "engineers",
        "plumbing",
        "electric",
        "electrical",
        "mechanical",
        "hvac",
        "roofing",
    ]
    applicant_lower = applicant_name.lower()
    return any(keyword in applicant_lower for keyword in company_keywords)


async def main() -> None:
    settings = get_settings()
    logger.info("Refreshing enriched leads from CKAN (clean slate)")
    logger.info("Apollo Enabled: %s", settings.apollo_enabled)
    logger.info("Enrichment Dry Run: %s", settings.enrichment_dry_run)

    source = PermitSource(
        source_type=PermitSourceType.CKAN_API,
        city="San Antonio",
        source_id="san_antonio_ckan_current",
        config={
            "portal_url": "https://data.sanantonio.gov",
            "resource_id": "c21106f9-3ef5-4f3a-8604-f992b4db7512",
            "field_mapping": {
                "permit_id": "PERMIT #",
                "permit_type": "PERMIT TYPE",
                "address": "ADDRESS",
                "status": "PERMIT TYPE",
                "applicant_name": "PRIMARY CONTACT",
                "issued_date": "DATE ISSUED",
            },
        },
    )

    ingestion = UnifiedPermitIngestion()
    permits = await ingestion.ingest_permits(source, days_back=365, limit=1000)
    logger.info("Fetched %s permits", len(permits))

    quality_permits = [
        p
        for p in permits
        if _is_quality_permit(p.applicant_name, p.address, p.permit_type)
    ]
    logger.info("Quality permits: %s", len(quality_permits))

    leads = []
    target_emails = 5
    for permit in quality_permits[:100]:
        lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="ckan_test", permit=permit))
        leads.append(lead.model_dump(mode="json"))
        email = lead.decision_maker.email if lead.decision_maker else None
        if email:
            target_emails -= 1
        if target_emails <= 0:
            break

    output_path = Path("data/enriched_leads.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(leads, indent=2))
    logger.info("Wrote %s enriched leads to %s", len(leads), output_path)


if __name__ == "__main__":
    asyncio.run(main())
