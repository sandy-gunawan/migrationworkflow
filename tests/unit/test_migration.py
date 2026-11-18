import hashlib
from pathlib import Path

import pytest
import yaml

from demo_common.migration import UnsupportedSource, compile_source

SOURCE = Path(__file__).resolve().parents[2] / "source" / "foundry" / "workflow.yaml"


def test_actual_native_source_preserves_all_dispatch_and_non_dispatch_branches():
    text = SOURCE.read_text(encoding="utf-8")
    mapping = compile_source(text)
    assert mapping.source_sha256 == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert len(mapping.branches) == 9
    assert sum(branch.agent is not None for branch in mapping.branches) == 5
    work = next(branch for branch in mapping.branches if branch.route.value == "work_iq")
    assert work.agent is None
    assert work.outcome.status == "blocked"
    assert "sandbox" in work.outcome.text
    assert mapping.fallback.status == "failed"


def test_changing_source_agent_version_changes_the_generated_binding():
    value = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    branch = value["trigger"]["actions"][2]["conditions"][1]
    branch["actions"][1]["agent"]["version"] = "9"
    changed = compile_source(yaml.safe_dump(value, sort_keys=False))
    rest = next(branch for branch in changed.branches if branch.route.value == "rest_api")
    assert rest.agent.version == "9"


def test_changing_a_source_outcome_changes_target_behavior_not_just_a_hash():
    value = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    branch = value["trigger"]["actions"][2]["conditions"][7]
    branch["actions"][0]["activity"] = (
        "KPP_ROUTE:clarification\nKPP_STATUS:clarification\nChoose one synthetic topic."
    )
    changed = compile_source(yaml.safe_dump(value, sort_keys=False))
    clarification = next(
        branch for branch in changed.branches if branch.route.value == "clarification"
    )
    assert clarification.outcome.text == "Choose one synthetic topic."


@pytest.mark.parametrize("mutation", ["unknown_action", "unknown_agent", "duplicate_route"])
def test_unsupported_source_semantics_are_rejected_instead_of_silently_dropped(mutation):
    value = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    actions = value["trigger"]["actions"]
    if mutation == "unknown_action":
        actions.insert(1, {"kind": "HttpRequest", "id": "unsafe_external_call"})
    elif mutation == "unknown_agent":
        actions[1]["agent"]["name"] = "existing-client-agent"
    else:
        actions[2]["conditions"][1]["condition"] = actions[2]["conditions"][0]["condition"]
    with pytest.raises(UnsupportedSource):
        compile_source(yaml.safe_dump(value, sort_keys=False))
