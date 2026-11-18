import asyncio
import copy
import json
from pathlib import Path

import pytest

from demo_common.contracts import DemoRequest
from demo_common.migration import compile_source
from maf_service.workflow import MiningWorkflow

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "tests" / "golden" / "cases.json").read_text(encoding="utf-8"))["cases"]

class FixtureAgents:
    def __init__(self, route, responses):
        self.route = route
        self.responses = responses
        self.calls = []
        self.activities = []
        self.original = None

    def start_conversation(self, question, run_id):
        self.original = question
        return "conv_owned_unit"

    def append_activity(self, conversation_id, text):
        assert conversation_id == "conv_owned_unit"
        self.activities.append(text)

    def invoke(self, name, question, version=None, *, conversation_id=None):
        assert conversation_id == "conv_owned_unit"
        assert question == self.original
        self.calls.append((name, version, conversation_id))
        if name == "kppdemo-router":
            return {
                "id": "resp_unit_router",
                "status": "completed",
                "agent_reference": {"name": name, "version": version},
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps({"route": self.route})}
                        ],
                    }
                ],
            }
        return copy.deepcopy(self.responses[self.route])


def mapping():
    source = ROOT / "source" / "foundry" / "workflow.yaml"
    return compile_source(source.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[item["id"] for item in CASES])
def test_real_framework_graph_preserves_all_fifty_source_branch_conditions(
    case, specialist_responses,
):
    source = mapping()
    agents = FixtureAgents(case["route"], specialist_responses)
    engine = MiningWorkflow(source, agents, identity_mode="unit_fixture")
    request = DemoRequest(question=case["question"])
    output = asyncio.run(engine.run(request))
    assert output.result.route.value == case["route"]
    assert output.result.status == case["expected_status"]
    assert output.result.run_id == request.run_id
    specialists = [call for call in agents.calls if call[0] != source.router.name]
    assert len(specialists) == (1 if case["expected_status"] == "success" else 0)
    if specialists:
        branch = next(item for item in source.branches if item.route.value == case["route"])
        assert specialists[0][:2] == (branch.agent.name, branch.agent.version)
        assert agents.activities == [f"KPP_ROUTE:{case['route']}"]
    else:
        assert f"KPP_STATUS:{case['expected_status']}" in agents.activities[0]


def test_malformed_router_output_takes_source_default_without_any_specialist(specialist_responses):
    agents = FixtureAgents("read_real_mail", specialist_responses)
    output = asyncio.run(
        MiningWorkflow(mapping(), agents, identity_mode="unit_fixture").run(
            DemoRequest(question="Synthetic question.")
        )
    )
    assert output.result.status == "failed"
    assert output.result.answer is None
    assert len(agents.calls) == 1
    assert "KPP_STATUS:failed" in agents.activities[0]


def test_changed_source_outcome_changes_executed_framework_result(specialist_responses):
    source = (ROOT / "source" / "foundry" / "workflow.yaml").read_text(encoding="utf-8")
    source = source.replace(
        "Please specify one topic: production, maintenance, stock, document lookup, or native "
        "knowledge retrieval.",
        "Choose a single synthetic topic.",
    )
    agents = FixtureAgents("clarification", specialist_responses)
    output = asyncio.run(
        MiningWorkflow(compile_source(source), agents, identity_mode="unit_fixture").run(
            DemoRequest(question="Tell me about MS01.")
        )
    )
    assert output.result.answer == "Choose a single synthetic topic."


def test_progress_identifies_running_agent_before_call_and_actual_tools_after_response(
    specialist_responses,
):
    updates = []

    class ObservedAgents(FixtureAgents):
        def invoke(self, name, question, version=None, *, conversation_id=None):
            phase = "router" if name == "kppdemo-router" else "specialist"
            assert any(
                item.phase == phase and item.status == "running" and item.agent_name == name
                for item in updates
            )
            return super().invoke(name, question, version, conversation_id=conversation_id)

    output = asyncio.run(
        MiningWorkflow(
            mapping(), ObservedAgents("mcp", specialist_responses), identity_mode="unit_fixture",
            on_progress=updates.append,
        ).run(DemoRequest(question="Show work orders for equipment TRK001."))
    )
    assert output.result.status == "success"
    route = next(item for item in updates if item.phase == "routing")
    assert route.route.value == "mcp"
    assert route.agent_name == "kppdemo-mcp"
    assert route.code_key == "switch"
    tool = next(item for item in updates if item.phase == "tool")
    assert tool.tool_name == "get_work_orders"
    assert tool.status == "done"
    assert updates[-1].phase == "workflow" and updates[-1].status == "done"


def test_blocked_progress_does_not_invent_specialist_or_tool_execution(specialist_responses):
    updates = []
    output = asyncio.run(
        MiningWorkflow(
            mapping(), FixtureAgents("work_iq", specialist_responses), identity_mode="unit_fixture",
            on_progress=updates.append,
        ).run(DemoRequest(question="Use Work IQ for the demo workplace handover."))
    )
    assert output.result.status == "blocked"
    assert not any(item.phase in ("specialist", "tool", "normalization") for item in updates)
    assert any(item.phase == "outcome" and item.status == "blocked" for item in updates)
    assert updates[-1].status == "blocked"
