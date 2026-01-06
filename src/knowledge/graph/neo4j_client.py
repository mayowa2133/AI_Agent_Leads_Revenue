from __future__ import annotations

from functools import lru_cache

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.core.config import get_settings


@lru_cache(maxsize=1)
def get_neo4j_driver() -> AsyncDriver:
    settings = get_settings()
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def close_neo4j_driver() -> None:
    try:
        driver = get_neo4j_driver()
    except Exception:
        return
    await driver.close()
    get_neo4j_driver.cache_clear()


