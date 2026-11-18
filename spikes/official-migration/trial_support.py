import asyncio
import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_framework import AgentContext, AgentMiddleware, AgentResponse, ChatResponse, Message
from agent_framework.foundry import FoundryAgent
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from demo_common.contracts import Route  # noqa: E402
from demo_common.environment import ENVIRONMENT  # noqa: E402
from demo_common.normalization import normalize_specialist_result  # noqa: E402

ENDPOINT = ENVIRONMENT.foundry_endpoint
SOURCE_SHA256 = "8a1b3b54903f26864bf81fad662e847cc97df18a945f536db9ff78b90aa4a8e1"
PINNED_AGENTS = {
    "kppdemo-router": "1",
    "kppdemo-mcp": "1",
    "kppdemo-rest": "4",
    "kppdemo-knowledge": "2",
    "kppdemo-foundry-iq": "2",
    "kppdemo-fabric-data": "1",
}
SPECIALISTS = {
    "mcp": "kppdemo-mcp",
    "rest_api": "kppdemo-rest",
    "knowledge": "kppdemo-knowledge",
    "foundry_iq": "kppdemo-foundry-iq",
    "fabric_data": "kppdemo-fabric-data",
}
ProgressCallback = Callable[[str, dict[str, Any]], None]


def check_source(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("This runner accepts only the copied synthetic demo workflow.")
    return digest


def native_evidence(response: AgentResponse) -> dict[str, Any]:
    native = response.raw_representation
    if isinstance(native, ChatResponse):
        native = native.raw_representation
    if hasattr(native, "model_dump"):
        native = native.model_dump(mode="json")
    if not isinstance(native, dict):
        raise TypeError("The official connector did not expose a native response object.")

    evidence = {
        key: native.get(key) for key in ("id", "status", "error", "agent_reference", "conversation")
    }
    evidence["output"] = [
        {
            key: value
            for key, value in item.items()
            if key
            in (
                "id",
                "type",
                "name",
                "arguments",
                "output",
                "status",
                "error",
                "agent_reference",
                "response_id",
                "content",
                "role",
            )
        }
        for item in native.get("output", [])
        if item.get("type") in ("message", "mcp_call")
    ]
    return evidence


class RecordAgent(AgentMiddleware):
    def __init__(
        self,
        name: str,
        agent_version: str,
        calls: list[dict[str, Any]],
        on_progress: ProgressCallback | None = None,
    ):
        self.name = name
        self.agent_version = agent_version
        self.calls = calls
        self.on_progress = on_progress

    async def process(
        self, context: AgentContext, call_next: Callable[[], Awaitable[None]]
    ) -> None:
        if self.on_progress is not None:
            self.on_progress("agent_started", {"agent": self.name, "version": self.agent_version})
        print(f"INVOKE {self.name}:{self.agent_version}", flush=True)
        await call_next()
        if not isinstance(context.result, AgentResponse):
            raise TypeError("The trial requires a completed, non-streaming AgentResponse.")
        native = native_evidence(context.result)
        expected = {"type": "agent_reference", "name": self.name, "version": self.agent_version}
        if native["agent_reference"] != expected:
            raise ValueError("The native service response does not match the pinned demo agent.")
        self.calls.append(
            {
                "agent": self.name,
                "version": self.agent_version,
                "input_messages": [message.text for message in context.messages],
                "text": context.result.text,
                "native": native,
            }
        )
        if self.on_progress is not None:
            self.on_progress("agent_completed", self.calls[-1])
        print(f"COMPLETED {self.name} response={native['id']}", flush=True)


class PreserveNativeContext(AgentMiddleware):
    def __init__(self, pool: "AgentPool"):
        self.pool = pool

    async def process(
        self, context: AgentContext, call_next: Callable[[], Awaitable[None]]
    ) -> None:
        if self.pool.question is None or self.pool.conversation_id is None:
            raise RuntimeError("The per-run native conversation has not been initialized.")
        name = context.agent.name
        if name != "kppdemo-router":
            routes = [route for route, specialist in SPECIALISTS.items() if specialist == name]
            if len(routes) != 1:
                raise ValueError(
                    "A native-context specialist must belong to the copied demo source."
                )
            await self.pool.append_activity(f"KPP_ROUTE:{routes[0]}")
        context.messages = [Message(role="user", contents=[self.pool.question])]
        context.options = {
            **dict(context.options or {}),
            "conversation_id": self.pool.conversation_id,
        }
        await call_next()


class AgentPool:
    def __init__(
        self,
        *,
        question: str | None = None,
        on_progress: ProgressCallback | None = None,
        credential: AzureCliCredential | None = None,
    ) -> None:
        self.credential = credential or AzureCliCredential()
        self.on_progress = on_progress
        self.calls: list[dict[str, Any]] = []
        self.question = question
        self.conversation_id: str | None = None
        self.project_client: AIProjectClient | None = None
        self.native_client: OpenAI | None = None
        self.activity_ids: list[str] = []
        self.agents = {
            name: FoundryAgent(
                project_endpoint=ENDPOINT,
                agent_name=name,
                agent_version=agent_version,
                credential=self.credential,
                allow_preview=False,
                default_headers={"Foundry-Features": "WorkflowAgents=V1Preview"},
                default_options={"max_output_tokens": 2048},
                env_file_path=(
                    str(Path(__file__).with_name(".env.example"))
                    if Path(__file__).with_name(".env.example").is_file() else None
                ),
                middleware=[
                    *([PreserveNativeContext(self)] if question is not None else []),
                    RecordAgent(name, agent_version, self.calls, on_progress),
                ],
                timeout=120,
            )
            for name, agent_version in PINNED_AGENTS.items()
        }

    async def __aenter__(self) -> "AgentPool":
        if self.question is not None:
            if self.on_progress is not None:
                self.on_progress("conversation_started", {})
            self.project_client = AIProjectClient(ENDPOINT, self.credential, allow_preview=True)
            self.native_client = self.project_client.get_openai_client(
                default_headers={"Foundry-Features": "WorkflowAgents=V1Preview"},
                timeout=120,
                max_retries=1,
            )
            conversation = await asyncio.to_thread(
                self.native_client.conversations.create,
                metadata={"demo_id": "48254cc6", "purpose": "isolated-official-migration-trial"},
            )
            self.conversation_id = conversation.id
            if self.on_progress is not None:
                self.on_progress("conversation_ready", {"conversation_id": self.conversation_id})
        return self

    async def append_activity(self, text: str) -> None:
        if self.native_client is None or self.conversation_id is None:
            raise RuntimeError("A native conversation is required before appending an activity.")
        activity_index = len(self.activity_ids)
        if self.on_progress is not None:
            self.on_progress("activity_started", {"text": text, "index": activity_index})
        result = await asyncio.to_thread(
            self.native_client.conversations.items.create,
            self.conversation_id,
            items=[
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
        )
        self.activity_ids.extend(item.id for item in result.data)
        if self.on_progress is not None:
            self.on_progress("activity_ready", {"text": text, "index": activity_index})

    async def read_conversation(self) -> list[dict]:
        if self.native_client is None or self.conversation_id is None:
            raise RuntimeError("There is no owned conversation to verify.")
        page = await asyncio.to_thread(
            self.native_client.conversations.items.list,
            self.conversation_id,
            order="asc",
            limit=100,
        )
        return [item.model_dump(mode="json") for item in page.data if item.type == "message"]

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        try:
            for agent in self.agents.values():
                await agent.close()
        finally:
            if self.native_client is not None:
                self.native_client.close()
            if self.project_client is not None:
                self.project_client.close()
            self.credential.close()


def verify_run(
    question: str,
    outputs: list[str],
    calls: list[dict[str, Any]],
    *,
    run_id: UUID | None = None,
) -> dict:
    if not calls or calls[0]["agent"] != "kppdemo-router":
        raise ValueError("A real router invocation must be the first agent call.")
    decision = json.loads(calls[0]["text"])
    route = Route(decision["route"])
    text = "\n".join(outputs)
    if f"KPP_ROUTE:{route.value}" not in text:
        raise ValueError("The workflow did not emit the route selected by the native router.")
    if route.value in SPECIALISTS:
        specialist = SPECIALISTS[route.value]
        if len(calls) != 2 or calls[1]["agent"] != specialist:
            raise ValueError("The selected specialist must be invoked exactly once.")
        binding = {"name": specialist, "version": PINNED_AGENTS[specialist]}
        normalized = normalize_specialist_result(
            calls[1]["native"],
            route,
            run_id or uuid4(),
            binding,
        )
        if normalized.status != "success":
            raise ValueError(f"Native tool evidence failed validation: {normalized.error}")
        result = normalized.model_dump(mode="json")
    else:
        if len(calls) != 1:
            raise ValueError("A non-dispatch route must not call a specialist.")
        status = "blocked" if route.value in ("fabric_iq", "work_iq") else route.value
        if f"KPP_STATUS:{status}" not in text:
            raise ValueError("The workflow did not emit its required terminal status.")
        result = {"route": route.value, "status": status, "answer": text}
    return {
        "question": question,
        "route": route.value,
        "outputs": outputs,
        "result": result,
        "calls": calls,
        "verification": "native agent/version, specialist count, actual MCP evidence and sources",
        "conversation_parity": "NOT_ASSERTED: inspect the separate native-context checks",
    }


async def verify_native_context(pool: AgentPool, outputs: list[str], report: dict) -> None:
    if report["route"] not in SPECIALISTS:
        for output in outputs:
            await pool.append_activity(output)
    conversation = await pool.read_conversation()
    texts = [
        part["text"]
        for item in conversation
        for part in item.get("content", [])
        if isinstance(part.get("text"), str)
    ]
    checks = {
        "original_question_exact": all(
            call["input_messages"] == [pool.question] for call in pool.calls
        ),
        "one_shared_native_conversation": all(
            call["native"]["conversation"] == {"id": pool.conversation_id} for call in pool.calls
        ),
        "source_activity_stored_natively": any(
            f"KPP_ROUTE:{report['route']}" in text for text in texts
        ),
    }
    report["native_context"] = {
        "conversation_id": pool.conversation_id,
        "activity_item_ids": pool.activity_ids,
        "checks": checks,
        "messages_read_back": conversation,
    }
    report["conversation_parity"] = "PASS" if all(checks.values()) else "FAIL"
    if not all(checks.values()):
        raise ValueError(f"Native conversation parity failed: {checks}")
