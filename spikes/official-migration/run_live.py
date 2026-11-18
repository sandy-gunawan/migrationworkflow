import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential
from trial_support import ROOT

HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence" / "official-migration"
CASE_IDS = (
    "MCP01",
    "REST01",
    "KNOW01",
    "FIQ01",
    "ONTO01",
    "WORK01",
    "CLAR01",
    "UNSUP03",
)


def run_case(implementation: str, case: dict) -> dict:
    project = HERE / ("a-codegen" if implementation == "A" else "b-declarative")
    python = project / ".venv" / "Scripts" / "python.exe"
    stem = f"{implementation.lower()}-{case['id'].lower()}"
    report_path = EVIDENCE / f"{stem}.json"
    command = [
        str(python),
        "-X",
        "utf8",
        str(project / "main.py"),
        "--question",
        case["question"],
        "--report",
        str(report_path),
    ]
    if implementation == "B":
        command.append("--native-context")
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=project, capture_output=True, text=True, encoding="utf-8", timeout=360
    )
    (EVIDENCE / f"{stem}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"{implementation}/{case['id']} exited {completed.returncode}; "
            f"see {stem}.log\n{completed.stderr[-3000:]}"
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["route"] == case["route"], (implementation, case["id"], report["route"])
    assert report["result"]["status"] == case["expected_status"], (implementation, case["id"])
    answer = report["result"]["answer"].replace(",", "")
    assert all(fact in answer for fact in case["facts"]), (implementation, case["id"], answer)
    sources = json.dumps(report["result"].get("sources", []))
    assert all(source in sources for source in case["sources"]), (
        implementation,
        case["id"],
        sources,
    )
    assert report["conversation_parity"] == "PASS", (implementation, case["id"])
    item = {
        "implementation": implementation,
        "case_id": case["id"],
        "route": report["route"],
        "status": report["result"]["status"],
        "exit_code": completed.returncode,
        "seconds": round(time.monotonic() - started, 2),
        "report": report_path.name,
        "conversation_checks": report["native_context"]["checks"],
        "agent_calls": [
            {"name": call["agent"], "version": call["version"], "response_id": call["native"]["id"]}
            for call in report["calls"]
        ],
    }
    print(json.dumps(item), flush=True)
    return item


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", choices=("A", "B", "both"), default="both")
    parser.add_argument("--include-fabric", action="store_true")
    parser.add_argument("--cases", nargs="+", choices=CASE_IDS, default=CASE_IDS)
    args = parser.parse_args()
    cases = json.loads((ROOT / "tests" / "golden" / "cases.json").read_text(encoding="utf-8"))
    by_id = {case["id"]: case for case in cases["cases"]}
    implementations = ("A", "B") if args.path == "both" else (args.path,)
    results = []
    for case_id in args.cases:
        for implementation in implementations:
            results.append(run_case(implementation, by_id[case_id]))
    if args.include_fabric:
        from demo_common.fabric import US_WORKSPACE, DemoFabric

        credential = AzureCliCredential()
        try:
            with httpx.Client(timeout=120) as client:
                fabric = DemoFabric(credential, client, EVIDENCE, workspace=US_WORKSPACE)
                before = fabric.capacity()
                if before["properties"]["state"] != "Paused":
                    raise RuntimeError(
                        "The owned US F2 is already in use; refusing to change its state."
                    )
                with fabric.active_capacity():
                    for implementation in implementations:
                        results.append(run_case(implementation, by_id["FAB01"]))
                after = fabric.capacity()
                assert after["properties"]["state"] == "Paused"
                assert after["properties"]["overage"] == "Disabled"
        finally:
            credential.close()
    summary = {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "PASS",
        "scope": "one original golden case per included route, not all original-50 cases",
        "paths": list(implementations),
        "fabric_included": args.include_fabric,
        "cases": results,
        "ui_codegen_handoff": "NOT_SENT_CONFIRMATION_UNAVAILABLE",
    }
    name = f"live-{args.path.lower()}.json"
    (EVIDENCE / name).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(results)} live cases; {name}", flush=True)


if __name__ == "__main__":
    main()
