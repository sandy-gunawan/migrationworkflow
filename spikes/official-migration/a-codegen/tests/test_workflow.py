import asyncio

import pytest
from fixture_agents import fixtures
from greeting import build_greeting
from trial_support import SPECIALISTS
from workflow import TERMINAL_ACTIVITIES, Run, build_workflow

QUESTION = "Show work orders for equipment TRK001."


@pytest.mark.parametrize("route", [*SPECIALISTS, *TERMINAL_ACTIVITIES])
def test_generated_graph_dispatches_exactly_the_source_branch(route):
    agents, calls = fixtures(route)
    graph = build_workflow(agents)
    execution = asyncio.run(graph.run(Run(QUESTION)))
    output = "\n".join(execution.get_outputs())
    assert f"KPP_ROUTE:{route}" in output
    expected_names = ["kppdemo-router"]
    if route in SPECIALISTS:
        expected_names.append(SPECIALISTS[route])
        assert f"OFFLINE FIXTURE ONLY: {SPECIALISTS[route]}" in output
    else:
        assert "KPP_STATUS:" in output
    assert [call["name"] for call in calls] == expected_names
    assert all(call["messages"] == [QUESTION] for call in calls)


def test_unknown_router_value_cannot_dispatch_a_specialist():
    agents, calls = fixtures("not-a-demo-route")
    execution = asyncio.run(build_workflow(agents).run(Run(QUESTION)))
    assert "KPP_STATUS:failed" in "\n".join(execution.get_outputs())
    assert [call["name"] for call in calls] == ["kppdemo-router"]


def test_other_source_codegen_greeting_executes_with_a_different_input():
    execution = asyncio.run(build_greeting().run("TRK001"))
    assert execution.get_outputs() == ["Hello, TRK001!"]
