from __future__ import annotations

from datetime import datetime

from fastmcp import FastMCP

from src.core.security import tenant_context
from src.integrations.mcp.auth import get_servicetitan_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @tenant_context
    async def check_availability(
        technician_id: str,
        start_datetime: str,
        end_datetime: str,
        tenant_id: str,
    ) -> list[dict]:
        """Check technician availability slots."""
        client = get_servicetitan_client(tenant_id)
        try:
            start = datetime.fromisoformat(start_datetime)
            end = datetime.fromisoformat(end_datetime)
            res = await client.check_availability(technician_id=technician_id, start=start, end=end)
            return [{"ok": True, "result": res}]
        finally:
            await client.aclose()


