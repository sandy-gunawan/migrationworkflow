import json
import re

import httpx
from azure.core.credentials import TokenCredential

from demo_common.environment import ENVIRONMENT

ENDPOINT = ENVIRONMENT.foundry_endpoint
PROJECT_ID = ENVIRONMENT.foundry_project_id
ALLOWED_AGENTS = {
    "kppdemo-router",
    "kppdemo-fabric-data",
    "kppdemo-mcp",
    "kppdemo-rest",
    "kppdemo-knowledge",
    "kppdemo-foundry-iq",
    "kppdemo-mining-workflow",
}


def _conversation_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 256
        or not re.fullmatch(r"conv_[A-Za-z0-9_-]+", value)
    ):
        raise ValueError("Invalid owned conversation identifier.")
    return value


class DemoFoundryError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Demo Foundry HTTP {status_code}: {detail[:2000]}")


class DemoFoundry:
    def __init__(self, credential: TokenCredential, client: httpx.Client):
        self.credential = credential
        self.client = client

    def request(self, method: str, path: str, body: object = None) -> dict:
        if method not in ("GET", "POST"):
            raise ValueError("Only read/create operations on demo agents are supported.")
        if any(value in path for value in ("..", "?", "#", "\\", "%")):
            raise ValueError("Unsafe demo project path.")
        if path.startswith("/agents/"):
            name = path.split("/")[2]
            if name not in ALLOWED_AGENTS:
                raise ValueError("Refusing access to an existing or non-demo agent.")
        elif path not in ("/openai/v1/responses", "/openai/v1/conversations") and not re.fullmatch(
            r"/openai/v1/conversations/conv_[A-Za-z0-9_-]+/items", path
        ):
            raise ValueError("Unsupported demo project operation.")
        token = self.credential.get_token("https://ai.azure.com/.default")
        response = self.client.request(
            method,
            f"{ENDPOINT}{path}",
            params={"api-version": "v1"} if path.startswith("/agents/") else None,
            headers={
                "Authorization": f"Bearer {token.token}",
                "Foundry-Features": "WorkflowAgents=V1Preview",
            },
            json=body,
        )
        if response.is_error:
            raise DemoFoundryError(response.status_code, response.text)
        return response.json()

    def start_conversation(self, question: str, run_id: str) -> str:
        response = self.request(
            "POST",
            "/openai/v1/conversations",
            {
                "metadata": {
                    "demo_id": "48254cc6",
                    "run_id": run_id,
                    "orchestrator": "agent_framework",
                },
                "items": [{
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": question}],
                }],
            },
        )
        return _conversation_id(response.get("id"))

    def append_activity(self, conversation_id: str, text: str) -> None:
        conversation_id = _conversation_id(conversation_id)
        if not text:
            raise ValueError("A native conversation activity must have text.")
        self.request(
            "POST",
            f"/openai/v1/conversations/{conversation_id}/items",
            {"items": [{
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }]},
        )

    def invoke(
        self,
        name: str,
        question: str,
        version: str | None = None,
        *,
        conversation_id: str | None = None,
    ) -> dict:
        if name not in ALLOWED_AGENTS:
            raise ValueError("Only newly created demo agents may be invoked.")
        reference = {"type": "agent_reference", "name": name}
        if version is not None:
            reference["version"] = version
        body: dict[str, object] = {
            "input": question,
            "stream": False,
            "agent_reference": reference,
        }
        if name == "kppdemo-mining-workflow":
            if conversation_id is not None:
                raise ValueError("Native source invocations require a fresh conversation.")
            conversation = self.request(
                "POST",
                "/openai/v1/conversations",
                {"metadata": {"demo_id": "48254cc6", "purpose": "native-source-validation"}},
            )
            if not isinstance(conversation.get("id"), str) or not conversation["id"]:
                raise RuntimeError("Native workflow conversation identifier was not returned.")
            body["conversation"] = conversation["id"]
        else:
            body["max_output_tokens"] = 2048
            if conversation_id is not None:
                body["conversation"] = _conversation_id(conversation_id)
        return self.request(
            "POST",
            "/openai/v1/responses",
            body,
        )


def response_text(response: dict) -> str:
    if response.get("status") != "completed":
        raise RuntimeError(
            f"Demo agent did not complete: {response.get('status')}; {response.get('error')}"
        )
    text = "\n".join(
        part["text"]
        for item in response["output"]
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )
    if not text:
        raise RuntimeError("Demo agent returned no output text.")
    return text


def structured_response(response: dict) -> dict:
    text = response_text(response)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Demo agent output is not a structured object.")
    return parsed
