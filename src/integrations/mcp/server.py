from __future__ import annotations

from fastmcp import FastMCP

from src.integrations.mcp.tools.calendar_tools import register as register_calendar
from src.integrations.mcp.tools.crm_tools import register as register_crm
from src.integrations.mcp.tools.pricebook_tools import register as register_pricebook


def create_mcp_server() -> FastMCP:
    mcp = FastMCP("AORO ServiceTitan Bridge")
    register_crm(mcp)
    register_calendar(mcp)
    register_pricebook(mcp)
    return mcp


mcp = create_mcp_server()


if __name__ == "__main__":
    # FastMCP runtime details depend on environment; leaving entrypoint for local runs.
    mcp.run()


