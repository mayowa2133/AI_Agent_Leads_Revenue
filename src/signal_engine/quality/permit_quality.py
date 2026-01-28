"""Permit quality scoring system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.signal_engine.models import PermitData


@dataclass
class QualityScore:
    """Quality score breakdown for a permit."""

    total_score: float
    has_applicant: bool
    has_complete_address: bool
    has_valid_permit_type: bool
    is_recent: bool
    has_good_status: bool
    is_geocodable: bool | None = None  # None if not checked
    factors: dict[str, float] | None = None  # Detailed factor scores


class PermitQualityScorer:
    """
    Score permits before enrichment to filter low-quality ones.
    
    Scoring factors:
    - Has applicant name: +0.3
    - Complete address: +0.2
    - Valid permit type: +0.2
    - Recent (last 30 days): +0.1
    - Status is "Issued" or "Active": +0.1
    - Address is geocodable: +0.1 (optional, requires geocoding)
    
    Maximum score: 1.0
    """

    def __init__(
        self,
        recent_days: int = 30,
        good_statuses: list[str] | None = None,
        fire_keywords: list[str] | None = None,
    ):
        """
        Initialize quality scorer.
        
        Args:
            recent_days: Number of days to consider "recent"
            good_statuses: List of status values considered "good" (e.g., "Issued", "Active")
            fire_keywords: Keywords in permit_type that indicate fire-related permits
        """
        self.recent_days = recent_days
        self.good_statuses = good_statuses or ["Issued", "Active", "In Progress", "Approved"]
        self.fire_keywords = fire_keywords or ["fire", "sprinkler", "alarm", "suppression"]

    def score(self, permit: PermitData, check_geocodable: bool = False) -> QualityScore:
        """
        Score permit quality (0.0 - 1.0).
        
        Args:
            permit: Permit to score
            check_geocodable: Whether to check if address is geocodable (requires API call)
        
        Returns:
            QualityScore with total score and breakdown
        """
        factors: dict[str, float] = {}
        total_score = 0.0

        # Factor 1: Has applicant name (+0.3)
        has_applicant = (
            permit.applicant_name is not None
            and len(permit.applicant_name.strip()) > 3
            and not self._is_likely_invalid_name(permit.applicant_name)
        )
        if has_applicant:
            factors["has_applicant"] = 0.3
            total_score += 0.3

        # Factor 2: Complete address (+0.2)
        has_complete_address = (
            permit.address is not None
            and len(permit.address.strip()) > 10
            and self._is_valid_address_format(permit.address)
        )
        if has_complete_address:
            factors["has_complete_address"] = 0.2
            total_score += 0.2

        # Factor 3: Valid permit type (+0.2)
        # Check both permit_type field AND source field (for Fire module permits)
        has_valid_permit_type = False
        if permit.permit_type is not None and len(permit.permit_type.strip()) > 2:
            # Check if permit_type contains fire keywords
            if self._is_fire_related(permit.permit_type):
                has_valid_permit_type = True
            # Also check if source indicates Fire module (e.g., "accela_cosa_fire")
            elif permit.source and "fire" in permit.source.lower():
                has_valid_permit_type = True
        
        if has_valid_permit_type:
            factors["has_valid_permit_type"] = 0.2
            total_score += 0.2

        # Factor 4: Recent permit (+0.1)
        is_recent = False
        if permit.issued_date:
            days_ago = (datetime.now(permit.issued_date.tzinfo) - permit.issued_date).days
            is_recent = days_ago <= self.recent_days
        elif permit.last_seen_at:
            # Fallback to last_seen_at if issued_date not available
            days_ago = (datetime.now(permit.last_seen_at.tzinfo) - permit.last_seen_at).days
            is_recent = days_ago <= self.recent_days
        
        if is_recent:
            factors["is_recent"] = 0.1
            total_score += 0.1

        # Factor 5: Good status (+0.1)
        # More lenient: accept if status exists and is not clearly invalid
        has_good_status = False
        if permit.status is not None and len(permit.status.strip()) > 0:
            status_lower = permit.status.lower()
            # Check for good statuses
            if any(good_status.lower() in status_lower for good_status in self.good_statuses):
                has_good_status = True
            # Also accept if status looks like a valid status (not an address or description)
            # Reject if it looks like an address (has numbers and common address words)
            elif not self._looks_like_address(permit.status):
                # If it's not an address and has some content, give partial credit
                # This handles cases where status might be a person name or other valid value
                has_good_status = True
        
        if has_good_status:
            factors["has_good_status"] = 0.1
            total_score += 0.1

        # Factor 6: Geocodable address (+0.1) - optional, requires API call
        is_geocodable: bool | None = None
        if check_geocodable and permit.address:
            # This would require an async geocoding call
            # For now, we'll skip it in the sync score method
            # Use should_enrich_with_validation() for full validation
            pass

        # Ensure score doesn't exceed 1.0
        total_score = min(total_score, 1.0)

        return QualityScore(
            total_score=total_score,
            has_applicant=has_applicant,
            has_complete_address=has_complete_address,
            has_valid_permit_type=has_valid_permit_type,
            is_recent=is_recent,
            has_good_status=has_good_status,
            is_geocodable=is_geocodable,
            factors=factors,
        )

    def should_enrich(self, permit: PermitData, threshold: float = 0.5) -> bool:
        """
        Determine if permit should be enriched based on quality score.
        
        Args:
            permit: Permit to check
            threshold: Minimum quality score (default: 0.5)
        
        Returns:
            True if permit should be enriched
        """
        score_result = self.score(permit)
        return score_result.total_score >= threshold

    async def should_enrich_with_validation(
        self, permit: PermitData, threshold: float = 0.5
    ) -> tuple[bool, QualityScore]:
        """
        Determine if permit should be enriched, including geocoding validation.
        
        Args:
            permit: Permit to check
            threshold: Minimum quality score
        
        Returns:
            Tuple of (should_enrich, quality_score)
        """
        from src.signal_engine.enrichment.geocoder import geocode_address

        # Get base score
        score_result = self.score(permit, check_geocodable=False)

        # Check geocodability if address exists
        if permit.address:
            try:
                geocode_result = await geocode_address(permit.address)
                if geocode_result and geocode_result.city:
                    score_result.is_geocodable = True
                    if "is_geocodable" not in (score_result.factors or {}):
                        score_result.factors = score_result.factors or {}
                        score_result.factors["is_geocodable"] = 0.1
                        score_result.total_score = min(score_result.total_score + 0.1, 1.0)
                else:
                    score_result.is_geocodable = False
            except Exception:
                score_result.is_geocodable = False

        should_enrich = score_result.total_score >= threshold
        return should_enrich, score_result

    def _is_likely_invalid_name(self, name: str) -> bool:
        """Check if name is likely invalid (e.g., "N/A", "Unknown", numbers only)."""
        name_lower = name.lower().strip()
        invalid_patterns = [
            "n/a",
            "na",
            "unknown",
            "none",
            "null",
            "tbd",
            "to be determined",
        ]
        
        # Check for invalid patterns
        if any(pattern in name_lower for pattern in invalid_patterns):
            return True
        
        # Check if it's mostly numbers or special characters
        if len([c for c in name if c.isalnum()]) < len(name) * 0.5:
            return True
        
        return False

    def _is_valid_address_format(self, address: str) -> bool:
        """Check if address has valid format (has street number and name)."""
        address = address.strip()
        
        # Must have at least 10 characters
        if len(address) < 10:
            return False
        
        # Should have a number (street number)
        has_number = any(c.isdigit() for c in address)
        
        # Should have letters (street name)
        has_letters = any(c.isalpha() for c in address)
        
        # Should not be just a description (e.g., "10 ft tunnel")
        is_description = any(
            word in address.lower()
            for word in ["ft", "feet", "tunnel", "area", "zone", "section"]
        )
        if is_description and not has_letters:
            return False
        
        return has_number and has_letters

    def _is_fire_related(self, permit_type: str) -> bool:
        """Check if permit type is fire-related."""
        permit_type_lower = permit_type.lower()
        return any(keyword in permit_type_lower for keyword in self.fire_keywords)
    
    def _looks_like_address(self, text: str) -> bool:
        """Check if text looks like an address (misplaced in status field)."""
        text_lower = text.lower()
        # Common address indicators
        address_indicators = ["st", "street", "ave", "avenue", "rd", "road", "dr", "drive", "blvd", "boulevard", "ln", "lane"]
        # Check if it has numbers and address words
        has_numbers = any(c.isdigit() for c in text)
        has_address_words = any(indicator in text_lower for indicator in address_indicators)
        return has_numbers and has_address_words
