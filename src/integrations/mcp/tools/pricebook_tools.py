from __future__ import annotations

from fastmcp import FastMCP

from src.core.security import tenant_context
from src.integrations.mcp.auth import get_servicetitan_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @tenant_context
    async def get_pricebook_services(category: str, tenant_id: str) -> list[dict]:
        """Retrieve service offerings and pricing."""
        client = get_servicetitan_client(tenant_id)
        try:
            res = await client.get_pricebook_services(category=category)
            return [{"ok": True, "result": res}]
        finally:
            await client.aclose()


