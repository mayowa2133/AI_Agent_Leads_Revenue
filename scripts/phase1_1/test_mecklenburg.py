from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper


async def main():
    """
    Test script for Mecklenburg County (Charlotte, NC) permit scraper.
    
    Usage (Project Name search - recommended):
        TENANT_ID=demo \
        SEARCH_TYPE="project_name" \
        SEARCH_VALUE="Fire" \
        poetry run python scripts/test_mecklenburg.py
    
    Usage (Address search):
        TENANT_ID=demo \
        SEARCH_TYPE="address" \
        SEARCH_VALUE="Tryon" \
        STREET_NUMBER="600" \
        poetry run python scripts/test_mecklenburg.py
    
    The scraper will automatically:
    1. Navigate to home page (initialize session)
    2. Click "View Permits"
    3. Click search type (By Project Name or By Address)
    4. Fill form and submit
    5. Scrape results
    """
    tenant_id = os.environ.get("TENANT_ID", "demo")
    search_type = os.environ.get("SEARCH_TYPE", "project_name")
    search_value = os.environ.get("SEARCH_VALUE", "Fire")
    street_number = os.environ.get("STREET_NUMBER")

    scraper = mecklenburg_county_scraper(
        search_type=search_type,
        search_value=search_value,
        street_number=street_number,
    )

    async with tenant_scoped_session(tenant_id):
        search_desc = f"{search_type}='{search_value}'"
        if street_number:
            search_desc += f", street_number='{street_number}'"
        print(f"Scraping Mecklenburg County permits: {search_desc}\n")
        
        permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
        
        if not permits:
            print("No permits found. Possible reasons:")
            print("- The search value doesn't match any permits")
            print("- The selectors don't match the actual page structure")
            print("- The form submission failed")
            print("\nTry:")
            print("  - Different search value (e.g., SEARCH_VALUE='Sprinkler')")
            print("  - Address search with street number (e.g., STREET_NUMBER='600' SEARCH_VALUE='Tryon')")
            print("  - Check debug_mecklenburg_error.png if it was created")
        else:
            print(f"Found {len(permits)} permit(s):\n")
            for p in permits:
                print(p.model_dump())


if __name__ == "__main__":
    asyncio.run(main())

