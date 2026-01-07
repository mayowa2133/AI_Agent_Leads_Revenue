"""LLM-based content processor for extracting compliance triggers."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.core.config import get_settings
from src.signal_engine.models import RegulatoryUpdate

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # type: ignore

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RegulatoryContentProcessor:
    """
    Process regulatory content using LLM to extract compliance triggers.
    
    Uses GPT-4o to extract:
    - Applicable NFPA codes
    - Building types affected
    - Compliance deadlines
    - Key compliance triggers
    """

    def __init__(self, *, enabled: bool = True):
        """
        Initialize content processor.
        
        Args:
            enabled: Whether LLM processing is enabled (can be disabled for cost savings)
        """
        self.enabled = enabled
        self.settings = get_settings()
        self.client = (
            AsyncOpenAI(api_key=self.settings.openai_api_key)
            if enabled and self.settings.openai_api_key and AsyncOpenAI
            else None
        )

    async def process_update(self, update: RegulatoryUpdate) -> RegulatoryUpdate:
        """
        Process a regulatory update to extract compliance triggers.
        
        Args:
            update: Regulatory update to process
            
        Returns:
            Updated RegulatoryUpdate with extracted information
        """
        if not self.enabled or not self.client:
            logger.debug("LLM processing disabled, skipping content extraction")
            return update

        # If already processed (has triggers), skip
        if update.compliance_triggers or update.building_types_affected:
            logger.debug(f"Update {update.update_id} already processed, skipping")
            return update

        try:
            extracted = await self._extract_with_llm(update)
            
            # Update the regulatory update with extracted information
            return RegulatoryUpdate(
                **update.model_dump(),
                applicable_codes=extracted.get("applicable_codes", update.applicable_codes),
                compliance_triggers=extracted.get("compliance_triggers", []),
                building_types_affected=extracted.get("building_types_affected", []),
            )
        except Exception as e:
            logger.warning(f"Error processing update {update.update_id} with LLM: {e}")
            return update  # Return original if processing fails

    async def _extract_with_llm(self, update: RegulatoryUpdate) -> dict:
        """
        Use LLM to extract compliance information from regulatory update.
        
        Args:
            update: Regulatory update to process
            
        Returns:
            Dictionary with extracted information
        """
        prompt = f"""Analyze this regulatory update and extract compliance-relevant information.

Title: {update.title}
Source: {update.source_name}
Content: {update.content[:4000]}  # Limit content length

Extract the following information in JSON format:
1. applicable_codes: List of NFPA codes, EPA regulations, or other codes mentioned (e.g., ["NFPA 72", "NFPA 101"])
2. compliance_triggers: List of key compliance triggers or requirements (e.g., ["Mandatory inspection by 2026", "Phase-out of R-22 refrigerant"])
3. building_types_affected: List of building types affected (e.g., ["hospitals", "data_centers", "commercial"])

Return only valid JSON in this format:
{{
    "applicable_codes": ["code1", "code2"],
    "compliance_triggers": ["trigger1", "trigger2"],
    "building_types_affected": ["type1", "type2"]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a compliance expert analyzing regulatory updates. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                extracted = json.loads(content)
                return {
                    "applicable_codes": extracted.get("applicable_codes", []),
                    "compliance_triggers": extracted.get("compliance_triggers", []),
                    "building_types_affected": extracted.get("building_types_affected", []),
                }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)

        # Return empty extraction on error
        return {
            "applicable_codes": [],
            "compliance_triggers": [],
            "building_types_affected": [],
        }

    async def process_batch(self, updates: list[RegulatoryUpdate]) -> list[RegulatoryUpdate]:
        """
        Process multiple updates in batch.
        
        Args:
            updates: List of regulatory updates to process
            
        Returns:
            List of processed updates
        """
        if not self.enabled:
            return updates

        processed = []
        for update in updates:
            processed_update = await self.process_update(update)
            processed.append(processed_update)

        return processed

