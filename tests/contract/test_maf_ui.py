import json

import httpx
import pytest
from fastapi.testclient import TestClient

from demo_common.foundry import DemoFoundryError
from maf_service.demo_ui import CODE, code_reference, create_ui_app, source_lessons
from tools import run_maf_ui

ORIGIN = "http://127.0.0.1:8765"


class UiAgents:
    def start_conversation(self, question, run_id):
        return "conv_ui_fixture"

    def append_activity(self, conversation_id, text):
        assert "KPP_STATUS:blocked" in text

    def invoke(self, name, question, version=None, *, conversation_id=None):
        assert name == "kppdemo-router"
        return {
            "id": "resp_ui_fixture", "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"route":"work_iq"}'},
            ]}],
        }


def test_local_ui_streams_real_graph_progress_and_blocked_result():
    with TestClient(create_ui_app(agents=UiAgents()), base_url=ORIGIN) as client:
        context = client.get("/ui/context").json()
        assert context["identity_mode"] == "unit_fixture"
        assert len(context["presets"]) == 9
        response = client.post(
            "/ui/runs", json={"question": "Use Work IQ for the demo workplace handover."},
            headers={"Origin": ORIGIN, "X-Demo-CSRF": context["csrf_token"]},
        )
        assert response.status_code == 200
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[0]["type"] == "started"
        assert any(
            item["type"] == "progress" and item["update"]["phase"] == "router"
            for item in events
        )
        assert events[-1]["type"] == "result"
        assert events[-1]["output"]["result"]["status"] == "blocked"
        assert events[-1]["output"]["trace"]["agent_calls"][0]["name"] == "kppdemo-router"


def test_ui_rejects_remote_hosts_origins_missing_csrf_and_route_overrides():
    with TestClient(create_ui_app(agents=UiAgents()), base_url=ORIGIN) as client:
        assert client.get("/ui/context", headers={"Host": "other.example"}).status_code == 403
        token = client.get("/ui/context").json()["csrf_token"]
        body = {"question": "Use Work IQ for the demo workplace handover."}
        assert client.post("/ui/runs", json=body, headers={"Origin": ORIGIN}).status_code == 403
        assert client.post(
            "/ui/runs", json=body,
            headers={"Origin": "https://other.example", "X-Demo-CSRF": token},
        ).status_code == 403
        assert client.post(
            "/ui/runs", json={**body, "route": "mcp"},
            headers={"Origin": ORIGIN, "X-Demo-CSRF": token},
        ).status_code == 422


def test_code_inspector_only_reads_whitelisted_actual_source():
    with TestClient(create_ui_app(agents=UiAgents()), base_url=ORIGIN) as client:
        code = client.get("/ui/code/router")
        assert code.status_code == 200
        value = code.json()
        assert value["path"] == "src/maf_service/workflow.py"
        assert value["line"] > 0
        assert "async def route(" in value["text"]
        assert "self.agents.invoke" in value["text"]
        assert client.get("/ui/code/not-a-symbol").status_code == 404


def test_local_ui_cannot_be_started_as_a_cloud_authentication_bypass(monkeypatch):
    monkeypatch.setenv("WEBSITE_HOSTNAME", "kppdemo-maf-48254cc6.azurewebsites.net")
    with pytest.raises(ValueError, match="local"):
        create_ui_app(agents=UiAgents())


def test_dependency_failure_is_a_terminal_error_not_a_success_shaped_ui_result():
    class FailingAgents(UiAgents):
        def invoke(self, *args, **kwargs):
            raise DemoFoundryError(503, "Synthetic dependency unavailable.")

    with TestClient(create_ui_app(agents=FailingAgents()), base_url=ORIGIN) as client:
        token = client.get("/ui/context").json()["csrf_token"]
        response = client.post(
            "/ui/runs", json={"question": "Use Work IQ for the demo workplace handover."},
            headers={"Origin": ORIGIN, "X-Demo-CSRF": token},
        )
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["type"] == "error"
        assert not any(item["type"] == "result" for item in events)
        assert client.get("/ui/context").json()["busy"] is False


