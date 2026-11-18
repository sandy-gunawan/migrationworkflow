import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from demo_common.contracts import DemoResult
from tools.azure_job import compare_result

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("foundry", "maf", "logicapps")


def compare_cases(cases: list[dict], proofs: dict[str, dict]) -> dict:
    if set(proofs) != set(TARGETS) or not cases:
        raise RuntimeError("Three orchestrators and a nonempty corpus are required.")
    expected = {case["id"] for case in cases}
    if len(expected) != len(cases):
        raise RuntimeError("The comparison corpus contains duplicate case IDs.")
    indexed = {}
    for name in TARGETS:
        rows = proofs[name]["results"]
        indexed[name] = {row["case_id"]: row for row in rows}
        if len(rows) != len(expected) or set(indexed[name]) != expected:
            raise RuntimeError(f"{name} must contain every original case exactly once.")
    records = []
    counts = {name: Counter() for name in TARGETS}
    correct = Counter()
    latency = {name: [] for name in TARGETS}
    for case in cases:
        record = {"case_id": case["id"]}
        run_ids = set()
        for name in TARGETS:
            row = indexed[name][case["id"]]
            result = DemoResult.model_validate(row["result"]).model_dump(mode="json")
            run_ids.add(result["run_id"])
            checked = compare_result(case, result, 0)
            if not all(checked[key] for key in ("status_match", "facts_pass", "sources_pass")):
                raise RuntimeError(f"{name} factual/source/status parity failed: {case['id']}.")
            correct[name] += checked["route_match"]
            counts[name][result["status"]] += 1
            if isinstance(row.get("seconds"), (int, float)):
                latency[name].append(row["seconds"])
            headers = row.get("execution_headers", {})
            record[name] = {
                "route": result["route"], "status": result["status"],
                "route_match": checked["route_match"],
                "facts_pass": checked["facts_pass"], "sources_pass": checked["sources_pass"],
                "native_ids": row.get("response_id", headers.get("x-kpp-native-responses")),
                "logic_run_id": headers.get("x-kpp-logic-run"),
            }
        if len(run_ids) != 1:
            raise RuntimeError(f"The three results do not share the original run ID: {case['id']}.")
        record["run_id"] = next(iter(run_ids))
        records.append(record)
    accuracy = {name: correct[name] / len(cases) for name in TARGETS}
    if min(accuracy.values()) < 0.98:
        raise RuntimeError("At least one orchestrator falls below 98% routing accuracy.")
    return {
        "case_count": len(cases),
        "classification_accuracy": accuracy,
        "status_counts": {name: dict(value) for name, value in counts.items()},
        "latency": {
            name: {
                "total_case_seconds": round(sum(values), 2),
                "median_case_seconds": round(statistics.median(values), 2),
                "p95_case_seconds": round(
                    statistics.quantiles(values, n=100, method="inclusive")[94], 2
                ),
            } if len(values) == len(cases) and len(values) > 1 else "UNVERIFIED"
            for name, values in latency.items()
        },
        "comparison": (
            "actual facts, required source IDs, statuses, routing and correlation; not prose"
        ),
        "cases": records,
    }


def main() -> None:
    baseline = json.loads(
        (ROOT / "source" / "foundry" / "baseline-manifest.json").read_text(encoding="utf-8")
    )
    corpus = ROOT / baseline["corpus"]
    checks = [
        (corpus, baseline["corpus_sha256"]),
        (ROOT / baseline["source"]["canonical_export"], baseline["source"]["sha256"]),
        (ROOT / "src" / "demo_common" / "normalization.py", baseline["normalization_sha256"]),
        (ROOT / baseline["fabric_provider"], baseline["fabric_provider_sha256"]),
        (ROOT / "data" / "seed" / "mining.json", baseline["source"]["seed_sha256"]),
    ]
    for path, digest in checks:
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"A frozen input changed before comparison: {path.name}.")
    cases = json.loads(corpus.read_text(encoding="utf-8"))["cases"]
    if len(cases) != 50:
        raise RuntimeError("The final comparison requires the exact original50 corpus.")
    paths = {
        "foundry": ROOT / baseline["source_outcomes"],
        "maf": ROOT / "evidence" / "maf" / "gate.json",
        "logicapps": ROOT / "evidence" / "logicapps" / "gate.json",
    }
    proofs = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    fields = {
        "foundry": "native_source_50_case_core_baseline",
        "maf": "hosted_managed_identity_gate",
        "logicapps": "native_logic_apps_gate",
    }
    for name, proof in proofs.items():
        if proof.get(fields[name]) != "PASS" or proof["corpus_sha256"] != baseline["corpus_sha256"]:
            raise RuntimeError(f"{name} has no passed actual original50 gate.")
        source_hash = (
            proof["source"]["sha256"] if name == "foundry" else proof["source_sha256"]
        )
        if source_hash != baseline["source"]["sha256"]:
            raise RuntimeError(f"{name} ran against a different source.")
        for row in proof["results"]:
            headers = row.get("execution_headers", {})
            if name == "foundry":
                verified = bool(row.get("response_id", "").startswith("wfresp_"))
            elif name == "maf":
                verified = (
                    headers.get("x-kpp-outbound-auth") == "managed_identity"
                    and bool(headers.get("x-kpp-native-responses"))
                )
            else:
                verified = bool(headers.get("x-kpp-logic-run")) and bool(row.get("native_actions"))
            if not verified:
                raise RuntimeError(f"{name} lacks actual native execution/identity evidence.")
    report = {
        "demo_id": "48254cc6",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "approved_five_provider_core": "PASS",
        "full_seven_provider_status": "BLOCKED",
        "unavailable_provider_cases": [
            item["id"] for item in cases
            if item.get("full_scope_expected_status") == "success"
            and item["expected_status"] == "blocked"
        ],
        "source_sha256": baseline["source"]["sha256"],
        "corpus_sha256": baseline["corpus_sha256"],
        "normalization_contract_version": baseline["normalization_contract_version"],
        "source_evidence_note": (
            "Original actual native run IDs, re-normalized under frozen contract 2; "
            "not a claim of another source execution."
            if baseline.get("prior_manifest") else
            "Actual native source baseline executed under the frozen normalization contract."
        ),
        "known_runtime_observation": {
            "native_fabric_sql_connectivity_transient": "retained; unchanged full50 rerun passed",
            "failed_evidence": "evidence/logicapps/FAB06-native-no-rows.json",
            "partial_results_merged_into_pass": False,
        },
        "evidence": {name: str(path.relative_to(ROOT)) for name, path in paths.items()},
        **compare_cases(cases, proofs),
    }
    destination = ROOT / "evidence" / "comparison"
    destination.mkdir(exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
