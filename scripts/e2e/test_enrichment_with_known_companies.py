"""Test enrichment pipeline with known companies that have websites."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.enrichment.company_enricher import match_company, find_decision_maker
from src.signal_engine.enrichment.geocoder import geocode_address
from src.signal_engine.models import PermitData

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_known_companies():
    """Test enrichment with companies that are known to have websites."""
    logger.info("="*80)
    logger.info("TESTING ENRICHMENT WITH KNOWN COMPANIES")
    logger.info("="*80)
    logger.info("Testing with companies that are likely to be in Apollo's database\n")
    
    # Test with companies that are more likely to have websites in Apollo
    # These are larger companies or well-known contractors
    test_companies = [
        {
            "name": "Turner Construction",
            "address": "New York, NY",
            "permit_id": "TEST-TURNER",
        },
        {
            "name": "Fluor Corporation",
            "address": "Irving, TX",
            "permit_id": "TEST-FLUOR",
        },
        {
            "name": "CBRE",
            "address": "Dallas, TX",
            "permit_id": "TEST-CBRE",
        },
        {
            "name": "JLL",
            "address": "Chicago, IL",
            "permit_id": "TEST-JLL",
        },
        {
            "name": "Cushman & Wakefield",
            "address": "New York, NY",
            "permit_id": "TEST-CW",
        },
    ]
    
    results = {
        "total": 0,
        "with_domains": 0,
        "with_emails": 0,
        "companies_with_domains": [],
        "companies_with_emails": [],
    }
    
    for i, test_data in enumerate(test_companies, 1):
        logger.info(f"[{i}/{len(test_companies)}] Testing: {test_data['name']}")
        logger.info(f"  Address: {test_data['address']}")
        
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
            logger.info(f"  Searching Apollo for company domain...")
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
                logger.info(f"  Searching Hunter.io for decision maker email...")
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
    logger.info("ENRICHMENT TEST SUMMARY")
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
            logger.info(f"    ✅ FULL PIPELINE WORKING!")
    else:
        logger.info("\n⚠️  No emails found. Possible reasons:")
        logger.info("  1. Companies not in Apollo database")
        logger.info("  2. Hunter.io couldn't find decision makers")
        logger.info("  3. Need person names (not just company names) to find emails")


if __name__ == "__main__":
    asyncio.run(test_known_companies())
