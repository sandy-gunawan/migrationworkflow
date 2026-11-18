import json
import time

import httpx
import pytest
from azure.core.credentials import AccessToken

from demo_common.foundry import DemoFoundry, DemoFoundryError


class Credential:
    def get_token(self, *scopes, **kwargs):
        return AccessToken("local-unit-fixture", int(time.time()) + 600)


def test_v1_responses_does_not_send_the_management_api_version_parameter():
    def respond(request):
        assert request.url.path.endswith("/openai/v1/responses")
        assert "api-version" not in request.url.params
        return httpx.Response(200, json={"status": "completed", "output": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        foundry = DemoFoundry(Credential(), client)
        foundry.invoke("kppdemo-router", "Classify a synthetic question.")


def test_invocation_cannot_target_an_existing_non_demo_agent():
    with httpx.Client() as client:
        foundry = DemoFoundry(Credential(), client)
        with pytest.raises(ValueError, match="newly created"):
            foundry.invoke("production-client-agent", "Do not send this.")


@pytest.mark.parametrize("status", [403, 404])
def test_native_http_errors_retain_status_without_hiding_permission_failures(status):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="demo error"))
    ) as client:
        foundry = DemoFoundry(Credential(), client)
        with pytest.raises(DemoFoundryError) as error:
            foundry.request("GET", "/agents/kppdemo-mining-workflow")
        assert error.value.status_code == status
        assert "demo error" in str(error.value)


def test_native_workflow_creates_a_fresh_conversation_and_omits_prompt_only_parameters():
    paths = []

    def respond(request):
        paths.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path.endswith("/conversations"):
            assert body["metadata"]["demo_id"] == "48254cc6"
            return httpx.Response(200, json={"id": "conv_owned_unit_fixture"})
        assert body["conversation"] == "conv_owned_unit_fixture"
        assert body["agent_reference"]["version"] == "1"
        assert "max_output_tokens" not in body
        return httpx.Response(200, json={"status": "completed", "output": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        foundry = DemoFoundry(Credential(), client)
        foundry.invoke("kppdemo-mining-workflow", "A synthetic question.", "1")
    assert len(paths) == 2
    assert paths[0].endswith("/conversations")
    assert paths[1].endswith("/responses")


def test_native_workflow_rejects_an_invalid_conversation_before_invocation():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": 123}))
    ) as client:
        foundry = DemoFoundry(Credential(), client)
        with pytest.raises(RuntimeError, match="conversation identifier"):
            foundry.invoke("kppdemo-mining-workflow", "A synthetic question.", "1")


def test_native_failure_preserves_evidence_without_dumping_the_entire_response():
    detail = "workflow action failure " + "x" * 3000
    error = DemoFoundryError(400, detail)
    assert error.detail == detail
    assert len(str(error)) < len(detail)


def test_prompt_agents_share_only_the_explicit_per_run_conversation():
    def respond(request):
        body = json.loads(request.content)
        assert body["conversation"] == "conv_owned_run"
        assert body["max_output_tokens"] == 2048
        return httpx.Response(200, json={"status": "completed", "output": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        foundry = DemoFoundry(Credential(), client)
        foundry.invoke("kppdemo-router", "Synthetic question.", "1",
                       conversation_id="conv_owned_run")


def test_run_context_preserves_the_original_user_message_and_activity_order():
    bodies = []

    def respond(request):
        bodies.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"id": "conv_owned_run"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        foundry = DemoFoundry(Credential(), client)
        conversation = foundry.start_conversation("Synthetic question.", "run-unit")
        foundry.append_activity(conversation, "KPP_ROUTE:mcp")
    assert bodies[0][1]["items"][0]["role"] == "user"
    assert bodies[0][1]["items"][0]["content"][0]["text"] == "Synthetic question."
    assert bodies[1][0].endswith("/conversations/conv_owned_run/items")
    assert bodies[1][1]["items"][0]["role"] == "assistant"
    assert bodies[1][1]["items"][0]["content"][0]["text"] == "KPP_ROUTE:mcp"


def test_conversation_paths_cannot_escape_the_owned_context_endpoint():
    with httpx.Client() as client:
        foundry = DemoFoundry(Credential(), client)
        with pytest.raises(ValueError, match="conversation"):
            foundry.append_activity("conv_owned/../../other", "Do not send.")
