"""Infrastructure components for agent workflow."""

from src.agents.infrastructure.crm_client import CRMClient
from src.agents.infrastructure.email_sender import EmailSender

__all__ = ["EmailSender", "CRMClient"]
