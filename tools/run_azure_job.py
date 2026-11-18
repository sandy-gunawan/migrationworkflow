import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import time
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric

ROOT = Path(__file__).resolve().parents[1]
GROUP = "demo_kpp"
IDENTITY = "kppdemo-deploy-48254cc6"
APP = "kppdemo-maf-48254cc6"


def cli(*args: str, timeout: int = 1200, raw: bool = False):
    executable = shutil.which("az")
    if not executable:
        raise RuntimeError("Azure CLI is required.")
    launcher = [executable]
    environment = os.environ.copy()
    if Path(executable).suffix.lower() == ".cmd":
        python = Path(executable).parent.parent / "python.exe"
        if not python.is_file():
            raise RuntimeError("The installed Azure CLI Python launcher is missing.")
        launcher = [str(python), "-IBm", "azure.cli"]
        environment["AZ_INSTALLER"] = "MSI"
    result = subprocess.run(
        [*launcher, *args, "--subscription", SUBSCRIPTION, "--only-show-errors", "-o", "json"],
        text=True, capture_output=True, timeout=timeout, env=environment,
    )
    if result.returncode:
        raise RuntimeError(f"Owned Azure job operation failed: {result.stderr[-2400:]}")
    if raw:
        return result.stdout
    return json.loads(result.stdout) if result.stdout.strip() else None


