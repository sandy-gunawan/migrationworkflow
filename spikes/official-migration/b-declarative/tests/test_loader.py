import asyncio
from pathlib import Path

import pytest
from agent_framework.declarative import WorkflowFactory
from fixture_agents import fixtures
from trial_support import SPECIALISTS, check_source

PROJECT = Path(__file__).resolve().parents[1]
ROUTES = [*SPECIALISTS, "fabric_iq", "work_iq", "clarification", "unsupported"]


@pytest.mark.parametrize("route", ROUTES)
def test_unchanged_source_executes_each_branch_in_official_loader(route):
    source = PROJECT / "source.workflow.yaml"
    check_source(source)
    agents, calls = fixtures(route)
    factory = WorkflowFactory(agents=agents, env_file=str(PROJECT.parent / ".env.example"))
    workflow = factory.create_workflow_from_yaml_path(source)
    execution = asyncio.run(workflow.run("Show work orders for equipment TRK001."))
    outputs = "\n".join(execution.get_outputs())
    assert f"KPP_ROUTE:{route}" in outputs
    expected_names = ["kppdemo-router"]
    if route in SPECIALISTS:
        expected_names.append(SPECIALISTS[route])
        assert f"OFFLINE FIXTURE ONLY: {SPECIALISTS[route]}" in outputs
    else:
        assert "KPP_STATUS:" in outputs
    assert [call["name"] for call in calls] == expected_names


def test_independent_official_greeting_yaml_loads_and_executes():
    workflow = WorkflowFactory(
        env_file=str(PROJECT.parent / ".env.example")
    ).create_workflow_from_yaml_path(PROJECT / "greeting.workflow.yaml")
    execution = asyncio.run(workflow.run({"name": "TRK001"}))
    assert execution.get_outputs() == ["Hello, TRK001!"]


def test_unapproved_source_fails_before_agent_binding(tmp_path):
    changed = tmp_path / "source.workflow.yaml"
    changed.write_text("name: unexpected\nactions: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="copied synthetic demo"):
        check_source(changed)
