from typing import Callable, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from demo_common.contracts import DemoRequest, Route

ProgressPhase = Literal[
    "workflow", "context", "router", "routing", "activity", "specialist",
    "tool", "normalization", "outcome", "capacity",
]
ProgressStatus = Literal["running", "done", "blocked", "failed"]
CodeKey = Literal[
    "workflow", "router", "switch", "specialist", "normalization", "outcome", "capacity",
]


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    phase: ProgressPhase
    status: ProgressStatus
    step_id: str
    code_key: CodeKey
    label: str
    detail: str
    route: Route | None = None
    agent_name: str | None = None
    agent_version: str | None = None
    tool_name: str | None = None
    response_id: str | None = None


ProgressObserver = Callable[[ProgressUpdate], None]


def report(
    observer: ProgressObserver | None, request: DemoRequest, *,
    phase: ProgressPhase, status: ProgressStatus, step_id: str, code_key: CodeKey,
    label: str, detail: str,
    route: Route | None = None, agent_name: str | None = None,
    agent_version: str | None = None, tool_name: str | None = None,
    response_id: str | None = None,
) -> None:
    if observer is not None:
        observer(ProgressUpdate(
            run_id=request.run_id, phase=phase, status=status, step_id=step_id, code_key=code_key,
            label=label, detail=detail, route=route, agent_name=agent_name,
            agent_version=agent_version, tool_name=tool_name, response_id=response_id,
        ))
