import json
from uuid import uuid4

import pytest

from demo_common.contracts import Route
from demo_common.fabric import US_WORKSPACE
from demo_common.normalization import (
    ToolEvidenceError,
    normalize_source_result,
    normalize_specialist_result,
)

BINDING = {"type": "agent_reference", "name": "kppdemo-mcp", "version": "1"}
FIXTURE = {
    "demo_id": "48254cc6",
    "synthetic": True,
    "data": [{"order_id": "WO001", "equipment_id": "TRK001"}],
    "sources": [{"kind": "demo_fixture", "id": "urn:kppdemo:maintenance/TRK001"}],
}


def response(output, *, error=None):
    return {
        "status": "completed",
        "output": [
            {
                "type": "mcp_call",
                "status": "completed",
                "error": error,
                "agent_reference": BINDING,
                "output": output,
                "name": "get_work_orders",
            },
            {
                "type": "message",
                "agent_reference": BINDING,
                "content": [{"type": "output_text", "text": "WO001 is open for TRK001."}],
            },
        ],
    }


def normalize(value):
    return normalize_specialist_result(value, Route.MCP, uuid4(), BINDING)


def test_real_fixture_and_structured_mirror_produce_one_grounded_reference():
    raw = json.dumps(FIXTURE) + "\n" + json.dumps({"structuredResponse": FIXTURE})
    result = normalize(response(raw))
    assert result.status == "success"
    assert result.answer == "WO001 is open for TRK001."
    assert [item.id for item in result.sources] == ["urn:kppdemo:maintenance/TRK001"]


@pytest.mark.parametrize(
    "raw",
    [
        "Error executing tool get_work_orders: Synthetic equipment was not found.",
        '{"demo_id":"unrelated","synthetic":false,"sources":[]}',
    ],
)
def test_tool_errors_or_out_of_scope_data_cannot_become_successful_answers(raw):
    result = normalize(response(raw))
    assert result.status == "failed"
    assert result.answer is None
    assert result.error
    assert not result.sources


def test_a_model_answer_without_an_actual_tool_call_is_not_grounded():
    value = response(json.dumps(FIXTURE))
    value["output"] = value["output"][1:]
    assert normalize(value).status == "failed"


def test_tool_execution_by_an_unexpected_agent_version_is_rejected():
    value = response(json.dumps(FIXTURE))
    value["output"][0]["agent_reference"] = {**BINDING, "version": "2"}
    assert normalize(value).status == "failed"


def test_native_tool_errors_are_not_hidden_by_a_completed_model_response():
    result = normalize(response("{}", error={"code": "unauthorized"}))
    assert result.status == "failed"
    assert result.answer is None


def source_response(extra_output=None):
    router = {"type": "agent_reference", "name": "kppdemo-router", "version": "1"}
    workflow = {"type": "agent_reference", "name": "kppdemo-mining-workflow", "version": "2"}
    return {
        "status": "completed",
        "output": [
            {
                "type": "workflow_action",
                "kind": "InvokeAzureAgent",
                "status": "completed",
                "agent_reference": workflow,
            },
            {
                "type": "message",
                "agent_reference": router,
                "content": [{"type": "output_text", "text": '{"route":"work_iq"}'}],
            },
            {
                "type": "message",
                "agent_reference": workflow,
                "content": [{
                    "type": "output_text",
                    "text": "KPP_ROUTE:work_iq\nKPP_STATUS:blocked\nWork IQ sandbox is missing.",
                }],
            },
            *(extra_output or []),
        ],
    }


SOURCE = {
    "name": "kppdemo-mining-workflow",
    "version": "2",
    "agent_versions": {"router": {"name": "kppdemo-router", "version": "1"}},
}


def test_native_blocked_activity_is_preserved_without_an_invented_answer():
    result = normalize_source_result(source_response(), uuid4(), SOURCE)
    assert result.route == Route.WORK_IQ
    assert result.status == "blocked"
    assert result.answer is None
    assert result.error == "Work IQ sandbox is missing."


