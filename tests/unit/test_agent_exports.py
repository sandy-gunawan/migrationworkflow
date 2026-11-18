import pytest

from tools.export_demo_agents import specialist_verified


def gate(version="4", status="PASS"):
    return {
        "demo_id": "48254cc6",
        "five_real_specialists": "PASS",
        "cases": [{"agent": "kppdemo-rest", "version": version, "status": status}],
    }


def test_runtime_evidence_verifies_only_the_exact_executed_agent_version():
    proof = gate()
    assert specialist_verified(proof, "kppdemo-rest", "4")
    assert not specialist_verified(proof, "kppdemo-rest", "5")
    assert not specialist_verified(proof, "kppdemo-knowledge", "4")


def test_failed_or_missing_runtime_evidence_cannot_be_exported_as_verified():
    assert not specialist_verified(gate(status="FAIL"), "kppdemo-rest", "4")
    assert not specialist_verified(None, "kppdemo-rest", "4")
    proof = gate()
    proof["five_real_specialists"] = "FAIL"
    assert not specialist_verified(proof, "kppdemo-rest", "4")


def test_runtime_evidence_from_another_demo_is_rejected():
    proof = gate()
    proof["demo_id"] = "unrelated-demo"
    with pytest.raises(ValueError, match="different demo"):
        specialist_verified(proof, "kppdemo-rest", "4")
