from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import san_antonio_fire_scraper


async def main():
    """
    Test script for San Antonio (TX) Accela Fire Module scraper.
    
    Usage:
        TENANT_ID=demo \
        RECORD_TYPE="Fire Alarm" \
        poetry run python scripts/test_san_antonio.py
    
    Or search all fire records:
        TENANT_ID=demo \
        poetry run python scripts/test_san_antonio.py
    """
    tenant_id = os.environ.get("TENANT_ID", "demo")
    record_type = os.environ.get("RECORD_TYPE")  # Optional: "Fire Alarm", "Fire Sprinkler", etc.
    days_back = int(os.environ.get("DAYS_BACK", "30"))

    scraper = san_antonio_fire_scraper(
        record_type=record_type,
        days_back=days_back,
    )

    async with tenant_scoped_session(tenant_id):
        search_desc = f"record_type={record_type or 'All'}, days_back={days_back}"
        print(f"Scraping San Antonio Fire permits: {search_desc}\n")
        
        permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
        
        if not permits:
            print("No permits found. Possible reasons:")
            print("- The record type filter doesn't match any permits")
            print("- The selectors don't match the actual Accela page structure")
            print("- The search form submission failed")
            print("\nTry:")
            print("  - Different record type (e.g., RECORD_TYPE='Fire Sprinkler')")
            print("  - Leave RECORD_TYPE unset to search all fire records")
            print("  - Check debug_san_antonio_error.png if it was created")
        else:
            print(f"Found {len(permits)} permit(s):\n")
            for p in permits:
                print(p.model_dump())


if __name__ == "__main__":
    asyncio.run(main())

