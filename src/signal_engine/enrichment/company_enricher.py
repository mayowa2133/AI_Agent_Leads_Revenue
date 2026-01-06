from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from src.signal_engine.enrichment.apollo_client import ApolloClient
from src.signal_engine.models import Company, DecisionMaker, EnrichedLead, PermitData


@dataclass(frozen=True)
class EnrichmentInputs:
    tenant_id: str
    permit: PermitData


def naive_company_guess_from_permit(permit: PermitData) -> Company:
    """
    MVP heuristic:
    - Use applicant_name if present, else a placeholder derived from address.
    In production:
    - Geocode address -> parcel/building owner -> match org -> domain.
    """
    if permit.applicant_name:
        name = permit.applicant_name
    else:
        name = f"Unknown Org ({permit.address[:32]})"
    return Company(name=name)


async def enrich_permit_to_lead(inputs: EnrichmentInputs) -> EnrichedLead:
    company = naive_company_guess_from_permit(inputs.permit)
    decision_maker: DecisionMaker | None = None

    # Apollo integration (optional in MVP; can be replaced with Clearbit, etc.)
    apollo_key = os.environ.get("APOLLO_API_KEY")
    if apollo_key:
        client = ApolloClient(api_key=apollo_key)
        try:
            people = await client.find_decision_maker(company_name=company.name, limit=3)
            if people:
                p0 = people[0]
                decision_maker = DecisionMaker(
                    full_name=p0.full_name,
                    title=p0.title,
                    email=p0.email,
                    phone=p0.phone,
                    linkedin_url=p0.linkedin_url,
                )
        finally:
            await client.aclose()

    lead_id = str(uuid.uuid4())
    return EnrichedLead(
        lead_id=lead_id,
        tenant_id=inputs.tenant_id,
        company=company,
        decision_maker=decision_maker,
        permit=inputs.permit,
    )


