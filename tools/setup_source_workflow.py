import hashlib
import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.fabric import SUBSCRIPTION
from demo_common.foundry import ENDPOINT, DemoFoundry, DemoFoundryError

ROOT = Path(__file__).resolve().parents[1]
NAME = "kppdemo-mining-workflow"


def main() -> None:
    manifest_path = ROOT / "config" / "foundry-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["demo_id"] != "48254cc6" or manifest["full_five_specialist_gate"] != "PASS":
        raise RuntimeError("The five real specialist gate must pass before source creation.")
    source_path = ROOT / "source" / "foundry" / "mining-router.workflow.yaml"
    source = source_path.read_text(encoding="utf-8")
    definition = {"kind": "workflow", "workflow": source}
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=180, follow_redirects=False) as client,
    ):
        foundry = DemoFoundry(credential, client)
        try:
            latest = foundry.request("GET", f"/agents/{NAME}")["versions"]["latest"]
        except DemoFoundryError as exc:
            if exc.status_code != 404:
                raise
            latest = None
        if latest is not None and latest["metadata"].get("demo_id") != "48254cc6":
            raise RuntimeError("Refusing to change an unrelated workflow.")
        if latest is None or latest["definition"] != definition:
            latest = foundry.request(
                "POST",
                f"/agents/{NAME}/versions",
                {
                    "definition": definition,
                    "metadata": {
                        "demo_id": "48254cc6",
                        "pattern": "router_if_else",
                        "scope": "five_real_providers_two_explicit_blocked_routes",
                    },
                },
            )
        readback = foundry.request("GET", f"/agents/{NAME}")["versions"]["latest"]
        if readback["version"] != latest["version"] or readback["definition"] != definition:
            raise RuntimeError("Native workflow read-back does not match the authored YAML.")
    exported = ROOT / "source" / "foundry" / f"mining-router.v{readback['version']}.workflow.yaml"
    exported.write_text(readback["definition"]["workflow"], encoding="utf-8", newline="\n")
    receipt = {
        "demo_id": "48254cc6",
        "project_endpoint": ENDPOINT,
        "name": NAME,
        "version": readback["version"],
        "export": str(exported.relative_to(ROOT)),
        "sha256": hashlib.sha256(exported.read_bytes()).hexdigest(),
        "seed_sha256": hashlib.sha256(
            (ROOT / "data" / "seed" / "mining.json").read_bytes()
        ).hexdigest(),
        "agent_versions": {
            route: {"name": value["name"], "version": value["version"]}
            for route, value in manifest["agents"].items()
        },
        "runtime_status": "PENDING_NATIVE_EXECUTION",
        "retirement": "2026-12-01",
    }
    (ROOT / "config" / "source-workflow.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    manifest["source_workflow"] = receipt
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
