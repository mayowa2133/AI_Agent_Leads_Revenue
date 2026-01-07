from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from src.core.security import tenant_scoped_session
from src.signal_engine.scrapers.permit_scraper import example_fire_permit_scraper


async def main():
    tenant_id = os.environ.get("TENANT_ID", "demo")
    start_url = os.environ.get("PERMIT_PORTAL_URL", "https://example.com/permits")

    scraper = example_fire_permit_scraper(start_url)

    async with tenant_scoped_session(tenant_id):
        permits = await scraper.check_for_updates(last_run=datetime.now(tz=timezone.utc))
        for p in permits:
            print(p.model_dump())


if __name__ == "__main__":
    asyncio.run(main())