def test_native_blocked_label_cannot_hide_actual_business_tool_dispatch():
    extra = [{
        "type": "mcp_call",
        "status": "completed",
        "agent_reference": BINDING,
        "output": json.dumps(FIXTURE),
    }]
    with pytest.raises(ToolEvidenceError, match="dispatched"):
        normalize_source_result(source_response(extra), uuid4(), SOURCE)


@pytest.mark.parametrize(
    "native_answer",
    [
        "I wasn't able to retrieve any matching data from the mining dataset.",
        '{"status":"not_found","site_id":"MS01","tonnes":null}',
    ],
)
def test_native_fabric_no_data_with_a_citation_document_is_still_a_failure(native_answer):
    binding = {"name": "kppdemo-fabric-data", "version": "1"}
    value = response(json.dumps({
        "response": native_answer,
        "documents": [{
            "title": "kpp_mining_data_us_48254cc6",
            "url": f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/demo",
        }],
    }))
    for item in value["output"]:
        item["agent_reference"] = binding
    value["output"][0]["name"] = "DataAgent_kpp_mining_data_us_48254cc6"
    value["output"][1]["content"][0]["text"] = "No matching production rows were retrieved."
    result = normalize_specialist_result(value, Route.FABRIC_DATA, uuid4(), binding)
    assert result.status == "failed"
    assert result.answer is None


def test_native_fabric_requires_retrieved_numeric_production_evidence():
    binding = {"name": "kppdemo-fabric-data", "version": "1"}
    record = {
        "status": "success",
        "site_id": "MS01",
        "date": "2026-11-01",
        "shift": "day",
        "tonnes": 1250,
        "source_table": "dbo.production",
    }
    native_text = (
        json.dumps(record)
        + "\n\nMS01 produced 1,250 tonnes.\n"
        + json.dumps({"structuredResponse": {"artifactName": "kpp_mining_data_us_48254cc6"}})
    )
    value = response(json.dumps({
        "response": native_text,
        "documents": [{
            "title": "kpp_mining_data_us_48254cc6",
            "url": f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/demo",
        }],
    }))
    for item in value["output"]:
        item["agent_reference"] = binding
    value["output"][0]["name"] = "DataAgent_kpp_mining_data_us_48254cc6"
    value["output"][1]["content"][0]["text"] = "MS01 produced 1,250 tonnes."
    assert normalize_specialist_result(
        value, Route.FABRIC_DATA, uuid4(), binding
    ).status == "success"
    record["tonnes"] = None
    value["output"][0]["output"] = json.dumps({
        "response": json.dumps(record),
        "documents": [{
            "title": "kpp_mining_data_us_48254cc6",
            "url": f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/demo",
        }],
    })
    assert normalize_specialist_result(
        value, Route.FABRIC_DATA, uuid4(), binding
    ).status == "failed"


@pytest.mark.parametrize("model_answer", ["1250 tonnes.", "9999 tonnes."])
def test_fabric_answer_is_rendered_from_verified_row_not_incomplete_or_wrong_prose(model_answer):
    binding = {"name": "kppdemo-fabric-data", "version": "1"}
    record = {
        "status": "success", "site_id": "MS01", "date": "2026-11-01",
        "shift": "day", "tonnes": 1250, "source_table": "dbo.production",
    }
    value = response(json.dumps({
        "response": json.dumps(record),
        "documents": [{
            "title": "kpp_mining_data_us_48254cc6",
            "url": f"https://app.fabric.microsoft.com/groups/{US_WORKSPACE}/aiskills/demo",
        }],
    }))
    for item in value["output"]:
        item["agent_reference"] = binding
    value["output"][1]["content"][0]["text"] = model_answer
    result = normalize_specialist_result(value, Route.FABRIC_DATA, uuid4(), binding)
    assert result.status == "success"
    assert all(fact in result.answer for fact in ("MS01", "2026-11-01", "day", "1250"))
    assert "9999" not in result.answer
