import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"
APP = "kppdemo-data-48254cc6"
RESOURCE = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/demo_kpp/providers/Microsoft.Web/sites/{APP}"
)


def cli(*args: str) -> str:
    executable = shutil.which("az")
    if not executable:
        raise RuntimeError("Azure CLI is required.")
    run = subprocess.run(
        [executable, *args, "--subscription", SUBSCRIPTION, "--only-show-errors"],
        text=True,
        capture_output=True,
        check=False,
    )
    if run.returncode:
        raise RuntimeError(f"Scoped artifact operation failed: {run.stderr[:2000]}")
    return run.stdout.strip()


def deployment_status(value: object) -> dict:
    if isinstance(value, dict) and isinstance(value.get("properties"), dict):
        value = value["properties"]
    if isinstance(value, dict) and isinstance(value.get("value"), list):
        value = value["value"]
    if isinstance(value, list):
        if not value:
            return {}
        value = value[0]
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected management-plane deployment status shape.")
    return value


def main() -> None:
    package = ROOT / "build" / "kppdemo-app.zip"
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    blob = f"kppdemo-{digest}.zip"
    cli(
        "storage",
        "blob",
        "upload",
        "--account-name",
        "kppdeploy48254cc6",
        "--container-name",
        "demo-artifacts",
        "--name",
        blob,
        "--file",
        str(package),
        "--auth-mode",
        "login",
        "--overwrite",
        "false",
        "--no-progress",
        "--output",
        "none",
    )
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%MZ")
    sas = cli(
        "storage",
        "blob",
        "generate-sas",
        "--account-name",
        "kppdeploy48254cc6",
        "--container-name",
        "demo-artifacts",
        "--name",
        blob,
        "--auth-mode",
        "login",
        "--as-user",
        "--permissions",
        "r",
        "--expiry",
        expires,
        "--https-only",
        "--output",
        "tsv",
    )
    if not sas or "sig=" not in sas:
        raise RuntimeError("User-delegation SAS was not generated.")
    artifact_url = f"https://kppdeploy48254cc6.blob.core.windows.net/demo-artifacts/{blob}?{sas}"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=400, follow_redirects=False) as client,
    ):
        token = credential.get_token("https://management.azure.com/.default")
        headers = {"Authorization": f"Bearer {token.token}"}
        url = f"https://management.azure.com{RESOURCE}"
        ownership = client.get(url, params={"api-version": "2024-11-01"}, headers=headers)
        ownership.raise_for_status()
        if ownership.json().get("tags", {}).get("demo_id") != "48254cc6":
            raise RuntimeError("Refusing to deploy to an unrelated application.")
        operation = f"{url}/extensions/onedeploy"
        params = {"api-version": "2024-11-01"}
        previous = client.get(operation, params=params, headers=headers)
        previous.raise_for_status()
        old_id = deployment_status(previous.json()).get("id")
        deployed = client.put(
            operation,
            params=params,
            headers=headers,
            json={
                "properties": {
                    "type": "zip",
                    "packageUri": artifact_url,
                    "clean": False,
                    "restart": True,
                }
            },
        )
        deployed.raise_for_status()
        print(
            "Official management-plane OneDeploy request accepted; verifying actual result.",
            flush=True,
        )
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = client.get(operation, params=params, headers=headers)
            response.raise_for_status()
            status = deployment_status(response.json())
            identifier = status.get("id")
            if identifier and identifier != old_id:
                if status.get("status") == 3:
                    raise RuntimeError("The new management-plane deployment failed.")
                if status.get("status") == 4 and status.get("complete") is True:
                    proof = {
                        "demo_id": "48254cc6",
                        "app": APP,
                        "deployment_id": identifier,
                        "status": "Succeeded",
                        "package_sha256": digest,
                        "deployment_transport": "official_ARM_OneDeploy_pull",
                        "artifact_storage_private": True,
                        "shared_keys_used": False,
                        "sas_saved_in_source_or_evidence": False,
                        "artifact_read_access_expires_utc": expires,
                    }
                    target = ROOT / "evidence" / "preflight" / "adapter-app-deployment.json"
                    target.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(proof, indent=2))
                    return
            time.sleep(10)
        raise TimeoutError("The new management-plane app deployment was not proven completed.")


if __name__ == "__main__":
    main()
