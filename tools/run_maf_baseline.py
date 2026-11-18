import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.contracts import DemoResult
from demo_common.environment import ENVIRONMENT
from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from tools.run_source_baseline import canonical_source_id

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    baseline = json.loads(
        (ROOT / "source" / "foundry" / "baseline-manifest.json").read_text(encoding="utf-8")
    )
    corpus_path = ROOT / baseline["corpus"]
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != baseline["corpus_sha256"]:
        raise RuntimeError("The frozen comparison corpus changed.")
    cases = json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]
    native = json.loads((ROOT / baseline["source_outcomes"]).read_text(encoding="utf-8"))
    source_results = {item["case_id"]: item for item in native["results"]}
    directory = ROOT / "evidence" / "maf" / f"local-baseline-{int(time.time())}"
    directory.mkdir(parents=True)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    key = secrets.token_urlsafe(48)
    environment = {
        **os.environ,
        "DEMO_TENANT_ID": ENVIRONMENT.tenant_id,
        "DEMO_API_AUDIENCE": ENVIRONMENT.api_audience,
        "DEMO_API_RESOURCE": f"api://{ENVIRONMENT.api_audience}",
        "DEMO_ALLOWED_CALLER_IDS": ENVIRONMENT.verification_caller_id,
        "DEMO_AUTH_MODE": "key_trial",
        "DEMO_API_TRIAL_KEY": key,
        "DEMO_BACKING_URL": ENVIRONMENT.backing_url,
        "DEMO_FOUNDRY_ENDPOINT": baseline["source"]["project_endpoint"],
    }
    environment.pop("WEBSITE_HOSTNAME", None)
    records = []
    started = time.monotonic()
    with (directory / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "maf_service.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                timeout=360,
                follow_redirects=False,
                trust_env=False,
            ) as api:
                deadline = time.monotonic() + 60
                while True:
                    if process.poll() is not None:
                        raise RuntimeError("The local MAF server exited; inspect server.log.")
                    try:
                        health = api.get("/health", timeout=3)
                    except (httpx.ConnectError, httpx.TimeoutException):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("The local MAF server did not start in 60 seconds.")
                        time.sleep(0.5)
                        continue
                    health.raise_for_status()
                    if (
                        health.json()["workflow_configured"] is not True
                        or health.json()["source_sha256"] != baseline["source"]["sha256"]
                    ):
                        raise RuntimeError("Local readiness does not identify the frozen workflow.")
                    break
                payload = {"question": "Tell me about MS01."}
                if api.post("/api/run", json=payload).status_code != 401:
                    raise RuntimeError("Anonymous local workflow access was not rejected.")
                if (
                    api.post("/api/run", json=payload, headers={"x-api-key": "invalid"}).status_code
                    != 401
                ):
                    raise RuntimeError("An invalid local trial key was not rejected.")
                headers = {"x-api-key": key}
                identity = api.get("/api/identity-check", headers=headers)
                identity.raise_for_status()
                if identity.json()["outbound_auth"] != "azure_cli":
                    raise RuntimeError("Local execution must not claim cloud Managed Identity.")
                if (
                    api.post(
                        "/api/run", json={**payload, "route": "mcp"}, headers=headers
                    ).status_code
                    != 422
                ):
                    raise RuntimeError("A caller-supplied route override was accepted.")
                with (
                    AzureCliCredential(subscription=SUBSCRIPTION) as credential,
                    httpx.Client(timeout=120, follow_redirects=False) as management,
                ):
                    fabric = DemoFabric(credential, management, ROOT / "evidence", US_WORKSPACE)
                    with fabric.active_capacity():
                        for case in cases:
                            if time.monotonic() - started > 1800:
                                raise RuntimeError("The local MAF baseline exceeded 30 minutes.")
                            run_id = source_results[case["id"]]["result"]["run_id"]
                            case_started = time.monotonic()
                            response = api.post(
                                "/api/run",
                                json={"question": case["question"], "run_id": run_id},
                                headers=headers,
                            )
                            path = directory / f"{case['id']}.json"
                            if response.is_error:
                                path.write_text(response.text + "\n", encoding="utf-8")
                                response.raise_for_status()
                            result = DemoResult.model_validate(response.json())
                            proof_headers = {
                                name: value
                                for name, value in response.headers.items()
                                if name.startswith("x-kpp-")
                            }
                            if (
                                proof_headers.get("x-kpp-framework") != "1.11.0"
                                or proof_headers.get("x-kpp-source-sha256")
                                != baseline["source"]["sha256"]
                                or proof_headers.get("x-kpp-outbound-auth") != "azure_cli"
                            ):
                                raise RuntimeError(
                                    "The HTTP response has no real SDK/source proof."
                                )
                            native_ids = proof_headers["x-kpp-native-responses"].split(",")
                            expected_calls = 2 if case["expected_status"] == "success" else 1
                            if len(native_ids) != expected_calls:
                                raise RuntimeError("An unexpected specialist dispatch occurred.")
                            actual = json.dumps(
                                {
                                    "answer": result.answer,
                                    "sources": [item.model_dump() for item in result.sources],
                                }
                            )
                            normalized = re.sub(r"(?<=\d),(?=\d)", "", actual).upper()
                            sources = {canonical_source_id(item.id) for item in result.sources}
                            record = {
                                "case_id": case["id"],
                                "route_match": result.route.value == case["route"],
                                "status_match": result.status == case["expected_status"],
                                "facts_pass": all(
                                    item.upper() in normalized for item in case["facts"]
                                ),
                                "sources_pass": all(
                                    canonical_source_id(item) in sources for item in case["sources"]
                                ),
                                "seconds": round(time.monotonic() - case_started, 2),
                                "result": result.model_dump(mode="json"),
                                "execution_headers": proof_headers,
                            }
                            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                            records.append(record)
                            print(
                                f"Local MAF {case['id']}: route={result.route} "
                                f"status={result.status} match={record['route_match']}",
                                flush=True,
                            )
                            if not all(
                                record[field]
                                for field in ("status_match", "facts_pass", "sources_pass")
                            ):
                                raise RuntimeError(f"Local MAF parity failed: {case['id']}")
        finally:
            if process.poll() is None:
                if sys.platform == "win32":
                    subprocess.run(
                        [
                            "pwsh",
                            "-NoProfile",
                            "-NonInteractive",
                            "-Command",
                            f"Stop-Process -Id {process.pid} -ErrorAction Stop",
                        ],
                        check=True,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                else:
                    process.terminate()
                process.wait(timeout=20)
    accuracy = sum(item["route_match"] for item in records) / len(records)
    if len(records) != 50 or accuracy < 0.98:
        raise RuntimeError("The local MAF corpus/accuracy gate failed.")
    proof = {
        "demo_id": "48254cc6",
        "local_authenticated_http_baseline": "PASS",
        "case_count": len(records),
        "classification_accuracy": accuracy,
        "actual_status_counts": dict(Counter(item["result"]["status"] for item in records)),
        "source_sha256": baseline["source"]["sha256"],
        "corpus_sha256": baseline["corpus_sha256"],
        "framework": "agent-framework-core",
        "framework_version": "1.11.0",
        "runtime_mode": "source_bound_code_defined_fallback",
        "inbound_auth": "temporary_key_loopback_only",
        "outbound_auth": "azure_cli",
        "anonymous_and_invalid_key": "REJECTED",
        "route_override": "REJECTED",
        "hosted_managed_identity_gate": "PENDING",
        "full_seven_provider_status": "BLOCKED",
        "results": records,
    }
    (ROOT / "evidence" / "maf" / "local-baseline.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in proof.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
