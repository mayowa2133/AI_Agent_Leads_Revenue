"""Quality filtering for permits before enrichment."""

from __future__ import annotations

import logging
from typing import Callable

from src.signal_engine.models import PermitData
from src.signal_engine.quality.permit_quality import PermitQualityScorer, QualityScore

logger = logging.getLogger(__name__)


class QualityFilter:
    """
    Filter permits by quality before enrichment.
    
    This saves API credits by only enriching high-quality permits
    that are likely to result in successful lead generation.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        validate_addresses: bool = False,
        custom_filter: Callable[[PermitData], bool] | None = None,
    ):
        """
        Initialize quality filter.
        
        Args:
            threshold: Minimum quality score (0.0-1.0)
            validate_addresses: Whether to validate addresses with geocoding (slower)
            custom_filter: Optional custom filter function
        """
        self.threshold = threshold
        self.validate_addresses = validate_addresses
        self.custom_filter = custom_filter
        self.scorer = PermitQualityScorer()

    async def filter_permits(
        self, permits: list[PermitData]
    ) -> tuple[list[PermitData], list[PermitData], dict[str, int]]:
        """
        Filter permits by quality.
        
        Args:
            permits: List of permits to filter
        
        Returns:
            Tuple of (high_quality_permits, filtered_permits, stats)
            - high_quality_permits: Permits that passed quality check
            - filtered_permits: Permits that were filtered out
            - stats: Statistics about filtering
        """
        if not permits:
            return [], [], {}

        high_quality = []
        filtered_out = []
        score_distribution: dict[str, int] = {
            "excellent": 0,  # 0.8-1.0
            "good": 0,  # 0.6-0.8
            "fair": 0,  # 0.4-0.6
            "poor": 0,  # 0.0-0.4
        }

        for permit in permits:
            # Get quality score
            if self.validate_addresses:
                should_enrich, score_result = await self.scorer.should_enrich_with_validation(
                    permit, self.threshold
                )
            else:
                score_result = self.scorer.score(permit)
                should_enrich = score_result.total_score >= self.threshold

            # Apply custom filter if provided
            if should_enrich and self.custom_filter:
                should_enrich = self.custom_filter(permit)

            # Categorize score
            if score_result.total_score >= 0.8:
                score_distribution["excellent"] += 1
            elif score_result.total_score >= 0.6:
                score_distribution["good"] += 1
            elif score_result.total_score >= 0.4:
                score_distribution["fair"] += 1
            else:
                score_distribution["poor"] += 1

            if should_enrich:
                high_quality.append(permit)
            else:
                filtered_out.append(permit)

        stats = {
            "total": len(permits),
            "passed": len(high_quality),
            "filtered": len(filtered_out),
            "filter_rate": len(filtered_out) / len(permits) if permits else 0.0,
            "score_distribution": score_distribution,
        }

        logger.info(
            f"Quality filter: {len(high_quality)}/{len(permits)} permits passed "
            f"({len(high_quality)/len(permits)*100:.1f}%) "
            f"with threshold {self.threshold}"
        )

        return high_quality, filtered_out, stats

    def filter_permits_sync(
        self, permits: list[PermitData]
    ) -> tuple[list[PermitData], list[PermitData], dict[str, int]]:
        """
        Filter permits synchronously (without address validation).
        
        Faster but less accurate than async version.
        
        Args:
            permits: List of permits to filter
        
        Returns:
            Tuple of (high_quality_permits, filtered_permits, stats)
        """
        if not permits:
            return [], [], {}

        high_quality = []
        filtered_out = []
        score_distribution: dict[str, int] = {
            "excellent": 0,
            "good": 0,
            "fair": 0,
            "poor": 0,
        }

        for permit in permits:
            score_result = self.scorer.score(permit)
            should_enrich = score_result.total_score >= self.threshold

            # Apply custom filter if provided
            if should_enrich and self.custom_filter:
                should_enrich = self.custom_filter(permit)

            # Categorize score
            if score_result.total_score >= 0.8:
                score_distribution["excellent"] += 1
            elif score_result.total_score >= 0.6:
                score_distribution["good"] += 1
            elif score_result.total_score >= 0.4:
                score_distribution["fair"] += 1
            else:
                score_distribution["poor"] += 1

            if should_enrich:
                high_quality.append(permit)
            else:
                filtered_out.append(permit)

        stats = {
            "total": len(permits),
            "passed": len(high_quality),
            "filtered": len(filtered_out),
            "filter_rate": len(filtered_out) / len(permits) if permits else 0.0,
            "score_distribution": score_distribution,
        }

        logger.info(
            f"Quality filter (sync): {len(high_quality)}/{len(permits)} permits passed "
            f"({len(high_quality)/len(permits)*100:.1f}%) "
            f"with threshold {self.threshold}"
        )

        return high_quality, filtered_out, stats
