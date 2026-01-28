from __future__ import annotations

from src.knowledge.graph.fire_code_graph import get_applicable_codes


def normalize_building_type(building_type: str | None) -> str:
    if not building_type:
        return "unknown"
    s = building_type.strip().lower()
    if "hospital" in s:
        return "hospital"
    if "data" in s and "center" in s:
        return "data_center"
    return s.replace(" ", "_")[:64]


async def lookup_applicable_fire_codes(*, building_type: str | None) -> list[str]:
    """
    Lookup applicable fire codes for a building type.
    
    Returns empty list if Neo4j is unavailable (graceful degradation).
    """
    building_type_id = normalize_building_type(building_type)
    try:
        rows = await get_applicable_codes(building_type_id)
    except Exception:
        # Graceful degradation: return empty list if Neo4j unavailable
        # This allows testing Phase 2.1 without Neo4j running
        return []
    
    # Return compact citations (id + edition) for LLM consumption.
    out: list[str] = []
    for r in rows:
        edition = r.get("edition")
        if edition:
            out.append(f'{r["code_id"]} ({edition})')
        else:
            out.append(r["code_id"])
    return out


