from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchSnippet:
    title: str
    snippet: str
    url: str


class SearchSnippetClient:
    """
    Google Custom Search wrapper for retrieving snippets.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        engine_id: str | None = None,
        base_url: str = "https://www.googleapis.com/customsearch/v1",
        timeout_s: float = 20.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.google_custom_search_api_key
        self.engine_id = engine_id or settings.google_custom_search_engine_id
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, *, query: str, limit: int = 5) -> list[SearchSnippet]:
        if not query or not self.api_key or not self.engine_id:
            return []

        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "num": max(1, min(limit, 10)),
        }

        resp = await self._client.get(self.base_url, params=params)
        if resp.status_code >= 400:
            logger.debug(f"Google CSE error {resp.status_code}: {resp.text}")
            return []

        data = resp.json() or {}
        items = data.get("items", []) or []
        results: list[SearchSnippet] = []
        for item in items:
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            url = item.get("link") or ""
            if title and snippet and url:
                results.append(SearchSnippet(title=title, snippet=snippet, url=url))

        return results
