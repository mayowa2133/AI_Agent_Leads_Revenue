from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from src.signal_engine.models import PermitData


class ScraperError(RuntimeError):
    pass


class BaseScraper(ABC):
    """
    Base interface for scrapers.

    Implementations should be:
    - idempotent (same run can return same permits)
    - polite (rate-limited) and resilient (retries)
    """

    source: str

    def __init__(self, *, max_retries: int = 3, base_delay_s: float = 1.0):
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s

    @abstractmethod
    async def scrape(self) -> list[PermitData]:
        """Full scrape (initial ingest)."""

    @abstractmethod
    async def check_for_updates(self, last_run: datetime) -> list[PermitData]:
        """Incremental scrape since last run."""

    async def _with_retries(self, coro_fn, *args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await coro_fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.base_delay_s * (2 ** (attempt - 1)))
        raise ScraperError(f"{self.source}: failed after {self.max_retries} retries") from last_exc


def dedupe_permits(items: Iterable[PermitData]) -> list[PermitData]:
    """
    Deduplicate by (source, permit_id).
    Last write wins (useful when later items have more fields populated).
    """
    out: dict[tuple[str, str], PermitData] = {}
    for it in items:
        out[(it.source, it.permit_id)] = it
    return list(out.values())


