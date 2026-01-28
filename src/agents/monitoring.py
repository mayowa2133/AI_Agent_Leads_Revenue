"""Workflow monitoring and observability."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.observability import audit_event

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """Track workflow execution metrics."""

    def __init__(self, metrics_file: Path | str | None = None):
        """
        Initialize workflow metrics tracker.

        Args:
            metrics_file: Path to JSON file for metrics persistence (default: data/workflow_metrics.json)
        """
        if metrics_file is None:
            metrics_file = Path("data/workflow_metrics.json")
        elif isinstance(metrics_file, str):
            metrics_file = Path(metrics_file)

        self.metrics_file = metrics_file
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory metrics
        self.node_executions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.workflow_executions: list[dict[str, Any]] = []
        self.node_success_rates: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        self.execution_times: dict[str, list[float]] = defaultdict(list)

    def record_node_execution(
        self,
        node_name: str,
        lead_id: str,
        success: bool,
        execution_time: float,
        error: str | None = None,
    ) -> None:
        """
        Record a node execution.

        Args:
            node_name: Name of the node
            lead_id: Lead ID
            success: Whether execution was successful
            execution_time: Execution time in seconds
            error: Error message if failed
        """
        record = {
            "node": node_name,
            "lead_id": lead_id,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "error": error,
        }

        # Initialize list if it doesn't exist
        if node_name not in self.node_executions:
            self.node_executions[node_name] = []
        if node_name not in self.execution_times:
            self.execution_times[node_name] = []

        self.node_executions[node_name].append(record)
        self.execution_times[node_name].append(execution_time)

        if success:
            self.node_success_rates[node_name]["success"] += 1
        else:
            self.node_success_rates[node_name]["failure"] += 1

        # Audit event
        audit_event(
            "node_execution",
            {
                "node": node_name,
                "lead_id": lead_id,
                "success": success,
                "execution_time": execution_time,
            },
        )

        logger.debug(f"Recorded {node_name} execution: success={success}, time={execution_time:.2f}s")

    def record_workflow_execution(
        self,
        lead_id: str,
        workflow_status: str,
        total_time: float,
        nodes_executed: list[str],
        final_state: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a complete workflow execution.

        Args:
            lead_id: Lead ID
            workflow_status: Final workflow status
            total_time: Total workflow execution time in seconds
            nodes_executed: List of nodes executed
            final_state: Final workflow state (optional)
        """
        record = {
            "lead_id": lead_id,
            "workflow_status": workflow_status,
            "total_time": total_time,
            "nodes_executed": nodes_executed,
            "timestamp": datetime.now().isoformat(),
            "final_state": final_state,
        }

        self.workflow_executions.append(record)

        # Audit event
        audit_event(
            "workflow_execution",
            {
                "lead_id": lead_id,
                "workflow_status": workflow_status,
                "total_time": total_time,
                "nodes_count": len(nodes_executed),
            },
        )

        logger.info(
            f"Workflow execution recorded: lead={lead_id}, status={workflow_status}, "
            f"time={total_time:.2f}s, nodes={len(nodes_executed)}"
        )

    def get_node_stats(self, node_name: str) -> dict[str, Any]:
        """
        Get statistics for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            Dictionary with node statistics
        """
        executions = self.node_executions.get(node_name, [])
        times = self.execution_times.get(node_name, [])
        success_rates = self.node_success_rates.get(node_name, {"success": 0, "failure": 0})

        total = success_rates["success"] + success_rates["failure"]
        success_rate = (success_rates["success"] / total * 100) if total > 0 else 0.0

        return {
            "node": node_name,
            "total_executions": total,
            "success_count": success_rates["success"],
            "failure_count": success_rates["failure"],
            "success_rate": success_rate,
            "avg_execution_time": sum(times) / len(times) if times else 0.0,
            "min_execution_time": min(times) if times else 0.0,
            "max_execution_time": max(times) if times else 0.0,
            "recent_executions": executions[-10:],  # Last 10 executions
        }

    def get_workflow_stats(self) -> dict[str, Any]:
        """
        Get overall workflow statistics.

        Returns:
            Dictionary with workflow statistics
        """
        total_workflows = len(self.workflow_executions)
        status_counts = defaultdict(int)
        total_times = []

        for execution in self.workflow_executions:
            status_counts[execution["workflow_status"]] += 1
            total_times.append(execution["total_time"])

        return {
            "total_workflows": total_workflows,
            "status_distribution": dict(status_counts),
            "avg_workflow_time": sum(total_times) / len(total_times) if total_times else 0.0,
            "min_workflow_time": min(total_times) if total_times else 0.0,
            "max_workflow_time": max(total_times) if total_times else 0.0,
            "node_stats": {
                node: self.get_node_stats(node) for node in self.node_executions.keys()
            },
        }

    def save_metrics(self) -> None:
        """Save metrics to file."""
        import json

        metrics_data = {
            "workflow_executions": self.workflow_executions[-100:],  # Last 100 workflows
            "node_executions": {
                node: executions[-50:]  # Last 50 per node
                for node, executions in self.node_executions.items()
            },
            "node_success_rates": dict(self.node_success_rates),
            "saved_at": datetime.now().isoformat(),
        }

        self.metrics_file.write_text(json.dumps(metrics_data, indent=2))
        logger.debug(f"Metrics saved to {self.metrics_file}")

    def load_metrics(self) -> None:
        """Load metrics from file."""
        import json

        if not self.metrics_file.exists():
            return

        try:
            content = self.metrics_file.read_text()
            if not content.strip():
                return

            metrics_data = json.loads(content)

            self.workflow_executions = metrics_data.get("workflow_executions", [])
            # Use defaultdict to ensure keys exist
            self.node_executions = defaultdict(list, {
                node: executions
                for node, executions in metrics_data.get("node_executions", {}).items()
            })
            # Initialize execution_times from loaded data
            for node, executions in self.node_executions.items():
                if node not in self.execution_times:
                    self.execution_times[node] = []
                self.execution_times[node].extend([
                    e.get("execution_time", 0.0) for e in executions
                ])
            
            self.node_success_rates = defaultdict(
                lambda: {"success": 0, "failure": 0},
                metrics_data.get("node_success_rates", {}),
            )

            logger.debug(f"Metrics loaded from {self.metrics_file}")
        except Exception as e:
            logger.warning(f"Error loading metrics: {e}", exc_info=True)


