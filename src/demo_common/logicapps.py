import re

from demo_common.contracts import DemoRequest
from demo_common.environment import ENVIRONMENT
from demo_common.foundry import ENDPOINT
from demo_common.migration import Outcome, UnsupportedSource, WorkflowMapping

NORMALIZER = f"{ENVIRONMENT.maf_url}/api/normalize-result"
API_RESOURCE = f"api://{ENVIRONMENT.api_audience}"
AI_RESOURCE = "https://ai.azure.com"
CONVERSATION = "@body('create_conversation')?['id']"
ACTIVITY_URI = (
    f"@concat('{ENDPOINT}/openai/v1/conversations/',"
    "body('create_conversation')?['id'],'/items')"
)


def _literal(value: str) -> str:
    return f"@{value}" if value.startswith("@") else value


def _after(action: str | None) -> dict:
    return {action: ["Succeeded"]} if action else {}


def _http(uri: str, body: dict, after: str | None, *, audience: str = AI_RESOURCE) -> dict:
    return {
        "type": "Http",
        "inputs": {
            "method": "POST",
            "uri": uri,
            "headers": {"Foundry-Features": "WorkflowAgents=V1Preview"}
            if audience == AI_RESOURCE else {},
            "body": body,
            "authentication": {"type": "ManagedServiceIdentity", "audience": audience},
            "retryPolicy": {"type": "none"},
        },
        "runAfter": _after(after),
    }


def _agent(name: str, version: str, question: str, after: str) -> dict:
    return _http(
        f"{ENDPOINT}/openai/v1/responses",
        {
            "input": question, "stream": False, "max_output_tokens": 2048,
            "conversation": CONVERSATION,
            "agent_reference": {"type": "agent_reference", "name": name, "version": version},
        },
        after,
    )


def _activity(text: str, after: str | None = None) -> dict:
    return _http(
        ACTIVITY_URI,
        {"items": [{
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": _literal(text)}],
        }]},
        after,
    )


def _outcome(outcome: Outcome, run_id: str) -> dict:
    answer = outcome.status in ("clarification", "unsupported")
    return {
        "run_id": run_id, "route": outcome.route.value, "status": outcome.status,
        "answer": _literal(outcome.text) if answer else None,
        "sources": [],
        "error": None if answer else _literal(outcome.text),
    }


def _set_result(value: object, after: str | None = None) -> dict:
    return {
        "type": "SetVariable", "inputs": {"name": "Result", "value": value},
        "runAfter": _after(after),
    }


