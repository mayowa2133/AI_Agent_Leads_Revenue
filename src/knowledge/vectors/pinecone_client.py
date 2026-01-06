from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.core.config import get_settings
from src.core.security import current_tenant_id


def _get_pinecone() -> Any:
    """
    Pinecone python package has had naming changes across versions.
    This helper keeps imports centralized.
    """
    try:
        from pinecone import Pinecone  # type: ignore

        return Pinecone
    except Exception:
        from pinecone import PineconeClient  # type: ignore

        return PineconeClient


@lru_cache(maxsize=1)
def get_pinecone_client() -> Any:
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required")
    PineconeCtor = _get_pinecone()
    return PineconeCtor(api_key=settings.pinecone_api_key)


def tenant_namespace(tenant_id: str | None = None) -> str:
    tenant_id = tenant_id or current_tenant_id()
    if not tenant_id:
        return "default"
    return tenant_id


def get_index() -> Any:
    settings = get_settings()
    pc = get_pinecone_client()
    # Newer SDKs use .Index(name); older use pc.Index too.
    if hasattr(pc, "Index"):
        return pc.Index(settings.pinecone_index)
    return pc.index(settings.pinecone_index)


def ensure_index(*, dimension: int = 1536, metric: str = "cosine") -> None:
    """
    Best-effort index creation for local/bootstrap flows.
    No-op if the index already exists.
    """
    settings = get_settings()
    pc = get_pinecone_client()

    # Newer SDK: pc.list_indexes().names() / pc.create_index(...)
    try:
        existing = pc.list_indexes()
        names = existing.names() if hasattr(existing, "names") else [i["name"] for i in existing]
        if settings.pinecone_index in names:
            return
        pc.create_index(name=settings.pinecone_index, dimension=dimension, metric=metric)
        return
    except Exception:
        # Older SDK variants: fall back to best-effort.
        try:
            indexes = pc.list_indexes()
            if settings.pinecone_index in indexes:
                return
            pc.create_index(settings.pinecone_index, dimension=dimension, metric=metric)
        except Exception:
            # If creation isn't supported in this environment, leave as manual setup.
            return


