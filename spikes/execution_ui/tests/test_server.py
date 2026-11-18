import asyncio
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from demo_common.contracts import DemoResult, Route
from spikes.execution_ui.server import RunFailure, create_app

ORIGIN = "http://127.0.0.1:8766"
ROOT = Path(__file__).resolve().parents[3]


class FixtureRuntime:
    info = {
        "kind": "fixture",
        "title": "Contract fixture",
        "service": "local-workbench-fixture",
        "identity_mode": "unit_fixture",
        "engine": "Fixture, bukan layanan Azure",
        "run_label": "Jalankan fixture",
        "description": "Contract fixture only.",
        "waiting_note": "No real service is called.",
        "guide_name": "logicapps-ui-walkthrough.html",
        "source_sha256": "fixture-only",
    }
    definition = {
        "path": "fixture.yaml",
        "language": "yaml",
        "sha256": "fixture-only",
        "text": "fixture: true\n",
    }
    sources = {
        "workflow": {
            "key": "workflow",
            "label": "Fixture",
            "path": "fixture.py",
            "symbol": "FixtureRuntime.execute",
            "language": "python",
            "line": 1,
            "end_line": 1,
            "text": "fixture = True\n",
            "lessons": [
                {
                    "id": "request",
                    "title": "Fixture only",
                    "line": 1,
                    "end_line": 1,
                    "explanation": "No Azure request.",
                    "analogy": "Latihan pos kontrol.",
                }
            ],
        }
    }

    def __init__(self):
        self.calls = []
        self.fail = False
        self.entered = None
        self.release = None

    async def execute(self, request, emit):
        self.calls.append(request)
        emit(
            {
                "phase": "workflow",
                "status": "running",
                "step_id": "fixture",
                "code_key": "workflow",
                "label": "Fixture sedang berjalan",
                "detail": "Contract test only; not live retrieval.",
            }
        )
        if self.entered is not None:
            self.entered.set()
            await self.release.wait()
        if self.fail:
            raise RunFailure("Caller tidak diizinkan.", upstream_status=403)
        result = DemoResult(
            run_id=request.run_id,
            route=Route.WORK_IQ,
            status="blocked",
            error="Fixture only: Work IQ remains blocked.",
        )
        return {"result": result.model_dump(mode="json"), "trace": {"fixture": True}}

    async def close(self):
        pass


def headers(client):
    return {
        "Origin": ORIGIN,
        "X-Demo-CSRF": client.get("/ui/context").json()["csrf_token"],
    }


def events(response):
    return [json.loads(line) for line in response.text.splitlines()]


def test_source_explanations_and_blocked_stream_preserve_real_result_shape():
    runtime = FixtureRuntime()
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        context = client.get("/ui/context").json()
        assert context["identity_mode"] == "unit_fixture"
        assert len(context["cases"]) == 50
        assert client.get("/ui/definition").json() == runtime.definition
        assert client.get("/ui/code/workflow").json()["text"] == "fixture = True\n"
        response = client.post(
            "/ui/runs",
            headers=headers(client),
            json={"question": "Fixture question."},
        )
        frames = events(response)
        assert [frame["type"] for frame in frames] == ["started", "progress", "result"]
        result = frames[-1]["output"]["result"]
        assert result["status"] == "blocked" and result["answer"] is None
        assert result["sources"] == [] and result["error"]
        assert result["run_id"] == frames[0]["run_id"]
        assert client.get("/ui/context").json()["busy"] is False
        assert client.get("/ui/code/credentials").status_code == 404
    assert len(runtime.calls) == 1


def test_request_journey_guide_is_available_without_running_a_workflow():
    runtime = FixtureRuntime()
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        response = client.get("/logicapps-alur-request.html")
        assert response.status_code == 200
        assert "<title>Logic Apps dari UI sampai jawaban:" in response.text
        assert "connect-src 'none'" in response.headers["Content-Security-Policy"]
        assert "img-src 'self' data:" in response.headers["Content-Security-Policy"]
        nodes = client.get("/logicapps-node-walkthrough.html")
        assert nodes.status_code == 200
        assert '<dialog id="node-help"' in nodes.text
        assert 'id="authentication-foundry"' in nodes.text
        assert "connect-src 'none'" in nodes.headers["Content-Security-Policy"]
        assert client.get("/logicapps-prasyarat.html").status_code == 404
        capture = client.get("/screenshots/logicapps-designer-20261117/main-workflow.png")
        assert capture.status_code == 200 and capture.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert (
            client.get("/screenshots/logicapps-designer-20261117/captures.json").status_code == 404
        )
        assert (
            client.get("/screenshots/logicapps-designer-20261117/unlisted.png").status_code == 404
        )
        assert client.get("/logicapps-alur-request.src.html").status_code == 404
        assert client.get("/unlisted-guide.html").status_code == 404
    assert runtime.calls == []


