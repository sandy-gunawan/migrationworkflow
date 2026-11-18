import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from uuid import UUID

import httpx
from azure.identity import AzureCliCredential

from demo_common.data import MiningSeed
from demo_common.fabric import (
    CAPACITY,
    SUBSCRIPTION,
    US_CAPACITY,
    US_WORKSPACE,
    WORKSPACE,
    DemoFabric,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed only the owned synthetic Fabric workspace.")
    parser.add_argument("--profile", choices=("singapore", "us"), default="singapore")
    args = parser.parse_args()
    prefix = "fabric-us" if args.profile == "us" else "fabric"
    workspace_id = US_WORKSPACE if args.profile == "us" else WORKSPACE
    own_capacity = US_CAPACITY if args.profile == "us" else CAPACITY
    region = "eastus2" if args.profile == "us" else "southeastasia"
    proof_path = ROOT / "evidence" / "preflight" / f"{prefix}-seed.json"
    if proof_path.exists():
        raise SystemExit("Seed proof already exists; refusing an implicit reload.")
    workspace_record = json.loads(
        (ROOT / "config" / f"{prefix}-workspace.json").read_text(encoding="utf-8-sig")
    )
    capacity_record = json.loads(
        (ROOT / "config" / f"{prefix}-capacity.json").read_text(encoding="utf-8-sig")
    )
    if (
        workspace_record["demoId"] != "48254cc6"
        or workspace_record["workspace"]["id"] != workspace_id
        or capacity_record["capacity"]["azureResourceId"].lower() != own_capacity.lower()
    ):
        raise SystemExit("Fabric creation receipts do not match the owned demo profile.")
    seed = MiningSeed.load()
    base = f"/workspaces/{workspace_id}"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=90, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", workspace_id)
        with fabric.active_capacity():
            current = fabric.request("GET", base).json()
            if current.get("capacityId") != capacity_record["capacity"]["id"]:
                raise RuntimeError("Demo workspace is not on its approved owned capacity.")
            lakehouse_path = ROOT / "config" / f"{prefix}-lakehouse.json"
            if lakehouse_path.exists():
                recorded = json.loads(lakehouse_path.read_text(encoding="utf-8-sig"))
                if recorded["demoId"] != "48254cc6" or recorded["workspaceId"] != workspace_id:
                    raise RuntimeError("Refusing to adopt a different lakehouse.")
                lakehouse = fabric.request(
                    "GET", f"{base}/lakehouses/{UUID(recorded['lakehouse']['id'])}"
                ).json()
            else:
                lakehouse = fabric.finish(
                    fabric.request(
                        "POST",
                        f"{base}/lakehouses",
                        {
                            "displayName": f"kpp_mining_{args.profile}_48254cc6",
                            "description": "New synthetic mining tables only; no existing sources.",
                        },
                    ),
                    resource=True,
                )
                lakehouse_path.write_text(
                    json.dumps(
                        {"demoId": "48254cc6", "workspaceId": workspace_id, "lakehouse": lakehouse},
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            lakehouse_id = str(UUID(lakehouse["id"]))
            file_root = (
                f"https://{region}-onelake.dfs.fabric.microsoft.com"
                f"/{workspace_id}/{lakehouse_id}/Files"
            )
            tables = fabric.request("GET", f"{base}/lakehouses/{lakehouse_id}/tables").json()
            existing_demo_tables = {item["name"] for item in tables["data"]}
            facts = {}
            for name in ("sites", "equipment", "production", "work_orders", "stock"):
                rows = [row.model_dump() for row in getattr(seed, name)]
                stream = io.StringIO(newline="")
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
                payload = stream.getvalue().encode("utf-8")
                file_url = f"{file_root}/{name}.csv"
                token = credential.get_token("https://storage.azure.com/.default")
                headers = {
                    "Authorization": f"Bearer {token.token}",
                    "x-ms-version": "2023-11-03",
                }
                created = client.put(
                    file_url,
                    params={"resource": "file"},
                    headers={**headers, "If-None-Match": "*"},
                )
                if created.status_code not in (409, 412):
                    created.raise_for_status()
                    appended = client.patch(
                        file_url,
                        params={"action": "append", "position": 0},
                        headers=headers,
                        content=payload,
                    )
                    appended.raise_for_status()
                    flushed = client.patch(
                        file_url,
                        params={"action": "flush", "position": len(payload)},
                        headers=headers,
                    )
                    flushed.raise_for_status()
                read_back = client.get(file_url, headers=headers)
                read_back.raise_for_status()
                if read_back.content != payload:
                    raise RuntimeError(f"Synthetic file read-back mismatch: {name}")
                if name in existing_demo_tables:
                    loaded = {"status": "ExistingTableFromSameDemoAttempt"}
                else:
                    loaded = fabric.finish(
                        fabric.request(
                            "POST",
                            f"{base}/lakehouses/{lakehouse_id}/tables/{name}/load",
                            {
                                "relativePath": f"Files/{name}.csv",
                                "pathType": "File",
                                "mode": "Overwrite",
                                "formatOptions": {
                                    "format": "Csv",
                                    "header": True,
                                    "delimiter": ",",
                                },
                            },
                        ),
                        resource=False,
                    )
                facts[name] = {
                    "rows_seeded": len(rows),
                    "file_read_back": "PASS",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "load": loaded,
                }
                print(
                    f"Seeded only {args.profile} demo table: {name}; rows={len(rows)}", flush=True
                )
            proof = {
                "demoId": "48254cc6",
                "workspaceId": workspace_id,
                "lakehouseId": lakehouse_id,
                "region": region,
                "tables": facts,
                "data_agent_query": "UNVERIFIED",
                "ontology": "UNVERIFIED",
            }
            proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
