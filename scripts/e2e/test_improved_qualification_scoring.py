"""Test improved qualification scoring with real permits."""

from __future__ import annotations

import asyncio
import logging

from src.agents.orchestrator import qualification_check_node
from src.agents.state import AOROState
from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.scrapers.accela_scraper import create_accela_scraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_improved_scoring():
    """Test improved qualification scoring."""
    logger.info("=" * 80)
    logger.info("TESTING IMPROVED QUALIFICATION SCORING")
    logger.info("=" * 80)
    logger.info("")
    
    # Get real permits
    logger.info("Fetching real permits...")
    scraper = create_accela_scraper("COSA", "Fire", None, days_back=120)
    scraper_permits = await scraper.scrape()
    
    client = SocrataPermitClient(
        portal_url="https://data.seattle.gov",
        dataset_id="76t5-zqzr",
        field_mapping={
            "permit_id": "permitnum",
            "permit_type": "permittypedesc",
            "address": "originaladdress1",
            "status": "statuscurrent",
        },
    )
    api_permits = await client.get_permits(days_back=30, limit=5)
    
    all_permits = scraper_permits[:5] + api_permits[:3]
    
    logger.info(f"Testing with {len(all_permits)} permits")
    logger.info("")
    
    # Test scoring
    logger.info("=" * 80)
    logger.info("Qualification Score Results")
    logger.info("=" * 80)
    logger.info("")
    
    scores = []
    
    for i, permit in enumerate(all_permits, 1):
        logger.info(f"Permit {i}: {permit.permit_id}")
        logger.info(f"  Type: '{permit.permit_type}'")
        logger.info(f"  Status: '{permit.status}'")
        logger.info(f"  Source: '{permit.source}'")
        
        # Create state
        state: AOROState = {
            "lead_id": f"test_{i}",
            "tenant_id": "test",
            "company_name": "Test Company",
            "decision_maker": {},  # No decision maker for now
            "permit_data": {
                "permit_id": permit.permit_id,
                "permit_type": permit.permit_type,
                "status": permit.status,
                "address": permit.address,
                "source": permit.source,
            },
        }
        
        # Calculate score
        result = await qualification_check_node(state)
        score = result.get("qualification_score", 0.0)
        scores.append(score)
        
        logger.info(f"  Qualification Score: {score:.2f}")
        
        # Explain score
        if score >= 0.5:
            logger.info(f"  ✅ PASSES threshold (0.5)")
        else:
            logger.info(f"  ❌ Below threshold (0.5)")
        
        logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info(f"Total Permits Tested: {len(all_permits)}")
    logger.info(f"Average Score: {sum(scores)/len(scores):.2f}")
    logger.info(f"Min Score: {min(scores):.2f}")
    logger.info(f"Max Score: {max(scores):.2f}")
    logger.info(f"Passing (>=0.5): {sum(1 for s in scores if s >= 0.5)}/{len(scores)} ({sum(1 for s in scores if s >= 0.5)/len(scores)*100:.1f}%)")
    logger.info("")
    
    if sum(1 for s in scores if s >= 0.5) > 0:
        logger.info("✅ Improved scoring is working! Some permits now pass.")
    else:
        logger.info("⚠️  Still no permits passing. May need further adjustments.")


if __name__ == "__main__":
    asyncio.run(test_improved_scoring())
