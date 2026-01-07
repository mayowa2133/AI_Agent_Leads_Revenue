"""Storage layer for regulatory updates using JSON file storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.signal_engine.models import RegulatoryUpdate

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RegulatoryStorage:
    """
    Storage for regulatory updates using JSON file storage.
    
    Matches Phase 1.1 approach for consistency. Can be upgraded to
    database later if needed.
    """

    def __init__(self, *, storage_file: Path | str | None = None):
        """
        Initialize regulatory storage.
        
        Args:
            storage_file: Path to JSON storage file (default: data/regulatory_updates.json)
        """
        if storage_file is None:
            storage_file = Path("data/regulatory_updates.json")
        elif isinstance(storage_file, str):
            storage_file = Path(storage_file)

        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def save_update(self, update: RegulatoryUpdate) -> None:
        """
        Save a regulatory update to storage.
        
        Args:
            update: Regulatory update to save
        """
        updates = self.load_all()
        
        # Deduplicate by update_id (last write wins)
        updates_dict = {u["update_id"]: u for u in updates}
        updates_dict[update.update_id] = update.model_dump(mode="json")
        
        # Convert datetime to ISO format for JSON
        for update_data in updates_dict.values():
            for key, value in update_data.items():
                if isinstance(value, datetime):
                    update_data[key] = value.isoformat()
        
        # Save to file
        self.storage_file.write_text(json.dumps(list(updates_dict.values()), indent=2))
        logger.debug(f"Saved regulatory update: {update.update_id}")

    def save_updates(self, updates: list[RegulatoryUpdate]) -> None:
        """
        Save multiple regulatory updates.
        
        Args:
            updates: List of regulatory updates to save
        """
        for update in updates:
            self.save_update(update)

    def load_all(self) -> list[dict]:
        """
        Load all regulatory updates from storage.
        
        Returns:
            List of update dictionaries
        """
        if not self.storage_file.exists():
            return []

        try:
            content = self.storage_file.read_text()
            if not content.strip():
                return []
            
            updates = json.loads(content)
            return updates if isinstance(updates, list) else []
        except Exception as e:
            logger.error(f"Error loading regulatory updates: {e}", exc_info=True)
            return []

    def get_update(self, update_id: str) -> RegulatoryUpdate | None:
        """
        Get a specific regulatory update by ID.
        
        Args:
            update_id: Update ID to retrieve
            
        Returns:
            RegulatoryUpdate or None if not found
        """
        updates = self.load_all()
        for update_data in updates:
            if update_data.get("update_id") == update_id:
                return self._dict_to_update(update_data)
        return None

    def query_updates(
        self,
        *,
        source: str | None = None,
        jurisdiction: str | None = None,
        since: datetime | None = None,
    ) -> list[RegulatoryUpdate]:
        """
        Query regulatory updates by filters.
        
        Args:
            source: Filter by source (e.g., "state_fire_marshal")
            jurisdiction: Filter by jurisdiction (e.g., "Texas")
            since: Filter by published date (only updates after this date)
            
        Returns:
            List of matching RegulatoryUpdate objects
        """
        updates = self.load_all()
        results = []

        for update_data in updates:
            # Apply filters
            if source and update_data.get("source") != source:
                continue
            if jurisdiction and update_data.get("jurisdiction") != jurisdiction:
                continue
            if since:
                published_str = update_data.get("published_date")
                if published_str:
                    try:
                        published_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                        if published_date <= since:
                            continue
                    except Exception:
                        pass

            results.append(self._dict_to_update(update_data))

        return results

    def _dict_to_update(self, data: dict) -> RegulatoryUpdate:
        """
        Convert dictionary to RegulatoryUpdate object.
        
        Args:
            data: Dictionary with update data
            
        Returns:
            RegulatoryUpdate object
        """
        # Convert ISO date strings back to datetime
        for date_field in ["published_date", "effective_date", "last_seen_at"]:
            if date_field in data and data[date_field]:
                try:
                    data[date_field] = datetime.fromisoformat(
                        data[date_field].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

        return RegulatoryUpdate(**data)

    def get_latest_update_date(self, source: str | None = None) -> datetime | None:
        """
        Get the latest published date for updates (useful for incremental fetching).
        
        Args:
            source: Optional source filter
            
        Returns:
            Latest published date or None if no updates
        """
        updates = self.query_updates(source=source)
        if not updates:
            return None

        dates = [u.published_date for u in updates if u.published_date]
        return max(dates) if dates else None

