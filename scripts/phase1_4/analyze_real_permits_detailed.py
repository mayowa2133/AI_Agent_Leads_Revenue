"""Detailed analysis of real permits to understand why they're failing."""

from __future__ import annotations

import asyncio
import logging

from src.signal_engine.quality.permit_quality import PermitQualityScorer
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Analyze real permits in detail."""
    logger.info("=" * 80)
    logger.info("Detailed Analysis of Real Permits")
    logger.info("=" * 80)
    logger.info("")
    
    # Get real permits from multiple cities
    cities = [
        ("COSA", "San Antonio, TX", "Fire"),
        ("DENVER", "Denver, CO", "Fire"),
        ("CHARLOTTE", "Charlotte, NC", "Fire"),
    ]
    
    all_permits = []
    
    for city_code, city_name, module in cities:
        logger.info(f"Fetching permits from {city_name}...")
        try:
            scraper = create_accela_scraper(city_code, module, None, days_back=120)
            permits = await scraper.scrape()
            logger.info(f"  Got {len(permits)} permits")
            for permit in permits:
                permit.source = f"{city_name}_{permit.source}"
            all_permits.extend(permits)
        except Exception as e:
            logger.warning(f"  Error: {e}")
    
    logger.info("")
    logger.info(f"Total permits: {len(all_permits)}")
    logger.info("")
    
    scorer = PermitQualityScorer()
    
    # Analyze each permit
    logger.info("=" * 80)
    logger.info("Permit Analysis")
    logger.info("=" * 80)
    logger.info("")
    
    for i, permit in enumerate(all_permits[:10], 1):
        score_result = scorer.score(permit)
        
        logger.info(f"Permit {i}: {permit.permit_id}")
        logger.info(f"  Source: {permit.source}")
        logger.info(f"  Type: '{permit.permit_type}'")
        logger.info(f"  Address: '{permit.address}'")
        logger.info(f"  Applicant: '{permit.applicant_name or 'None'}'")
        logger.info(f"  Status: '{permit.status}'")
        logger.info(f"  Issued: {permit.issued_date or 'None'}")
        logger.info(f"  Score: {score_result.total_score:.2f}")
        logger.info(f"  Breakdown:")
        logger.info(f"    - Has Applicant ({score_result.has_applicant}): {0.3 if score_result.has_applicant else 0.0}")
        logger.info(f"    - Complete Address ({score_result.has_complete_address}): {0.2 if score_result.has_complete_address else 0.0}")
        logger.info(f"    - Valid Permit Type ({score_result.has_valid_permit_type}): {0.2 if score_result.has_valid_permit_type else 0.0}")
        logger.info(f"    - Recent ({score_result.is_recent}): {0.1 if score_result.is_recent else 0.0}")
        logger.info(f"    - Good Status ({score_result.has_good_status}): {0.1 if score_result.has_good_status else 0.0}")
        logger.info("")
    
    # Summary statistics
    scores = [scorer.score(p).total_score for p in all_permits]
    
    has_applicant_count = sum(1 for p in all_permits if p.applicant_name and len(p.applicant_name.strip()) > 3)
    has_good_address_count = sum(1 for p in all_permits if p.address and len(p.address.strip()) > 10)
    has_fire_type_count = sum(1 for p in all_permits if p.permit_type and any(kw in p.permit_type.lower() for kw in ["fire", "sprinkler", "alarm", "suppression"]))
    is_recent_count = sum(1 for p in all_permits if scorer.score(p).is_recent)
    has_good_status_count = sum(1 for p in all_permits if scorer.score(p).has_good_status)
    
    logger.info("=" * 80)
    logger.info("Summary Statistics")
    logger.info("=" * 80)
    logger.info(f"Total Permits: {len(all_permits)}")
    logger.info(f"Average Score: {sum(scores)/len(scores):.2f}")
    logger.info(f"Min Score: {min(scores):.2f}")
    logger.info(f"Max Score: {max(scores):.2f}")
    logger.info("")
    logger.info("Factor Breakdown:")
    logger.info(f"  Has Applicant: {has_applicant_count}/{len(all_permits)} ({has_applicant_count/len(all_permits)*100:.1f}%)")
    logger.info(f"  Good Address: {has_good_address_count}/{len(all_permits)} ({has_good_address_count/len(all_permits)*100:.1f}%)")
    logger.info(f"  Fire-Related Type: {has_fire_type_count}/{len(all_permits)} ({has_fire_type_count/len(all_permits)*100:.1f}%)")
    logger.info(f"  Recent: {is_recent_count}/{len(all_permits)} ({is_recent_count/len(all_permits)*100:.1f}%)")
    logger.info(f"  Good Status: {has_good_status_count}/{len(all_permits)} ({has_good_status_count/len(all_permits)*100:.1f}%)")
    logger.info("")
    logger.info("Recommendations:")
    logger.info("  1. Make permit type check more lenient (check source module)")
    logger.info("  2. Lower threshold to 0.3 for real-world data")
    logger.info("  3. Give partial credit for addresses that are close to valid")
    logger.info("  4. Accept more status values as 'good'")


if __name__ == "__main__":
    asyncio.run(main())
