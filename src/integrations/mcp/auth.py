from __future__ import annotations

import json
import os

from src.core.config import get_settings
from src.integrations.servicetitan.client import ServiceTitanAuth, ServiceTitanClient


def _load_tenant_overrides() -> dict[str, dict]:
    """
    Optional multi-tenant credential mapping.
    Format (env): SERVICETITAN_TENANTS_JSON='{\"tenantA\": {...}, \"tenantB\": {...}}'
    """
    raw = os.environ.get("SERVICETITAN_TENANTS_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_servicetitan_client(tenant_id: str) -> ServiceTitanClient:
    """
    MVP: single credential set loaded from env.
    Prod: map tenant_id -> encrypted credentials.
    """
    s = get_settings()
    overrides = _load_tenant_overrides().get(tenant_id, {})

    client_id = overrides.get("client_id") or s.servicetitan_client_id
    client_secret = overrides.get("client_secret") or s.servicetitan_client_secret
    app_key = overrides.get("app_key") or s.servicetitan_app_key
    base_url = overrides.get("base_url") or s.servicetitan_base_url
    st_tenant_id = overrides.get("servicetitan_tenant_id") or s.servicetitan_tenant_id

    missing = [
        k
        for k, v in {
            "SERVICETITAN_CLIENT_ID": client_id,
            "SERVICETITAN_CLIENT_SECRET": client_secret,
            "SERVICETITAN_APP_KEY": app_key,
            "SERVICETITAN_BASE_URL": base_url,
            "SERVICETITAN_TENANT_ID": st_tenant_id,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(f"Missing ServiceTitan config: {', '.join(missing)}")

    auth = ServiceTitanAuth(
        client_id=client_id or "",
        client_secret=client_secret or "",
        app_key=app_key or "",
        base_url=base_url or "",
        tenant_id=st_tenant_id or "",
    )
    return ServiceTitanClient(auth=auth)


