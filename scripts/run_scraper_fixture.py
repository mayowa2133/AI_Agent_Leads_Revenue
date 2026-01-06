from __future__ import annotations

import asyncio
from pathlib import Path

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import example_fire_permit_scraper


def _fixture_file_url() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / "tests" / "fixtures" / "permits_table.html"
    return fixture.as_uri()


async def main():
    tenant_id = "demo"
    start_url = _fixture_file_url()

    scraper = example_fire_permit_scraper(start_url)

    async with tenant_scoped_session(tenant_id):
        permits = await scraper.scrape()
        for p in permits:
            print(p.model_dump())


if __name__ == "__main__":
    asyncio.run(main())


