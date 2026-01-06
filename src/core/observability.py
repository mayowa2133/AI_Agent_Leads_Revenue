from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI

from src.core.config import get_settings
from src.core.security import current_tenant_id
from src.core.audit_log import audit as append_audit


def get_openai_client() -> AsyncOpenAI:
    """
    Central place to construct the OpenAI client.
    LangSmith wrapping is applied only when tracing is enabled.
    """
    settings = get_settings()
    client: Any = AsyncOpenAI(api_key=settings.openai_api_key)

    if settings.langsmith_tracing:
        try:
            from langsmith.wrappers import wrap_openai

            client = wrap_openai(client)
        except Exception:
            # Tracing is optional; if wrapper import fails, return raw client.
            pass

    return client


def traceable_fn(name: str):
    """
    Thin wrapper to avoid hard-depending on LangSmith decorators at import time.
    """
    try:
        from langsmith import traceable

        return traceable(name=name)
    except Exception:

        def passthrough_decorator(fn):
            return fn

        return passthrough_decorator


def init_observability() -> None:
    """
    Configure LangSmith/LangChain tracing env vars from Settings.
    Safe to call multiple times.
    """
    s = get_settings()
    if s.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", s.langsmith_api_key)
    os.environ.setdefault("LANGSMITH_PROJECT", s.langsmith_project)

    if s.langsmith_tracing:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


def audit_event(event_type: str, payload: dict[str, Any]) -> None:
    """
    Minimal audit trail hook. In production, ship to LangSmith/DB/log sink.
    """
    evt = {"type": event_type, "tenant_id": current_tenant_id(), **payload}
    print(evt)
    # Optional JSONL audit log (set AORO_AUDIT_LOG_PATH to enable)
    try:
        append_audit(event_type, payload, lead_id=payload.get("lead_id"))
    except Exception:
        pass


