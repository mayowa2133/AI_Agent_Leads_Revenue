from __future__ import annotations

from src.agents.state import AOROState
from src.agents.tools.case_study_search import search_case_studies
from src.agents.tools.regulatory_lookup import lookup_applicable_fire_codes
from src.core.observability import traceable_fn


@traceable_fn("researcher_agent")
async def researcher_node(state: AOROState) -> AOROState:
    permit = state.get("permit_data") or {}
    building_type = permit.get("building_type")
    permit_type = permit.get("permit_type")
    status = permit.get("status")

    applicable = await lookup_applicable_fire_codes(building_type=building_type)

    # MVP compliance gaps are heuristic; later: infer from inspection history + code graph.
    compliance_gaps: list[str] = []
    if permit_type and "fire" in str(permit_type).lower():
        compliance_gaps.append("Fire alarm system scope likely impacted by code-required inspection/acceptance testing.")
    if status and "inspection" in str(status).lower():
        compliance_gaps.append("Inspection milestone indicates near-term compliance deadline.")

    query = f"{state.get('company_name','')} {building_type or ''} {permit_type or ''} fire safety case study"
    case_studies = await search_case_studies(query, top_k=5)

    return {
        **state,
        "applicable_codes": applicable,
        "compliance_gaps": compliance_gaps,
        "case_studies": case_studies,
    }


