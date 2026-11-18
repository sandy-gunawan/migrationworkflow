import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from demo_common.auth import Authorizer, AuthSettings
from demo_common.migration import compile_source
from maf_service.app import create_app
from maf_service.workflow import MiningWorkflow

ROOT = Path(__file__).resolve().parents[2]
TENANT = "020201e2-0ae9-446c-8981-55a2bdecc00d"
AUDIENCE = "551b356f-3265-4a3e-8b87-95704b5f503c"
CALLER = "50d57e04-3ed5-4123-bf9f-e3a8739009c9"
KEY = "local-maf-contract-key-not-a-cloud-secret"
LOGIC_CALLER = "00000000-0000-0000-0000-000000000017"


class RouterFixture:
    def __init__(self):
        self.calls = 0

    def start_conversation(self, question, run_id):
        return "conv_contract_fixture"

    def append_activity(self, conversation_id, text):
        assert text.startswith("KPP_ROUTE:clarification")

    def invoke(self, name, question, version=None, *, conversation_id=None):
        self.calls += 1
        assert name == "kppdemo-router"
        return {
            "id": "resp_contract_router",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps({"route": "clarification"})}
                    ],
                }
            ],
        }


def app(monkeypatch, *, callers=frozenset({CALLER})):
    monkeypatch.setenv("DEMO_BACKING_URL", "https://kppdemo-data-48254cc6.azurewebsites.net")
    endpoint = "https://kppfoundry48254cc6.services.ai.azure.com/api/projects/kpp-mining-demo"
    monkeypatch.setenv("DEMO_FOUNDRY_ENDPOINT", endpoint)
    monkeypatch.setenv("DEMO_API_RESOURCE", f"api://{AUDIENCE}")
    agents = RouterFixture()
    mapping = compile_source(
        (ROOT / "source" / "foundry" / "workflow.yaml").read_text(encoding="utf-8")
    )
    workflow = MiningWorkflow(mapping, agents, identity_mode="unit_fixture")
    settings = AuthSettings(TENANT, AUDIENCE, frozenset(callers), "key_trial", KEY)
    return create_app(settings, workflow=workflow), agents, mapping


def test_authenticated_local_api_runs_the_real_framework_and_preserves_correlation(monkeypatch):
    application, agents, mapping = app(monkeypatch)
    with TestClient(application) as client:
        assert client.get("/health").json()["workflow_configured"] is True
        assert client.post("/api/run", json={"question": "Tell me about MS01."}).status_code == 401
        assert agents.calls == 0
        run_id = str(uuid4())
        response = client.post(
            "/api/run",
            json={"question": "Tell me about MS01.", "run_id": run_id},
            headers={"x-api-key": KEY},
        )
        assert response.status_code == 200
        assert response.json()["run_id"] == run_id
        assert response.json()["status"] == "clarification"
        assert response.headers["x-kpp-framework"] == "1.11.0"
        assert response.headers["x-kpp-source-sha256"] == mapping.source_sha256
        assert agents.calls == 1


def normalizer_app(monkeypatch, caller=LOGIC_CALLER):
    monkeypatch.setenv("DEMO_NORMALIZER_CALLER_ID", LOGIC_CALLER)
    monkeypatch.setattr(Authorizer, "authorize", lambda self, headers: caller)
    return app(monkeypatch, callers={CALLER, LOGIC_CALLER})


def native_mcp_result():
    binding = {"type": "agent_reference", "name": "kppdemo-mcp", "version": "1"}
    return {
        "status": "completed",
        "output": [
            {
                "type": "mcp_call",
                "status": "completed",
                "agent_reference": binding,
                "output": json.dumps({
                    "demo_id": "48254cc6", "synthetic": True,
                    "data": [{"order_id": "WO001", "equipment_id": "TRK001"}],
                    "sources": [{"kind": "demo_fixture", "id": "urn:kppdemo:maintenance/TRK001"}],
                }),
            },
            {
                "type": "message",
                "agent_reference": binding,
                "content": [{"type": "output_text", "text": "WO001 belongs to TRK001."}],
            },
        ],
    }


def test_logic_identity_can_only_normalize_existing_evidence_without_orchestrating(monkeypatch):
    application, agents, _ = normalizer_app(monkeypatch)
    run_id = str(uuid4())
    with TestClient(application) as client:
        response = client.post(
            "/api/normalize-result",
            json={"route": "mcp", "run_id": run_id, "response": native_mcp_result()},
        )
        assert response.status_code == 200
        assert response.json()["run_id"] == run_id
        assert response.json()["status"] == "success"
        assert response.json()["sources"][0]["id"] == "urn:kppdemo:maintenance/TRK001"
        assert response.headers["x-kpp-provider-calls"] == "0"
        assert client.post("/api/run", json={"question": "MS01"}).status_code == 403
        assert client.post("/api/verify-foundry").status_code == 403
        assert client.post("/api/verify-backend").status_code == 403
        assert agents.calls == 0


def test_other_authenticated_callers_cannot_use_the_logic_normalizer(monkeypatch):
    application, agents, _ = normalizer_app(monkeypatch, CALLER)
    with TestClient(application) as client:
        response = client.post(
            "/api/normalize-result",
            json={"route": "mcp", "run_id": str(uuid4()), "response": native_mcp_result()},
        )
        assert response.status_code == 403
        assert agents.calls == 0


def test_malformed_native_evidence_is_rejected_without_dispatch_or_fake_grounding(monkeypatch):
    application, agents, _ = normalizer_app(monkeypatch)
    with TestClient(application) as client:
        response = client.post(
            "/api/normalize-result",
            json={
                "route": "mcp", "run_id": str(uuid4()),
                "response": {"status": "completed", "output": [{"unexpected": "shape"}]},
            },
        )
        assert response.status_code == 422
        ungrounded = native_mcp_result()
        ungrounded["output"] = ungrounded["output"][1:]
        response = client.post(
            "/api/normalize-result",
            json={"route": "mcp", "run_id": str(uuid4()), "response": ungrounded},
        )
        assert response.status_code == 502
        assert response.json()["status"] == "failed"
        assert response.json()["answer"] is None
        assert agents.calls == 0


def test_invalid_request_and_key_cannot_override_routing_or_call_a_provider(monkeypatch):
    application, agents, _ = app(monkeypatch)
    with TestClient(application) as client:
        request = {"question": "Tell me about MS01.", "route": "work_iq"}
        assert client.post("/api/run", json=request, headers={"x-api-key": KEY}).status_code == 422
        assert (
            client.post("/api/run", json={"question": ""}, headers={"x-api-key": KEY}).status_code
            == 422
        )
        assert (
            client.post(
                "/api/run", json={"question": "MS01"}, headers={"x-api-key": "invalid"}
            ).status_code
            == 401
        )
        assert agents.calls == 0
