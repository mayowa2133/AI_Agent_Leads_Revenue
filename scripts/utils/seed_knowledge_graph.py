from __future__ import annotations

import asyncio

from src.knowledge.graph.fire_code_graph import seed_minimal_fire_safety_graph


async def main():
    await seed_minimal_fire_safety_graph()
    print("Seeded minimal fire safety knowledge graph.")


if __name__ == "__main__":
    asyncio.run(main())


