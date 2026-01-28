"""Find actual Building permits by searching with different parameters."""

from __future__ import annotations

import asyncio
from playwright.async_api import async_playwright
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper


async def find_building_permits():
    """Try different search parameters to find Building permits."""
    print("Searching for Building permits with different parameters...\n")
    
    # Try different record types that might be Building permits
    record_types = [
        None,  # No filter
        "Building Permit",
        "Residential Building",
        "Commercial Building",
    ]
    
    for record_type in record_types:
        print(f"{'='*80}")
        print(f"Testing with record_type: {record_type or 'None'}")
        print(f"{'='*80}")
        
        scraper = create_accela_scraper(
            city_code="COSA",
            module="Building",
            record_type=record_type,
            days_back=90,  # Look back further
            max_pages=1,
            extract_applicant=True,
        )
        
        permits = await scraper.scrape()
        
        print(f"Found {len(permits)} permits")
        
        # Check permit types
        permit_types = set(p.permit_type for p in permits)
        print(f"Permit types: {', '.join(list(permit_types)[:5])}")
        
        # Check for addresses
        has_address = [p for p in permits if p.address and len(p.address.strip()) > 10]
        print(f"Permits with addresses: {len(has_address)}/{len(permits)}")
        
        if has_address:
            print(f"\n✅ Found permits with addresses!")
            for p in has_address[:3]:
                print(f"  - {p.permit_id}: {p.address[:80]}")
            break  # Found some, stop searching
        else:
            print("  No addresses found\n")


if __name__ == "__main__":
    asyncio.run(find_building_permits())
