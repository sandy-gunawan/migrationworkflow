import hashlib
import json
import re
from pathlib import Path
from uuid import UUID

from demo_common.normalization import normalize_source_result
from tools.run_source_baseline import canonical_source_id

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    original_path = ROOT / "evidence" / "foundry" / "source-baseline.v1.json"
    original = json.loads(original_path.read_text(encoding="utf-8"))
    baseline_path = ROOT / "source" / "foundry" / "baseline-manifest.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    corpus_path = ROOT / baseline["corpus"]
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != original["corpus_sha256"]:
        raise RuntimeError("The original golden questions/expectations changed.")
    cases = {
        item["id"]: item
        for item in json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]
    }
    results = []
    for previous in original["results"]:
        response = json.loads((ROOT / previous["raw_response"]).read_text(encoding="utf-8"))
        if response["id"] != previous["response_id"]:
            raise RuntimeError("The retained actual native response identifier changed.")
        result = normalize_source_result(
            response, UUID(previous["result"]["run_id"]), original["source"]
        )
        case = cases[previous["case_id"]]
        text = json.dumps({
            "answer": result.answer,
            "sources": [item.model_dump() for item in result.sources],
        })
        facts = re.sub(r"(?<=\d),(?=\d)", "", text).upper()
        references = {canonical_source_id(item.id) for item in result.sources}
        if (
            result.route.value != case["route"]
            or result.status != case["expected_status"]
            or not all(item.upper() in facts for item in case["facts"])
            or not all(canonical_source_id(item) in references for item in case["sources"])
        ):
            raise RuntimeError(f"Actual source evidence was not preserved: {previous['case_id']}")
        results.append({**previous, "result": result.model_dump(mode="json")})
    if len(results) != 50:
        raise RuntimeError("All 50 original native executions must be retained.")
    digest = hashlib.sha256(
        (ROOT / "src" / "demo_common" / "normalization.py").read_bytes()
    ).hexdigest()
    proof = {
        **original,
        "normalization_sha256": digest,
        "normalization_contract_version": 2,
        "normalization_replay": "50_retained_actual_native_responses_no_new_execution_claim",
        "prior_normalization": "source/foundry/normalization.v1.py",
        "results": results,
    }
    (ROOT / "evidence" / "foundry" / "source-baseline.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    baseline["normalization_sha256"] = digest
    baseline["normalization_contract_version"] = 2
    baseline["prior_manifest"] = "source/foundry/baseline-manifest.v1.json"
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "retained_native_runs": len(results),
        "source_sha256": baseline["source"]["sha256"],
        "corpus_sha256": baseline["corpus_sha256"],
        "normalization_sha256": digest,
        "normalization_contract_version": 2,
        "new_native_executions": 0,
        "facts_sources_statuses_preserved": True,
    }, indent=2))


if __name__ == "__main__":
    main()
