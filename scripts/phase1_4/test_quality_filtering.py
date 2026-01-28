"""Test Phase 1.4.4: Data Quality & Filtering."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from src.signal_engine.models import PermitData
from src.signal_engine.quality.permit_quality import PermitQualityScorer
from src.signal_engine.quality.quality_filter import QualityFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_sample_permits() -> list[PermitData]:
    """Create sample permits with varying quality."""
    now = datetime.now()
    
    return [
        # Excellent permit (has everything)
        PermitData(
            source="test_excellent",
            permit_id="EX001",
            permit_type="Fire Sprinkler Installation",
            address="123 Main St, San Antonio, TX 78201",
            status="Issued",
            applicant_name="ABC Fire Systems Inc",
            issued_date=now - timedelta(days=5),
        ),
        # Good permit (missing applicant)
        PermitData(
            source="test_good",
            permit_id="GD001",
            permit_type="Fire Alarm System",
            address="456 Oak Ave, Denver, CO 80202",
            status="Active",
            applicant_name=None,
            issued_date=now - timedelta(days=10),
        ),
        # Fair permit (incomplete address)
        PermitData(
            source="test_fair",
            permit_id="FA001",
            permit_type="Fire Suppression",
            address="789 Elm St",  # Missing city/state
            status="In Progress",
            applicant_name="XYZ Company",
            issued_date=now - timedelta(days=20),
        ),
        # Poor permit (bad address, old)
        PermitData(
            source="test_poor",
            permit_id="PO001",
            permit_type="Fire Permit",
            address="10 ft tunnel",  # Invalid address
            status="Pending",
            applicant_name=None,
            issued_date=now - timedelta(days=60),
        ),
        # Poor permit (invalid name)
        PermitData(
            source="test_poor2",
            permit_id="PO002",
            permit_type="Fire System",
            address="321 Pine St, Charlotte, NC 28201",
            status="Issued",
            applicant_name="N/A",  # Invalid name
            issued_date=now - timedelta(days=5),
        ),
        # Good permit (recent, valid)
        PermitData(
            source="test_good2",
            permit_id="GD002",
            permit_type="Sprinkler Installation",
            address="654 Maple Dr, Seattle, WA 98101",
            status="Approved",
            applicant_name="Fire Safety Corp",
            issued_date=now - timedelta(days=2),
        ),
    ]


async def test_quality_scoring():
    """Test permit quality scoring."""
    logger.info("=" * 80)
    logger.info("Testing Permit Quality Scoring")
    logger.info("=" * 80)
    logger.info("")
    
    scorer = PermitQualityScorer()
    permits = create_sample_permits()
    
    for permit in permits:
        score_result = scorer.score(permit)
        logger.info(f"Permit: {permit.permit_id}")
        logger.info(f"  Type: {permit.permit_type}")
        logger.info(f"  Address: {permit.address}")
        logger.info(f"  Applicant: {permit.applicant_name or 'None'}")
        logger.info(f"  Status: {permit.status}")
        logger.info(f"  Quality Score: {score_result.total_score:.2f}")
        logger.info(f"  Factors: {score_result.factors}")
        logger.info(f"  Should Enrich: {scorer.should_enrich(permit)}")
        logger.info("")


async def test_quality_filtering():
    """Test quality filtering."""
    logger.info("=" * 80)
    logger.info("Testing Quality Filtering")
    logger.info("=" * 80)
    logger.info("")
    
    permits = create_sample_permits()
    logger.info(f"Total permits: {len(permits)}")
    logger.info("")
    
    # Test with different thresholds
    thresholds = [0.3, 0.5, 0.7]
    
    for threshold in thresholds:
        logger.info(f"-" * 80)
        logger.info(f"Threshold: {threshold}")
        logger.info(f"-" * 80)
        
        quality_filter = QualityFilter(threshold=threshold)
        high_quality, filtered, stats = quality_filter.filter_permits_sync(permits)
        
        logger.info(f"  Passed: {stats['passed']}/{stats['total']} ({stats['passed']/stats['total']*100:.1f}%)")
        logger.info(f"  Filtered: {stats['filtered']}/{stats['total']} ({stats['filtered']/stats['total']*100:.1f}%)")
        logger.info(f"  Score Distribution:")
        logger.info(f"    Excellent (0.8-1.0): {stats['score_distribution']['excellent']}")
        logger.info(f"    Good (0.6-0.8): {stats['score_distribution']['good']}")
        logger.info(f"    Fair (0.4-0.6): {stats['score_distribution']['fair']}")
        logger.info(f"    Poor (0.0-0.4): {stats['score_distribution']['poor']}")
        logger.info("")
        
        if high_quality:
            logger.info("  High-quality permits:")
            for permit in high_quality:
                score = quality_filter.scorer.score(permit)
                logger.info(f"    - {permit.permit_id}: {score.total_score:.2f}")
        logger.info("")


async def test_real_permits():
    """Test with real permits from scrapers."""
    logger.info("=" * 80)
    logger.info("Testing with Real Permits")
    logger.info("=" * 80)
    logger.info("")
    
    from src.signal_engine.scrapers.accela_scraper import create_accela_scraper
    
    # Get real permits
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    permits = await scraper.scrape()
    
    logger.info(f"Fetched {len(permits)} real permits from San Antonio")
    logger.info("")
    
    # Apply quality filter
    quality_filter = QualityFilter(threshold=0.5)
    high_quality, filtered, stats = quality_filter.filter_permits_sync(permits)
    
    logger.info(f"Quality Filter Results:")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  Passed: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    logger.info(f"  Filtered: {stats['filtered']} ({stats['filtered']/stats['total']*100:.1f}%)")
    logger.info(f"  Score Distribution: {stats['score_distribution']}")
    logger.info("")
    
    if high_quality:
        logger.info("Sample high-quality permits:")
        for permit in high_quality[:5]:
            score = quality_filter.scorer.score(permit)
            logger.info(f"  - {permit.permit_id}: {score.total_score:.2f}")
            logger.info(f"    Type: {permit.permit_type}")
            logger.info(f"    Address: {permit.address}")
            logger.info(f"    Applicant: {permit.applicant_name or 'None'}")
            logger.info("")
    
    if filtered:
        logger.info("Sample filtered permits:")
        for permit in filtered[:3]:
            score = quality_filter.scorer.score(permit)
            logger.info(f"  - {permit.permit_id}: {score.total_score:.2f} (filtered)")
            logger.info(f"    Reason: Low quality score")
            logger.info("")


async def main():
    """Run all quality filtering tests."""
    logger.info("=" * 80)
    logger.info("PHASE 1.4.4: DATA QUALITY & FILTERING TEST")
    logger.info("=" * 80)
    logger.info("")
    
    await test_quality_scoring()
    await test_quality_filtering()
    await test_real_permits()
    
    logger.info("=" * 80)
    logger.info("✅ Quality Filtering Test Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
