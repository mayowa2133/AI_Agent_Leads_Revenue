"""Test Phase 1.4.3: Open Data API Integration."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.api.ckan_client import CKANPermitClient
from src.signal_engine.api.custom_api_client import CustomAPIPermitClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Known open data portals with permit datasets
# These are real examples - we'll test them

SOCRATA_PORTALS = [
    {
        "city": "Charlotte, NC",
        "portal_url": "https://data.cityofcharlotte.org",
        "dataset_id": "permits",  # Need to find actual dataset ID
        "field_mapping": {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
            "applicant_name": "applicant",
            "issued_date": "issue_date",
        },
    },
    {
        "city": "Seattle, WA",
        "portal_url": "https://data.seattle.gov",
        "dataset_id": "building-permits",  # Need to find actual dataset ID
        "field_mapping": {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
            "applicant_name": "applicant",
            "issued_date": "issue_date",
        },
    },
]

CKAN_PORTALS = [
    {
        "city": "Example City",
        "portal_url": "https://data.gov",
        "resource_id": "example-resource-id",
        "field_mapping": {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
        },
    },
]

CUSTOM_APIS = [
    {
        "city": "San Antonio, TX",
        "api_url": "https://data.sanantonio.gov",
        "endpoint": "api/permits",
        "field_mapping": {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
        },
    },
]


async def test_socrata_client():
    """Test Socrata API client."""
    logger.info("=" * 80)
    logger.info("Testing Socrata API Client")
    logger.info("=" * 80)
    logger.info("")
    
    for portal in SOCRATA_PORTALS:
        logger.info(f"Testing: {portal['city']}")
        logger.info(f"  Portal: {portal['portal_url']}")
        logger.info(f"  Dataset: {portal['dataset_id']}")
        
        try:
            client = SocrataPermitClient(
                portal_url=portal["portal_url"],
                dataset_id=portal["dataset_id"],
                field_mapping=portal["field_mapping"],
            )
            
            permits = await client.get_permits(days_back=30, limit=100)
            
            logger.info(f"  ✅ Fetched {len(permits)} permits")
            
            if permits:
                logger.info("  Sample permits:")
                for i, permit in enumerate(permits[:3], 1):
                    logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
                    logger.info(f"       Address: {permit.address}")
                    logger.info(f"       Status: {permit.status}")
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
        
        logger.info("")


async def test_ckan_client():
    """Test CKAN API client."""
    logger.info("=" * 80)
    logger.info("Testing CKAN API Client")
    logger.info("=" * 80)
    logger.info("")
    
    for portal in CKAN_PORTALS:
        logger.info(f"Testing: {portal['city']}")
        logger.info(f"  Portal: {portal['portal_url']}")
        logger.info(f"  Resource: {portal['resource_id']}")
        
        try:
            client = CKANPermitClient(
                portal_url=portal["portal_url"],
                resource_id=portal["resource_id"],
                field_mapping=portal["field_mapping"],
            )
            
            permits = await client.get_permits(days_back=30, limit=100)
            
            logger.info(f"  ✅ Fetched {len(permits)} permits")
            
            if permits:
                logger.info("  Sample permits:")
                for i, permit in enumerate(permits[:3], 1):
                    logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
        
        logger.info("")


async def test_custom_api_client():
    """Test Custom API client."""
    logger.info("=" * 80)
    logger.info("Testing Custom API Client")
    logger.info("=" * 80)
    logger.info("")
    
    for api in CUSTOM_APIS:
        logger.info(f"Testing: {api['city']}")
        logger.info(f"  API: {api['api_url']}")
        logger.info(f"  Endpoint: {api['endpoint']}")
        
        try:
            client = CustomAPIPermitClient(
                api_url=api["api_url"],
                endpoint=api["endpoint"],
                field_mapping=api["field_mapping"],
            )
            
            permits = await client.get_permits(days_back=30, limit=100)
            
            logger.info(f"  ✅ Fetched {len(permits)} permits")
            
            if permits:
                logger.info("  Sample permits:")
                for i, permit in enumerate(permits[:3], 1):
                    logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
        
        logger.info("")


async def test_all_apis():
    """Test all API clients."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.3: OPEN DATA API INTEGRATION TEST")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Testing API clients for open data portals")
    logger.info("")
    
    await test_socrata_client()
    await test_ckan_client()
    await test_custom_api_client()
    
    logger.info("=" * 80)
    logger.info("Test Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_all_apis())
