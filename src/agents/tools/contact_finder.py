from __future__ import annotations

from typing import Any

from src.signal_engine.enrichment.apollo_client import ApolloClient


async def find_contacts_via_apollo(
    *,
    api_key: str,
    company_name: str | None,
    company_domain: str | None = None,
    titles: list[str] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    client = ApolloClient(api_key=api_key)
    try:
        people = await client.find_decision_maker(
            company_name=company_name,
            company_domain=company_domain,
            titles=titles,
            limit=limit,
        )
        return [p.__dict__ for p in people]
    finally:
        await client.aclose()


