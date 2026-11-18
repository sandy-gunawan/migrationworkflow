import json
import re
import time
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.contracts import RouterDecision
from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry, response_text, structured_response

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("mcp", "kppdemo-mcp", "Show work orders for equipment TRK001.", ["WO001", "TRK001"]),
    ("rest_api", "kppdemo-rest", "How much DIESEL stock is at MS01?", ["18000", "litres"]),
    (
        "knowledge",
        "kppdemo-knowledge",
        "Find the document reporting code for Copper Ridge MS01.",
        ["DEMO-COPPER-17", "DMO-DOC-01"],
    ),
    (
        "foundry_iq",
        "kppdemo-foundry-iq",
        "Use Foundry IQ native knowledge-base retrieval: what is the Copper Ridge reporting code?",
        ["DEMO-COPPER-17", "DMO-DOC-01"],
    ),
    (
        "fabric_data",
        "kppdemo-fabric-data",
        "What was production in tonnes for MS01 on November 1, 2026 for the day shift?",
        ["1250", "MS01"],
    ),
]


def main() -> None:
    directory = ROOT / "evidence" / "foundry"
    directory.mkdir(exist_ok=True, parents=True)
    proofs = []
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=300, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            for route, name, question, facts in CASES:
                decision = RouterDecision.model_validate(
                    structured_response(foundry.invoke("kppdemo-router", question))
                )
                if decision.route.value != route:
                    raise RuntimeError(f"Router chose {decision.route} rather than {route}.")
                started = time.monotonic()
                response = foundry.invoke(name, question)
                target = directory / f"{route}-{int(time.time())}-response.json"
                target.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
                text = response_text(response)
                normalized = re.sub(r"(?<=\d),(?=\d)", "", text).upper()
                kinds = [item["type"] for item in response["output"]]
                calls = [
                    item
                    for item in response["output"]
                    if item["type"].endswith("_call") and item.get("status") != "failed"
                ]
                if any(fact.upper() not in normalized for fact in facts) or not calls:
                    raise RuntimeError(
                        f"Specialist {route} lacks required facts or actual tool execution. "
                        f"Observed output types: {kinds}. Inspect {target.name}."
                    )
                record = {
                    "route": route,
                    "agent": name,
                    "version": response["agent_reference"]["version"],
                    "status": "PASS",
                    "facts": facts,
                    "output_types": kinds,
                    "seconds": round(time.monotonic() - started, 2),
                    "response_file": str(target.relative_to(ROOT)),
                    "response_id": response["id"],
                    "answer": text,
                }
                proofs.append(record)
                (directory / "specialist-progress.json").write_text(
                    json.dumps(proofs, indent=2) + "\n", encoding="utf-8"
                )
                print(f"Native Foundry specialist PASS: {route}", flush=True)
            for route, question in [
                ("fabric_iq", "Use the native Fabric IQ ontology to explain MineSite entities."),
                ("work_iq", "Use Work IQ to read the demo workplace handover."),
                ("clarification", "Tell me about MS01."),
                ("unsupported", "Delete records from the real production system."),
            ]:
                decision = RouterDecision.model_validate(
                    structured_response(foundry.invoke("kppdemo-router", question))
                )
                if decision.route.value != route:
                    raise RuntimeError(f"Router negative/blocked classification failed: {route}.")
        proof = {
            "demo_id": "48254cc6",
            "five_real_specialists": "PASS",
            "cases": proofs,
            "ontology": "BLOCKED_FeatureNotAvailable",
            "work_iq": "BLOCKED_separate_sandbox_not_supplied",
            "existing_business_system_access": False,
        }
        (directory / "specialist-gate.json").write_text(
            json.dumps(proof, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
