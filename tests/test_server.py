"""Tests for MCP server construction."""

import importlib

import pytest

from mcp_server_buildium.config import BuildiumConfig


def test_server_import_does_not_require_buildium_credentials(monkeypatch):
    monkeypatch.delenv("BUILDIUM_CLIENT_ID", raising=False)
    monkeypatch.delenv("BUILDIUM_CLIENT_SECRET", raising=False)

    import mcp_server_buildium.server as server

    importlib.reload(server)


@pytest.mark.asyncio
async def test_create_server_registers_enabled_categories():
    from mcp_server_buildium.server import create_server

    config = BuildiumConfig(client_id="x", client_secret="y", categories="rentals")
    mcp = create_server(config)

    tools = await mcp.get_tools()

    assert "list_rentals" in tools
    assert "list_vendors" not in tools
