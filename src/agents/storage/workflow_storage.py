"""Storage layer for workflow state and responses using JSON file storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.state import AOROState

logger = logging.getLogger(__name__)


class WorkflowStorage:
    """
    Storage for workflow state and responses using JSON file storage.
    
    Matches Phase 1 storage approach for consistency. Can be upgraded to
    database later if needed.
    """

    def __init__(self, *, storage_file: Path | str | None = None):
        """
        Initialize workflow storage.

        Args:
            storage_file: Path to JSON storage file (default: data/workflow_states.json)
        """
        if storage_file is None:
            storage_file = Path("data/workflow_states.json")
        elif isinstance(storage_file, str):
            storage_file = Path(storage_file)

        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

    def save_workflow_state(self, lead_id: str, state: AOROState) -> None:
        """
        Save workflow state snapshot.

        Args:
            lead_id: Lead ID (used as key)
            state: Workflow state to save
        """
        states = self.load_all_states()
        
        # Convert datetime objects to ISO strings for JSON
        state_dict = self._state_to_dict(state)
        state_dict["_saved_at"] = datetime.now().isoformat()
        
        states[lead_id] = state_dict
        
        # Save to file
        self.storage_file.write_text(json.dumps(states, indent=2))
        logger.debug(f"Saved workflow state for lead: {lead_id}")

    def load_workflow_state(self, lead_id: str) -> AOROState | None:
        """
        Load workflow state for a lead.

        Args:
            lead_id: Lead ID to retrieve

        Returns:
            AOROState or None if not found
        """
        states = self.load_all_states()
        state_dict = states.get(lead_id)
        
        if not state_dict:
            return None
        
        return self._dict_to_state(state_dict)

    def load_all_states(self) -> dict[str, dict[str, Any]]:
        """
        Load all workflow states from storage.

        Returns:
            Dictionary mapping lead_id to state dictionaries
        """
        if not self.storage_file.exists():
            return {}

        try:
            content = self.storage_file.read_text()
            if not content.strip():
                return {}

            states = json.loads(content)
            return states if isinstance(states, dict) else {}
        except Exception as e:
            logger.error(f"Error loading workflow states: {e}", exc_info=True)
            return {}

    def save_outreach(self, lead_id: str, outreach: dict[str, Any]) -> None:
        """
        Save outreach message that was sent.

        Args:
            lead_id: Lead ID
            outreach: Outreach data (channel, subject, body, sent_at, etc.)
        """
        outreachs = self.load_all_outreachs()
        outreach["lead_id"] = lead_id
        outreach["sent_at"] = outreach.get("sent_at") or datetime.now().isoformat()
        
        if lead_id not in outreachs:
            outreachs[lead_id] = []
        
        outreachs[lead_id].append(outreach)
        
        # Save to file
        outreach_file = self.storage_file.parent / "workflow_outreachs.json"
        outreach_file.write_text(json.dumps(outreachs, indent=2))
        logger.debug(f"Saved outreach for lead: {lead_id}")

    def load_all_outreachs(self) -> dict[str, list[dict[str, Any]]]:
        """
        Load all outreach messages.

        Returns:
            Dictionary mapping lead_id to list of outreach dictionaries
        """
        outreach_file = self.storage_file.parent / "workflow_outreachs.json"
        
        if not outreach_file.exists():
            return {}

        try:
            content = outreach_file.read_text()
            if not content.strip():
                return {}

            outreachs = json.loads(content)
            return outreachs if isinstance(outreachs, dict) else {}
        except Exception as e:
            logger.error(f"Error loading outreachs: {e}", exc_info=True)
            return {}

    def save_response(self, lead_id: str, response: dict[str, Any]) -> None:
        """
        Save response received.

        Args:
            lead_id: Lead ID
            response: Response data (content, received_at, source, etc.)
        """
        responses = self.load_all_responses()
        response["lead_id"] = lead_id
        response["received_at"] = response.get("received_at") or datetime.now().isoformat()
        
        if lead_id not in responses:
            responses[lead_id] = []
        
        responses[lead_id].append(response)
        
        # Save to file
        response_file = self.storage_file.parent / "workflow_responses.json"
        response_file.write_text(json.dumps(responses, indent=2))
        logger.debug(f"Saved response for lead: {lead_id}")

    def load_all_responses(self) -> dict[str, list[dict[str, Any]]]:
        """
        Load all responses.

        Returns:
            Dictionary mapping lead_id to list of response dictionaries
        """
        response_file = self.storage_file.parent / "workflow_responses.json"
        
        if not response_file.exists():
            return {}

        try:
            content = response_file.read_text()
            if not content.strip():
                return {}

            responses = json.loads(content)
            return responses if isinstance(responses, dict) else {}
        except Exception as e:
            logger.error(f"Error loading responses: {e}", exc_info=True)
            return {}

    def get_latest_response(self, lead_id: str) -> dict[str, Any] | None:
        """
        Get the latest response for a lead.

        Args:
            lead_id: Lead ID

        Returns:
            Latest response dictionary or None
        """
        responses = self.load_all_responses()
        lead_responses = responses.get(lead_id, [])
        
        if not lead_responses:
            return None
        
        # Return most recent (last in list)
        return lead_responses[-1]

    def _state_to_dict(self, state: AOROState) -> dict[str, Any]:
        """Convert AOROState to dictionary, handling datetime serialization."""
        state_dict = dict(state)
        
        # Convert datetime objects to ISO strings
        for key, value in state_dict.items():
            if isinstance(value, datetime):
                state_dict[key] = value.isoformat()
            elif isinstance(value, dict):
                # Handle nested datetime fields
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, datetime):
                        value[nested_key] = nested_value.isoformat()
        
        return state_dict

    def _dict_to_state(self, data: dict[str, Any]) -> AOROState:
        """Convert dictionary to AOROState, handling datetime deserialization."""
        # Convert ISO date strings back to datetime
        if "appointment_datetime" in data and data["appointment_datetime"]:
            try:
                data["appointment_datetime"] = datetime.fromisoformat(
                    data["appointment_datetime"].replace("Z", "+00:00")
                )
            except Exception:
                pass
        
        # Remove internal fields
        data.pop("_saved_at", None)
        
        return AOROState(**data)
