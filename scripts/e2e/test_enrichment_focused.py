"""Focused test of enrichment pipeline with known companies."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.enrichment.company_enricher import match_company, find_decision_maker
from src.signal_engine.enrichment.geocoder import geocode_address
from src.signal_engine.models import PermitData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_enrichment_focused():
    """Test enrichment with a focused set of test companies."""
    logger.info("="*80)
    logger.info("FOCUSED ENRICHMENT PIPELINE TEST")
    logger.info("="*80)
    logger.info("Testing with companies that are more likely to have websites\n")
    
    # Test with companies that are more likely to be in Apollo's database
    # These are larger companies that typically have websites
    test_companies = [
        {
            "name": "TX Septic Systems LLC",
            "address": "109 TERESA ST, San Antonio, TX",
            "permit_id": "TEST-001",
        },
        # Add more test cases with companies that might have websites
        # We'll test with real permits we've scraped
    ]
    
    logger.info("Testing enrichment for known companies...\n")
    
    results = {
        "total": 0,
        "with_domains": 0,
        "with_emails": 0,
        "companies_with_domains": [],
        "companies_with_emails": [],
    }
    
    for i, test_data in enumerate(test_companies, 1):
        logger.info(f"[{i}/{len(test_companies)}] Testing: {test_data['name']}")
        
        # Create test permit
        permit = PermitData(
            source="test",
            permit_id=test_data["permit_id"],
            permit_type="Test Permit",
            address=test_data["address"],
            building_type=None,
            status="issued",
            applicant_name=test_data["name"],
            issued_date=None,
            detail_url=None,
        )
        
        results["total"] += 1
        
        try:
            # Step 1: Geocode address
            geocode_result = None
            if permit.address:
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
    
    # Now test with real scraped permits
    logger.info("="*80)
    logger.info("TESTING WITH REAL SCRAPED PERMITS")
    logger.info("="*80 + "\n")
    
    from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
    
    # Scrape permits from multiple cities that might have more companies with websites
    cities_to_test = [
        {"code": "COSA", "name": "San Antonio, TX"},
        # Add more cities if needed
    ]
    
    for city in cities_to_test:
        logger.info(f"Scraping permits from {city['name']}...")
        scraper = create_accela_scraper(
            city_code=city["code"],
            module="Fire",  # Start with Fire permits
            days_back=90,
            max_pages=1,
            extract_applicant=True,
        )
        
        permits = await scraper.scrape()
        logger.info(f"  Found {len(permits)} permits")
        
        # Filter for companies (not person names)
        company_permits = []
        for permit in permits:
            if permit.applicant_name and len(permit.applicant_name.strip()) > 2:
                name_lower = permit.applicant_name.lower()
                company_indicators = ['llc', 'inc', 'corp', 'ltd', 'company', 'co', 'systems', 'services', 'group', 'associates', 'construction', 'electric', 'plumbing', 'hvac', 'contractor', 'contractors']
                if any(indicator in name_lower for indicator in company_indicators):
                    company_permits.append(permit)
        
        logger.info(f"  Found {len(company_permits)} permits with company names")
        
        # Test enrichment for first 5 companies (to avoid rate limits)
        for permit in company_permits[:5]:
            logger.info(f"\nTesting: {permit.applicant_name}")
            logger.info(f"  Permit ID: {permit.permit_id}")
            logger.info(f"  Address: {permit.address[:60] if permit.address else '(empty)'}")
            
            results["total"] += 1
            
            try:
                # Geocode
                geocode_result = None
                if permit.address and len(permit.address.strip()) > 5:
                    try:
                        geocode_result = await geocode_address(permit.address)
                    except:
                        pass
                
                # Match company
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
                    
                    # Find decision maker
                    try:
                        decision_maker = await find_decision_maker(company, geocode_result, permit)
                        if decision_maker and decision_maker.email:
                            results["with_emails"] += 1
                            logger.info(f"  ✅ Email found: {decision_maker.email}")
                            results["companies_with_emails"].append({
                                "company": company.name,
                                "domain": domain,
                                "email": decision_maker.email,
                                "name": decision_maker.name,
                                "title": decision_maker.title,
                                "permit_id": permit.permit_id,
                            })
                    except Exception as e:
                        logger.debug(f"  Decision maker search: {e}")
                else:
                    logger.info(f"  ⚠️  No domain found")
            except Exception as e:
                logger.error(f"  ❌ Failed: {e}")
    
    # Final Summary
    logger.info("\n" + "="*80)
    logger.info("FINAL ENRICHMENT TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Companies Tested: {results['total']}")
    if results['total'] > 0:
        logger.info(f"Companies with Domains: {results['with_domains']}/{results['total']} ({results['with_domains']/results['total']*100:.1f}%)")
        logger.info(f"Companies with Emails: {results['with_emails']}/{results['total']} ({results['with_emails']/results['total']*100:.1f}%)")
    
    if results["companies_with_domains"]:
        logger.info(f"\n✅ Companies with Domains ({len(results['companies_with_domains'])}):")
        for item in results["companies_with_domains"]:
            logger.info(f"  - {item['company']} → {item['domain']}")
    
    if results["companies_with_emails"]:
        logger.info(f"\n🎯 Companies with Emails ({len(results['companies_with_emails'])}):")
        for item in results["companies_with_emails"]:
            logger.info(f"  - {item['company']} → {item['email']}")
            logger.info(f"    Name: {item['name']}, Title: {item['title']}")
    else:
        logger.info("\n⚠️  No emails found in this test batch.")


if __name__ == "__main__":
    asyncio.run(test_enrichment_focused())
