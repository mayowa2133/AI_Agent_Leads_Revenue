from __future__ import annotations

from dataclasses import dataclass

from src.knowledge.graph.neo4j_client import get_neo4j_driver
from src.knowledge.graph.schemas import CONSTRAINTS


@dataclass(frozen=True)
class FireCode:
    code_id: str
    name: str
    edition: str | None = None


async def ensure_schema() -> None:
    driver = get_neo4j_driver()
    async with driver.session() as session:
        for stmt in CONSTRAINTS:
            await session.run(stmt)


async def upsert_fire_code(code: FireCode) -> None:
    driver = get_neo4j_driver()
    query = """
    MERGE (c:FireCode {code_id: $code_id})
    SET c.name = $name,
        c.edition = $edition
    """
    async with driver.session() as session:
        await session.run(
            query,
            code_id=code.code_id,
            name=code.name,
            edition=code.edition,
        )


async def upsert_building_type(type_id: str, label: str) -> None:
    driver = get_neo4j_driver()
    query = """
    MERGE (b:BuildingType {type_id: $type_id})
    SET b.label = $label
    """
    async with driver.session() as session:
        await session.run(query, type_id=type_id, label=label)


async def link_code_applies_to_building(code_id: str, building_type_id: str) -> None:
    driver = get_neo4j_driver()
    query = """
    MATCH (c:FireCode {code_id: $code_id})
    MATCH (b:BuildingType {type_id: $building_type_id})
    MERGE (c)-[:APPLIES_TO]->(b)
    """
    async with driver.session() as session:
        await session.run(query, code_id=code_id, building_type_id=building_type_id)


async def get_applicable_codes(building_type_id: str) -> list[dict]:
    """
    Return a minimal list of codes applicable to the given building type.
    """
    driver = get_neo4j_driver()
    query = """
    MATCH (c:FireCode)-[:APPLIES_TO]->(b:BuildingType {type_id: $building_type_id})
    RETURN c.code_id AS code_id, c.name AS name, c.edition AS edition
    ORDER BY c.code_id
    """
    async with driver.session() as session:
        res = await session.run(query, building_type_id=building_type_id)
        rows = await res.data()
    return rows


async def seed_minimal_fire_safety_graph() -> None:
    """
    MVP seed to unblock end-to-end demos.
    Expand with jurisdiction-specific enforcement and amendments later.
    """
    await ensure_schema()
    await upsert_fire_code(FireCode(code_id="NFPA_72", name="National Fire Alarm and Signaling Code", edition="2022"))
    await upsert_fire_code(FireCode(code_id="NFPA_25", name="Inspection, Testing, and Maintenance of Water-Based Fire Protection Systems", edition="2023"))
    await upsert_building_type("hospital", "Hospital")
    await upsert_building_type("data_center", "Data Center")
    await link_code_applies_to_building("NFPA_72", "hospital")
    await link_code_applies_to_building("NFPA_72", "data_center")
    await link_code_applies_to_building("NFPA_25", "hospital")


