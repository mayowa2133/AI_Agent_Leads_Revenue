"""Check what data we've actually extracted from permits."""

from __future__ import annotations

import asyncio
import json
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

async def check_extracted_data():
    """Check what data we've actually extracted."""
    scraper = create_accela_scraper(
        city_code="COSA",
        module="Fire",
        days_back=30,
        max_pages=1,
        extract_applicant=True,
    )
    
    print("Scraping permits...")
    permits = await scraper.scrape()
    
    print(f"\n{'='*80}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*80}\n")
    
    print(f"Total Permits: {len(permits)}\n")
    
    # Check addresses
    has_address = [p for p in permits if p.address and len(p.address.strip()) > 5]
    valid_addresses = [p for p in has_address if not any(skip in p.address.lower() for skip in ['location', 'applicant:', 'n/a', 'none', 'tunnel', 'tops'])]
    
    print(f"Addresses:")
    print(f"  - With any address text: {len(has_address)}/{len(permits)}")
    print(f"  - With valid addresses: {len(valid_addresses)}/{len(permits)}")
    if valid_addresses:
        print(f"  - Sample valid addresses:")
        for p in valid_addresses[:3]:
            print(f"    * {p.permit_id}: {p.address[:80]}")
    
    # Check applicant names
    has_applicant = [p for p in permits if p.applicant_name and len(p.applicant_name.strip()) > 2]
    valid_applicants = [p for p in has_applicant if not any(skip in p.applicant_name.lower() for skip in ['applicant:', 'location', 'due on', 'assigned to', 'marked as'])]
    
    print(f"\nApplicant Names:")
    print(f"  - With any applicant text: {len(has_applicant)}/{len(permits)}")
    print(f"  - With valid applicant names: {len(valid_applicants)}/{len(permits)}")
    if valid_applicants:
        print(f"  - Sample valid applicants:")
        for p in valid_applicants[:3]:
            print(f"    * {p.permit_id}: {p.applicant_name[:80]}")
    
    # Show all extracted data
    print(f"\n{'='*80}")
    print(f"DETAILED EXTRACTION DATA")
    print(f"{'='*80}\n")
    
    for i, permit in enumerate(permits[:5], 1):
        print(f"{i}. Permit ID: {permit.permit_id}")
        print(f"   Type: {permit.permit_type}")
        print(f"   Status: {permit.status}")
        print(f"   Address: '{permit.address}' (length: {len(permit.address) if permit.address else 0})")
        print(f"   Applicant: '{permit.applicant_name}' (length: {len(permit.applicant_name) if permit.applicant_name else 0})")
        print(f"   Detail URL: {permit.detail_url[:80] if permit.detail_url else 'None'}...")
        print()
    
    # Check for emails (shouldn't be any, but let's check)
    emails_found = []
    for p in permits:
        if p.address and '@' in p.address:
            emails_found.append((p.permit_id, p.address))
        if p.applicant_name and '@' in p.applicant_name:
            emails_found.append((p.permit_id, p.applicant_name))
    
    if emails_found:
        print(f"\n⚠️  Found {len(emails_found)} potential emails (likely false positives):")
        for permit_id, text in emails_found:
            print(f"  - {permit_id}: {text[:80]}")
    else:
        print(f"\n✅ No emails found in extracted data (expected - emails come from enrichment, not scraping)")

if __name__ == "__main__":
    asyncio.run(check_extracted_data())
