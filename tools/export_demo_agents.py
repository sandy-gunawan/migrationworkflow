import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter

from demo_common.contracts import DemoRequest, DemoResult, RouterDecision
from demo_common.fabric import SUBSCRIPTION
from demo_common.foundry import DemoFoundry, structured_response

ROOT = Path(__file__).resolve().parents[1]
AGENTS = {
    "kppdemo-router": "router",
    "kppdemo-mcp": "mcp",
    "kppdemo-fabric-data": "fabric_data",
    "kppdemo-rest": "rest_api",
    "kppdemo-knowledge": "knowledge",
    "kppdemo-foundry-iq": "foundry_iq",
}
ROUTER_CASES = [
    ("mcp", "Show work orders for TRK001."),
    ("rest_api", "How much DIESEL stock is at MS01?"),
    ("fabric_data", "What was production tonnage for MS01 on November 1, 2026 day shift?"),
    ("knowledge", "Find the document reporting code for Copper Ridge."),
    ("foundry_iq", "Use Foundry IQ native knowledge-base retrieval for the Copper Ridge code."),
    ("fabric_iq", "Use the Fabric IQ ontology to describe MineSite entities."),
    ("work_iq", "Use Work IQ for the demo workplace handover."),
    ("clarification", "Give both the production output and stock quantities for MS01."),
    ("unsupported", "Change a record in the real live business system."),
]


def specialist_verified(gate: dict | None, name: str, version: str) -> bool:
    if gate is None:
        return False
    if gate["demo_id"] != "48254cc6":
        raise ValueError("Specialist evidence belongs to a different demo.")
    return gate["five_real_specialists"] == "PASS" and any(
        case["agent"] == name and case["version"] == version and case["status"] == "PASS"
        for case in gate["cases"]
    )


def main() -> None:
    directory = ROOT / "source" / "foundry" / "exported-agents"
    directory.mkdir(exist_ok=True, parents=True)
    gate_path = ROOT / "evidence" / "foundry" / "specialist-gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else None
    manifest_path = ROOT / "config" / "foundry-manifest.json"
    previous = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    )
    receipts = {}
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=120, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        for name, route in AGENTS.items():
            saved = foundry.request("GET", f"/agents/{name}")
            latest = saved["versions"]["latest"]
            if latest["metadata"].get("demo_id") != "48254cc6":
                raise RuntimeError("Refusing to export an unrelated agent.")
            if name == "kppdemo-router" and latest["definition"]["tools"]:
                raise RuntimeError("Router must have no data tools.")
            target = directory / f"{name}.v{latest['version']}.json"
            target.write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
            receipts[route] = {
                "name": name,
                "version": latest["version"],
                "export": str(target.relative_to(ROOT)),
                "integration_status": (
                    "CLASSIFICATION_ONLY"
                    if route == "router"
                    else "PASS_REAL_TOOL_CALL"
                    if specialist_verified(gate, name, latest["version"])
                    else "PENDING_RUNTIME_VERIFICATION"
                ),
            }
        cases = []
        for expected, question in ROUTER_CASES:
            response = foundry.invoke("kppdemo-router", question, receipts["router"]["version"])
            actual = RouterDecision.model_validate(structured_response(response)).route.value
            cases.append({"expected": expected, "actual": actual, "response_id": response["id"]})
            if actual != expected:
                raise RuntimeError(f"Router smoke failed: expected {expected}, got {actual}.")
            print(f"Router classification PASS: {expected}", flush=True)
    proof = {
        "demo_id": "48254cc6",
        "agents": receipts,
        "router_smoke": cases,
        "router_smoke_status": "PASS",
        "full_five_specialist_gate": (
            "PASS"
            if all(
                receipt["integration_status"] == "PASS_REAL_TOOL_CALL"
                for route, receipt in receipts.items()
                if route != "router"
            )
            else "PENDING_RUNTIME_VERIFICATION"
        ),
        "source_workflow": previous.get("source_workflow", "NOT_CREATED"),
        "fabric_iq": "BLOCKED_FeatureNotAvailable",
        "work_iq": "BLOCKED_separate_sandbox_not_supplied",
    }
    manifest_path.write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    schema = TypeAdapter(DemoRequest | DemoResult).json_schema()
    Draft202012Validator.check_schema(schema)
    (ROOT / "contracts" / "demo.schema.json").write_text(
        json.dumps(schema, indent=2) + "\n", encoding="utf-8"
    )
    print("Exported six versioned demo definitions; integration status matches runtime evidence.")


if __name__ == "__main__":
    main()
