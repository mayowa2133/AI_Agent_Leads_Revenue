from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import san_antonio_fire_scraper


async def main():
    """
    Test San Antonio scraper with different search strategies to get actual results.
    """
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    # Try different search strategies
    strategies = [
        {"record_type": None, "days_back": 90, "name": "All records, last 90 days"},
        {"record_type": None, "days_back": 180, "name": "All records, last 180 days"},
        {"record_type": None, "days_back": 365, "name": "All records, last year"},
    ]
    
    async with tenant_scoped_session(tenant_id):
        for strategy in strategies:
            print(f"\n{'='*60}")
            print(f"Testing: {strategy['name']}")
            print(f"{'='*60}\n")
            
            scraper = san_antonio_fire_scraper(
                record_type=strategy["record_type"],
                days_back=strategy["days_back"],
            )
            
            try:
                permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
                
                if permits:
                    print(f"✅ SUCCESS! Found {len(permits)} permit(s):\n")
                    for i, p in enumerate(permits[:5], 1):  # Show first 5
                        print(f"  {i}. {p.permit_id} - {p.permit_type}")
                        print(f"     Address: {p.address}")
                        print(f"     Status: {p.status}")
                        if p.detail_url:
                            print(f"     URL: {p.detail_url}")
                        print()
                    
                    if len(permits) > 5:
                        print(f"  ... and {len(permits) - 5} more permits\n")
                    
                    print(f"✅ Strategy '{strategy['name']}' works! Exiting.")
                    return
                else:
                    print(f"❌ No permits found with strategy: {strategy['name']}\n")
            except Exception as e:
                print(f"❌ Error with strategy '{strategy['name']}': {e}\n")
                continue
        
        print("\n⚠️  None of the search strategies returned results.")
        print("   This could mean:")
        print("   - No fire permits in the date ranges tested")
        print("   - The search needs different criteria")
        print("   - Results extraction selectors need adjustment")


if __name__ == "__main__":
    asyncio.run(main())

