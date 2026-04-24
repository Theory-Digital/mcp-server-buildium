"""Tests that handwritten MCP tools match the generated SDK surface."""

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP

from mcp_server_buildium.buildium_client import BuildiumClient
from mcp_server_buildium.buildium_sdk.models.lease_message import LeaseMessage
from mcp_server_buildium.config import BuildiumConfig
from mcp_server_buildium.tools.leases import register_lease_tools
from mcp_server_buildium.tools.owners import register_owner_tools
from mcp_server_buildium.tools.tenants import register_tenant_tools

TOOLS_DIR = Path(__file__).parents[1] / "src" / "mcp_server_buildium" / "tools"


def _client_sdk_calls() -> list[tuple[Path, int, str, str]]:
    calls: list[tuple[Path, int, str, str]] = []
    for path in TOOLS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Attribute)
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "client"
            ):
                continue
            calls.append((path, node.lineno, func.value.attr, func.attr))
    return calls


def test_registered_tool_sdk_methods_exist():
    client = BuildiumClient(BuildiumConfig(client_id="x", client_secret="y"))

    missing = []
    for path, lineno, api_name, method_name in _client_sdk_calls():
        api = getattr(client, api_name, None)
        if api is None or not hasattr(api, method_name):
            missing.append(f"{path}:{lineno}: client.{api_name}.{method_name}")

    assert missing == []


def test_registered_tool_sdk_keyword_arguments_exist():
    client = BuildiumClient(BuildiumConfig(client_id="x", client_secret="y"))

    bad_kwargs = []
    for path, lineno, api_name, method_name in _client_sdk_calls():
        api = getattr(client, api_name, None)
        if api is None or not hasattr(api, method_name):
            continue

        tree = ast.parse(path.read_text(), filename=str(path))
        matching_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "client"
            and node.func.value.attr == api_name
            and node.func.attr == method_name
            and node.lineno == lineno
        ]
        params = set(inspect.signature(getattr(api, method_name)).parameters)
        for call in matching_calls:
            bad = [kw.arg for kw in call.keywords if kw.arg is not None and kw.arg not in params]
            if bad:
                bad_kwargs.append(
                    f"{path}:{lineno}: client.{api_name}.{method_name} bad kwargs {bad}"
                )

    assert bad_kwargs == []


class CapturingApi:
    def __init__(self, result: list[Any] | None = None):
        self.calls: list[dict[str, Any]] = []
        self.result = result if result is not None else []

    async def external_api_leases_get_leases(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    async def external_api_rental_owners_get_rental_owners(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    async def external_api_rental_tenants_get_all_tenants(self, **kwargs):
        self.calls.append(kwargs)
        return self.result

    async def external_api_association_tenants_get_association_tenants(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeClient:
    def __init__(self):
        self.leases_api = CapturingApi([LeaseMessage(id=1)])
        self.rental_owners_api = CapturingApi()
        self.association_owners_api = CapturingApi()
        self.rental_tenants_api = CapturingApi()
        self.association_tenants_api = CapturingApi()


async def _run_tool(mcp: FastMCP, name: str, arguments: dict[str, Any]) -> Any:
    tools = await mcp.get_tools()
    return await tools[name].fn(**arguments)


@pytest.mark.asyncio
async def test_filtered_list_wrappers_use_generated_sdk_parameter_names():
    client = FakeClient()
    mcp = FastMCP("test")
    register_lease_tools(mcp, client)
    register_owner_tools(mcp, client)
    register_tenant_tools(mcp, client)

    await _run_tool(
        mcp,
        "list_leases",
        {"property_id": 123, "unit_number": "2A", "lease_status": "Active"},
    )
    await _run_tool(mcp, "list_rental_owners", {"property_id": 123})
    await _run_tool(
        mcp,
        "list_rental_tenants",
        {"property_id": 123, "unit_id": 456, "status": "Active"},
    )
    await _run_tool(
        mcp,
        "list_association_tenants",
        {"association_id": 789, "status": "Active"},
    )

    assert client.leases_api.calls[-1] == {
        "limit": 100,
        "offset": 0,
        "propertyids": [123],
        "unitnumber": "2A",
        "leasestatuses": ["Active"],
    }
    assert client.rental_owners_api.calls[-1] == {
        "limit": 100,
        "offset": 0,
        "propertyids": [123],
    }
    assert client.rental_tenants_api.calls[-1] == {
        "limit": 100,
        "offset": 0,
        "propertyids": [123],
        "unitids": [456],
        "leasetermstatuses": ["Active"],
    }
    assert client.association_tenants_api.calls[-1] == {
        "limit": 100,
        "offset": 0,
        "associationids": [789],
        "statuses": ["Active"],
    }
