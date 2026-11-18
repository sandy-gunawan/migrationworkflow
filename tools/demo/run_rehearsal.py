import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx
from azure.identity import AzureCliCredential

from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry
from demo_common.normalization import normalize_source_result
from tools.azure_job import compare_result
from tools.compare_runs import compare_cases

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="Fresh, provider-validated helper run ID.")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{14}", args.run_id):
        raise ValueError("Use the exact 14-digit validated helper run ID.")
    started = time.monotonic()
    baseline = json.loads((ROOT / "source" / "foundry" / "baseline-manifest.json").read_text())
    source = baseline["source"]
    actual50 = json.loads((ROOT / baseline["source_outcomes"]).read_text())
    run_ids = {row["case_id"]: row["result"]["run_id"] for row in actual50["results"]}
    corpus_path = ROOT / baseline["corpus"]
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != baseline["corpus_sha256"]:
        raise RuntimeError("The rehearsal corpus differs from the original50.")
    selected = {}
    for case in json.loads(corpus_path.read_text())["cases"]:
        selected.setdefault(case["route"], case)
    if len(selected) != 9:
        raise RuntimeError("All nine representative source routes are required.")
    directory = ROOT / "evidence" / "rehearsal" / args.run_id
    directory.mkdir(parents=True)
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=300, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        native = foundry.request("GET", f"/agents/{source['name']}/versions/{source['version']}")
        exported = native["definition"]["workflow"].encode("utf-8")
        if hashlib.sha256(exported).hexdigest() != source["sha256"]:
            raise RuntimeError("The live native version differs from the frozen source export.")
        (directory / "native-export.workflow.yaml").write_bytes(exported)
        for target in ("maf", "logicapps"):
            subprocess.run(
                [sys.executable, "-m", "tools.migrate_workflow", "--target", target],
                cwd=ROOT, check=True,
            )
        records = []
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            for case in selected.values():
                case_started = time.monotonic()
                raw = foundry.invoke(source["name"], case["question"], source["version"])
                (directory / f"source-{case['id']}.json").write_text(
                    json.dumps(raw, indent=2) + "\n", encoding="utf-8",
                )
                result = normalize_source_result(raw, UUID(run_ids[case["id"]]), source)
                checked = compare_result(
                    case, result.model_dump(mode="json"), time.monotonic() - case_started,
                )
                if not all(checked[key] for key in (
                    "route_match", "status_match", "facts_pass", "sources_pass",
                )):
                    raise RuntimeError(f"Native source rehearsal failed: {case['id']}.")
                checked["response_id"] = raw["id"]
                records.append(checked)
                print(f"Rehearsal native source {case['id']}: {result.status}", flush=True)
    subprocess.run(
        [
            sys.executable, "-m", "tools.run_azure_job", "--mode", "rehearse-core",
            "--run-id", args.run_id,
        ],
        cwd=ROOT, check=True,
    )
    remote = json.loads((ROOT / "evidence" / "rehearsal" / "remote.json").read_text())
    if remote["remote_core_rehearsal"] != "PASS" or not remote["job_name"].endswith(args.run_id):
        raise RuntimeError("The actual remote rehearsal does not match this run.")
    proofs = {
        "foundry": {"results": records},
        **{
            name: {"results": [row for row in remote["results"] if row["orchestrator"] == name]}
            for name in ("maf", "logicapps")
        },
    }
    comparison = compare_cases(list(selected.values()), proofs)
    elapsed = round(time.monotonic() - started, 2)
    if elapsed > 1800:
        raise RuntimeError("The live core rehearsal exceeded its 30-minute target.")
    proof = {
        "demo_id": "48254cc6", "live_core_rehearsal": "PASS",
        "wall_seconds": elapsed, "under_30_minutes": True,
        "live_requests": 27, "cases_per_path": 9,
        "actual_source_export_hash_verified": source["sha256"],
        "both_targets_regenerated_from_source": True,
        "existing_tested_targets_invoked_without_semantic_change": True,
        "new_or_changed_client_resources": False,
        "full_seven_provider_status": "BLOCKED",
        **comparison,
    }
    (ROOT / "evidence" / "rehearsal" / "report.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in proof.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
