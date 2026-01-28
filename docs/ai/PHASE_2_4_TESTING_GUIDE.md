# Phase 2.4: Testing & Monitoring Guide

**Status:** ✅ All Tests Passing  
**Date:** January 2026

## Quick Test Commands

### Run All Phase 2.4 Tests

```bash
# Comprehensive monitoring tests (recommended)
poetry run python scripts/phase2/test_phase2_4_monitoring.py

# Comprehensive end-to-end test with monitoring
poetry run python scripts/phase2/test_phase2_4_comprehensive.py

# End-to-end workflow test with real enriched leads
poetry run python scripts/phase2/test_workflow_e2e.py
```

### Run Individual Test Suites

```bash
# Test 1: Monitoring system tests
poetry run python scripts/phase2/test_phase2_4_monitoring.py

# Test 2: Comprehensive E2E with monitoring
poetry run python scripts/phase2/test_phase2_4_comprehensive.py

# Test 3: End-to-end workflow test
poetry run python scripts/phase2/test_workflow_e2e.py
```

## Test Coverage

### ✅ Monitoring System Tests (`test_phase2_4_monitoring.py`)

**Test 1: Node Execution Tracking**
- ✓ Successful node execution tracking
- ✓ Failed node execution tracking
- ✓ Execution time measurement
- ✓ Success rate calculation

**Test 2: Workflow Metrics Collection**
- ✓ Workflow execution recording
- ✓ Status distribution tracking
- ✓ Average workflow time calculation

**Test 3: Node Statistics**
- ✓ Multiple execution tracking
- ✓ Statistics calculation (avg, min, max)
- ✓ Success rate tracking

**Test 4: Metrics Persistence**
- ✓ Save metrics to file
- ✓ Load metrics from file
- ✓ Data integrity verification

**Test 5: Integration with Researcher Node**
- ✓ Real node execution tracking
- ✓ Metrics collection during execution

### ✅ Comprehensive E2E Test (`test_phase2_4_comprehensive.py`)

**Test: Complete Workflow with Monitoring**
- ✓ Full workflow execution
- ✓ Metrics collection during execution
- ✓ Workflow execution recording
- ✓ Statistics summary

### ✅ End-to-End Workflow Test (`test_workflow_e2e.py`)

**Test: Full Workflow with Real Leads**
- ✓ Load enriched leads from Phase 1.3
- ✓ Complete workflow execution
- ✓ Response handling path
- ✓ Workflow state persistence

## Expected Test Results

### Monitoring Tests Output

```
✓ Test 1 passed (Node Execution Tracking)
✓ Test 2 passed (Workflow Metrics Collection)
✓ Test 3 passed (Node Statistics)
✓ Test 4 passed (Metrics Persistence)
✓ Test 5 passed (Integration with Researcher Node)

Final Metrics Summary:
  Total Workflows: X
  Status Distribution: {...}
  Average Workflow Time: X.XXs
  Node Statistics:
    Research: XX.X% success, X.XXXs avg
```

### Comprehensive E2E Test Output

```
✓ Workflow completed in X.XXs
✓ Qualification Score: X.XX
✓ Compliance Urgency: X.XX
✓ Outreach Sent: True/False
✓ Nodes Executed: X

Metrics Summary:
  Total Workflows: X
  Average Time: X.XXs

🎉 PHASE 2.4 COMPREHENSIVE TEST PASSED!
```

## Using Monitoring in Your Code

### Track Node Execution

```python
from src.agents.monitoring import NodeExecutionTracker

async def my_node(state: AOROState) -> AOROState:
    lead_id = state.get("lead_id", "")
    
    with NodeExecutionTracker("MyNode", lead_id):
        # Your node logic here
        result = await do_work()
        return {**state, "result": result}
```

### Record Workflow Execution

```python
from src.agents.monitoring import get_metrics

metrics = get_metrics()
metrics.record_workflow_execution(
    lead_id=lead_id,
    workflow_status="booking_ready",
    total_time=2.5,
    nodes_executed=["LeadIngestion", "Research", "QualificationCheck"],
)
```

### Get Statistics

```python
from src.agents.monitoring import get_metrics

metrics = get_metrics()

# Node statistics
node_stats = metrics.get_node_stats("Research")
print(f"Success rate: {node_stats['success_rate']:.1f}%")
print(f"Avg time: {node_stats['avg_execution_time']:.3f}s")

# Workflow statistics
workflow_stats = metrics.get_workflow_stats()
print(f"Total workflows: {workflow_stats['total_workflows']}")
print(f"Avg workflow time: {workflow_stats['avg_workflow_time']:.2f}s")
```

## Metrics Data

### Storage Location

Metrics are saved to: `data/workflow_metrics.json`

### Data Structure

```json
{
  "workflow_executions": [
    {
      "lead_id": "lead-123",
      "workflow_status": "booking_ready",
      "total_time": 2.5,
      "nodes_executed": ["LeadIngestion", "Research"],
      "timestamp": "2026-01-12T..."
    }
  ],
  "node_executions": {
    "Research": [
      {
        "node": "Research",
        "lead_id": "lead-123",
        "success": true,
        "execution_time": 1.5,
        "timestamp": "2026-01-12T..."
      }
    ]
  },
  "node_success_rates": {
    "Research": {"success": 10, "failure": 1}
  },
  "saved_at": "2026-01-12T..."
}
```

## Verification Checklist

After running tests, verify:

- [ ] All test suites pass
- [ ] Node execution tracking works
- [ ] Workflow metrics are collected
- [ ] Statistics are calculated correctly
- [ ] Metrics are persisted to file
- [ ] Metrics can be loaded from file
- [ ] Integration with nodes works
- [ ] End-to-end workflow executes successfully
- [ ] Monitoring adds minimal overhead

## Troubleshooting

### Issue: "Metrics file not found"
**Solution:** Metrics file is created automatically on first save. Run a test that records metrics.

### Issue: "Statistics show 0 executions"
**Solution:** Ensure you're using `NodeExecutionTracker` or calling `record_node_execution()`.

### Issue: "Metrics not persisting"
**Solution:** Call `metrics.save_metrics()` after recording metrics, or metrics auto-save periodically.

### Issue: "High execution times"
**Solution:** Check if LLM calls are taking long. Monitor individual node times to identify bottlenecks.

## Success Criteria

Phase 2.4 is fully implemented when:

- ✅ All test suites pass
- ✅ Node execution tracking works
- ✅ Workflow metrics are collected
- ✅ Statistics are calculated correctly
- ✅ Metrics are persisted and loadable
- ✅ Integration with nodes works
- ✅ End-to-end workflow executes successfully
- ✅ Monitoring provides visibility into execution

## Next Steps

After Phase 2.4 verification:
- Proceed to Phase 3: MCP Integration
- Build metrics dashboard (optional)
- Set up alerting (optional)
- Optimize based on metrics (optional)