@pytest.mark.parametrize("key", CODE)
def test_beginner_highlights_cover_exact_current_source_statements(key):
    value = code_reference(key, include_text=True)
    assert value["lessons"]
    for lesson in value["lessons"]:
        assert value["line"] <= lesson["line"] <= lesson["end_line"] <= value["end_line"]
        assert lesson["explanation"] and lesson["analogy"]
    if key == "specialist":
        lesson = next(item for item in value["lessons"] if item["id"] == "agent_call")
        lines = value["text"].splitlines()
        snippet = "\n".join(
            lines[lesson["line"] - value["line"]:lesson["end_line"] - value["line"] + 1]
        )
        assert "self.agents.invoke" in snippet
        assert "state.request.question" in snippet
        assert "normalize_specialist_result" not in snippet


def test_highlight_numbers_move_with_source_and_missing_anchor_is_an_error():
    value = code_reference("specialist", include_text=True)
    moved = source_lessons("specialist", "\n\n" + value["text"], value["line"])
    for old, new in zip(value["lessons"], moved, strict=True):
        assert new["line"] == old["line"] + 2
        assert new["end_line"] == old["end_line"] + 2
    changed = value["text"].replace(
        "response = await asyncio.to_thread(", "other = await asyncio.to_thread("
    )
    with pytest.raises(RuntimeError, match="anchor"):
        source_lessons("specialist", changed, value["line"])


def test_shutdown_requires_browser_guard_and_blocks_new_runs_after_acknowledgement():
    calls = []
    app = create_ui_app(agents=UiAgents(), on_shutdown=lambda: calls.append("shutdown"))
    with TestClient(app, base_url=ORIGIN) as client:
        token = client.get("/ui/context").json()["csrf_token"]
        assert client.post("/ui/shutdown").status_code == 403
        assert calls == []
        headers = {"Origin": ORIGIN, "X-Demo-CSRF": token}
        response = client.post("/ui/shutdown", headers=headers)
        assert response.json() == {"status": "stopping", "scope": "local_ui_only"}
        assert calls == ["shutdown"]
        assert client.get("/ui/context").json()["stopping"] is True
        assert client.post(
            "/ui/runs", json={"question": "Show work orders for equipment TRK001."},
            headers=headers,
        ).status_code == 503


def test_shutdown_does_not_interrupt_an_active_native_run():
    calls = []
    app = create_ui_app(agents=UiAgents(), on_shutdown=lambda: calls.append("shutdown"))
    with TestClient(app, base_url=ORIGIN) as client:
        token = client.get("/ui/context").json()["csrf_token"]
        client.portal.call(app.state.run_lock.acquire)
        try:
            response = client.post(
                "/ui/shutdown", headers={"Origin": ORIGIN, "X-Demo-CSRF": token},
            )
            assert response.status_code == 409
            assert calls == []
            assert client.get("/ui/context").json()["stopping"] is False
        finally:
            client.portal.call(app.state.run_lock.release)


def test_shutdown_cli_checks_owned_service_and_authenticated_acknowledgement(monkeypatch, capsys):
    stopping = False

    def handle(request):
        nonlocal stopping
        if request.url.path == "/ui/context":
            return httpx.Response(200, json={"csrf_token": "local-fixture"})
        if request.url.path == "/ui/shutdown":
            assert request.headers["origin"] == ORIGIN
            assert request.headers["x-demo-csrf"] == "local-fixture"
            stopping = True
            return httpx.Response(200, json={"status": "stopping", "scope": "local_ui_only"})
        if stopping:
            raise AssertionError("Shutdown acknowledgement must not reopen a closing connection.")
        return httpx.Response(200, json={"service": "local-maf-ui"})

    client = httpx.Client(base_url=ORIGIN, transport=httpx.MockTransport(handle))
    monkeypatch.setattr(run_maf_ui.httpx, "Client", lambda **kwargs: client)
    run_maf_ui.stop_ui(8765)
    assert stopping
    assert "Shutdown MAF UI" in capsys.readouterr().out
