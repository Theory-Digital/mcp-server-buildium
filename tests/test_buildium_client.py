"""Tests for BuildiumClient lifecycle helpers."""

import pytest

from mcp_server_buildium.buildium_client import BuildiumClient
from mcp_server_buildium.config import BuildiumConfig


class FakeApiClient:
    def __init__(self):
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_sync_context_manager_closes_api_client():
    client = BuildiumClient(BuildiumConfig(client_id="x", client_secret="y"))
    fake_api_client = FakeApiClient()
    client._api_client = fake_api_client

    with client:
        pass

    assert fake_api_client.closed


@pytest.mark.asyncio
async def test_async_context_manager_closes_api_client():
    client = BuildiumClient(BuildiumConfig(client_id="x", client_secret="y"))
    fake_api_client = FakeApiClient()
    client._api_client = fake_api_client

    async with client:
        pass

    assert fake_api_client.closed
