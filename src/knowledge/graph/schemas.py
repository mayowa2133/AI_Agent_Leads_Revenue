from __future__ import annotations

# Schema statements for the Fire Code knowledge graph.

CONSTRAINTS = [
    "CREATE CONSTRAINT fire_code_id IF NOT EXISTS FOR (c:FireCode) REQUIRE c.code_id IS UNIQUE",
    "CREATE CONSTRAINT building_type_id IF NOT EXISTS FOR (b:BuildingType) REQUIRE b.type_id IS UNIQUE",
    "CREATE CONSTRAINT jurisdiction_fips IF NOT EXISTS FOR (j:Jurisdiction) REQUIRE j.fips_code IS UNIQUE",
]


