import json
from pathlib import Path

import pytest
import yaml

from demo_common.logicapps import build_logic_workflow
from demo_common.migration import UnsupportedSource, compile_source

SOURCE = Path(__file__).resolve().parents[2] / "source" / "foundry" / "workflow.yaml"


def test_source_agent_version_mutation_changes_native_logic_apps_invocation():
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    source["trigger"]["actions"][2]["conditions"][1]["actions"][1]["agent"]["version"] = "9"
    mapping = compile_source(yaml.safe_dump(source, sort_keys=False))
    definition = build_logic_workflow(mapping)
    switch = definition["actions"]["Execute"]["actions"][mapping.condition_action_id]
    request = switch["cases"]["rest_api"]["actions"]["invoke_rest_api"]["inputs"]["body"]
    assert request["agent_reference"]["version"] == "9"
    assert request["conversation"] == "@body('create_conversation')?['id']"


def test_source_outcome_mutation_is_preserved_as_literal_not_a_wdl_expression():
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    source["trigger"]["actions"][2]["conditions"][7]["actions"][0]["activity"] = (
        "KPP_ROUTE:clarification\nKPP_STATUS:clarification\n@Choose one synthetic topic."
    )
    mapping = compile_source(yaml.safe_dump(source, sort_keys=False))
    definition = build_logic_workflow(mapping)
    switch = definition["actions"]["Execute"]["actions"][mapping.condition_action_id]
    result = switch["cases"]["clarification"]["actions"]["set_result_clarification"]
    assert result["inputs"]["value"]["answer"] == "@@Choose one synthetic topic."


def test_wdl_contains_direct_router_and_specialists_not_a_maf_orchestration_wrapper():
    mapping = compile_source(SOURCE.read_text(encoding="utf-8"))
    definition = build_logic_workflow(mapping)
    actions = definition["actions"]["Execute"]["actions"]
    assert actions[mapping.router_action_id]["inputs"]["body"]["agent_reference"] == {
        "type": "agent_reference", "name": mapping.router.name, "version": mapping.router.version,
    }
    switch = actions[mapping.condition_action_id]
    assert set(switch["cases"]) == {branch.route.value for branch in mapping.branches}
    for branch in mapping.branches:
        if branch.agent is None:
            continue
        native = switch["cases"][branch.route.value]["actions"][branch.action_id]
        assert native["inputs"]["body"]["agent_reference"]["name"] == branch.agent.name
        assert native["inputs"]["authentication"]["type"] == "ManagedServiceIdentity"
    encoded = json.dumps(definition)
    assert "/api/normalize-result" in encoded
    assert "/api/run" not in encoded


def test_source_id_collision_is_rejected_instead_of_overwriting_native_conversation_creation():
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    source["trigger"]["actions"][1]["id"] = "create_conversation"
    mapping = compile_source(yaml.safe_dump(source, sort_keys=False))
    with pytest.raises(UnsupportedSource, match="collide"):
        build_logic_workflow(mapping)
