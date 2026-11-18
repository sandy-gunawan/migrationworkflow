import hashlib
import json
import re
import time
from contextlib import nullcontext
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.contracts import RouterDecision
from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry, DemoFoundryError
from tools.verify_foundry_specialists import CASES

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE_CASES = [
    ("fabric_iq", "Use the native Fabric IQ ontology to describe MineSite entities.", "blocked"),
    ("work_iq", "Use Work IQ for the demo workplace handover.", "blocked"),
    ("clarification", "Tell me about MS01.", "clarification"),
    ("unsupported", "Change a record in the real live business system.", "unsupported"),
]


def agent_text(response: dict, name: str) -> str:
    return "\n".join(
        part["text"]
        for item in response["output"]
        if item["type"] == "message" and item["agent_reference"]["name"] == name
        for part in item["content"]
        if part["type"] == "output_text"
    )


def main() -> None:
    source_path = ROOT / "config" / "source-workflow.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    exported = ROOT / source["export"]
    if hashlib.sha256(exported.read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("The native workflow export changed after read-back.")
    directory = ROOT / "evidence" / "foundry"
    cases = [(route, question, facts, "success") for route, _, question, facts in CASES]
    cases += [(route, question, [], status) for route, question, status in NEGATIVE_CASES]
    records = []
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=300, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        for route, question, facts, status in cases:
            path = directory / f"native-source-{route}-{int(time.time())}.json"
            manager = fabric.active_capacity() if route == "fabric_data" else nullcontext()
            with manager:
                try:
                    response = foundry.invoke(source["name"], question, source["version"])
                except DemoFoundryError as exc:
                    path.write_text(exc.detail + "\n", encoding="utf-8")
                    raise
            path.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
            if response["status"] != "completed" or response.get("error"):
                raise RuntimeError(f"Native source did not complete: {path.name}")
            router_name = source["agent_versions"]["router"]["name"]
            decision = RouterDecision.model_validate_json(agent_text(response, router_name))
            if decision.route.value != route:
                raise RuntimeError(f"Native router chose {decision.route} instead of {route}.")
            activity = agent_text(response, source["name"])
            if f"KPP_ROUTE:{route}" not in activity:
                raise RuntimeError("The native route activity is missing.")
            actions = [
                item["action_id"]
                for item in response["output"]
                if item["type"] == "workflow_action"
                and item["kind"] == "InvokeAzureAgent"
                and item["action_id"] != "classify_question"
            ]
            calls = [item for item in response["output"] if item["type"] == "mcp_call"]
            if status == "success":
                expected = source["agent_versions"][route]
                if actions != [f"invoke_{route}"] or not calls:
                    raise RuntimeError("Native workflow did not invoke exactly its specialist.")
                if any(
                    item.get("status") != "completed" or item.get("error")
                    for item in calls
                ):
                    raise RuntimeError("A real native tool call failed.")
                if any(item["agent_reference"] != {"type": "agent_reference", **expected}
                       for item in calls):
                    raise RuntimeError("Native workflow used an unexpected specialist version.")
                answer = agent_text(response, expected["name"])
                outputs = "\n".join(str(item.get("output", "")) for item in calls)
                for value in (answer, outputs):
                    normalized = re.sub(r"(?<=\d),(?=\d)", "", value).upper()
                    if any(fact.upper() not in normalized for fact in facts):
                        raise RuntimeError("Required facts are absent from real tool/answer data.")
            elif actions or calls or f"KPP_STATUS:{status}" not in activity:
                raise RuntimeError("Blocked/negative route dispatched data or hid its status.")
            records.append({
                "route": route,
                "status": status,
                "response_id": response["id"],
                "specialist_action_ids": actions,
                "tool_names": [item.get("name") for item in calls],
                "proof": str(path.relative_to(ROOT)),
                "facts": facts,
            })
            print(f"Native source PASS: {route} ({status})", flush=True)
    proof = {
        "demo_id": "48254cc6",
        "workflow": source["name"],
        "version": source["version"],
        "sha256": source["sha256"],
        "native_smoke": "PASS",
        "cases": records,
        "full_50_case_baseline": "PENDING",
        "ontology": "BLOCKED_FeatureNotAvailable",
        "work_iq": "BLOCKED_separate_sandbox_not_supplied",
    }
    (directory / "source-native-gate.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    source["runtime_status"] = "PASS_NINE_NATIVE_BRANCHES"
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    manifest_path = ROOT / "config" / "foundry-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_workflow"] = source
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
