"""Test CKAN ingestion via UnifiedPermitIngestion for San Antonio building permits."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.api.unified_ingestion import PermitSource, PermitSourceType, UnifiedPermitIngestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    source = PermitSource(
        source_type=PermitSourceType.CKAN_API,
        city="San Antonio",
        source_id="san_antonio_ckan_building_permits",
        config={
            "portal_url": "https://data.sanantonio.gov",
            # Current, actively updated dataset
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
    permits = await ingestion.ingest_permits(source, days_back=30, limit=20)

    logger.info("Fetched %d permits", len(permits))
    for permit in permits[:5]:
        logger.info(
            "Permit %s | type=%s | address=%s | applicant=%s | issued=%s",
            permit.permit_id,
            permit.permit_type,
            permit.address,
            permit.applicant_name,
            permit.issued_date,
        )


if __name__ == "__main__":
    asyncio.run(main())
