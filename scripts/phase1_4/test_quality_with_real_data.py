"""Test quality filtering with real data to see score breakdown."""

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
    """Test quality scoring with real permits to understand scores."""
    logger.info("=" * 80)
    logger.info("Quality Scoring Analysis - Real Permits")
    logger.info("=" * 80)
    logger.info("")
    
    # Get real permits
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    permits = await scraper.scrape()
    
    logger.info(f"Fetched {len(permits)} permits from San Antonio")
    logger.info("")
    
    scorer = PermitQualityScorer()
    
    # Analyze each permit
    for i, permit in enumerate(permits[:5], 1):
        score_result = scorer.score(permit)
        
        logger.info(f"Permit {i}: {permit.permit_id}")
        logger.info(f"  Type: {permit.permit_type}")
        logger.info(f"  Address: {permit.address}")
        logger.info(f"  Applicant: {permit.applicant_name or 'None'}")
        logger.info(f"  Status: {permit.status}")
        logger.info(f"  Issued Date: {permit.issued_date or 'None'}")
        logger.info(f"  Quality Score: {score_result.total_score:.2f}")
        logger.info(f"  Factors:")
        logger.info(f"    - Has Applicant: {score_result.has_applicant} (+0.3)")
        logger.info(f"    - Complete Address: {score_result.has_complete_address} (+0.2)")
        logger.info(f"    - Valid Permit Type: {score_result.has_valid_permit_type} (+0.2)")
        logger.info(f"    - Recent: {score_result.is_recent} (+0.1)")
        logger.info(f"    - Good Status: {score_result.has_good_status} (+0.1)")
        logger.info(f"  Should Enrich (threshold 0.5): {scorer.should_enrich(permit, 0.5)}")
        logger.info("")
    
    # Summary
    scores = [scorer.score(p).total_score for p in permits]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info(f"Average Quality Score: {avg_score:.2f}")
    logger.info(f"Min Score: {min(scores):.2f}")
    logger.info(f"Max Score: {max(scores):.2f}")
    logger.info("")
    logger.info("Recommendation: Adjust threshold or scoring weights based on real data patterns")


if __name__ == "__main__":
    asyncio.run(main())
