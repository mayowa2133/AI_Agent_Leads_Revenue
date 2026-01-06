from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.security import current_tenant_id


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    payload: dict[str, Any]
    tenant_id: str | None = None
    lead_id: str | None = None
    actor_kind: str = "system"  # ai|human|system
    actor_id: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    sources: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "event_type": self.event_type,
            "tenant_id": self.tenant_id,
            "lead_id": self.lead_id,
            "actor": {"kind": self.actor_kind, "id": self.actor_id},
            "model": {"provider": self.model_provider, "name": self.model_name, "version": self.model_version},
            "sources": self.sources or [],
            "payload": self.payload,
        }


def _default_audit_log_path() -> str | None:
    return os.environ.get("AORO_AUDIT_LOG_PATH")


def append_audit_event(event: AuditEvent) -> None:
    """
    Append an audit event to a JSONL log.

    This is intentionally simple for MVP. In production, ship to a durable store with
    retention, encryption-at-rest, and per-tenant access controls.
    """
    path = _default_audit_log_path()
    if not path:
        return

    p = Path(path)
    if not p.is_absolute():
        # Resolve relative to repo root (current working dir of the process).
        p = Path.cwd() / p

    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), ensure_ascii=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def audit(event_type: str, payload: dict[str, Any], *, lead_id: str | None = None) -> None:
    append_audit_event(
        AuditEvent(
            event_type=event_type,
            payload=payload,
            tenant_id=current_tenant_id(),
            lead_id=lead_id,
            actor_kind="system",
        )
    )


