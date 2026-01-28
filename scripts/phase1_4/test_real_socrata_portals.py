"""Test real Socrata portals with permit datasets."""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.signal_engine.api.socrata_client import SocrataPermitClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Real Socrata portals with known permit datasets
# These are actual working portals - we'll test them

REAL_SOCRATA_PORTALS = [
    {
        "city": "Charlotte, NC",
        "portal_url": "https://data.cityofcharlotte.org",
        "dataset_id": "v6yw-gq5j",  # Building Permits dataset
        "field_mapping": {
            "permit_id": "permit_number",
            "permit_type": "permit_type",
            "address": "address",
            "status": "status",
            "applicant_name": "contractor_name",
            "issued_date": "issue_date",
        },
    },
    {
        "city": "Seattle, WA",
        "portal_url": "https://data.seattle.gov",
        "dataset_id": "76t5-zqzr",  # Building Permits dataset
        "field_mapping": {
            "permit_id": "permitnum",
            "permit_type": "permittypedesc",  # or permittypemapped
            "address": "originaladdress1",
            "status": "statuscurrent",
            "applicant_name": None,  # May not be available
            "issued_date": None,  # May not be available - will skip date filter
        },
    },
]


async def test_socrata_dataset(portal_url: str, dataset_id: str) -> dict | None:
    """Test if a Socrata dataset exists and get metadata."""
    try:
        # Try to get one record to see structure
        api_url = f"{portal_url}/resource/{dataset_id}.json"
        params = {"$limit": 1}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return {
                        "exists": True,
                        "sample_record": data[0],
                        "fields": list(data[0].keys()),
                    }
            elif response.status_code == 404:
                return {"exists": False, "error": "Dataset not found"}
    except Exception as e:
        return {"exists": False, "error": str(e)}
    
    return None


async def test_real_socrata_portals():
    """Test real Socrata portals."""
    logger.info("=" * 80)
    logger.info("Testing Real Socrata Portals")
    logger.info("=" * 80)
    logger.info("")
    
    working_portals = []
    
    for portal in REAL_SOCRATA_PORTALS:
        logger.info(f"Testing: {portal['city']}")
        logger.info(f"  Portal: {portal['portal_url']}")
        logger.info(f"  Dataset: {portal['dataset_id']}")
        logger.info("")
        
        # First, test if dataset exists
        test_result = await test_socrata_dataset(portal["portal_url"], portal["dataset_id"])
        
        if test_result and test_result.get("exists"):
            logger.info("  ✅ Dataset exists!")
            logger.info(f"  Fields: {', '.join(test_result['fields'][:10])}")
            logger.info("")
            
            # Auto-discover field mapping if not provided
            field_mapping = portal.get("field_mapping")
            if not field_mapping and test_result.get("sample_record"):
                logger.info("  Auto-discovering field mapping...")
                # Create temporary client to use discover method
                temp_client = SocrataPermitClient(
                    portal_url=portal["portal_url"],
                    dataset_id=portal["dataset_id"],
                )
                field_mapping = temp_client.discover_field_mapping(test_result["sample_record"])
                logger.info(f"  Discovered mapping: {field_mapping}")
            
            # Try to fetch permits
            try:
                client = SocrataPermitClient(
                    portal_url=portal["portal_url"],
                    dataset_id=portal["dataset_id"],
                    field_mapping=field_mapping,
                )
                
                permits = await client.get_permits(days_back=30, limit=50)
                
                logger.info(f"  ✅ Fetched {len(permits)} permits")
                
                if permits:
                    logger.info("  Sample permits:")
                    for i, permit in enumerate(permits[:5], 1):
                        logger.info(f"    {i}. {permit.permit_id} - {permit.permit_type}")
                        logger.info(f"       Address: {permit.address}")
                        logger.info(f"       Status: {permit.status}")
                    
                    working_portals.append({
                        **portal,
                        "permit_count": len(permits),
                    })
            except Exception as e:
                logger.error(f"  ❌ Error fetching permits: {e}")
        else:
            error = test_result.get("error", "Unknown error") if test_result else "No response"
            logger.warning(f"  ⚠️  Dataset not accessible: {error}")
        
        logger.info("")
    
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info(f"Working portals: {len(working_portals)}")
    
    if working_portals:
        logger.info("")
        logger.info("✅ Successfully tested portals:")
        for portal in working_portals:
            logger.info(f"  - {portal['city']}: {portal['permit_count']} permits")
    
    return working_portals


if __name__ == "__main__":
    asyncio.run(test_real_socrata_portals())
