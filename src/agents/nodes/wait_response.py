"""WaitForResponse node - monitors for responses with timeout handling."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.agents.state import AOROState
from src.agents.storage.workflow_storage import WorkflowStorage
from src.core.config import get_settings

logger = logging.getLogger(__name__)


async def wait_response_node(state: AOROState) -> AOROState:
    """
    Wait for response with timeout handling.
    
    Checks for responses via storage (populated by webhook).
    If timeout reached, routes to FollowUp.
    If response received, routes to HandleResponse.
    """
    settings = get_settings()
    lead_id = state.get("lead_id", "")
    outreach_sent_at_str = state.get("outreach_sent_at")
    timeout_days = getattr(settings, "response_timeout_days", 7)
    
    storage = WorkflowStorage()
    
    # Check if response received (via webhook)
    latest_response = storage.get_latest_response(lead_id)
    
    def _to_naive(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    if latest_response:
        # Check if this response is newer than the outreach
        response_received_at = latest_response.get("received_at")
        if response_received_at and outreach_sent_at_str:
            try:
                response_time = _to_naive(datetime.fromisoformat(response_received_at.replace("Z", "+00:00")))
                outreach_time = _to_naive(datetime.fromisoformat(outreach_sent_at_str.replace("Z", "+00:00")))
                
                # Only process if response is after outreach
                if response_time > outreach_time:
                    logger.info(f"Response received for lead {lead_id}")
                    return {
                        **state,
                        "response_received": True,
                        "response_data": latest_response,
                    }
            except Exception as e:
                logger.warning(f"Error parsing dates: {e}")
                # If date parsing fails, assume response is valid
                return {
                    **state,
                    "response_received": True,
                    "response_data": latest_response,
                }
        else:
            # No timestamps, assume response is valid
            return {
                **state,
                "response_received": True,
                "response_data": latest_response,
            }
    
    # Check if timeout reached
    if outreach_sent_at_str:
        try:
            outreach_time = _to_naive(datetime.fromisoformat(outreach_sent_at_str.replace("Z", "+00:00")))
            time_elapsed = datetime.now() - outreach_time
            
            if time_elapsed.days >= timeout_days:
                logger.info(f"Response timeout reached for lead {lead_id} ({time_elapsed.days} days)")
                return {
                    **state,
                    "response_timeout": True,
                    "timeout_days": timeout_days,
                }
        except Exception as e:
            logger.warning(f"Error checking timeout: {e}")
    
    # Still waiting - for MVP, we'll mark as waiting and let the workflow continue
    # In production with checkpointer, this would interrupt and resume later
    logger.info(f"Still waiting for response from lead {lead_id}")
    return {
        **state,
        "response_received": False,
        "response_timeout": False,
        "waiting_for_response": True,
    }
