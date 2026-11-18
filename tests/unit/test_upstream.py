import asyncio
import time

import httpx
import pytest
from azure.core.credentials import AccessToken

from backing_service.upstream import DemoUpstream


class Credential:
    async def get_token(self, *scopes, **kwargs):
        assert scopes[0] in (
            "api://551b356f-3265-4a3e-8b87-95704b5f503c/.default",
            "https://search.azure.com/.default",
        )
        return AccessToken("local-unit-fixture", int(time.time()) + 600)


def test_rest_adapter_must_make_a_real_https_request_not_read_the_fixture():
    calls = []

    def respond(request):
        calls.append(str(request.url))
        assert request.headers["authorization"] == "Bearer local-unit-fixture"
        return httpx.Response(
            200,
            json={
                "demo_id": "48254cc6",
                "synthetic": True,
                "data": {"quantity": 18000},
                "sources": [],
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            api = DemoUpstream(Credential(), client, "551b356f-3265-4a3e-8b87-95704b5f503c")
            return await api.stock("MS01", "DIESEL")

    value = asyncio.run(run())
    assert calls == ["https://kppdemo-data-48254cc6.azurewebsites.net/api/stock/MS01/DIESEL"]
    assert value["data"]["quantity"] == 18000
    assert value["upstream_protocol"] == "https_rest"


def test_adapter_rejects_an_existing_system_endpoint_before_requesting_a_token():
    async def run():
        async with httpx.AsyncClient() as client:
            api = DemoUpstream(Credential(), client, "551b356f-3265-4a3e-8b87-95704b5f503c")
            await api.request("GET", "https://existing.example/data", "untrusted/.default")

    with pytest.raises(ValueError, match="new read-only"):
        asyncio.run(run())


def test_search_cannot_return_non_demo_content():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"value": [{"demo_id": "other"}]})
            )
        ) as client:
            api = DemoUpstream(Credential(), client, "551b356f-3265-4a3e-8b87-95704b5f503c")
            await api.search("reporting code")

    with pytest.raises(RuntimeError, match="out-of-scope"):
        asyncio.run(run())
