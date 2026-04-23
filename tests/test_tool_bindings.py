"""Tests that handwritten MCP tools match the generated SDK surface."""

import ast
from pathlib import Path

from mcp_server_buildium.buildium_client import BuildiumClient
from mcp_server_buildium.config import BuildiumConfig

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
