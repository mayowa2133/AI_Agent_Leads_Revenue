"""Status normalization for permit data."""

from __future__ import annotations

import re
from typing import Literal

# Common status mappings
STATUS_MAPPINGS: dict[str, str] = {
    # Numbers that might be status codes
    "34845": "issued",  # Common Accela status code
    "2103": "issued",
    # Names that appear in status field (likely inspector names)
    "rita ghose": "in_progress",
    "tunnel": "in_progress",
    # Addresses that appear in status field (data extraction error)
    "2103 w martin": "issued",
    "10 ft tunnel": "in_progress",
    # Common variations
    "canceled": "canceled",
    "cancelled": "canceled",
    "closed": "closed",
    "completed": "completed",
    "finished": "completed",
}

# Status categories
GOOD_STATUSES: list[str] = ["issued", "approved", "active", "completed", "in progress", "in_progress"]
PROGRESS_STATUSES: list[str] = ["inspection", "passed", "scheduled", "ready", "in progress", "in_progress"]


def normalize_status(status: str | None) -> str:
    """
    Normalize permit status to standard values.
    
    Args:
        status: Raw status string from permit data
        
    Returns:
        Normalized status string
    """
    if not status:
        return "unknown"
    
    status_lower = status.lower().strip()
    
    # Check direct mappings first
    if status_lower in STATUS_MAPPINGS:
        return STATUS_MAPPINGS[status_lower]
    
    # Check if it's already a good status
    for good_status in GOOD_STATUSES:
        if good_status in status_lower:
            return good_status.replace("_", " ")
    
    # Check if it's a progress status
    for progress_status in PROGRESS_STATUSES:
        if progress_status in status_lower:
            return progress_status.replace("_", " ")
    
    # Check for common patterns
    if re.match(r"^\d+$", status_lower):
        # Pure number - likely a status code, default to "issued"
        return "issued"
    
    if len(status_lower.split()) > 2:
        # Multiple words - likely not a status, might be address or name
        # Check if it looks like an address
        if any(word in status_lower for word in ["street", "st", "ave", "avenue", "road", "rd", "drive", "dr"]):
            return "issued"  # Default for address-like values
        # Otherwise might be inspector name or other data
        return "in_progress"
    
    # If it's a single word and not recognized, return as-is but lowercase
    return status_lower


def is_good_status(status: str | None) -> bool:
    """Check if status indicates a good/active permit."""
    normalized = normalize_status(status)
    return any(gs in normalized for gs in GOOD_STATUSES)


def is_progress_status(status: str | None) -> bool:
    """Check if status indicates progress/inspection."""
    normalized = normalize_status(status)
    return any(ps in normalized for ps in PROGRESS_STATUSES)
