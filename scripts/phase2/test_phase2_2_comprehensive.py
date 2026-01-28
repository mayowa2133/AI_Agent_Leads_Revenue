"""Comprehensive Phase 2.2 test suite - runs all tests in sequence."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_all_tests():
    """Run all Phase 2.2 tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2.2: Comprehensive Test Suite")
    logger.info("=" * 70 + "\n")
    
    tests = [
        ("Response Handling Components", "scripts/phase2/test_phase2_2_response_handling.py"),
        ("Workflow Integration", "scripts/phase2/test_phase2_2_workflow_integration.py"),
    ]
    
    results = []
    
    for test_name, test_script in tests:
        logger.info(f"\n{'='*70}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*70}\n")
        
        try:
            result = subprocess.run(
                [sys.executable, test_script],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(result.stdout)
            results.append((test_name, True, None))
            logger.info(f"\n✓ {test_name} PASSED\n")
        except subprocess.CalledProcessError as e:
            logger.error(f"\n✗ {test_name} FAILED")
            logger.error(e.stdout)
            logger.error(e.stderr)
            results.append((test_name, False, str(e)))
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("Test Summary")
    logger.info("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"  {status}: {test_name}")
        if error:
            logger.error(f"    Error: {error}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n" + "=" * 70)
        logger.info("🎉 ALL PHASE 2.2 TESTS PASSED!")
        logger.info("=" * 70)
        logger.info("\nPhase 2.2 Components Verified:")
        logger.info("  ✓ Response Storage (save/retrieve)")
        logger.info("  ✓ WaitForResponse Node (response detection, timeout)")
        logger.info("  ✓ HandleResponse Node (classification, sentiment, objections)")
        logger.info("  ✓ Webhook Handler (email response endpoint)")
        logger.info("  ✓ Workflow Integration (nodes in graph, routing)")
        logger.info("  ✓ State Schema (response fields)")
        logger.info("\nPhase 2.2 is FULLY IMPLEMENTED and TESTED! ✅")
        return 0
    else:
        logger.error("\n" + "=" * 70)
        logger.error("❌ SOME TESTS FAILED")
        logger.error("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