def encode(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def decode_evidence(log: str) -> dict:
    chunks = {}
    count = None
    expected_hash = None
    for line in log.splitlines():
        if line.startswith("KPP_EVIDENCE:"):
            _, index, total, value = line.split(":", 3)
            if count is not None and count != int(total):
                raise ValueError("Inconsistent Azure evidence chunk count.")
            count = int(total)
            if int(index) in chunks:
                raise ValueError("Duplicate Azure evidence chunk.")
            chunks[int(index)] = value
        elif line.startswith("KPP_EVIDENCE_SHA256:"):
            expected_hash = line.split(":", 1)[1]
    if not count or set(chunks) != set(range(count)) or not expected_hash:
        raise ValueError("The Azure job did not retain complete test evidence.")
    encoded = "".join(chunks[index] for index in range(count))
    if hashlib.sha256(encoded.encode()).hexdigest() != expected_hash:
        raise ValueError("Azure evidence transfer checksum failed.")
    return json.loads(base64.b64decode(encoded, validate=True))


def prepare(mode: str, run_id: str) -> tuple[Path, str, str]:
    identity = cli("identity", "show", "--resource-group", GROUP, "--name", IDENTITY)
    if identity.get("tags", {}).get("demo_id") != "48254cc6":
        raise RuntimeError("The setup identity has no owned-demo tag.")
    principal = identity["principalId"]
    app = cli("webapp", "show", "--resource-group", GROUP, "--name", APP)
    if app.get("tags", {}).get("demo_id") != "48254cc6":
        raise RuntimeError("The target application is not the owned demo.")
    settings = cli(
        "webapp", "config", "appsettings", "list", "--resource-group", GROUP, "--name", APP,
        "--query",
        "[?contains(['DEMO_AUTH_MODE','DEMO_ALLOWED_CALLER_IDS'],name)].{name:name,value:value}",
    )
    current = {item["name"]: item["value"] for item in settings}
    if current.get("DEMO_AUTH_MODE") != "entra":
        raise RuntimeError("The hosted demo must remain in Entra mode.")
    baseline = json.loads((ROOT / "source/foundry/baseline-manifest.json").read_text())
    source = json.loads((ROOT / baseline["source_outcomes"]).read_text())
    data = {
        "principal_id": principal,
        "corpus_base64": encode(ROOT / baseline["corpus"]),
        "run_ids": {
            item["case_id"]: item["result"]["run_id"] for item in source["results"]
        },
    }
    if mode in ("verify-logic", "rehearse-core"):
        manifest = json.loads((ROOT / "config" / "logicapps-manifest.json").read_text())
        if manifest["state"] != "Enabled" or manifest["sas_authentication"] != "Disabled":
            raise RuntimeError("Enable the new Logic App with SAS disabled before testing.")
        from tools.azure_job import require_logic_callback

        data["logic_callback"] = require_logic_callback(manifest["callback_url"])
        data["logic_principal_id"] = manifest["principal_id"]
        mapping_path = ROOT / "src" / "maf_service" / "resources" / "mapping.json"
        mapping = json.loads(mapping_path.read_text())
        data["logic_actions"] = {
            item["route"]: item["action_id"] for item in mapping["branches"] if item["agent"]
        }
    job = f"kppdemo-{mode}-48254cc6-{run_id}"
    existing = cli(
        "resource", "list", "--resource-group", GROUP,
        "--resource-type", "Microsoft.ContainerInstance/containerGroups",
        "--query", f"[?name=='{job}'].id",
    )
    if existing:
        raise RuntimeError(
            "Refusing to overwrite an existing deployment job; choose a fresh run ID."
        )
    parameters = {
        "runId": {"value": run_id},
        "jobMode": {"value": mode},
        "scriptBase64": {"value": encode(ROOT / "tools/azure_job.py")},
        "sourceZipBase64": {"value": encode(ROOT / "build/kppdemo-maf-source.zip")},
        "requirementsBase64": {"value": encode(ROOT / "build/requirements.linux.txt")},
        "testDataBase64": {"value": base64.b64encode(json.dumps(data).encode()).decode("ascii")},
    }
    destination = ROOT / "build" / f"job-{run_id}.parameters.json"
    destination.write_text(
        json.dumps({"parameters": parameters}, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return destination, job, principal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("deploy-maf", "verify-maf", "diagnose-maf", "verify-logic", "rehearse-core"),
        default="deploy-maf",
    )
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not args.run_id.isdigit() or len(args.run_id) != 14:
        raise ValueError("The job run ID must be a 14-digit UTC timestamp.")
    parameters, job, principal = prepare(args.mode, args.run_id)
    if args.prepare_only:
        print(json.dumps({"parameters": str(parameters), "job_name": job}, indent=2))
        return
    # This execution path is entered only after azure-validate and azure-deploy.
    settings = cli(
        "webapp", "config", "appsettings", "list", "--resource-group", GROUP, "--name", APP,
        "--query", "[?name=='DEMO_ALLOWED_CALLER_IDS'].value",
    )
    if len(settings) != 1:
        raise RuntimeError("The owned app must have exactly one explicit caller allowlist.")
    callers = set(settings[0].split(","))
    if principal not in callers:
        callers.add(principal)
        cli(
            "webapp", "config", "appsettings", "set", "--resource-group", GROUP, "--name", APP,
            "--settings", f"DEMO_ALLOWED_CALLER_IDS={','.join(sorted(callers))}",
            "--query", "length(@)",
        )
    evidence_group = (
        "rehearsal" if args.mode == "rehearse-core"
        else "logicapps" if args.mode == "verify-logic" else "maf"
    )
    evidence = ROOT / "evidence" / evidence_group / f"hosted-job-{args.run_id}"
    evidence.mkdir(parents=True)
    started = time.monotonic()
    created = False
    terminated = False
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=120, follow_redirects=False) as management,
    ):
        fabric = DemoFabric(credential, management, ROOT / "evidence", US_WORKSPACE)
        try:
            with (nullcontext() if args.mode == "diagnose-maf" else fabric.active_capacity()):
                # Set this before PUT: a failed ARM operation can still allocate a container.
                created = True
                deployment = cli(
                    "deployment", "group", "create", "--resource-group", GROUP,
                    "--name", f"kpp-job-{args.run_id}",
                    "--template-file", str(ROOT / "infra/deployment-job.bicep"),
                    "--parameters", str(parameters), timeout=1200,
                )
                (evidence / "deployment.json").write_text(
                    json.dumps(
                        {
                            "id": deployment["id"],
                            "state": deployment["properties"]["provisioningState"],
                        }, indent=2,
                    ) + "\n", encoding="utf-8",
                )
                while True:
                    view = cli("container", "show", "--resource-group", GROUP, "--name", job)
                    state = view["containers"][0].get("instanceView", {}).get("currentState", {})
                    print(f"Owned Azure job state: {state.get('state', 'Pending')}", flush=True)
                    if state.get("state") == "Terminated":
                        terminated = True
                        break
                    if time.monotonic() - started > 3600:
                        raise TimeoutError("The owned Azure deployment job exceeded one hour.")
                    time.sleep(30)
                log = cli("container", "logs", "--resource-group", GROUP, "--name", job, raw=True)
                if not isinstance(log, str):
                    raise RuntimeError("The Azure container did not return text logs.")
                (evidence / "job.log").write_text(log, encoding="utf-8")
                if state.get("exitCode") != 0:
                    raise RuntimeError(
                        f"The owned Azure job exited {state.get('exitCode')}; inspect {evidence}."
                    )
                proof = decode_evidence(log)
                proof["job_name"] = job
                proof["seconds"] = round(time.monotonic() - started, 2)
                output = (
                    evidence / "diagnostics.json"
                    if args.mode == "diagnose-maf"
                    else ROOT / "evidence" / evidence_group / (
                        "remote.json" if args.mode == "rehearse-core" else "gate.json"
                    )
                )
                output.write_text(
                    json.dumps(proof, indent=2) + "\n", encoding="utf-8",
                )
                print(json.dumps(
                    {key: value for key, value in proof.items() if key != "results"}, indent=2,
                ))
        finally:
            if created and not terminated:
                allocated = cli(
                    "resource", "list", "--resource-group", GROUP,
                    "--resource-type", "Microsoft.ContainerInstance/containerGroups",
                    "--query", f"[?name=='{job}'].tags.demo_id",
                )
                if allocated:
                    if allocated != ["48254cc6"]:
                        raise RuntimeError(
                            "Refusing to stop a container without the owned-demo tag."
                        )
                    cli("container", "stop", "--resource-group", GROUP, "--name", job, timeout=180)


if __name__ == "__main__":
    main()
