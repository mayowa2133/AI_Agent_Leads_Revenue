from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import wraps

from src.core.config import get_settings

_tenant_id_ctx: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def current_tenant_id() -> str | None:
    return _tenant_id_ctx.get()


async def verify_tenant_access(tenant_id: str) -> bool:
    # Dev-friendly allowlist from env; swap with DB-backed tenant auth later.
    settings = get_settings()
    return tenant_id in settings.tenant_list()


@asynccontextmanager
async def tenant_scoped_session(tenant_id: str):
    """
    Establish a tenant context for downstream calls.

    Note: DB-level RLS is implemented later; this context is used to enforce
    namespace scoping (e.g., Pinecone namespaces) and structured audit logs.
    """
    token = _tenant_id_ctx.set(tenant_id)
    try:
        yield
    finally:
        _tenant_id_ctx.reset(token)


def tenant_context(func):
    """Decorator ensuring tenant isolation for tool/API entrypoints."""

    @wraps(func)
    async def wrapper(*args, tenant_id: str, **kwargs):
        if not await verify_tenant_access(tenant_id):
            raise PermissionError("Invalid tenant context")
        async with tenant_scoped_session(tenant_id):
            return await func(*args, tenant_id=tenant_id, **kwargs)

    return wrapper


