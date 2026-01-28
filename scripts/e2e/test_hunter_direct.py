"""Test Hunter.io directly with a known domain to verify email finding works."""

from __future__ import annotations

import asyncio
import logging
from src.signal_engine.enrichment.hunter_client import HunterClient
from src.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_hunter_direct():
    """Test Hunter.io directly with a known domain."""
    logger.info("="*80)
    logger.info("DIRECT HUNTER.IO TEST")
    logger.info("="*80)
    logger.info("Testing Hunter.io email finder with known domains\n")
    
    config = get_settings()
    
    if not config.hunter_api_key:
        logger.error("❌ Hunter API key not configured!")
        return
    
    logger.info(f"Hunter API Key: {'✅ Configured' if config.hunter_api_key else '❌ Not configured'}")
    logger.info(f"Dry Run Mode: {config.enrichment_dry_run}\n")
    
    # Test with known companies that have domains
    test_cases = [
        {
            "domain": "cbre.com",
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
        },
        {
            "domain": "jll.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "full_name": "Jane Doe",
        },
        {
            "domain": "turnerconstruction.com",
            "first_name": "Mike",
            "last_name": "Johnson",
            "full_name": "Mike Johnson",
        },
    ]
    
    hunter = HunterClient(api_key=config.hunter_api_key, dry_run=config.enrichment_dry_run)
    
    results = {
        "total": 0,
        "with_emails": 0,
        "emails_found": [],
    }
    
    try:
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"[{i}/{len(test_cases)}] Testing: {test_case['domain']}")
            logger.info(f"  Name: {test_case['full_name']}")
            
            results["total"] += 1
            
            try:
                email_result = await hunter.find_email(
                    domain=test_case["domain"],
                    first_name=test_case["first_name"],
                    last_name=test_case["last_name"],
                    full_name=test_case["full_name"],
                )
                
                if email_result and email_result.email:
                    results["with_emails"] += 1
                    logger.info(f"  ✅ Email found: {email_result.email}")
                    logger.info(f"  Confidence: {email_result.score}%")
                    results["emails_found"].append({
                        "domain": test_case["domain"],
                        "name": test_case["full_name"],
                        "email": email_result.email,
                        "score": email_result.score,
                    })
                else:
                    logger.info(f"  ⚠️  No email found")
            except Exception as e:
                logger.error(f"  ❌ Error: {e}")
            
            logger.info("")
    
    finally:
        await hunter.aclose()
    
    # Summary
    logger.info("="*80)
    logger.info("HUNTER.IO TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Tests: {results['total']}")
    logger.info(f"Emails Found: {results['with_emails']}/{results['total']} ({results['with_emails']/results['total']*100:.1f}%)")
    
    if results["emails_found"]:
        logger.info(f"\n✅ Emails Found ({len(results['emails_found'])}):")
        for item in results["emails_found"]:
            logger.info(f"  - {item['name']} @ {item['domain']} → {item['email']} (confidence: {item['score']}%)")
        logger.info("\n🎯 HUNTER.IO IS WORKING! The pipeline can find emails when we have:")
        logger.info("   1. Company domain ✅")
        logger.info("   2. Person name ✅")
    else:
        logger.info("\n⚠️  No emails found. This could be because:")
        logger.info("   1. Dry run mode is enabled (no real API calls)")
        logger.info("   2. Hunter.io couldn't find emails for these names")
        logger.info("   3. Need real person names (not test names)")


if __name__ == "__main__":
    asyncio.run(test_hunter_direct())
