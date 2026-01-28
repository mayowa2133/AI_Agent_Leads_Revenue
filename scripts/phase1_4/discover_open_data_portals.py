"""Discover open data portals with permit datasets."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.signal_engine.discovery.portal_discovery import PortalDiscoveryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Cities known to have open data portals
CITIES_WITH_OPEN_DATA = [
    "Charlotte",
    "Seattle",
    "New York",
    "San Francisco",
    "Chicago",
    "Austin",
    "San Antonio",
    "Denver",
    "Portland",
    "Boston",
]


async def discover_socrata_portals():
    """Discover Socrata portals for cities."""
    logger.info("=" * 80)
    logger.info("Discovering Socrata Open Data Portals")
    logger.info("=" * 80)
    logger.info("")
    
    discovery = PortalDiscoveryService()
    
    # Search for open data portals
    queries = [
        '"{city} open data" site:.gov',
        '"{city} building permits" site:data.*.gov',
        '"{city} socrata" site:.gov',
    ]
    
    discovered_portals = []
    
    for city in CITIES_WITH_OPEN_DATA[:5]:  # Test with first 5 cities
        logger.info(f"Searching for: {city}")
        
        for query_template in queries:
            query = query_template.format(city=city)
            try:
                results = await discovery._search_google(query, max_results=5)
                
                for result in results:
                    url = result.get("link", "")
                    if "data." in url and ".gov" in url:
                        # Likely a Socrata portal
                        discovered_portals.append({
                            "city": city,
                            "url": url,
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                        })
                        logger.info(f"  ✅ Found: {url}")
            except Exception as e:
                logger.warning(f"  ⚠️  Search failed: {e}")
        
        logger.info("")
    
    return discovered_portals


async def test_socrata_dataset(portal_url: str, dataset_id: str) -> dict[str, Any] | None:
    """Test if a Socrata dataset exists and get sample data."""
    try:
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
                        "fields": list(data[0].keys()) if data else [],
                    }
    except Exception:
        pass
    
    return None


async def find_permit_datasets(portal_url: str) -> list[dict[str, Any]]:
    """Find permit datasets in a Socrata portal."""
    # Try common dataset IDs/names
    common_names = [
        "building-permits",
        "permits",
        "construction-permits",
        "building_permits",
        "permits_current",
    ]
    
    datasets = []
    
    for name in common_names:
        result = await test_socrata_dataset(portal_url, name)
        if result:
            datasets.append({
                "dataset_id": name,
                "fields": result["fields"],
                "sample": result["sample_record"],
            })
    
    return datasets


async def main():
    """Main discovery function."""
    logger.info("Discovering open data portals with permit datasets...")
    logger.info("")
    
    portals = await discover_socrata_portals()
    
    logger.info("=" * 80)
    logger.info("Testing Discovered Portals")
    logger.info("=" * 80)
    logger.info("")
    
    working_portals = []
    
    for portal in portals:
        logger.info(f"Testing: {portal['city']} - {portal['url']}")
        
        # Try to find permit datasets
        datasets = await find_permit_datasets(portal["url"])
        
        if datasets:
            logger.info(f"  ✅ Found {len(datasets)} permit dataset(s)")
            for ds in datasets:
                logger.info(f"    - Dataset: {ds['dataset_id']}")
                logger.info(f"      Fields: {', '.join(ds['fields'][:10])}")
            
            working_portals.append({
                **portal,
                "datasets": datasets,
            })
        else:
            logger.info("  ⚠️  No permit datasets found")
        
        logger.info("")
    
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info(f"Found {len(working_portals)} working portals with permit datasets")
    
    return working_portals


if __name__ == "__main__":
    asyncio.run(main())
