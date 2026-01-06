from __future__ import annotations

from datetime import datetime

from fastmcp import FastMCP

from src.core.security import tenant_context
from src.integrations.mcp.auth import get_servicetitan_client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @tenant_context
    async def create_booking(
        customer_id: str,
        job_type: str,
        scheduled_datetime: str,
        notes: str,
        tenant_id: str,
    ) -> dict:
        """Create a new booking in ServiceTitan CRM."""
        client = get_servicetitan_client(tenant_id)
        try:
            dt = datetime.fromisoformat(scheduled_datetime)
            res = await client.create_booking(
                customer_id=customer_id, job_type=job_type, scheduled_datetime=dt, notes=notes
            )
            return {"ok": True, "result": res}
        finally:
            await client.aclose()


