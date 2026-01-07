"""Service for matching regulatory updates to permits based on jurisdiction, building type, and codes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.signal_engine.enrichment.geocoder import GeocodeResult
from src.signal_engine.models import PermitData, RegulatoryUpdate
from src.signal_engine.storage.regulatory_storage import RegulatoryStorage

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RegulatoryMatcher:
    """
    Matches regulatory updates to permits based on various criteria.

    Matching criteria:
    1. Jurisdiction match (permit location matches update jurisdiction)
    2. Building type match (permit building_type in update's building_types_affected)
    3. Code match (permit type or codes match update's applicable_codes)
    4. Date relevance (update published/effective date is recent)
    """

    def __init__(self, *, storage: RegulatoryStorage | None = None):
        """
        Initialize regulatory matcher.

        Args:
            storage: RegulatoryStorage instance (creates default if None)
        """
        self.storage = storage or RegulatoryStorage()
        self.relevance_window_days = 180  # 6 months

    def _normalize_jurisdiction(self, jurisdiction: str | None) -> str | None:
        """
        Normalize jurisdiction string for matching.

        Args:
            jurisdiction: Raw jurisdiction string

        Returns:
            Normalized jurisdiction or None
        """
        if not jurisdiction:
            return None

        # Normalize to lowercase, strip whitespace
        normalized = jurisdiction.lower().strip()

        # Handle common variations
        # "Texas" -> "texas", "TX" -> "texas", "Texas State" -> "texas"
        state_abbreviations = {
            "tx": "texas",
            "nc": "north carolina",
            "ca": "california",
            "ny": "new york",
            "fl": "florida",
        }

        # Check if it's a state abbreviation
        if normalized in state_abbreviations:
            return state_abbreviations[normalized]

        # Remove common suffixes
        for suffix in [" state", " state fire marshal", " fire marshal"]:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]

        return normalized

    def _jurisdiction_matches(
        self, permit_jurisdiction: str | None, update_jurisdiction: str | None
    ) -> bool:
        """
        Check if permit and update jurisdictions match.

        Args:
            permit_jurisdiction: Jurisdiction from permit (e.g., "Texas")
            update_jurisdiction: Jurisdiction from update (e.g., "Texas State Fire Marshal")

        Returns:
            True if jurisdictions match
        """
        if not permit_jurisdiction or not update_jurisdiction:
            return False

        permit_norm = self._normalize_jurisdiction(permit_jurisdiction)
        update_norm = self._normalize_jurisdiction(update_jurisdiction)

        if not permit_norm or not update_norm:
            return False

        # Exact match
        if permit_norm == update_norm:
            return True

        # Check if one contains the other (e.g., "texas" in "texas state fire marshal")
        return permit_norm in update_norm or update_norm in permit_norm

    def _building_type_matches(
        self, permit_building_type: str | None, update_building_types: list[str]
    ) -> bool:
        """
        Check if permit building type matches any in update's affected types.

        Args:
            permit_building_type: Building type from permit
            update_building_types: List of building types affected by update

        Returns:
            True if there's a match
        """
        if not permit_building_type or not update_building_types:
            return False

        permit_type_lower = permit_building_type.lower().strip()

        for update_type in update_building_types:
            if not update_type:
                continue
            update_type_lower = update_type.lower().strip()

            # Exact match
            if permit_type_lower == update_type_lower:
                return True

            # Partial match (e.g., "commercial" in "commercial office")
            if permit_type_lower in update_type_lower or update_type_lower in permit_type_lower:
                return True

        return False

    def _code_matches(self, permit_type: str, update_codes: list[str]) -> bool:
        """
        Check if permit type matches any applicable codes in update.

        Args:
            permit_type: Permit type (e.g., "Fire Alarm", "Sprinkler")
            update_codes: List of applicable codes (e.g., ["NFPA 72", "NFPA 101"])

        Returns:
            True if there's a match
        """
        if not permit_type or not update_codes:
            return False

        permit_type_lower = permit_type.lower()

        # Check if permit type contains code keywords
        code_keywords = ["fire alarm", "sprinkler", "hvac", "fire suppression", "fire safety"]

        for keyword in code_keywords:
            if keyword in permit_type_lower:
                # Check if any update code is relevant
                for code in update_codes:
                    if not code:
                        continue
                    code_lower = code.lower()

                    # Match NFPA codes
                    if "nfpa" in code_lower and ("fire" in permit_type_lower or "sprinkler" in permit_type_lower):
                        return True

                    # Match EPA codes for HVAC
                    if "epa" in code_lower and "hvac" in permit_type_lower:
                        return True

        return False

    def _is_recent(self, update: RegulatoryUpdate) -> bool:
        """
        Check if update is recent enough to be relevant.

        Args:
            update: Regulatory update to check

        Returns:
            True if update is within relevance window
        """
        # Use effective_date if available, otherwise published_date
        reference_date = update.effective_date or update.published_date

        if not reference_date:
            return False

        cutoff_date = datetime.now(reference_date.tzinfo) - timedelta(days=self.relevance_window_days)
        return reference_date >= cutoff_date

    async def match_updates(
        self, permit: PermitData, geocode_result: GeocodeResult | None = None
    ) -> list[RegulatoryUpdate]:
        """
        Find regulatory updates that match a permit.

        Args:
            permit: Permit to match
            geocode_result: Optional geocoding result (for jurisdiction extraction)

        Returns:
            List of matching RegulatoryUpdate objects
        """
        # Extract jurisdiction from geocode result or permit
        permit_jurisdiction = None
        if geocode_result:
            permit_jurisdiction = geocode_result.state or geocode_result.county

        # Load all regulatory updates
        all_updates = self.storage.load_all()
        matches = []

        for update_data in all_updates:
            try:
                update = self.storage._dict_to_update(update_data)

                # Check date relevance first (fast filter)
                if not self._is_recent(update):
                    continue

                # Check jurisdiction match
                jurisdiction_match = self._jurisdiction_matches(
                    permit_jurisdiction, update.jurisdiction
                )

                # Check building type match
                building_type_match = self._building_type_matches(
                    permit.building_type, update.building_types_affected
                )

                # Check code match
                code_match = self._code_matches(permit.permit_type, update.applicable_codes)

                # Match if any criteria match (OR logic - any relevance is enough)
                if jurisdiction_match or building_type_match or code_match:
                    matches.append(update)
                    logger.debug(
                        f"Matched update {update.update_id} to permit {permit.permit_id}: "
                        f"jurisdiction={jurisdiction_match}, "
                        f"building_type={building_type_match}, "
                        f"code={code_match}"
                    )

            except Exception as e:
                logger.warning(f"Error processing update for matching: {e}", exc_info=True)
                continue

        return matches


async def match_regulatory_updates(
    permit: PermitData, geocode_result: GeocodeResult | None = None
) -> list[RegulatoryUpdate]:
    """
    Convenience function to match regulatory updates to a permit.

    Args:
        permit: Permit to match
        geocode_result: Optional geocoding result

    Returns:
        List of matching RegulatoryUpdate objects
    """
    matcher = RegulatoryMatcher()
    return await matcher.match_updates(permit, geocode_result)

