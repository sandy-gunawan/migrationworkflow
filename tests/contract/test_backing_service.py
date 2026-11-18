from fastapi.testclient import TestClient

from backing_service.app import create_app
from demo_common.auth import AuthSettings

TENANT = "020201e2-0ae9-446c-8981-55a2bdecc00d"
AUDIENCE = "551b356f-3265-4a3e-8b87-95704b5f503c"
CALLER = "50d57e04-3ed5-4123-bf9f-e3a8739009c9"
TRIAL_KEY = "local-contract-test-key-not-a-cloud-secret"


def settings() -> AuthSettings:
    return AuthSettings(TENANT, AUDIENCE, frozenset({CALLER}), "key_trial", TRIAL_KEY)


def test_api_is_protected_and_returns_only_seeded_records():
    with TestClient(create_app(settings()), base_url="http://localhost") as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/stock/MS01/DIESEL").status_code == 401
        headers = {"x-api-key": TRIAL_KEY}
        stock = client.get("/api/stock/MS01/DIESEL", headers=headers)
        assert stock.status_code == 200
        assert stock.json()["synthetic"] is True
        assert stock.json()["data"]["quantity"] == 18000
        assert client.get("/api/equipment/REAL-SYSTEM-ID", headers=headers).status_code == 404


def test_mcp_discovery_and_tool_call_are_authenticated():
    headers = {"x-api-key": TRIAL_KEY, "accept": "application/json, text/event-stream"}
    with TestClient(create_app(settings()), base_url="http://localhost") as client:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        assert client.post("/mcp", json=payload).status_code == 401
        discovery = client.post("/mcp", json=payload, headers=headers)
        assert discovery.status_code == 200
        names = {tool["name"] for tool in discovery.json()["result"]["tools"]}
        assert names == {
            "get_equipment",
            "get_work_orders",
            "read_synthetic_stock_api",
            "search_synthetic_documents",
            "retrieve_native_demo_knowledge",
        }
        called = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_equipment", "arguments": {"equipment_id": "TRK001"}},
            },
            headers=headers,
        )
        assert called.status_code == 200
        assert called.json()["result"]["isError"] is False
        assert "TRK001" in called.text
        assert "MS01" in called.text
        assert (
            client.post(
                "/mcp", json=payload, headers={**headers, "host": "unrelated.example"}
            ).status_code
            == 421
        )
