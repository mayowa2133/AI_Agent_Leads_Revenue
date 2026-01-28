from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class ClearbitError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClearbitCompany:
    name: str | None = None
    domain: str | None = None
    website: str | None = None


class ClearbitClient:
    """
    Minimal Clearbit client for company domain discovery.

    Uses the public autocomplete endpoint (no API key required).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://autocomplete.clearbit.com/v1",
        timeout_s: float = 20.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def suggest_company(self, *, query: str) -> ClearbitCompany | None:
        """
        Lookup company domain via Clearbit autocomplete.

        Args:
            query: Company name to search

        Returns:
            ClearbitCompany or None
        """
        if not query:
            return None

        url = f"{self.base_url}/companies/suggest"
        params = {"query": query}

        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            raise ClearbitError(f"Clearbit error {resp.status_code}: {resp.text}")

        data = resp.json() or []
        if not data:
            return None

        item = data[0]
        domain = item.get("domain")
        name = item.get("name")
        website = f"https://{domain}" if domain else None
        return ClearbitCompany(name=name, domain=domain, website=website)
