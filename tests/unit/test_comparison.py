import copy

import pytest

from tools.compare_runs import compare_cases

CASES = [
    {"id": "MCP01", "route": "mcp", "expected_status": "success",
     "facts": ["WO001", "TRK001"], "sources": ["urn:kppdemo:maintenance/TRK001"]},
    {"id": "REST01", "route": "rest_api", "expected_status": "success",
     "facts": ["18000"], "sources": ["urn:kppdemo:stock/MS01/DIESEL"]},
]


def recorded():
    rows = [
        {
            "case_id": case["id"], "facts_pass": True,
            "result": {
                "run_id": f"00000000-0000-0000-0000-{index:012d}",
                "route": case["route"], "status": "success",
                "answer": "Retrieved " + " ".join(case["facts"]),
                "sources": [{"id": item, "kind": "demo_fixture"} for item in case["sources"]],
            },
        }
        for index, case in enumerate(CASES, 1)
    ]
    return {name: {"results": copy.deepcopy(rows)} for name in ("foundry", "maf", "logicapps")}


def test_comparison_uses_facts_sources_status_and_correlation_not_identical_prose():
    proofs = recorded()
    proofs["maf"]["results"][0]["result"]["answer"] = "WO001 belongs to TRK001."
    result = compare_cases(CASES, proofs)
    assert result["case_count"] == 2
    assert result["classification_accuracy"] == {"foundry": 1.0, "maf": 1.0, "logicapps": 1.0}


@pytest.mark.parametrize("defect", ["missing_case", "different_run_id", "false_fact_flag"])
def test_comparison_rejects_missing_uncorrelated_or_factually_wrong_evidence(defect):
    proofs = recorded()
    if defect == "missing_case":
        proofs["logicapps"]["results"].pop()
    elif defect == "different_run_id":
        proofs["maf"]["results"][0]["result"]["run_id"] = "00000000-0000-0000-0000-000000000099"
    else:
        proofs["logicapps"]["results"][0]["result"]["answer"] = "No retrieved work-order facts."
    with pytest.raises(RuntimeError):
        compare_cases(CASES, proofs)
