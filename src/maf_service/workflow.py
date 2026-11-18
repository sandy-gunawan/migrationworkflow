import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal, Protocol

from agent_framework import (
    Case,
    Default,
    Executor,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from demo_common.contracts import DemoRequest, DemoResult, Route, RouterDecision
from demo_common.foundry import response_text
from demo_common.migration import Branch, Outcome, WorkflowMapping
from demo_common.normalization import normalize_specialist_result
from maf_service.progress import ProgressObserver, report

logger = logging.getLogger(__name__)
IdentityMode = Literal["managed_identity", "azure_cli", "unit_fixture"]


def load_mapping() -> WorkflowMapping:
    from demo_common import normalization

    resources = Path(__file__).parent / "resources"
    mapping = WorkflowMapping.model_validate_json(
        (resources / "mapping.json").read_text(encoding="utf-8")
    )
    baseline = json.loads((resources / "baseline.json").read_text(encoding="utf-8"))
    checks = (
        hashlib.sha256((resources / "source.workflow.yaml").read_bytes()).hexdigest()
        == mapping.source_sha256
        == baseline["source_sha256"],
        hashlib.sha256(Path(normalization.__file__).read_bytes()).hexdigest()
        == baseline["normalization_sha256"],
        version("agent-framework-core") == baseline["core_version"],
    )
    if not all(checks):
        raise ValueError("Runtime mapping, source, normalization, or SDK differs from baseline.")
    return mapping


class WorkflowAgents(Protocol):
    def start_conversation(self, question: str, run_id: str) -> str: ...
    def append_activity(self, conversation_id: str, text: str) -> None: ...
    def invoke(
        self,
        name: str,
        question: str,
        version: str | None = None,
        *,
        conversation_id: str | None = None,
    ) -> dict: ...


class AgentCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: str
    response_id: str


class RunTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    framework: Literal["agent_framework"] = "agent_framework"
    framework_version: str
    framework_module: str = ""
    source_sha256: str
    outbound_auth: IdentityMode
    conversation_id: str = ""
    source_actions: list[str] = Field(default_factory=list)
    executors: list[str] = Field(default_factory=list)
    agent_calls: list[AgentCall] = Field(default_factory=list)


class WorkflowOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: DemoResult
    trace: RunTrace


class WorkflowExecutionError(RuntimeError):
    pass


@dataclass
class RunState:
    request: DemoRequest
    trace: RunTrace
    route: Route | None = None
    invalid_router: bool = False


class RouterExecutor(Executor):
    def __init__(
        self, mapping: WorkflowMapping, agents: WorkflowAgents,
        observer: ProgressObserver | None = None,
    ):
        super().__init__(id=mapping.router_action_id)
        self.mapping = mapping
        self.agents = agents
        self.observer = observer

    @handler
    async def route(self, state: RunState, ctx: WorkflowContext[RunState, WorkflowOutput]) -> None:
        state.trace.executors.append(self.id)
        state.trace.source_actions.extend(
            [self.mapping.capture_action_id, self.mapping.router_action_id]
        )
        report(
            self.observer, state.request, phase="context", status="running",
            step_id=self.mapping.capture_action_id, code_key="router",
            label="Menyiapkan percakapan", detail="Menyimpan pertanyaan asli pada percakapan baru.",
        )
        conversation = await asyncio.to_thread(
            self.agents.start_conversation, state.request.question, str(state.request.run_id)
        )
        state.trace.conversation_id = conversation
        report(
            self.observer, state.request, phase="context", status="done",
            step_id=self.mapping.capture_action_id, code_key="router",
            label="Percakapan siap",
            detail="Pertanyaan asli dipertahankan untuk router dan specialist.",
        )
        binding = self.mapping.router
        report(
            self.observer, state.request, phase="router", status="running",
            step_id=self.id, code_key="router", agent_name=binding.name,
            agent_version=binding.version, label="Router menentukan topik",
            detail="Menunggu respons agent router Foundry; router tidak mengambil data bisnis.",
        )
        response = await asyncio.to_thread(
            self.agents.invoke,
            binding.name,
            state.request.question,
            binding.version,
            conversation_id=conversation,
        )
        state.trace.agent_calls.append(
            AgentCall(name=binding.name, version=binding.version, response_id=response["id"])
        )
        report(
            self.observer, state.request, phase="router", status="done", step_id=self.id,
            code_key="router", agent_name=binding.name, agent_version=binding.version,
            response_id=response["id"], label="Respons router diterima",
            detail="Output router diperiksa terhadap schema route, bukan instruksi bebas.",
        )
        try:
            state.route = RouterDecision.model_validate_json(response_text(response)).route
        except ValidationError:
            logger.error("Native router returned invalid structured output; no data is dispatched.")
            state.invalid_router = True
        state.trace.source_actions.append(self.mapping.condition_action_id)
        selected = next(
            (branch for branch in self.mapping.branches if branch.route == state.route), None
        )
        agent = selected.agent if selected else None
        report(
            self.observer, state.request, phase="routing",
            status="failed" if state.invalid_router else "done",
            step_id=self.mapping.condition_action_id, code_key="switch", route=state.route,
            agent_name=agent.name if agent else None,
            agent_version=agent.version if agent else None,
            label="Memilih branch",
            detail=(
                "Output router tidak valid; tidak ada specialist yang dipanggil."
                if state.invalid_router else
                f"Route {state.route} memilih satu branch dari kondisi sumber yang dibekukan."
            ),
        )
        await ctx.send_message(state)


class SpecialistExecutor(Executor):
    def __init__(
        self, branch: Branch, end_action: str, agents: WorkflowAgents,
        observer: ProgressObserver | None = None,
    ):
        if branch.agent is None or branch.marker_action_id is None:
            raise ValueError("A specialist executor needs a source agent and route marker.")
        super().__init__(id=branch.action_id)
        self.branch = branch
        self.binding = branch.agent
        self.marker_id = branch.marker_action_id
        self.end_action = end_action
        self.agents = agents
        self.observer = observer

    @handler
    async def retrieve(self, state: RunState, ctx: WorkflowContext[None, WorkflowOutput]) -> None:
        state.trace.executors.append(self.id)
        state.trace.source_actions.extend([self.marker_id, self.branch.action_id])
        report(
            self.observer, state.request, phase="activity", status="running",
            step_id=self.marker_id, code_key="specialist", route=self.branch.route,
            label="Mencatat pilihan route",
            detail="Penanda route disimpan pada percakapan yang sama.",
        )
        await asyncio.to_thread(
            self.agents.append_activity,
            state.trace.conversation_id,
            f"KPP_ROUTE:{self.branch.route.value}",
        )
        report(
            self.observer, state.request, phase="activity", status="done",
            step_id=self.marker_id, code_key="specialist", route=self.branch.route,
            label="Route tercatat",
            detail="Specialist menerima pertanyaan asli, bukan pertanyaan baru.",
        )
        report(
            self.observer, state.request, phase="specialist", status="running",
            step_id=self.id, code_key="specialist", route=self.branch.route,
            agent_name=self.binding.name, agent_version=self.binding.version,
            label="Specialist mengambil jawaban",
            detail=(
                "Menunggu respons agent Foundry. Nama/status tool aktual baru diketahui "
                "setelah native response kembali."
            ),
        )
        response = await asyncio.to_thread(
            self.agents.invoke,
            self.binding.name,
            state.request.question,
            self.binding.version,
            conversation_id=state.trace.conversation_id,
        )
        state.trace.agent_calls.append(
            AgentCall(
                name=self.binding.name,
                version=self.binding.version,
                response_id=response["id"],
            )
        )
        report(
            self.observer, state.request, phase="specialist", status="done",
            step_id=self.id, code_key="specialist", route=self.branch.route,
            agent_name=self.binding.name, agent_version=self.binding.version,
            response_id=response["id"], label="Respons specialist diterima",
            detail="Respons native diterima; grounding dan tool evidence belum dinyatakan sukses.",
        )
        if self.observer is not None:
            for item in response.get("output", []):
                if not isinstance(item, dict) or item.get("type") != "mcp_call":
                    continue
                reference = item.get("agent_reference", response.get("agent_reference", {}))
                name = reference.get("name") if isinstance(reference, dict) else None
                version = reference.get("version") if isinstance(reference, dict) else None
                tool = item.get("name")
                report(
                    self.observer, state.request, phase="tool",
                    status="done" if item.get("status") == "completed" and not item.get("error")
                    else "failed",
                    step_id=self.id, code_key="specialist", route=self.branch.route,
                    agent_name=name if isinstance(name, str) else None,
                    agent_version=version if isinstance(version, str) else None,
                    tool_name=tool if isinstance(tool, str) else None,
                    label="Tool native tercatat",
                    detail=f"Status dari evidence Foundry: {item.get('status')}.",
                )
        report(
            self.observer, state.request, phase="normalization", status="running",
            step_id=self.id, code_key="normalization", route=self.branch.route,
            label="Memverifikasi jawaban dan sumber",
            detail="Memeriksa versi agent, hasil tool, batas data dummy dan sumber nyata.",
        )
        result = normalize_specialist_result(
            response, self.branch.route, state.request.run_id, self.binding.model_dump()
        )
        report(
            self.observer, state.request, phase="normalization",
            status="done" if result.status == "success" else "failed",
            step_id=self.id, code_key="normalization", route=self.branch.route,
            label="Grounding terverifikasi" if result.status == "success" else "Evidence ditolak",
            detail="Fakta dan sumber berasal dari tool yang benar." if result.status == "success"
            else f"Evidence ditolak: {result.error}",
        )
        state.trace.source_actions.append(self.end_action)
        await ctx.yield_output(WorkflowOutput(result=result, trace=state.trace))


class OutcomeExecutor(Executor):
    def __init__(
        self, outcome: Outcome, end_action: str, agents: WorkflowAgents,
        observer: ProgressObserver | None = None,
    ):
        super().__init__(id=outcome.action_id)
        self.outcome = outcome
        self.end_action = end_action
        self.agents = agents
        self.observer = observer

    @handler
    async def finish(self, state: RunState, ctx: WorkflowContext[None, WorkflowOutput]) -> None:
        state.trace.executors.append(self.id)
        state.trace.source_actions.extend([self.outcome.action_id, self.end_action])
        status = self.outcome.status
        await asyncio.to_thread(
            self.agents.append_activity,
            state.trace.conversation_id,
            f"KPP_ROUTE:{self.outcome.route.value}\nKPP_STATUS:{status}\n{self.outcome.text}",
        )
        result = DemoResult(
            run_id=state.request.run_id,
            route=self.outcome.route,
            status=status,
            answer=self.outcome.text if status in ("clarification", "unsupported") else None,
            error=self.outcome.text if status in ("blocked", "failed") else None,
        )
        report(
            self.observer, state.request, phase="outcome",
            status="blocked" if status == "blocked" else "failed" if status == "failed" else "done",
            step_id=self.id, code_key="outcome", route=self.outcome.route,
            label="Tidak ada specialist yang dipanggil", detail=self.outcome.text,
        )
        await ctx.yield_output(WorkflowOutput(result=result, trace=state.trace))


class MiningWorkflow:
    def __init__(
        self, mapping: WorkflowMapping, agents: WorkflowAgents, *, identity_mode: IdentityMode,
        on_progress: ProgressObserver | None = None,
    ):
        self.mapping = mapping
        self.agents = agents
        self.identity_mode = identity_mode
        self.on_progress = on_progress

    def build(self) -> Workflow:
        router = RouterExecutor(self.mapping, self.agents, self.on_progress)
        builder = WorkflowBuilder(
            start_executor=router,
            max_iterations=4,
            output_from="all",
            name=self.mapping.trigger_id,
            description="Source-derived router/if-else; specialists remain Foundry-hosted.",
        )
        cases = []
        for branch in self.mapping.branches:
            if branch.agent is not None:
                target = SpecialistExecutor(
                    branch, self.mapping.end_action_id, self.agents, self.on_progress,
                )
            elif branch.outcome is not None:
                target = OutcomeExecutor(
                    branch.outcome, self.mapping.end_action_id, self.agents, self.on_progress,
                )
            else:
                raise ValueError("The compiled source branch has no behavior.")
            cases.append(
                Case(
                    condition=lambda state, route=branch.route: (
                        not state.invalid_router and state.route == route
                    ),
                    target=target,
                )
            )
        fallback = OutcomeExecutor(
            self.mapping.fallback, self.mapping.end_action_id, self.agents, self.on_progress,
        )
        builder.add_switch_case_edge_group(router, [*cases, Default(target=fallback)])
        return builder.build()

    async def run(self, request: DemoRequest) -> WorkflowOutput:
        report(
            self.on_progress, request, phase="workflow", status="running",
            step_id=self.mapping.trigger_id, code_key="workflow", label="MAF mulai mengeksekusi",
            detail="Graph WorkflowBuilder baru dipakai untuk run ini; bukan hasil replay.",
        )
        workflow = self.build()
        trace = RunTrace(
            framework_version=version("agent-framework-core"),
            framework_module=type(workflow).__module__,
            source_sha256=self.mapping.source_sha256,
            outbound_auth=self.identity_mode,
        )
        execution = await workflow.run(RunState(request=request, trace=trace))
        outputs = execution.get_outputs()
        if len(outputs) != 1 or not isinstance(outputs[0], WorkflowOutput):
            logger.error("Agent Framework did not produce exactly one typed run result.")
            raise WorkflowExecutionError("Agent Framework produced no valid run result.")
        output = outputs[0]
        report(
            self.on_progress, request, phase="workflow",
            status="blocked" if output.result.status == "blocked"
            else "failed" if output.result.status == "failed" else "done",
            step_id=self.mapping.end_action_id, code_key="workflow", route=output.result.route,
            label="Run selesai", detail=f"Hasil akhir: {output.result.status}.",
        )
        return output
