import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from demo_common.contracts import BLOCKED_ROUTES, Route
from demo_common.foundry import ALLOWED_AGENTS


class UnsupportedSource(ValueError):
    pass


class AgentBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    version: str


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    route: Route
    status: Literal["blocked", "failed", "clarification", "unsupported"]
    text: str
    action_id: str


class Branch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    route: Route
    condition: str
    action_id: str
    marker_action_id: str | None = None
    agent: AgentBinding | None = None
    outcome: Outcome | None = None


class WorkflowMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    runtime: Literal["agent_framework_workflow_builder"] = "agent_framework_workflow_builder"
    source_sha256: str
    trigger_id: str
    capture_action_id: str
    question_variable: str
    router_action_id: str
    condition_action_id: str
    decision_variable: str
    router: AgentBinding
    branches: list[Branch]
    fallback: Outcome
    end_action_id: str


def _node(value: object, keys: set[str], kind: str | None = None) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise UnsupportedSource(f"Unsupported fields for {kind or 'source node'}.")
    if kind is not None and value["kind"] != kind:
        raise UnsupportedSource(f"Expected {kind}, found {value['kind']}.")
    return value


def _identifier(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise UnsupportedSource("A source action has an invalid identifier.")
    return value


def _variable(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"Local\.[A-Za-z][A-Za-z0-9_]*", value):
        raise UnsupportedSource("Only simple Local variables are supported.")
    return value


def _binding(value: object, *, router: bool = False) -> AgentBinding:
    agent = _node(value, {"name", "version"})
    name = agent["name"]
    allowed = (
        {"kppdemo-router"}
        if router
        else ALLOWED_AGENTS - {"kppdemo-router", "kppdemo-mining-workflow"}
    )
    if not isinstance(name, str) or name not in allowed:
        raise UnsupportedSource("Source references an existing or unsupported agent.")
    version = agent["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[1-9]\d*", version):
        raise UnsupportedSource("Agent references must pin an immutable numeric version.")
    return AgentBinding(name=name, version=version)


def _outcome(value: object, route: Route, status: str) -> Outcome:
    action = _node(value, {"kind", "id", "activity"}, "SendActivity")
    activity = action["activity"]
    if not isinstance(activity, str):
        raise UnsupportedSource("Computed/non-text outcome activities are not supported.")
    lines = activity.strip().splitlines()
    if (
        len(lines) < 3
        or lines[0] != f"KPP_ROUTE:{route.value}"
        or lines[1] != f"KPP_STATUS:{status}"
        or not "\n".join(lines[2:]).strip()
    ):
        raise UnsupportedSource("A non-dispatch route has unsupported outcome semantics.")
    return Outcome(
        route=route,
        status=status,
        text="\n".join(lines[2:]).strip(),
        action_id=_identifier(action["id"]),
    )


def compile_source(text: str) -> WorkflowMapping:
    import yaml

    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise UnsupportedSource("The source YAML is invalid.") from exc
    root = _node(value, {"kind", "trigger"}, "workflow")
    trigger = _node(root["trigger"], {"kind", "id", "actions"}, "OnConversationStart")
    actions = trigger["actions"]
    if not isinstance(actions, list) or len(actions) != 4:
        raise UnsupportedSource("Only capture -> router -> conditions -> end is supported.")
    capture = _node(actions[0], {"kind", "id", "variable", "value"}, "SetVariable")
    if capture["value"] != "=System.LastMessage.Text":
        raise UnsupportedSource("The source modifies the original question.")
    question = _variable(capture["variable"])
    invoke_keys = {"kind", "id", "agent", "conversationId", "input", "output"}
    router = _node(actions[1], invoke_keys, "InvokeAzureAgent")
    if router["conversationId"] != "=System.ConversationId" or router["input"] != {
        "messages": f"=UserMessage({question})"
    }:
        raise UnsupportedSource("Router input/conversation semantics are not supported.")
    router_output = _node(router["output"], {"responseObject", "messages", "autoSend"})
    decision = _variable(router_output["responseObject"])
    _variable(router_output["messages"])
    if router_output["autoSend"] is not False:
        raise UnsupportedSource("The router must not replace the specialist answer.")
    group = _node(actions[2], {"kind", "id", "conditions", "elseActions"}, "ConditionGroup")
    if not isinstance(group["conditions"], list):
        raise UnsupportedSource("Route conditions must be a list.")
    branches = []
    seen = set()
    action_ids = {
        _identifier(trigger["id"]),
        _identifier(capture["id"]),
        _identifier(router["id"]),
        _identifier(group["id"]),
    }
    if len(action_ids) != 4:
        raise UnsupportedSource("Top-level action identifiers are duplicated.")
    pattern = rf'={re.escape(decision)}\.route = "([a-z_]+)"'
    for raw in group["conditions"]:
        condition = _node(raw, {"id", "condition", "actions"})
        expression = condition["condition"]
        match = re.fullmatch(pattern, expression) if isinstance(expression, str) else None
        if match is None:
            raise UnsupportedSource("Only equality tests on the validated route are supported.")
        try:
            route = Route(match.group(1))
        except ValueError as exc:
            raise UnsupportedSource("An unknown route is present.") from exc
        if route in seen:
            raise UnsupportedSource("Route conditions overlap.")
        seen.add(route)
        children = condition["actions"]
        if not isinstance(children, list):
            raise UnsupportedSource("Branch actions must be a list.")
        child_ids = [_identifier(condition["id"])]
        if route in BLOCKED_ROUTES or route in (Route.CLARIFICATION, Route.UNSUPPORTED):
            status = "blocked" if route in BLOCKED_ROUTES else route.value
            if len(children) != 1:
                raise UnsupportedSource("Non-dispatch branches must not call a specialist.")
            outcome = _outcome(children[0], route, status)
            branch = Branch(
                route=route, condition=expression, action_id=outcome.action_id, outcome=outcome
            )
            child_ids.append(outcome.action_id)
        else:
            if len(children) != 2:
                raise UnsupportedSource("A data branch must mark and invoke exactly one agent.")
            marker = _node(children[0], {"kind", "id", "activity"}, "SendActivity")
            if marker["activity"] != f"KPP_ROUTE:{route.value}":
                raise UnsupportedSource("The data branch marker is unsupported.")
            child = _node(children[1], invoke_keys, "InvokeAzureAgent")
            output = _node(child["output"], {"messages", "autoSend"})
            _variable(output["messages"])
            if (
                child["conversationId"] != "=System.ConversationId"
                or child["input"] != {"messages": f"=UserMessage({question})"}
                or output["autoSend"] is not True
            ):
                raise UnsupportedSource("Specialist question/context/output semantics changed.")
            marker_id = _identifier(marker["id"])
            branch = Branch(
                route=route,
                condition=expression,
                action_id=_identifier(child["id"]),
                marker_action_id=marker_id,
                agent=_binding(child["agent"]),
            )
            child_ids.extend([branch.action_id, marker_id])
        if len(set(child_ids)) != len(child_ids) or action_ids.intersection(child_ids):
            raise UnsupportedSource("Source action identifiers are duplicated.")
        action_ids.update(child_ids)
        branches.append(branch)
    if seen != set(Route):
        raise UnsupportedSource("The source is missing a required route.")
    fallback = group["elseActions"]
    if not isinstance(fallback, list) or len(fallback) != 1:
        raise UnsupportedSource("Exactly one explicit default failure is required.")
    default = _outcome(fallback[0], Route.UNSUPPORTED, "failed")
    end = _node(actions[3], {"kind", "id"}, "EndConversation")
    end_id = _identifier(end["id"])
    if default.action_id in action_ids or end_id in action_ids or default.action_id == end_id:
        raise UnsupportedSource("Default/end action identifiers are duplicated.")
    return WorkflowMapping(
        source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        trigger_id=trigger["id"],
        capture_action_id=capture["id"],
        question_variable=question,
        router_action_id=router["id"],
        condition_action_id=group["id"],
        decision_variable=decision,
        router=_binding(router["agent"], router=True),
        branches=branches,
        fallback=default,
        end_action_id=end_id,
    )
