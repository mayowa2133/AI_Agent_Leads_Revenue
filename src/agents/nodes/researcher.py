from __future__ import annotations

from src.agents.state import AOROState
from src.agents.tools.case_study_search import search_case_studies
from src.agents.tools.regulatory_lookup import lookup_applicable_fire_codes
from src.core.observability import traceable_fn


async def calculate_compliance_urgency(state: AOROState) -> float:
    """
    Calculate compliance urgency score (0.0 - 1.0).
    
    Factors:
    - Permit status (inspection scheduled = high urgency)
    - Permit type (fire-related = higher urgency)
    - Number of applicable codes
    - Number of compliance gaps
    - Building type risk level
    
    Args:
        state: Current workflow state
        
    Returns:
        Urgency score between 0.0 and 1.0
    """
    permit = state.get("permit_data") or {}
    status = str(permit.get("status", "")).lower()
    permit_type = str(permit.get("permit_type", "")).lower()
    building_type = str(permit.get("building_type", "")).lower()
    
    codes = state.get("applicable_codes") or []
    gaps = state.get("compliance_gaps") or []
    
    score = 0.0
    
    # Status-based urgency (0.0 - 0.4)
    if "inspection" in status and ("scheduled" in status or "required" in status):
        score += 0.4  # High urgency - inspection coming up
    elif "inspection" in status:
        score += 0.3
    elif "issued" in status or "approved" in status:
        score += 0.2  # Medium urgency - permit issued
    elif "pending" in status:
        score += 0.1  # Low urgency - still pending
    
    # Permit type urgency (0.0 - 0.2)
    if "fire" in permit_type:
        score += 0.2  # Fire-related permits are high priority
    elif "sprinkler" in permit_type or "alarm" in permit_type:
        score += 0.15
    elif "hvac" in permit_type or "mechanical" in permit_type:
        score += 0.1
    
    # Code-based urgency (0.0 - 0.2)
    if len(codes) > 0:
        # More codes = higher urgency (capped at 0.2)
        code_score = min(len(codes) * 0.05, 0.2)
        score += code_score
    
    # Gap-based urgency (0.0 - 0.15)
    if len(gaps) > 0:
        gap_score = min(len(gaps) * 0.075, 0.15)
        score += gap_score
    
    # Building type risk level (0.0 - 0.05)
    high_risk_types = ["hospital", "data_center", "school", "nursing", "care"]
    if any(risk_type in building_type for risk_type in high_risk_types):
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0


@traceable_fn("researcher_agent")
async def researcher_node(state: AOROState) -> AOROState:
    """
    Researcher agent node that:
    - Queries Neo4j for applicable fire codes
    - Searches Pinecone for relevant case studies
    - Identifies compliance gaps
    - Calculates compliance urgency score
    """
    permit = state.get("permit_data") or {}
    building_type = permit.get("building_type")
    permit_type = permit.get("permit_type")
    status = permit.get("status")

    # Lookup applicable fire codes
    applicable = await lookup_applicable_fire_codes(building_type=building_type)

    # MVP compliance gaps are heuristic; later: infer from inspection history + code graph.
    compliance_gaps: list[str] = []
    if permit_type and "fire" in str(permit_type).lower():
        compliance_gaps.append("Fire alarm system scope likely impacted by code-required inspection/acceptance testing.")
    if status and "inspection" in str(status).lower():
        compliance_gaps.append("Inspection milestone indicates near-term compliance deadline.")

    # Search for relevant case studies
    query = f"{state.get('company_name','')} {building_type or ''} {permit_type or ''} fire safety case study"
    case_studies = await search_case_studies(query, top_k=5)

    # Calculate compliance urgency score
    urgency_score = await calculate_compliance_urgency({
        **state,
        "applicable_codes": applicable,
        "compliance_gaps": compliance_gaps,
    })

    return {
        **state,
        "applicable_codes": applicable,
        "compliance_gaps": compliance_gaps,
        "case_studies": case_studies,
        "compliance_urgency_score": urgency_score,
    }


