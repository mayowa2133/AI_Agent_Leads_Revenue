"""Comprehensive test script for Phase 1.3 enrichment pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.core.config import get_settings
from src.signal_engine.enrichment.company_enricher import EnrichmentInputs, enrich_permit_to_lead
from src.signal_engine.enrichment.geocoder import geocode_address
from src.signal_engine.enrichment.regulatory_matcher import match_regulatory_updates
from src.signal_engine.models import PermitData
from src.signal_engine.storage.lead_storage import LeadStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def test_geocoding():
    """Test geocoding service."""
    logger.info("=" * 60)
    logger.info("Testing Geocoding Service")
    logger.info("=" * 60)

    test_addresses = [
        "600 Tryon St, Charlotte, NC 28202",
        "100 W Houston St, San Antonio, TX 78205",
        "1600 Pennsylvania Avenue NW, Washington, DC 20500",
    ]

    for address in test_addresses:
        try:
            result = await geocode_address(address)
            logger.info(f"✓ Geocoded: {address}")
            logger.info(f"  → {result.formatted_address}")
            logger.info(f"  → Coordinates: ({result.latitude}, {result.longitude})")
            logger.info(f"  → City: {result.city}, State: {result.state}")
        except Exception as e:
            logger.error(f"✗ Failed to geocode {address}: {e}")

    logger.info("")


async def test_company_matching():
    """Test company matching logic."""
    logger.info("=" * 60)
    logger.info("Testing Company Matching")
    logger.info("=" * 60)

    test_permits = [
        PermitData(
            source="test",
            permit_id="TEST-001",
            permit_type="Fire Alarm",
            address="600 Tryon St, Charlotte, NC 28202",
            building_type="Commercial Office",
            status="Issued",
            applicant_name="ABC Facilities Management LLC",
        ),
        PermitData(
            source="test",
            permit_id="TEST-002",
            permit_type="Sprinkler",
            address="100 W Houston St, San Antonio, TX 78205",
            building_type="Retail",
            status="Issued",
            applicant_name="John Smith",  # Person name
        ),
        PermitData(
            source="test",
            permit_id="TEST-003",
            permit_type="HVAC",
            address="123 Main St, Austin, TX 78701",
            building_type="Office",
            status="Issued",
            applicant_name=None,  # No applicant name
        ),
    ]

    for permit in test_permits:
        try:
            lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="test", permit=permit))
            logger.info(f"✓ Enriched permit: {permit.permit_id}")
            logger.info(f"  → Company: {lead.company.name}")
            if lead.company.website:
                logger.info(f"  → Website: {lead.company.website}")
            if lead.company.employee_count:
                logger.info(f"  → Employees: {lead.company.employee_count}")
        except Exception as e:
            logger.error(f"✗ Failed to enrich permit {permit.permit_id}: {e}")

    logger.info("")


async def test_decision_maker_identification():
    """Test decision maker identification."""
    logger.info("=" * 60)
    logger.info("Testing Decision Maker Identification")
    logger.info("=" * 60)

    settings = get_settings()
    if not settings.apollo_api_key:
        logger.warning("⚠ Apollo API key not set - skipping decision maker tests")
        return

    permit = PermitData(
        source="test",
        permit_id="TEST-DM-001",
        permit_type="Fire Alarm",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="ABC Facilities Management LLC",
    )

    try:
        lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="test", permit=permit))
        logger.info(f"✓ Enriched permit: {permit.permit_id}")
        logger.info(f"  → Company: {lead.company.name}")

        if lead.decision_maker:
            logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
            logger.info(f"  → Title: {lead.decision_maker.title}")
            if lead.decision_maker.email:
                logger.info(f"  → Email: {lead.decision_maker.email}")
        else:
            logger.warning("  → No decision maker found")
    except Exception as e:
        logger.error(f"✗ Failed to find decision maker: {e}")

    logger.info("")


async def test_regulatory_matching():
    """Test regulatory update matching."""
    logger.info("=" * 60)
    logger.info("Testing Regulatory Update Matching")
    logger.info("=" * 60)

    permit = PermitData(
        source="test",
        permit_id="TEST-REG-001",
        permit_type="Fire Alarm",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="Test Company",
    )

    try:
        # Geocode first
        geocode_result = await geocode_address(permit.address)
        logger.info(f"✓ Geocoded address: {permit.address}")
        logger.info(f"  → State: {geocode_result.state}")

        # Match regulatory updates
        matches = await match_regulatory_updates(permit, geocode_result)
        logger.info(f"✓ Found {len(matches)} matching regulatory updates")

        for update in matches[:3]:  # Show first 3
            logger.info(f"  → {update.title[:60]}")
            if update.applicable_codes:
                logger.info(f"    Codes: {', '.join(update.applicable_codes[:3])}")
    except Exception as e:
        logger.error(f"✗ Failed to match regulatory updates: {e}")

    logger.info("")


async def test_end_to_end_enrichment():
    """Test complete end-to-end enrichment pipeline."""
    logger.info("=" * 60)
    logger.info("Testing End-to-End Enrichment Pipeline")
    logger.info("=" * 60)

    permit = PermitData(
        source="test",
        permit_id="TEST-E2E-001",
        permit_type="Fire Alarm",
        address="600 Tryon St, Charlotte, NC 28202",
        building_type="Commercial Office",
        status="Issued",
        applicant_name="ABC Facilities Management LLC",
        issued_date=datetime.now(tz=timezone.utc),
    )

    try:
        lead = await enrich_permit_to_lead(EnrichmentInputs(tenant_id="test", permit=permit))

        logger.info(f"✓ Enriched lead created: {lead.lead_id}")
        logger.info(f"  → Company: {lead.company.name}")
        if lead.decision_maker:
            logger.info(f"  → Decision Maker: {lead.decision_maker.full_name}")
        logger.info(f"  → Compliance Codes: {len(lead.compliance.applicable_codes)} codes")
        logger.info(f"  → Compliance Triggers: {len(lead.compliance.triggers)} triggers")

        # Test storage
        storage = LeadStorage()
        storage.save_lead(lead)
        logger.info("  → Saved to lead storage")

        # Verify retrieval
        retrieved = storage.get_lead(lead.lead_id)
        if retrieved:
            logger.info("  → Successfully retrieved from storage")
        else:
            logger.error("  → Failed to retrieve from storage")

    except Exception as e:
        logger.error(f"✗ End-to-end test failed: {e}", exc_info=True)

    logger.info("")


async def main():
    """Run all enrichment pipeline tests."""
    logger.info("Starting Phase 1.3 Enrichment Pipeline Tests")
    logger.info("")

    await test_geocoding()
    await test_company_matching()
    await test_decision_maker_identification()
    await test_regulatory_matching()
    await test_end_to_end_enrichment()

    logger.info("=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

