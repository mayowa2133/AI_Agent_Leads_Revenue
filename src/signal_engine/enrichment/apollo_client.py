from __future__ import annotations

from dataclasses import dataclass

import httpx


class ApolloError(RuntimeError):
    pass


@dataclass(frozen=True)
class ApolloPerson:
    full_name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None


class ApolloClient:
    """
    Minimal Apollo-style client wrapper.

    Note: Apollo endpoints/fields can change; this wrapper is intentionally small and
    isolates HTTP concerns so the rest of the system only consumes normalized objects.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.apollo.io/v1",
        timeout_s: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def find_decision_maker(
        self,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
        titles: list[str] | None = None,
        location: str | None = None,
        limit: int = 5,
    ) -> list[ApolloPerson]:
        """
        Find likely decision makers at a company.

        This uses a conservative, provider-agnostic request format; adapt the payload
        mapping to your Apollo plan once you have the exact endpoint/fields.
        """
        titles = titles or [
            "Facility Director",
            "Facilities Director",
            "Facilities Manager",
            "Director of Facilities",
            "Building Engineer",
            "Chief Engineer",
        ]

        # Provider-agnostic payload shape (adjust when wiring real Apollo endpoint)
        payload = {
            "api_key": self.api_key,
            "q_organization_name": company_name,
            "q_organization_domains": [company_domain] if company_domain else None,
            "person_titles": titles,
            "q_location": location,
            "page": 1,
            "per_page": max(1, min(limit, 25)),
        }

        # Remove Nones for cleaner requests.
        payload = {k: v for k, v in payload.items() if v is not None}

        url = f"{self.base_url}/mixed_people/search"
        resp = await self._client.post(url, json=payload)
        if resp.status_code >= 400:
            raise ApolloError(f"Apollo error {resp.status_code}: {resp.text}")

        data = resp.json()
        people = data.get("people") or data.get("contacts") or []
        out: list[ApolloPerson] = []
        for p in people:
            out.append(
                ApolloPerson(
                    full_name=p.get("name") or p.get("full_name"),
                    title=p.get("title"),
                    email=p.get("email"),
                    phone=p.get("phone") or p.get("phone_numbers", [None])[0],
                    linkedin_url=p.get("linkedin_url"),
                )
            )
        return out