# Global metrics instance
_metrics_instance: WorkflowMetrics | None = None


def get_metrics() -> WorkflowMetrics:
    """Get or create global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = WorkflowMetrics()
        _metrics_instance.load_metrics()
    return _metrics_instance


def append_workflow_event(event_type: str, payload: dict[str, Any], *, metrics_file: str | Path | None = None) -> None:
    """
    Append a lightweight workflow event to the shared metrics file.
    Used for cheap monitoring of outreach, replies, and bookings.
    """
    import json

    metrics_path = Path(metrics_file) if metrics_file else Path("data/workflow_metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    event = {"type": event_type, "timestamp": datetime.now().isoformat(), **payload}

    try:
        if metrics_path.exists():
            content = metrics_path.read_text()
            metrics = json.loads(content) if content.strip() else {}
        else:
            metrics = {}
    except Exception:
        metrics = {}

    events = metrics.get("workflow_events", [])
    events.append(event)
    metrics["workflow_events"] = events[-500:]  # keep last 500

    try:
        metrics_path.write_text(json.dumps(metrics, indent=2))
    except Exception as exc:
        logger.warning(f"Failed to append workflow event: {exc}")


class NodeExecutionTracker:
    """Context manager for tracking node execution."""

    def __init__(self, node_name: str, lead_id: str):
        self.node_name = node_name
        self.lead_id = lead_id
        self.start_time: float | None = None
        self.metrics = get_metrics()

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - (self.start_time or 0)
        success = exc_type is None
        error = str(exc_val) if exc_val else None

        self.metrics.record_node_execution(
            node_name=self.node_name,
            lead_id=self.lead_id,
            success=success,
            execution_time=execution_time,
            error=error,
        )

        return False  # Don't suppress exceptions
