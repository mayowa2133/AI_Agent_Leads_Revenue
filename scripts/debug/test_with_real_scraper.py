from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper, san_antonio_fire_scraper


async def test_mecklenburg_real():
    """Test with actual scraper class"""
    print("\n" + "="*60)
    print("MECKLENBURG - USING ACTUAL SCRAPER CLASS")
    print("="*60)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        # Try multiple search strategies
        strategies = [
            {"type": "project_name", "value": "Building", "street": None},
            {"type": "project_name", "value": "Fire", "street": None},
            {"type": "address", "value": "MAIN", "street": "100"},
            {"type": "address", "value": "TRADE", "street": "200"},
        ]
        
        for strategy in strategies:
            print(f"\n--- Trying: {strategy['type']} = '{strategy['value']}' ---")
            
            scraper = mecklenburg_county_scraper(
                search_type=strategy["type"],
                search_value=strategy["value"],
                street_number=strategy["street"],
            )
            
            try:
                permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
                
                if permits:
                    print(f"\n✅ SUCCESS! Found {len(permits)} permit(s):\n")
                    for i, p in enumerate(permits[:10], 1):
                        print(f"  {i}. Permit ID: {p.permit_id}")
                        print(f"     Type: {p.permit_type}")
                        print(f"     Address: {p.address}")
                        print(f"     Status: {p.status}")
                        if p.detail_url:
                            print(f"     URL: {p.detail_url}")
                        print()
                    return True
                else:
                    print(f"❌ No permits found")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        return False


async def test_san_antonio_real():
    """Test with actual scraper class - try different approaches"""
    print("\n" + "="*60)
    print("SAN ANTONIO - USING ACTUAL SCRAPER CLASS")
    print("="*60)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        # Try different strategies
        strategies = [
            {"record_type": None, "days_back": 365, "name": "All types, last year"},
            {"record_type": None, "days_back": 730, "name": "All types, last 2 years"},
            {"record_type": "Adult Day Care Permit", "days_back": 365, "name": "Adult Day Care, last year"},
        ]
        
        for strategy in strategies:
            print(f"\n--- Trying: {strategy['name']} ---")
            
            scraper = san_antonio_fire_scraper(
                record_type=strategy["record_type"],
                days_back=strategy["days_back"],
            )
            
            try:
                permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
                
                if permits:
                    print(f"\n✅ SUCCESS! Found {len(permits)} permit(s):\n")
                    for i, p in enumerate(permits[:10], 1):
                        print(f"  {i}. Permit ID: {p.permit_id}")
                        print(f"     Type: {p.permit_type}")
                        print(f"     Address: {p.address}")
                        print(f"     Status: {p.status}")
                        if p.detail_url:
                            print(f"     URL: {p.detail_url}")
                        print()
                    return True
                else:
                    print(f"❌ No permits found")
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        return False


async def main():
    """Run both tests"""
    meck_success = await test_mecklenburg_real()
    sa_success = await test_san_antonio_real()
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Mecklenburg: {'✅ FOUND RESULTS' if meck_success else '❌ No results'}")
    print(f"San Antonio: {'✅ FOUND RESULTS' if sa_success else '❌ No results'}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

