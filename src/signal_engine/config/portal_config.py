"""Portal configuration management system."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.signal_engine.api.unified_ingestion import PermitSourceType
from src.signal_engine.discovery.portal_discovery import PortalType

logger = logging.getLogger(__name__)


@dataclass
class PortalConfig:
    """
    Configuration for each permit portal.
    
    Tracks portal settings, status, and metrics.
    """

    city: str
    portal_url: str
    system_type: PortalType
    source_type: PermitSourceType
    source_id: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_scraped: datetime | None = None
    last_successful_scrape: datetime | None = None
    permit_count: int = 0
    total_permits_scraped: int = 0
    error_count: int = 0
    last_error: str | None = None
    quality_score_avg: float | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key in ["last_scraped", "last_successful_scrape", "created_at", "updated_at"]:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        # Convert enums to strings
        data["system_type"] = self.system_type.value
        data["source_type"] = self.source_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PortalConfig:
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        for key in ["last_scraped", "last_successful_scrape", "created_at", "updated_at"]:
            if data.get(key):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError):
                    data[key] = None
        
        # Convert strings back to enums
        data["system_type"] = PortalType(data["system_type"])
        data["source_type"] = PermitSourceType(data["source_type"])
        
        return cls(**data)


class PortalConfigManager:
    """
    Manages portal configurations.
    
    Handles storage, retrieval, and updates of portal configurations.
    """

    def __init__(self, config_file: Path | str | None = None):
        """
        Initialize portal config manager.
        
        Args:
            config_file: Path to JSON file for storing configs
        """
        if config_file is None:
            config_file = Path("data/portal_configs.json")
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._configs: dict[str, PortalConfig] = {}
        self._load()

    def _load(self) -> None:
        """Load configurations from file."""
        if self.config_file.exists():
            try:
                content = self.config_file.read_text()
                if content.strip():
                    data = json.loads(content)
                    for key, config_data in data.items():
                        self._configs[key] = PortalConfig.from_dict(config_data)
                    logger.info(f"Loaded {len(self._configs)} portal configurations")
            except Exception as e:
                logger.warning(f"Failed to load portal configs: {e}")
                self._configs = {}

    def save(self) -> None:
        """Save configurations to file."""
        try:
            data = {key: config.to_dict() for key, config in self._configs.items()}
            self.config_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved {len(self._configs)} portal configurations")
        except Exception as e:
            logger.error(f"Failed to save portal configs: {e}")

    def add_config(self, config: PortalConfig) -> None:
        """Add or update a portal configuration."""
        key = config.source_id
        config.updated_at = datetime.utcnow()
        self._configs[key] = config
        self.save()
        logger.info(f"Added/updated portal config: {config.city} - {config.source_id}")

    def get_config(self, source_id: str) -> PortalConfig | None:
        """Get configuration by source ID."""
        return self._configs.get(source_id)

    def get_all_configs(self, enabled_only: bool = False) -> list[PortalConfig]:
        """Get all configurations."""
        configs = list(self._configs.values())
        if enabled_only:
            configs = [c for c in configs if c.enabled]
        return configs

    def get_configs_by_city(self, city: str) -> list[PortalConfig]:
        """Get configurations for a specific city."""
        return [c for c in self._configs.values() if c.city == city]

    def get_configs_by_type(
        self, system_type: PortalType | None = None, source_type: PermitSourceType | None = None
    ) -> list[PortalConfig]:
        """Get configurations filtered by type."""
        configs = list(self._configs.values())
        if system_type:
            configs = [c for c in configs if c.system_type == system_type]
        if source_type:
            configs = [c for c in configs if c.source_type == source_type]
        return configs

    def enable_portal(self, source_id: str) -> None:
        """Enable a portal."""
        config = self.get_config(source_id)
        if config:
            config.enabled = True
            config.updated_at = datetime.utcnow()
            self.save()
            logger.info(f"Enabled portal: {source_id}")

    def disable_portal(self, source_id: str) -> None:
        """Disable a portal."""
        config = self.get_config(source_id)
        if config:
            config.enabled = False
            config.updated_at = datetime.utcnow()
            self.save()
            logger.info(f"Disabled portal: {source_id}")

    def update_scrape_result(
        self,
        source_id: str,
        permit_count: int,
        success: bool = True,
        error: str | None = None,
        quality_score_avg: float | None = None,
    ) -> None:
        """Update portal with scrape results."""
        config = self.get_config(source_id)
        if config:
            config.last_scraped = datetime.utcnow()
            config.permit_count = permit_count
            config.updated_at = datetime.utcnow()
            
            if success:
                config.last_successful_scrape = datetime.utcnow()
                config.total_permits_scraped += permit_count
                config.error_count = 0
                config.last_error = None
            else:
                config.error_count += 1
                config.last_error = error
            
            if quality_score_avg is not None:
                # Update running average
                if config.quality_score_avg is None:
                    config.quality_score_avg = quality_score_avg
                else:
                    # Simple moving average
                    config.quality_score_avg = (config.quality_score_avg + quality_score_avg) / 2
            
            self.save()

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about portal configurations."""
        configs = list(self._configs.values())
        
        stats = {
            "total": len(configs),
            "enabled": sum(1 for c in configs if c.enabled),
            "disabled": sum(1 for c in configs if not c.enabled),
            "by_system_type": {},
            "by_source_type": {},
            "total_permits_scraped": sum(c.total_permits_scraped for c in configs),
            "portals_with_errors": sum(1 for c in configs if c.error_count > 0),
            "avg_quality_score": None,
        }
        
        # Count by system type
        for config in configs:
            sys_type = config.system_type.value
            stats["by_system_type"][sys_type] = stats["by_system_type"].get(sys_type, 0) + 1
            
            src_type = config.source_type.value
            stats["by_source_type"][src_type] = stats["by_source_type"].get(src_type, 0) + 1
        
        # Average quality score
        quality_scores = [c.quality_score_avg for c in configs if c.quality_score_avg is not None]
        if quality_scores:
            stats["avg_quality_score"] = sum(quality_scores) / len(quality_scores)
        
        return stats
