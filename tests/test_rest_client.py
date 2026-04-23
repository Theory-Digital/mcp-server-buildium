"""Tests for the generated SDK REST client wrapper."""

import httpx
import pytest

from mcp_server_buildium.buildium_sdk.configuration import Configuration
from mcp_server_buildium.buildium_sdk.rest import RESTClientObject


class FakeResponse:
    status_code = 200
    reason_phrase = "OK"
    headers = {"content-type": "application/json"}

    async def aread(self) -> bytes:
        return b"{}"


class FakePool:
    def __init__(self, *, is_closed: bool = False, error: Exception | None = None):
        self.is_closed = is_closed
        self.error = error
        self.close_count = 0
        self.request_count = 0

    async def aclose(self) -> None:
        self.close_count += 1
        self.is_closed = True

    async def request(self, **_kwargs) -> FakeResponse:
        self.request_count += 1
        if self.error:
            raise self.error
        return FakeResponse()


@pytest.fixture
def rest_client() -> RESTClientObject:
    return RESTClientObject(Configuration(host="http://example.test"))


@pytest.mark.asyncio
async def test_close_resets_pool_manager(rest_client: RESTClientObject):
    pool = FakePool()
    rest_client.pool_manager = pool

    await rest_client.close()

    assert pool.close_count == 1
    assert rest_client.pool_manager is None


@pytest.mark.asyncio
async def test_request_recreates_closed_pool(rest_client: RESTClientObject, monkeypatch):
    closed_pool = FakePool(is_closed=True)
    fresh_pool = FakePool()
    rest_client.pool_manager = closed_pool
    monkeypatch.setattr(rest_client, "_create_pool_manager", lambda: fresh_pool)

    await rest_client.request("GET", "http://example.test/v1/rentals")

    assert closed_pool.request_count == 0
    assert fresh_pool.request_count == 1
    assert rest_client.pool_manager is fresh_pool


@pytest.mark.asyncio
async def test_request_retries_once_after_transport_error(
    rest_client: RESTClientObject, monkeypatch
):
    failing_pool = FakePool(error=httpx.RemoteProtocolError("stale connection"))
    fresh_pool = FakePool()
    rest_client.pool_manager = failing_pool
    monkeypatch.setattr(rest_client, "_create_pool_manager", lambda: fresh_pool)

    await rest_client.request("GET", "http://example.test/v1/rentals")

    assert failing_pool.request_count == 1
    assert failing_pool.close_count == 1
    assert fresh_pool.request_count == 1
    assert rest_client.pool_manager is fresh_pool


@pytest.mark.asyncio
async def test_request_does_not_retry_non_idempotent_transport_error(
    rest_client: RESTClientObject, monkeypatch
):
    error = httpx.RemoteProtocolError("stale connection")
    failing_pool = FakePool(error=error)
    fresh_pool = FakePool()
    rest_client.pool_manager = failing_pool
    monkeypatch.setattr(rest_client, "_create_pool_manager", lambda: fresh_pool)

    with pytest.raises(httpx.RemoteProtocolError):
        await rest_client.request("POST", "http://example.test/v1/rentals", body={})

    assert failing_pool.request_count == 1
    assert failing_pool.close_count == 1
    assert fresh_pool.request_count == 0
    assert rest_client.pool_manager is None
