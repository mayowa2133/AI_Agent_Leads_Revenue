from __future__ import annotations

from typing import Any

from src.core.security import current_tenant_id
from src.knowledge.vectors.embeddings import embed_text
from src.knowledge.vectors.pinecone_client import get_index, tenant_namespace


async def search_case_studies(query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Semantic search against tenant-namespaced case studies.
    Returns a normalized list of {id, score, metadata}.
    """
    try:
        vec = await embed_text(query)
    except Exception:
        return []

    try:
        index = get_index()
        ns = tenant_namespace(current_tenant_id())
        res = index.query(vector=vec, top_k=top_k, include_metadata=True, namespace=ns)
    except Exception:
        return []

    matches = res.get("matches") if isinstance(res, dict) else getattr(res, "matches", None)
    if not matches:
        return []

    out: list[dict[str, Any]] = []
    for m in matches:
        out.append(
            {
                "id": m.get("id") if isinstance(m, dict) else getattr(m, "id", None),
                "score": m.get("score") if isinstance(m, dict) else getattr(m, "score", None),
                "metadata": m.get("metadata") if isinstance(m, dict) else getattr(m, "metadata", None),
            }
        )
    return out


