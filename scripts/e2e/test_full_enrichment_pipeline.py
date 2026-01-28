"""Test full enrichment pipeline with multiple permits to find companies with websites."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
from src.signal_engine.enrichment.company_enricher import match_company, find_decision_maker
from src.signal_engine.enrichment.geocoder import geocode_address
from src.signal_engine.models import PermitData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_full_pipeline():
    """Test full enrichment pipeline with multiple permits."""
    logger.info("="*80)
    logger.info("FULL ENRICHMENT PIPELINE TEST")
    logger.info("="*80)
    logger.info("Testing with multiple permits to find companies with websites\n")
    
    # Scrape permits from multiple modules and date ranges
    test_configs = [
        {"module": "Fire", "days_back": 60},
        {"module": "Building", "days_back": 60},
        {"module": "DSD", "days_back": 90},
    ]
    
    all_permits = []
    
    for config in test_configs:
        logger.info(f"Scraping {config['module']} permits (last {config['days_back']} days)...")
        scraper = create_accela_scraper(
            city_code="COSA",
            module=config["module"],
            days_back=config["days_back"],
            max_pages=2,
            extract_applicant=True,
        )
        
        permits = await scraper.scrape()
        logger.info(f"  Found {len(permits)} permits")
        all_permits.extend(permits)
    
    # Deduplicate by permit_id
    seen = set()
    unique_permits = []
    for permit in all_permits:
        if permit.permit_id not in seen:
            seen.add(permit.permit_id)
            unique_permits.append(permit)
    
    logger.info(f"\nTotal unique permits: {len(unique_permits)}")
    
    # Show sample permits
    logger.info("\nSample permits found:")
    for permit in unique_permits[:5]:
        logger.info(f"  - {permit.permit_id}: {permit.applicant_name or '(no applicant)'} - {permit.permit_type}")
    
    # Filter permits with company names (not person names)
    permits_with_companies = []
    for permit in unique_permits:
        if permit.applicant_name and len(permit.applicant_name.strip()) > 2:
            # Check if it looks like a company (not a person name)
            name_lower = permit.applicant_name.lower()
            company_indicators = ['llc', 'inc', 'corp', 'ltd', 'company', 'co', 'systems', 'services', 'group', 'associates', 'construction', 'electric', 'plumbing', 'hvac', 'contractor']
            if any(indicator in name_lower for indicator in company_indicators):
                permits_with_companies.append(permit)
    
    logger.info(f"\nPermits with company names: {len(permits_with_companies)}")
    
    if permits_with_companies:
        logger.info("Company names found:")
        for permit in permits_with_companies[:10]:
            logger.info(f"  - {permit.applicant_name}")
    
    if not permits_with_companies:
        logger.warning("No permits with company names found!")
        return
    
    logger.info("\n" + "="*80)
    logger.info("TESTING ENRICHMENT FOR EACH COMPANY")
    logger.info("="*80 + "\n")
    
    results = {
        "total": len(permits_with_companies),
        "with_domains": 0,
        "with_emails": 0,
        "companies_with_domains": [],
        "companies_with_emails": [],
    }
    
    # Test enrichment for each permit (limit to first 10 to avoid API rate limits)
    test_permits = permits_with_companies[:10]
    logger.info(f"Testing enrichment for {len(test_permits)} companies (limited to avoid rate limits)\n")
    
    for i, permit in enumerate(test_permits, 1):
        logger.info(f"[{i}/{len(test_permits)}] Testing: {permit.applicant_name}")
        logger.info(f"  Permit ID: {permit.permit_id}")
        logger.info(f"  Type: {permit.permit_type}")
        logger.info(f"  Address: {permit.address[:60] if permit.address else '(empty)'}")
        
        try:
            # Step 1: Geocode address
            geocode_result = None
            if permit.address and len(permit.address.strip()) > 5:
                try:
                    geocode_result = await geocode_address(permit.address)
                    logger.info(f"  Location: {geocode_result.city}, {geocode_result.state}")
                except Exception as e:
                    logger.debug(f"  Geocoding failed: {e}")
            
            # Step 2: Match company (Apollo domain lookup)
            company = await match_company(permit, geocode_result)
            logger.info(f"  Company: {company.name}")
            
            if company.website:
                results["with_domains"] += 1
                domain = company.website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                logger.info(f"  ✅ Domain found: {domain}")
                results["companies_with_domains"].append({
                    "company": company.name,
                    "domain": domain,
                    "permit_id": permit.permit_id,
                })
                
                # Step 3: Find decision maker (Hunter.io email lookup)
                try:
                    decision_maker = await find_decision_maker(company, geocode_result, permit)
                    if decision_maker and decision_maker.email:
                        results["with_emails"] += 1
                        logger.info(f"  ✅ Email found: {decision_maker.email}")
                        logger.info(f"  Name: {decision_maker.name or '(not found)'}")
                        logger.info(f"  Title: {decision_maker.title or '(not found)'}")
                        results["companies_with_emails"].append({
                            "company": company.name,
                            "domain": domain,
                            "email": decision_maker.email,
                            "name": decision_maker.name,
                            "title": decision_maker.title,
                            "permit_id": permit.permit_id,
                        })
                    else:
                        logger.info(f"  ⚠️  No email found (domain available but no decision maker)")
                except Exception as e:
                    logger.warning(f"  ⚠️  Decision maker search failed: {e}")
            else:
                logger.info(f"  ⚠️  No domain found (company not in Apollo database)")
        
        except Exception as e:
            logger.error(f"  ❌ Enrichment failed: {e}")
        
        logger.info("")
    
    # Summary
    logger.info("="*80)
    logger.info("ENRICHMENT PIPELINE TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Companies Tested: {results['total']}")
    logger.info(f"Companies with Domains: {results['with_domains']}/{len(test_permits)} ({results['with_domains']/len(test_permits)*100:.1f}%)")
    logger.info(f"Companies with Emails: {results['with_emails']}/{len(test_permits)} ({results['with_emails']/len(test_permits)*100:.1f}%)")
    
    if results["companies_with_domains"]:
        logger.info(f"\n✅ Companies with Domains ({len(results['companies_with_domains'])}):")
        for item in results["companies_with_domains"]:
            logger.info(f"  - {item['company']} → {item['domain']} (Permit: {item['permit_id']})")
    
    if results["companies_with_emails"]:
        logger.info(f"\n🎯 Companies with Emails ({len(results['companies_with_emails'])}):")
        for item in results["companies_with_emails"]:
            logger.info(f"  - {item['company']} → {item['email']}")
            logger.info(f"    Name: {item['name']}, Title: {item['title']}")
            logger.info(f"    Permit: {item['permit_id']}")
    else:
        logger.info("\n⚠️  No emails found. This could be because:")
        logger.info("  1. Companies don't have websites in Apollo's database")
        logger.info("  2. Hunter.io couldn't find emails for the decision makers")
        logger.info("  3. Need person names (not just company names) to find emails")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
