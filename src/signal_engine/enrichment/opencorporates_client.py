from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class OpenCorporatesError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenCorporatesCompany:
    name: str
    jurisdiction_code: str
    company_number: str


class OpenCorporatesClient:
    """
    Minimal OpenCorporates client for officer/agent name lookup.

    Uses public API. Optionally accepts api_key for higher rate limits.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.opencorporates.com/v0.4",
        timeout_s: float = 20.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search_company(self, *, name: str) -> OpenCorporatesCompany | None:
        if not name:
            return None

        url = f"{self.base_url}/companies/search"
        params = {"q": name, "per_page": 1}
        if self.api_key:
            params["api_token"] = self.api_key

        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            raise OpenCorporatesError(f"OpenCorporates error {resp.status_code}: {resp.text}")

        data = resp.json() or {}
        companies = data.get("results", {}).get("companies", [])
        if not companies:
            return None

        company = companies[0].get("company", {})
        jurisdiction_code = company.get("jurisdiction_code")
        company_number = company.get("company_number")
        company_name = company.get("name") or name

        if not jurisdiction_code or not company_number:
            return None

        return OpenCorporatesCompany(
            name=company_name,
            jurisdiction_code=jurisdiction_code,
            company_number=company_number,
        )

    async def get_officer_names(
        self,
        *,
        jurisdiction_code: str,
        company_number: str,
        limit: int = 3,
    ) -> list[str]:
        if not jurisdiction_code or not company_number:
            return []

        url = f"{self.base_url}/companies/{jurisdiction_code}/{company_number}/officers"
        params = {"per_page": max(1, min(limit, 10))}
        if self.api_key:
            params["api_token"] = self.api_key

        resp = await self._client.get(url, params=params)
        if resp.status_code >= 400:
            logger.debug(f"OpenCorporates officers returned {resp.status_code}: {resp.text}")
            return []

        data = resp.json() or {}
        officers = data.get("results", {}).get("officers", [])
        names: list[str] = []
        for entry in officers:
            officer = entry.get("officer", {})
            name = officer.get("name")
            if name:
                names.append(name)

        return names[:limit]

    async def find_officer_names_by_company(self, *, name: str) -> list[str]:
        company = await self.search_company(name=name)
        if not company:
            return []

        return await self.get_officer_names(
            jurisdiction_code=company.jurisdiction_code,
            company_number=company.company_number,
        )
