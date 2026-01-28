"""Test Phase 2.4: Workflow Monitoring & Observability."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from src.agents.monitoring import NodeExecutionTracker, WorkflowMetrics, get_metrics
from src.agents.nodes.researcher import researcher_node
from src.agents.state import AOROState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_node_execution_tracking():
    """Test node execution tracking."""
    logger.info("=" * 70)
    logger.info("Test 1: Node Execution Tracking")
    logger.info("=" * 70)

    metrics = get_metrics()

    # Test successful execution
    logger.info("\n[Test 1a] Tracking successful node execution")
    lead_id = f"test-monitoring-{int(datetime.now().timestamp())}"

    with NodeExecutionTracker("TestNode", lead_id):
        # Simulate node execution
        await asyncio.sleep(0.1)

    stats = metrics.get_node_stats("TestNode")
    assert stats["total_executions"] > 0, "Should have recorded execution"
    assert stats["success_count"] > 0, "Should have recorded success"
    logger.info(f"  ✓ Executions recorded: {stats['total_executions']}")
    logger.info(f"  ✓ Success rate: {stats['success_rate']:.1f}%")
    logger.info(f"  ✓ Avg execution time: {stats['avg_execution_time']:.3f}s")

    # Test failed execution
    logger.info("\n[Test 1b] Tracking failed node execution")
    try:
        with NodeExecutionTracker("TestNode", lead_id):
            raise ValueError("Test error")
    except ValueError:
        pass

    stats = metrics.get_node_stats("TestNode")
    assert stats["failure_count"] > 0, "Should have recorded failure"
    logger.info(f"  ✓ Failures recorded: {stats['failure_count']}")

    logger.info("✓ Test 1 passed\n")


async def test_workflow_metrics():
    """Test workflow metrics collection."""
    logger.info("=" * 70)
    logger.info("Test 2: Workflow Metrics Collection")
    logger.info("=" * 70)

    metrics = get_metrics()

    # Record workflow execution
    logger.info("\n[Test 2a] Recording workflow execution")
    lead_id = f"test-workflow-{int(datetime.now().timestamp())}"

    metrics.record_workflow_execution(
        lead_id=lead_id,
        workflow_status="booking_ready",
        total_time=2.5,
        nodes_executed=["LeadIngestion", "Research", "QualificationCheck", "DraftOutreach", "SendOutreach"],
    )

    stats = metrics.get_workflow_stats()
    assert stats["total_workflows"] > 0, "Should have recorded workflow"
    logger.info(f"  ✓ Workflows recorded: {stats['total_workflows']}")
    logger.info(f"  ✓ Status distribution: {stats['status_distribution']}")
    logger.info(f"  ✓ Avg workflow time: {stats['avg_workflow_time']:.2f}s")

    logger.info("✓ Test 2 passed\n")


async def test_node_stats():
    """Test node statistics."""
    logger.info("=" * 70)
    logger.info("Test 3: Node Statistics")
    logger.info("=" * 70)

    metrics = get_metrics()

    # Record multiple node executions
    logger.info("\n[Test 3a] Recording multiple node executions")
    lead_id = f"test-stats-{int(datetime.now().timestamp())}"

    for i in range(5):
        with NodeExecutionTracker("Researcher", lead_id):
            await asyncio.sleep(0.05)

    stats = metrics.get_node_stats("Researcher")
    logger.info(f"  ✓ Total executions: {stats['total_executions']}")
    logger.info(f"  ✓ Success rate: {stats['success_rate']:.1f}%")
    logger.info(f"  ✓ Avg time: {stats['avg_execution_time']:.3f}s")
    logger.info(f"  ✓ Min time: {stats['min_execution_time']:.3f}s")
    logger.info(f"  ✓ Max time: {stats['max_execution_time']:.3f}s")

    logger.info("✓ Test 3 passed\n")


async def test_metrics_persistence():
    """Test metrics persistence."""
    logger.info("=" * 70)
    logger.info("Test 4: Metrics Persistence")
    logger.info("=" * 70)

    metrics = get_metrics()

    # Record some metrics
    logger.info("\n[Test 4a] Recording metrics")
    lead_id = f"test-persistence-{int(datetime.now().timestamp())}"

    metrics.record_workflow_execution(
        lead_id=lead_id,
        workflow_status="completed",
        total_time=1.5,
        nodes_executed=["TestNode"],
    )

    # Save metrics
    logger.info("\n[Test 4b] Saving metrics to file")
    metrics.save_metrics()
    logger.info("  ✓ Metrics saved")

    # Create new metrics instance and load
    logger.info("\n[Test 4c] Loading metrics from file")
    new_metrics = WorkflowMetrics()
    new_metrics.load_metrics()

    stats = new_metrics.get_workflow_stats()
    assert stats["total_workflows"] > 0, "Should have loaded workflows"
    logger.info(f"  ✓ Metrics loaded: {stats['total_workflows']} workflows")

    logger.info("✓ Test 4 passed\n")


async def test_integration_with_researcher():
    """Test monitoring integration with actual node."""
    logger.info("=" * 70)
    logger.info("Test 5: Integration with Researcher Node")
    logger.info("=" * 70)

    metrics = get_metrics()
    lead_id = f"test-integration-{int(datetime.now().timestamp())}"

    state: AOROState = {
        "lead_id": lead_id,
        "company_name": "Test Company",
        "permit_data": {
            "permit_id": "TEST-001",
            "permit_type": "Fire Alarm",
        },
    }

    logger.info("\n[Test 5a] Running Researcher node with monitoring")
    with NodeExecutionTracker("Research", lead_id):
        result = await researcher_node(state)

    stats = metrics.get_node_stats("Research")
    logger.info(f"  ✓ Researcher execution tracked")
    logger.info(f"  ✓ Execution time: {stats['avg_execution_time']:.3f}s")
    logger.info(f"  ✓ Success: {result.get('compliance_urgency_score') is not None}")

    logger.info("✓ Test 5 passed\n")


async def main():
    """Run all Phase 2.4 monitoring tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Phase 2.4: Workflow Monitoring & Observability Tests")
    logger.info("=" * 70 + "\n")

    try:
        await test_node_execution_tracking()
        await test_workflow_metrics()
        await test_node_stats()
        await test_metrics_persistence()
        await test_integration_with_researcher()

        # Final summary
        metrics = get_metrics()
        stats = metrics.get_workflow_stats()

        logger.info("=" * 70)
        logger.info("Final Metrics Summary")
        logger.info("=" * 70)
        logger.info(f"Total Workflows: {stats['total_workflows']}")
        logger.info(f"Status Distribution: {stats['status_distribution']}")
        logger.info(f"Average Workflow Time: {stats['avg_workflow_time']:.2f}s")
        logger.info(f"\nNode Statistics:")
        for node, node_stats in stats.get("node_stats", {}).items():
            logger.info(f"  {node}: {node_stats['success_rate']:.1f}% success, "
                       f"{node_stats['avg_execution_time']:.3f}s avg")

        logger.info("\n" + "=" * 70)
        logger.info("✓ All Phase 2.4 monitoring tests passed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
