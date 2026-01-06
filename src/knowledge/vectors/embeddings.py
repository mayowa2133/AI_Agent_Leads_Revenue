from __future__ import annotations

from typing import Iterable

from src.core.observability import get_openai_client


async def embed_texts(texts: Iterable[str], *, model: str = "text-embedding-3-small") -> list[list[float]]:
    client = get_openai_client()
    resp = await client.embeddings.create(model=model, input=list(texts))
    return [d.embedding for d in resp.data]


async def embed_text(text: str, *, model: str = "text-embedding-3-small") -> list[float]:
    return (await embed_texts([text], model=model))[0]