def build_logic_workflow(mapping: WorkflowMapping) -> dict:
    identifiers = [
        mapping.capture_action_id, mapping.router_action_id, mapping.condition_action_id,
        mapping.end_action_id, mapping.fallback.action_id,
        *(branch.action_id for branch in mapping.branches),
        *(branch.marker_action_id for branch in mapping.branches if branch.marker_action_id),
    ]
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", value) for value in identifiers):
        raise UnsupportedSource("A source action identifier is not supported by this WDL subset.")
    reserved = {
        "create_conversation", "record_router_response", "Parse_router", "router_messages",
        "router_decision", "require_completed_router", "Execute", "Initialize_result",
        "default_invalid_route", "Validate_request", "Reject_invalid_request",
        *(f"normalize_{branch.route.value}" for branch in mapping.branches),
        *(f"record_{branch.route.value}_response" for branch in mapping.branches),
        *(f"set_result_{branch.route.value}" for branch in mapping.branches),
    }
    if len(identifiers) != len(set(identifiers)) or reserved.intersection(identifiers):
        raise UnsupportedSource("Source action identifiers collide with WDL adapter actions.")
    question = f"@outputs('{mapping.capture_action_id}')?['question']"
    run_id = f"@outputs('{mapping.capture_action_id}')?['run_id']"
    router_id = f"@body('{mapping.router_action_id}')?['id']"
    cases = {}
    for branch in mapping.branches:
        route = branch.route.value
        actions = {}
        if branch.agent is not None:
            if branch.marker_action_id is None:
                raise ValueError("A data branch must retain its source route activity.")
            actions[branch.marker_action_id] = _activity(f"KPP_ROUTE:{route}")
            actions[branch.action_id] = _agent(
                branch.agent.name, branch.agent.version, question, branch.marker_action_id,
            )
            actions[f"normalize_{route}"] = _http(
                NORMALIZER,
                {"run_id": run_id, "route": route, "response": f"@body('{branch.action_id}')"},
                branch.action_id,
                audience=API_RESOURCE,
            )
            actions[f"record_{route}_response"] = {
                "type": "SetVariable",
                "inputs": {
                    "name": "NativeResponses",
                    "value": (
                        f"@concat(body('{mapping.router_action_id}')?['id'],',',"
                        f"body('{branch.action_id}')?['id'])"
                    ),
                },
                "runAfter": _after(f"normalize_{route}"),
            }
            actions[f"set_result_{route}"] = _set_result(
                f"@body('normalize_{route}')", f"record_{route}_response",
            )
        else:
            if branch.outcome is None:
                raise ValueError("A non-dispatch branch must retain its source outcome.")
            outcome = branch.outcome
            actions[branch.action_id] = _activity(
                f"KPP_ROUTE:{route}\nKPP_STATUS:{outcome.status}\n{outcome.text}"
            )
            actions[f"set_result_{route}"] = _set_result(
                _outcome(outcome, run_id), branch.action_id,
            )
        cases[route] = {"case": route, "actions": actions}
    router_schema = {
        "type": "object", "required": ["route"], "additionalProperties": False,
        "properties": {"route": {"type": "string", "enum": list(cases)}},
    }
    execute = {
        "create_conversation": _http(
            f"{ENDPOINT}/openai/v1/conversations",
            {
                "metadata": {
                    "demo_id": "48254cc6", "run_id": run_id, "orchestrator": "logic_apps",
                },
                "items": [{
                    "type": "message", "role": "user",
                    "content": [{"type": "input_text", "text": question}],
                }],
            },
            None,
        ),
        mapping.router_action_id: _agent(
            mapping.router.name, mapping.router.version, question, "create_conversation",
        ),
        "record_router_response": {
            "type": "SetVariable", "inputs": {"name": "NativeResponses", "value": router_id},
            "runAfter": _after(mapping.router_action_id),
        },
        "Parse_router": {
            "type": "Scope", "runAfter": _after("record_router_response"),
            "actions": {
                "require_completed_router": {
                    "type": "ParseJson", "runAfter": {},
                    "inputs": {
                        "content": f"@body('{mapping.router_action_id}')",
                        "schema": {
                            "type": "object", "required": ["status", "output"],
                            "properties": {"status": {"enum": ["completed"]}, "output": {
                                "type": "array",
                            }},
                        },
                    },
                },
                "router_messages": {
                    "type": "Query", "runAfter": _after("require_completed_router"),
                    "inputs": {
                        "from": "@body('require_completed_router')?['output']",
                        "where": "@equals(item()?['type'],'message')",
                    },
                },
                "router_decision": {
                    "type": "ParseJson", "runAfter": _after("router_messages"),
                    "inputs": {
                        "content": "@first(first(body('router_messages'))?['content'])?['text']",
                        "schema": router_schema,
                    },
                },
            },
        },
        mapping.fallback.action_id: {
            **_set_result(_outcome(mapping.fallback, run_id)),
            "runAfter": {"Parse_router": ["Failed", "TimedOut"]},
        },
        mapping.condition_action_id: {
            "type": "Switch", "expression": "@body('router_decision')?['route']",
            "cases": cases,
            "default": {"actions": {
                "default_invalid_route": _set_result(_outcome(mapping.fallback, run_id)),
            }},
            "runAfter": _after("Parse_router"),
        },
    }
    return {
        "$schema": (
            "https://schema.management.azure.com/providers/Microsoft.Logic/"
            "schemas/2016-06-01/workflowdefinition.json#"
        ),
        "contentVersion": "1.0.0.0",
        "triggers": {
            mapping.trigger_id: {
                "type": "Request", "kind": "Http",
                "inputs": {"method": "POST", "schema": DemoRequest.model_json_schema()},
                "runtimeConfiguration": {
                    "secureData": {"properties": ["inputs"]},
                },
            },
        },
        "actions": {
            "Validate_request": {
                "type": "ParseJson", "runAfter": {},
                "inputs": {
                    "content": "@triggerBody()", "schema": DemoRequest.model_json_schema(),
                },
            },
            "Reject_invalid_request": {
                "type": "Response", "kind": "Http",
                "runAfter": {"Validate_request": ["Failed", "TimedOut"]},
                "inputs": {
                    "statusCode": 400,
                    "body": {"error": {
                        "code": "invalid_request",
                        "message": (
                            "Supply a question and optional run_id only; "
                            "route overrides are rejected."
                        ),
                    }},
                },
            },
            mapping.capture_action_id: {
                "type": "Compose", "runAfter": _after("Validate_request"),
                "inputs": {
                    "question": "@triggerBody()?['question']",
                    "run_id": "@coalesce(triggerBody()?['run_id'],guid())",
                },
            },
            "Initialize_result": {
                "type": "InitializeVariable", "runAfter": _after(mapping.capture_action_id),
                "inputs": {"variables": [
                    {"name": "NativeResponses", "type": "string", "value": ""},
                    {"name": "Result", "type": "object", "value": {
                        "run_id": run_id, "route": "unsupported", "status": "failed",
                        "answer": None, "sources": [],
                        "error": "A native Logic Apps action failed. Inspect the correlated run.",
                    }},
                ]},
            },
            "Execute": {
                "type": "Scope", "actions": execute, "runAfter": _after("Initialize_result"),
            },
            mapping.end_action_id: {
                "type": "Response", "kind": "Http",
                "runAfter": {"Execute": ["Succeeded", "Failed", "TimedOut"]},
                "inputs": {
                    "statusCode": "@if(equals(variables('Result')?['status'],'failed'),502,200)",
                    "body": "@variables('Result')",
                    "headers": {
                        "Content-Type": "application/json",
                        "x-kpp-orchestrator": "logic_apps",
                        "x-kpp-source-sha256": mapping.source_sha256,
                        "x-kpp-logic-run": "@workflow()['run']['name']",
                        "x-kpp-native-responses": "@variables('NativeResponses')",
                        "x-kpp-route": "@variables('Result')?['route']",
                    },
                },
            },
        },
        "outputs": {},
    }
