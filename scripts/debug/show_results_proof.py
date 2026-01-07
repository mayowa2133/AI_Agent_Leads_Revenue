from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import mecklenburg_county_scraper


async def main():
    """Show proof that Mecklenburg scraper works with actual results"""
    print("\n" + "="*70)
    print("PROOF: MECKLENBURG SCRAPER EXTRACTS REAL PERMITS")
    print("="*70)
    
    tenant_id = os.environ.get("TENANT_ID", "demo")
    
    async with tenant_scoped_session(tenant_id):
        scraper = mecklenburg_county_scraper(
            search_type="project_name",
            search_value="Building",
        )
        
        print("\n🔍 Searching for permits with project name 'Building'...")
        print("   (This is a broad search that should return many results)\n")
        
        permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
        
        if permits:
            print(f"✅ SUCCESS! Found {len(permits)} permit(s)\n")
            print("="*70)
            print("SAMPLE PERMITS (First 20):")
            print("="*70 + "\n")
            
            for i, p in enumerate(permits[:20], 1):
                print(f"Permit #{i}:")
                print(f"  ID: {p.permit_id}")
                print(f"  Type: {p.permit_type}")
                print(f"  Address: {p.address}")
                print(f"  Status: {p.status}")
                if p.detail_url:
                    print(f"  Detail URL: {p.detail_url}")
                print()
            
            if len(permits) > 20:
                print(f"... and {len(permits) - 20} more permits\n")
            
            print("="*70)
            print("STATISTICS:")
            print("="*70)
            
            # Count by status
            status_counts = {}
            for p in permits:
                status = p.status or "Unknown"
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("\nBy Status:")
            for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {status}: {count}")
            
            # Count fire-related permits
            fire_permits = [p for p in permits if "fire" in p.permit_type.lower() or "Fire" in p.permit_type]
            print(f"\nFire-related permits: {len(fire_permits)}")
            if fire_permits:
                print("\nFire Permit Examples:")
                for p in fire_permits[:5]:
                    print(f"  - {p.permit_id}: {p.permit_type} ({p.status})")
            
            print("\n" + "="*70)
            print("✅ PROOF: Scraper successfully extracts real permit data!")
            print("="*70 + "\n")
        else:
            print("❌ No permits found")


if __name__ == "__main__":
    asyncio.run(main())

