import asyncio
import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from azure.core.credentials import AccessToken

from demo_common.contracts import DemoRequest
from spikes.execution_ui.server import RunFailure
from spikes.logicapps_ui.client import NativeLogicRuntime

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = UUID("00000000-0000-4000-8000-000000000001")
SECRET = "fixture-token-never-send-to-browser"


class FixtureCredential:
    def get_token(self, *scopes):
        return AccessToken(SECRET, 9999999999)

    def close(self):
        pass


def test_native_gateway_uses_the_trigger_and_observed_run_history_not_maf_orchestration():
    async def exercise():
        manifest = json.loads((ROOT / "config" / "logicapps-manifest.json").read_text())
        definition = json.loads((ROOT / "targets" / "logicapps" / "workflow.json").read_text())
        definition["parameters"] = {}
        posted = []
        seen = []
        cloud_run = "085fixtureui"
        result = {
            "run_id": str(RUN_ID),
            "route": "work_iq",
            "status": "blocked",
            "answer": None,
            "sources": [],
            "error": "A separate Work IQ sandbox is missing.",
        }

        async def handle(request):
            seen.append(str(request.url))
            if request.url.host.endswith(".logic.azure.com"):
                posted.append(json.loads(request.content))
                assert request.headers["x-ms-client-tracking-id"] == str(RUN_ID)
                await asyncio.sleep(0.01)
                return httpx.Response(
                    200,
                    json=result,
                    headers={
                        "x-kpp-orchestrator": "logic_apps",
                        "x-kpp-logic-run": cloud_run,
                        "x-kpp-source-sha256": (
                            "8a1b3b54903f26864bf81fad662e847cc97df18a945f536db9ff78b90aa4a8e1"
                        ),
                        "x-kpp-native-responses": "resp_fixture_router",
                    },
                )
            if request.url.path.endswith("/actions"):
                return httpx.Response(
                    200,
                    json={
                        "value": [
                            {"name": name, "properties": {"status": "Succeeded"}}
                            for name in (
                                "classify_question",
                                "route_question",
                                "blocked_work_iq",
                                "set_result_work_iq",
                                "kpp_mining_end",
                            )
                        ]
                    },
                )
            if request.url.path.endswith("/runs"):
                return httpx.Response(
                    200,
                    json={
                        "value": [
                            {
                                "name": cloud_run,
                                "properties": {
                                    "correlation": {
                                        "clientTrackingId": str(RUN_ID),
                                    }
                                },
                            }
                        ]
                    },
                )
            return httpx.Response(
                200,
                json={
                    "tags": {"demo_id": "48254cc6"},
                    "identity": {"principalId": manifest["principal_id"]},
                    "properties": {
                        "state": "Enabled",
                        "definition": definition,
                        "accessControl": {
                            "triggers": {"sasAuthenticationPolicy": {"state": "Disabled"}}
                        },
                    },
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        runtime = NativeLogicRuntime(
            credential=FixtureCredential(),
            client=client,
            poll_interval=0.001,
        )
        observations = []
        try:
            output = await runtime.execute(
                DemoRequest(question="Fixture Work IQ request.", run_id=RUN_ID),
                observations.append,
            )
        finally:
            await runtime.close()
        assert posted == [{"question": "Fixture Work IQ request.", "run_id": str(RUN_ID)}]
        assert output["result"] == result
        assert output["trace"]["native_run_id"] == cloud_run
        assert any(item["step_id"] == "classify_question" for item in observations)
        assert all("/api/run" not in url for url in seen)
        assert SECRET not in json.dumps({"output": output, "events": observations})
        assert not any(item.get("agent_name") == "kppdemo-mcp" for item in observations)

    asyncio.run(exercise())


def test_unauthorized_callback_is_reported_without_a_fabricated_result():
    async def exercise():
        async def handle(request):
            if request.url.host.endswith(".logic.azure.com"):
                return httpx.Response(403, json={"error": {"code": "MisMatchingOAuthClaims"}})
            if request.url.path.endswith("/runs"):
                return httpx.Response(200, json={"value": []})
            manifest = json.loads((ROOT / "config" / "logicapps-manifest.json").read_text())
            definition = json.loads((ROOT / "targets" / "logicapps" / "workflow.json").read_text())
            return httpx.Response(
                200,
                json={
                    "tags": {"demo_id": "48254cc6"},
                    "identity": {"principalId": manifest["principal_id"]},
                    "properties": {
                        "state": "Enabled",
                        "definition": definition,
                        "accessControl": {
                            "triggers": {"sasAuthenticationPolicy": {"state": "Disabled"}}
                        },
                    },
                },
            )

        runtime = NativeLogicRuntime(
            credential=FixtureCredential(),
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
            poll_interval=0.001,
        )
        try:
            with pytest.raises(RunFailure, match="403") as error:
                await runtime.execute(DemoRequest(question="Fixture request."), lambda value: None)
            assert error.value.upstream_status == 403
        finally:
            await runtime.close()

    asyncio.run(exercise())


def test_content_links_cannot_escape_the_owned_workflow_or_leak_tokens():
    runtime = NativeLogicRuntime(
        credential=FixtureCredential(),
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(500))
        ),
    )
    try:
        with pytest.raises(ValueError, match="owned"):
            runtime.content_url(
                "https://outside.example/steal?sig=fixture", "fixture", "invoke_mcp"
            )
        with pytest.raises(ValueError, match="owned"):
            runtime.content_url(
                "https://prod-42.southeastasia.logic.azure.com/workflows/other/runs/"
                "fixture/actions/invoke_mcp/contents/ActionOutputs?sig=fixture",
                "fixture",
                "invoke_mcp",
            )
    finally:
        asyncio.run(runtime.close())


def test_added_nonempty_cloud_parameters_are_not_ignored_by_the_source_guard():
    async def exercise():
        manifest = json.loads((ROOT / "config" / "logicapps-manifest.json").read_text())
        definition = json.loads((ROOT / "targets" / "logicapps" / "workflow.json").read_text())
        definition["parameters"] = {"unapproved": {"type": "String", "defaultValue": "changed"}}

        def handle(request):
            return httpx.Response(
                200,
                json={
                    "tags": {"demo_id": "48254cc6"},
                    "identity": {"principalId": manifest["principal_id"]},
                    "properties": {
                        "state": "Enabled",
                        "definition": definition,
                        "accessControl": {
                            "triggers": {"sasAuthenticationPolicy": {"state": "Disabled"}}
                        },
                    },
                },
            )

        runtime = NativeLogicRuntime(
            credential=FixtureCredential(),
            client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        )
        try:
            with pytest.raises(RunFailure, match="berubah"):
                await runtime.verify_workflow()
        finally:
            await runtime.close()

    asyncio.run(exercise())
