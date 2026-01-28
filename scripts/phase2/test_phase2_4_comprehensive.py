"""Comprehensive Phase 2.4 test - end-to-end workflow with monitoring."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.agents.monitoring import NodeExecutionTracker, get_metrics
from src.agents.orchestrator import build_graph
from src.agents.state import AOROState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_complete_workflow_with_monitoring():
    """Test complete workflow with monitoring enabled."""
    logger.info("=" * 70)
    logger.info("Phase 2.4: Comprehensive End-to-End Test with Monitoring")
    logger.info("=" * 70 + "\n")

    graph = build_graph()
    metrics = get_metrics()

    # Create test lead
    lead_id = f"test-e2e-monitoring-{int(datetime.now().timestamp())}"
    state: AOROState = {
        "lead_id": lead_id,
        "tenant_id": "test-tenant",
        "company_name": "E2E Test Company",
        "permit_data": {
            "permit_id": "E2E-001",
            "permit_type": "Fire Alarm Installation",
            "status": "Issued",
            "address": "123 Test St, San Antonio, TX",
        },
        "decision_maker": {
            "full_name": "Test Manager",
            "email": "test.manager@testcompany.com",
            "title": "Facilities Manager",
        },
        "outreach_channel": "email",
        "response_history": [],
    }

    logger.info(f"Lead ID: {lead_id}")
    logger.info(f"Company: {state['company_name']}")

    # Run workflow with monitoring
    logger.info("\n[Step 1] Running complete workflow with monitoring...")
    start_time = datetime.now()

    try:
        result = await graph.ainvoke(state)
        execution_time = (datetime.now() - start_time).total_seconds()

        # Record workflow execution
        nodes_executed = []
        if result.get("qualification_score") is not None:
            nodes_executed.append("QualificationCheck")
        if result.get("compliance_urgency_score") is not None:
            nodes_executed.append("Research")
        if result.get("outreach_draft"):
            nodes_executed.append("DraftOutreach")
        if result.get("outreach_sent_at"):
            nodes_executed.append("SendOutreach")

        workflow_status = result.get("workflow_status") or "in_progress"
        metrics.record_workflow_execution(
            lead_id=lead_id,
            workflow_status=workflow_status,
            total_time=execution_time,
            nodes_executed=nodes_executed,
        )

        logger.info(f"\n[Results]")
        logger.info(f"  ✓ Workflow completed in {execution_time:.2f}s")
        logger.info(f"  ✓ Qualification Score: {result.get('qualification_score', 0):.2f}")
        logger.info(f"  ✓ Compliance Urgency: {result.get('compliance_urgency_score', 0):.2f}")
        logger.info(f"  ✓ Outreach Sent: {result.get('outreach_sent_at') is not None}")
        logger.info(f"  ✓ Nodes Executed: {len(nodes_executed)}")

        # Get metrics summary
        stats = metrics.get_workflow_stats()
        logger.info(f"\n[Metrics Summary]")
        logger.info(f"  Total Workflows: {stats['total_workflows']}")
        logger.info(f"  Average Time: {stats['avg_workflow_time']:.2f}s")

        logger.info("\n✓ Complete workflow test passed!")
        return True

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"✗ Workflow failed: {e}", exc_info=True)

        # Record failed workflow
        metrics.record_workflow_execution(
            lead_id=lead_id,
            workflow_status="failed",
            total_time=execution_time,
            nodes_executed=[],
        )

        return False


async def main():
    """Run comprehensive Phase 2.4 test."""
    try:
        success = await test_complete_workflow_with_monitoring()

        if success:
            logger.info("\n" + "=" * 70)
            logger.info("🎉 PHASE 2.4 COMPREHENSIVE TEST PASSED!")
            logger.info("=" * 70)
            return 0
        else:
            logger.error("\n" + "=" * 70)
            logger.error("❌ TEST FAILED")
            logger.error("=" * 70)
            return 1

    except Exception as e:
        logger.error(f"✗ Test suite failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
