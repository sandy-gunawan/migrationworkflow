import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.contracts import DemoRequest, Route
from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry, DemoFoundryError
from demo_common.normalization import normalize_source_result

ROOT = Path(__file__).resolve().parents[1]


def canonical_source_id(value: str) -> str:
    prefix = "urn:kppdemo:knowledge/"
    return value.removeprefix(prefix) if value.startswith(prefix) else value


def main() -> None:
    corpus_path = ROOT / "tests" / "golden" / "cases.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    cases = corpus["cases"]
    positive = Counter(item["route"] for item in cases if item["intent"] == "positive")
    if (
        corpus["demo_id"] != "48254cc6"
        or len(cases) != 50
        or len({item["id"] for item in cases}) != 50
        or positive != {
            route.value: 6
            for route in Route
            if route not in (Route.CLARIFICATION, Route.UNSUPPORTED)
        }
        or Counter(item["intent"] for item in cases)
        != {"positive": 42, "clarification": 4, "unsupported": 4}
    ):
        raise RuntimeError("The corpus must retain all original 50 routing cases.")
    source_path = ROOT / "config" / "source-workflow.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source["runtime_status"] != "PASS_NINE_NATIVE_BRANCHES":
        raise RuntimeError("The nine native source branches must pass before the baseline.")
    exported = ROOT / source["export"]
    if hashlib.sha256(exported.read_bytes()).hexdigest() != source["sha256"]:
        raise RuntimeError("The actual source export changed before baseline execution.")
    directory = ROOT / "evidence" / "foundry" / f"baseline-{int(time.time())}"
    directory.mkdir(parents=True)
    provider_path = ROOT / "config" / "fabric-us-data-agent.json"
    provider_sha256 = hashlib.sha256(provider_path.read_bytes()).hexdigest()
    records = []
    started = time.monotonic()
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=300, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            for case in cases:
                if time.monotonic() - started > 1800:
                    raise RuntimeError("The source baseline exceeded its 30-minute budget.")
                request = DemoRequest(question=case["question"])
                raw_path = directory / f"{case['id']}.json"
                case_started = time.monotonic()
                try:
                    response = foundry.invoke(
                        source["name"], request.question, source["version"]
                    )
                except DemoFoundryError as exc:
                    raw_path.write_text(exc.detail + "\n", encoding="utf-8")
                    raise
                raw_path.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
                result = normalize_source_result(response, request.run_id, source)
                factual = json.dumps({
                    "answer": result.answer,
                    "sources": [item.model_dump() for item in result.sources],
                })
                normalized = re.sub(r"(?<=\d),(?=\d)", "", factual).upper()
                references = {canonical_source_id(item.id) for item in result.sources}
                facts_pass = all(item.upper() in normalized for item in case["facts"])
                sources_pass = all(
                    canonical_source_id(item) in references for item in case["sources"]
                )
                record = {
                    "case_id": case["id"],
                    "expected_route": case["route"],
                    "route_match": result.route.value == case["route"],
                    "status_match": result.status == case["expected_status"],
                    "facts_pass": facts_pass,
                    "sources_pass": sources_pass,
                    "seconds": round(time.monotonic() - case_started, 2),
                    "response_id": response["id"],
                    "raw_response": str(raw_path.relative_to(ROOT)),
                    "result": result.model_dump(mode="json"),
                }
                records.append(record)
                (directory / "progress.json").write_text(
                    json.dumps(records, indent=2) + "\n", encoding="utf-8"
                )
                print(
                    f"Source {case['id']}: route={result.route} status={result.status} "
                    f"match={record['route_match']} facts={facts_pass} sources={sources_pass}",
                    flush=True,
                )
                if not record["status_match"] or not facts_pass or not sources_pass:
                    raise RuntimeError(
                        f"Native source factual/status/source gate failed: {case['id']}"
                    )
    classification = sum(item["route_match"] for item in records) / len(records)
    if classification < 0.98:
        raise RuntimeError(f"Native source classification accuracy is only {classification:.1%}.")
    if hashlib.sha256(provider_path.read_bytes()).hexdigest() != provider_sha256:
        raise RuntimeError("The native Fabric provider configuration changed during the baseline.")
    proof = {
        "demo_id": "48254cc6",
        "native_source_50_case_core_baseline": "PASS",
        "normalization_contract_version": 2,
        "classification_accuracy": classification,
        "case_count": len(records),
        "actual_status_counts": dict(Counter(item["result"]["status"] for item in records)),
        "full_seven_provider_status": "BLOCKED",
        "unavailable_provider_cases": [
            item["id"] for item in cases if item["expected_status"] == "blocked"
        ],
        "source": source,
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "normalization_sha256": hashlib.sha256(
            (ROOT / "src" / "demo_common" / "normalization.py").read_bytes()
        ).hexdigest(),
        "fabric_provider_sha256": provider_sha256,
        "results": records,
    }
    proof_path = ROOT / "evidence" / "foundry" / "source-baseline.json"
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    canonical = ROOT / "source" / "foundry" / "workflow.yaml"
    canonical.write_bytes(exported.read_bytes())
    baseline = {
        "demo_id": "48254cc6",
        "source": {**source, "canonical_export": str(canonical.relative_to(ROOT))},
        "corpus": str(corpus_path.relative_to(ROOT)),
        "corpus_sha256": proof["corpus_sha256"],
        "normalization_sha256": proof["normalization_sha256"],
        "normalization_contract_version": proof["normalization_contract_version"],
        "fabric_provider": str(provider_path.relative_to(ROOT)),
        "fabric_provider_sha256": provider_sha256,
        "result_schema": "contracts/demo.schema.json",
        "source_outcomes": str(proof_path.relative_to(ROOT)),
        "core_status": "PASS",
        "full_seven_provider_status": "BLOCKED",
    }
    (ROOT / "source" / "foundry" / "baseline-manifest.json").write_text(
        json.dumps(baseline, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in proof.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
