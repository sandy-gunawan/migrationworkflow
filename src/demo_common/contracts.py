from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Route(StrEnum):
    FABRIC_DATA = "fabric_data"
    FABRIC_IQ = "fabric_iq"
    MCP = "mcp"
    REST_API = "rest_api"
    KNOWLEDGE = "knowledge"
    FOUNDRY_IQ = "foundry_iq"
    WORK_IQ = "work_iq"
    CLARIFICATION = "clarification"
    UNSUPPORTED = "unsupported"


BLOCKED_ROUTES = {
    Route.FABRIC_IQ: "Fabric ontology is unavailable in this tenant (FeatureNotAvailable).",
    Route.WORK_IQ: "A separate Work IQ sandbox has not been supplied; no Work IQ is accessed.",
}


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=4000)
    run_id: UUID = Field(default_factory=uuid4)


class RouterDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: Route


class NativeTextPart(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    text: str


class NativeResponseOutput(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    agent_reference: dict[str, str] | None = None
    content: list[NativeTextPart] = Field(default_factory=list)


class NativeAgentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str
    agent_reference: dict[str, str] | None = None
    output: list[NativeResponseOutput]


class NormalizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    route: Literal[
        Route.MCP, Route.REST_API, Route.KNOWLEDGE, Route.FOUNDRY_IQ, Route.FABRIC_DATA
    ]
    response: NativeAgentResponse


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: str


class DemoResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    route: Route
    status: str
    answer: str | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="after")
    def reject_success_shaped_failure(self) -> "DemoResult":
        if self.route in BLOCKED_ROUTES and self.status != "blocked":
            raise ValueError("Unavailable native routes must be explicitly blocked.")
        if self.status == "success":
            if not self.answer or not self.sources or self.error:
                raise ValueError(
                    "Successful results require grounded text and sources, not errors."
                )
        elif self.status in ("blocked", "failed"):
            if self.answer is not None or not self.error:
                raise ValueError(
                    "Blocked/failed results require an error and no fabricated answer."
                )
        elif self.status not in ("clarification", "unsupported"):
            raise ValueError("Unknown demo result status.")
        return self
