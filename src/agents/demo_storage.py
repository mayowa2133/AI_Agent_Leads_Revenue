from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def _storage_path() -> Path:
    path = Path("data/demo_runs.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_all() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {}
    try:
        content = path.read_text()
        if not content.strip():
            return {}
        data = json.loads(content)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_all(data: dict[str, Any]) -> None:
    path = _storage_path()
    path.write_text(json.dumps(data, indent=2))


def create_run(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = payload.get("run_id") or str(uuid.uuid4())
    now = datetime.now().isoformat()
    record = {
        "run_id": run_id,
        "created_at": now,
        "updated_at": now,
        **payload,
    }
    data = _load_all()
    data[run_id] = record
    _save_all(data)
    return record


def get_run(run_id: str) -> dict[str, Any] | None:
    return _load_all().get(run_id)


def update_run(run_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    data = _load_all()
    record = data.get(run_id)
    if not record:
        return None
    record.update(updates)
    record["updated_at"] = datetime.now().isoformat()
    data[run_id] = record
    _save_all(data)
    return record
