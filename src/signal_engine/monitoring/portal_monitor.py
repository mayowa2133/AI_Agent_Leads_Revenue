"""Monitoring and metrics for permit portals."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from src.signal_engine.config.portal_config import PortalConfig, PortalConfigManager

logger = logging.getLogger(__name__)


class PortalMonitor:
    """
    Monitor portal health, performance, and quality metrics.
    
    Provides insights into portal status, permit counts, quality scores,
    and error rates.
    """

    def __init__(self, config_manager: PortalConfigManager | None = None):
        """
        Initialize portal monitor.
        
        Args:
            config_manager: Portal configuration manager
        """
        self.config_manager = config_manager or PortalConfigManager()

    def get_portal_health(self, source_id: str) -> dict[str, Any]:
        """
        Get health status for a specific portal.
        
        Args:
            source_id: Portal source ID
        
        Returns:
            Health status dictionary
        """
        config = self.config_manager.get_config(source_id)
        if not config:
            return {"status": "not_found", "message": "Portal not found"}

        # Determine health status
        health_status = "healthy"
        issues = []

        # Check if portal is enabled
        if not config.enabled:
            health_status = "disabled"
            issues.append("Portal is disabled")

        # Check for recent errors
        if config.error_count > 3:
            health_status = "unhealthy"
            issues.append(f"High error count: {config.error_count}")

        # Check if last scrape was recent (within 7 days)
        if config.last_scraped:
            days_since_scrape = (datetime.utcnow() - config.last_scraped).days
            if days_since_scrape > 7:
                health_status = "stale"
                issues.append(f"Last scrape was {days_since_scrape} days ago")
        else:
            health_status = "never_scraped"
            issues.append("Portal has never been scraped")

        # Check quality score
        if config.quality_score_avg is not None and config.quality_score_avg < 0.3:
            issues.append(f"Low quality score: {config.quality_score_avg:.2f}")

        return {
            "status": health_status,
            "source_id": source_id,
            "city": config.city,
            "enabled": config.enabled,
            "last_scraped": config.last_scraped.isoformat() if config.last_scraped else None,
            "last_successful_scrape": (
                config.last_successful_scrape.isoformat() if config.last_successful_scrape else None
            ),
            "permit_count": config.permit_count,
            "total_permits_scraped": config.total_permits_scraped,
            "error_count": config.error_count,
            "last_error": config.last_error,
            "quality_score_avg": config.quality_score_avg,
            "issues": issues,
        }

    def get_all_portals_health(self) -> dict[str, Any]:
        """
        Get health status for all portals.
        
        Returns:
            Dictionary with health status for all portals
        """
        configs = self.config_manager.get_all_configs()
        
        health_summary = {
            "total": len(configs),
            "healthy": 0,
            "unhealthy": 0,
            "disabled": 0,
            "stale": 0,
            "never_scraped": 0,
            "portals": [],
        }

        for config in configs:
            health = self.get_portal_health(config.source_id)
            health_summary["portals"].append(health)
            
            status = health["status"]
            if status == "healthy":
                health_summary["healthy"] += 1
            elif status == "unhealthy":
                health_summary["unhealthy"] += 1
            elif status == "disabled":
                health_summary["disabled"] += 1
            elif status == "stale":
                health_summary["stale"] += 1
            elif status == "never_scraped":
                health_summary["never_scraped"] += 1

        return health_summary

    def get_metrics(self, days: int = 30) -> dict[str, Any]:
        """
        Get aggregated metrics for all portals.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Metrics dictionary
        """
        configs = self.config_manager.get_all_configs(enabled_only=True)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        metrics = {
            "period_days": days,
            "total_portals": len(configs),
            "active_portals": 0,
            "total_permits_scraped": 0,
            "total_permits_recent": 0,
            "avg_quality_score": None,
            "portals_by_type": {},
            "top_performers": [],
            "underperformers": [],
        }

        quality_scores = []
        portal_performance = []

        for config in configs:
            # Check if portal is active (scraped recently)
            if config.last_successful_scrape and config.last_successful_scrape >= cutoff_date:
                metrics["active_portals"] += 1
                metrics["total_permits_recent"] += config.permit_count

            metrics["total_permits_scraped"] += config.total_permits_scraped

            # Quality scores
            if config.quality_score_avg is not None:
                quality_scores.append(config.quality_score_avg)

            # Performance tracking
            if config.last_successful_scrape:
                portal_performance.append({
                    "source_id": config.source_id,
                    "city": config.city,
                    "permit_count": config.permit_count,
                    "total_permits": config.total_permits_scraped,
                    "quality_score": config.quality_score_avg,
                    "error_count": config.error_count,
                })

            # Count by system type
            sys_type = config.system_type.value
            metrics["portals_by_type"][sys_type] = (
                metrics["portals_by_type"].get(sys_type, 0) + 1
            )

        # Average quality score
        if quality_scores:
            metrics["avg_quality_score"] = sum(quality_scores) / len(quality_scores)

        # Top performers (by permit count)
        portal_performance.sort(key=lambda x: x["total_permits"], reverse=True)
        metrics["top_performers"] = portal_performance[:10]

        # Underperformers (high error count or low quality)
        underperformers = [
            p
            for p in portal_performance
            if p["error_count"] > 3 or (p["quality_score"] is not None and p["quality_score"] < 0.3)
        ]
        metrics["underperformers"] = underperformers[:10]

        return metrics

    def get_dashboard_data(self) -> dict[str, Any]:
        """
        Get comprehensive dashboard data.
        
        Returns:
            Complete dashboard data dictionary
        """
        stats = self.config_manager.get_statistics()
        health = self.get_all_portals_health()
        metrics = self.get_metrics()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats,
            "health": health,
            "metrics": metrics,
        }
