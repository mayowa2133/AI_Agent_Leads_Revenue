from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx


class ServiceTitanError(RuntimeError):
    pass


@dataclass(frozen=True)
class ServiceTitanAuth:
    client_id: str
    client_secret: str
    app_key: str
    base_url: str
    tenant_id: str


class ServiceTitanClient:
    """
    Minimal async REST wrapper around ServiceTitan.

    This is intentionally small; we only implement endpoints needed for the MVP:
    - bookings create
    - availability lookup
    - pricebook services lookup
    - customers lookup (optional)
    """

    def __init__(self, *, auth: ServiceTitanAuth, timeout_s: float = 30.0):
        self.auth = auth
        self._client = httpx.AsyncClient(base_url=auth.base_url.rstrip("/"), timeout=timeout_s)
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_token(self) -> str:
        if self._token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._token
        # NOTE: ServiceTitan OAuth specifics vary by region/tenant.
        # This is a generic client-credentials flow placeholder.
        resp = await self._client.post(
            "/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.auth.client_id,
                "client_secret": self.auth.client_secret,
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise ServiceTitanError(f"Token error {resp.status_code}: {resp.text}")
        data = resp.json()
        self._token = data["access_token"]
        # Many providers return expires_in seconds.
        expires_in = data.get("expires_in")
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            self._token_expires_at = datetime.utcnow().replace(microsecond=0)  # coarse is fine
            self._token_expires_at = self._token_expires_at + timedelta(seconds=int(expires_in) - 30)
        return self._token

    async def _request(self, method: str, url: str, *, json: dict | None = None, params: dict | None = None) -> Any:
        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "ST-App-Key": self.auth.app_key,
            "Accept": "application/json",
        }
        resp = await self._client.request(method, url, json=json, params=params, headers=headers)
        if resp.status_code >= 400:
            raise ServiceTitanError(f"ServiceTitan error {resp.status_code}: {resp.text}")
        return resp.json()

    async def create_booking(self, *, customer_id: str, job_type: str, scheduled_datetime: datetime, notes: str) -> Any:
        payload = {
            "customerId": customer_id,
            "jobType": job_type,
            "scheduledDateTime": scheduled_datetime.isoformat(),
            "notes": notes,
        }
        return await self._request("POST", f"/bookings/v2/tenant/{self.auth.tenant_id}/bookings", json=payload)

    async def check_availability(self, *, technician_id: str, start: datetime, end: datetime) -> Any:
        params = {"technicianId": technician_id, "start": start.isoformat(), "end": end.isoformat()}
        return await self._request(
            "GET",
            f"/dispatch/v2/tenant/{self.auth.tenant_id}/technicians/availability",
            params=params,
        )

    async def get_pricebook_services(self, *, category: str) -> Any:
        params = {"category": category}
        return await self._request(
            "GET",
            f"/pricebook/v2/tenant/{self.auth.tenant_id}/services",
            params=params,
        )

    async def find_customers(self, *, query: str, limit: int = 10) -> Any:
        """
        Best-effort customer search; exact endpoints vary by ST API version.
        """
        params = {"query": query, "pageSize": max(1, min(limit, 100))}
        return await self._request(
            "GET",
            f"/crm/v2/tenant/{self.auth.tenant_id}/customers",
            params=params,
        )


