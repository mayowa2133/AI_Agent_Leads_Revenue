"""Open Data API clients for permit data."""

from src.signal_engine.api.socrata_client import SocrataPermitClient
from src.signal_engine.api.ckan_client import CKANPermitClient
from src.signal_engine.api.custom_api_client import CustomAPIPermitClient
from src.signal_engine.api.base_api_client import BaseAPIPermitClient

__all__ = [
    "SocrataPermitClient",
    "CKANPermitClient",
    "CustomAPIPermitClient",
    "BaseAPIPermitClient",
]
