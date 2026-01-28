"""Storage for discovered permit portals."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.signal_engine.discovery.portal_discovery import PortalInfo, PortalType

logger = logging.getLogger(__name__)


class PortalStorage:
    """Storage for discovered permit portals."""

    def __init__(self, storage_file: Path | str | None = None):
        """Initialize portal storage."""
        if storage_file is None:
            storage_file = Path("data/discovered_portals.json")
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._portals: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load portals from storage file."""
        if self.storage_file.exists():
            try:
                content = self.storage_file.read_text()
                if content.strip():
                    self._portals = json.loads(content)
                    logger.info(f"Loaded {len(self._portals)} portals from storage")
            except Exception as e:
                logger.warning(f"Failed to load portals: {e}")
                self._portals = {}

    def save(self) -> None:
        """Save portals to storage file."""
        try:
            self.storage_file.write_text(json.dumps(self._portals, indent=2))
            logger.info(f"Saved {len(self._portals)} portals to {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to save portals: {e}")

    def add_portal(self, portal: PortalInfo) -> None:
        """Add or update a portal in storage."""
        # Use normalized URL as key
        key = self._normalize_url(portal.url)
        self._portals[key] = {
            "url": portal.url,
            "city": portal.city,
            "system_type": portal.system_type.value,
            "confidence_score": portal.confidence_score,
            "title": portal.title,
            "snippet": portal.snippet,
            "validated": portal.validated,
            "config": portal.config or {},
        }
        logger.debug(f"Added portal: {portal.city} - {portal.url}")

    def add_portals(self, portals: list[PortalInfo]) -> None:
        """Add multiple portals."""
        for portal in portals:
            self.add_portal(portal)

    def get_portals(
        self,
        city: str | None = None,
        system_type: PortalType | None = None,
        validated_only: bool = False,
    ) -> list[PortalInfo]:
        """Get portals with optional filters."""
        portals = []
        for data in self._portals.values():
            if city and data.get("city") != city:
                continue
            if system_type and data.get("system_type") != system_type.value:
                continue
            if validated_only and not data.get("validated", False):
                continue

            portal = PortalInfo(
                url=data["url"],
                city=data["city"],
                system_type=PortalType(data["system_type"]),
                confidence_score=data["confidence_score"],
                title=data.get("title"),
                snippet=data.get("snippet"),
                validated=data.get("validated", False),
                config=data.get("config"),
            )
            portals.append(portal)

        return portals

    def get_all_portals(self) -> list[PortalInfo]:
        """Get all stored portals."""
        return self.get_portals()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for use as key."""
        url = url.lower().strip()
        url = url.replace("https://", "").replace("http://", "")
        url = url.replace("www.", "")
        url = url.rstrip("/")
        return url

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored portals."""
        stats = {
            "total": len(self._portals),
            "by_city": {},
            "by_system_type": {},
            "validated": 0,
            "unvalidated": 0,
        }

        for data in self._portals.values():
            city = data.get("city", "Unknown")
            system_type = data.get("system_type", "unknown")
            validated = data.get("validated", False)

            stats["by_city"][city] = stats["by_city"].get(city, 0) + 1
            stats["by_system_type"][system_type] = (
                stats["by_system_type"].get(system_type, 0) + 1
            )

            if validated:
                stats["validated"] += 1
            else:
                stats["unvalidated"] += 1

        return stats