def test_code_first_guide_uses_only_whitelisted_local_diagram_assets():
    runtime = FixtureRuntime()
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        guide = client.get("/maf-code-first-walkthrough.html")
        assert guide.status_code == 200 and "portal-gallery-data" not in guide.text
        image = client.get("/diagrams/maf/07-yaml-python-paired.png")
        assert image.status_code == 200 and image.content.startswith(b"\x89PNG\r\n\x1a\n")
        source = client.get("/diagrams/maf/07-yaml-python-paired.drawio")
        assert source.status_code == 200
        assert "attachment" in source.headers["Content-Disposition"]
        assert client.get("/diagrams/maf/unlisted.png").status_code == 404
        assert client.get("/diagrams/maf/generate.py").status_code == 404
    assert runtime.calls == []


def test_declarative_lesson_assets_are_local_and_do_not_run_the_workflow():
    runtime = FixtureRuntime()
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        guide = client.get("/maf-declarative-walkthrough.html")
        assert guide.status_code == 200
        assert "connect-src 'none'" in guide.headers["Content-Security-Policy"]
        for path in (
            "/diagrams/local-ui/declarative-ui-flow.png",
            "/screenshots/local-ui/declarative-mcp.png",
        ):
            image = client.get(path)
            assert image.status_code == 200 and image.content.startswith(b"\x89PNG\r\n\x1a\n")
        source = client.get("/diagrams/local-ui/declarative-ui-flow.drawio")
        assert source.status_code == 200 and "attachment" in source.headers["Content-Disposition"]
        assert client.get("/diagrams/local-ui/unlisted.png").status_code == 404
        assert client.get("/screenshots/local-ui/unlisted.png").status_code == 404
    assert runtime.calls == []


def test_host_origin_csrf_and_route_override_fail_before_upstream_work():
    runtime = FixtureRuntime()
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        body = {"question": "Fixture question."}
        assert client.get("/ui/context", headers={"Host": "outside.example"}).status_code == 403
        assert client.post("/ui/runs", json=body).status_code == 403
        legitimate = headers(client)
        assert (
            client.post(
                "/ui/runs",
                json=body,
                headers={**legitimate, "Origin": "https://outside.example"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/ui/runs",
                json={**body, "route": "mcp"},
                headers=legitimate,
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/ui/runs",
                json={"question": "   "},
                headers=legitimate,
            ).status_code
            == 422
        )
    assert runtime.calls == []


def test_upstream_failure_is_a_terminal_error_not_a_success_fallback():
    runtime = FixtureRuntime()
    runtime.fail = True
    with TestClient(create_app(runtime), base_url=ORIGIN) as client:
        response = client.post(
            "/ui/runs",
            json={"question": "Fixture question."},
            headers=headers(client),
        )
        frames = events(response)
        assert frames[-1]["type"] == "error"
        assert frames[-1]["upstream_status"] == 403
        assert not any(frame["type"] == "result" for frame in frames)
        assert client.get("/ui/context").json()["busy"] is False


def test_concurrent_run_and_shutdown_are_rejected_until_execution_finishes():
    async def exercise():
        runtime = FixtureRuntime()
        runtime.entered, runtime.release = asyncio.Event(), asyncio.Event()
        stopped = []
        app = create_app(runtime, on_shutdown=lambda: stopped.append(True))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN,
        ) as client:
            context = (await client.get("/ui/context")).json()
            valid = {"Origin": ORIGIN, "X-Demo-CSRF": context["csrf_token"]}
            first = asyncio.create_task(
                client.post(
                    "/ui/runs",
                    json={"question": "First fixture."},
                    headers=valid,
                )
            )
            await asyncio.wait_for(runtime.entered.wait(), timeout=3)
            assert (
                await client.post(
                    "/ui/runs",
                    json={"question": "Second fixture."},
                    headers=valid,
                )
            ).status_code == 409
            assert (await client.post("/ui/shutdown", headers=valid)).status_code == 409
            runtime.release.set()
            assert (await first).status_code == 200
            assert (await client.post("/ui/shutdown", headers=valid)).status_code == 200
            assert stopped == [True]
            assert (
                await client.post(
                    "/ui/runs",
                    json={"question": "After stop."},
                    headers=valid,
                )
            ).status_code == 503

    asyncio.run(exercise())


def test_local_ui_refuses_an_accidental_cloud_authentication_bypass(monkeypatch):
    monkeypatch.setenv("WEBSITE_HOSTNAME", "fixture.azurewebsites.net")
    try:
        create_app(FixtureRuntime())
    except ValueError as error:
        assert "local" in str(error).lower()
    else:
        raise AssertionError("A local-only UI must refuse cloud hosting.")
