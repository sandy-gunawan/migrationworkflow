import argparse
import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

from demo_common.fabric import LAKEHOUSE, SUBSCRIPTION, US_WORKSPACE, WORKSPACE, DemoFabric

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure the native synthetic Fabric agent.")
    parser.add_argument("--profile", choices=("singapore", "us"), default="singapore")
    args = parser.parse_args()
    prefix = "fabric-us" if args.profile == "us" else "fabric"
    workspace = US_WORKSPACE if args.profile == "us" else WORKSPACE
    config_path = ROOT / "config" / f"{prefix}-data-agent.json"
    seed = json.loads(
        (ROOT / "evidence" / "preflight" / f"{prefix}-seed.json").read_text(encoding="utf-8")
    )
    lakehouse = seed["lakehouseId"]
    if seed["demoId"] != "48254cc6" or seed["workspaceId"] != workspace:
        raise SystemExit("Synthetic seed ownership check failed.")
    if args.profile == "singapore" and lakehouse != LAKEHOUSE:
        raise SystemExit("Singapore source has no matching demo creation receipt.")
    owned_lakehouse = json.loads(
        (ROOT / "config" / f"{prefix}-lakehouse.json").read_text(encoding="utf-8-sig")
    )
    if owned_lakehouse["lakehouse"]["id"] != lakehouse:
        raise SystemExit("Data source does not match the newly created demo lakehouse.")
    name = f"kpp_mining_data_{args.profile}_48254cc6"
    instructions = (
        f"Use only the selected synthetic tables in lakehouse {lakehouse}, workspace {workspace}. "
        "Never discover or access other items, workspaces, mail, or live business systems. "
        "Answer using exact retrieved values and name the synthetic source table. "
        "Do not execute writes or invent records. Production uses tonnes; diesel uses litres."
    )
    config = json.loads(config_path.read_text()) if config_path.exists() else {"demoId": "48254cc6"}

    def save() -> None:
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    if config["demoId"] != "48254cc6":
        raise SystemExit("Refusing to configure another data agent.")
    prefix = f"/workspaces/{workspace}/dataAgents"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=90, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", workspace)
        with fabric.active_capacity():
            if "agent" not in config:
                agent = fabric.finish(
                    fabric.request(
                        "POST",
                        prefix,
                        {
                            "displayName": name,
                            "description": "Synthetic mining demo only. No live sources.",
                        },
                    ),
                    resource=True,
                )
                if agent.get("displayName") != name or agent.get("workspaceId") != workspace:
                    raise RuntimeError("Unexpected native data-agent creation response.")
                config["agent"] = agent
                save()
            agent = config["agent"]
            base = f"{prefix}/{agent['id']}"
            if agent["displayName"] != name or agent["workspaceId"] != workspace:
                raise RuntimeError("Refusing to adopt a different Fabric data agent.")
            fabric.request("PATCH", f"{base}/staging/settings", {"aiInstructions": instructions})
            if "source" not in config:
                source = fabric.finish(
                    fabric.request(
                        "POST",
                        f"{base}/staging/datasources",
                        {
                            "type": "LakehouseTables",
                            "lakehouseReference": {
                                "referenceType": "ById",
                                "itemId": lakehouse,
                                "workspaceId": workspace,
                            },
                        },
                    ),
                    resource=True,
                )
                config["source"] = source
                save()
            source_id = config["source"].get("id", config["source"].get("Id"))
            if source_id != lakehouse:
                raise RuntimeError("The configured native source is not the new demo lakehouse.")
            config["staging_elements"] = fabric.request(
                "GET", f"{base}/staging/datasources/{source_id}/elements"
            ).json()
            save()
            print(
                json.dumps(
                    {
                        "agent": agent,
                        "source": config["source"],
                        "elements": config["staging_elements"],
                        "next": "Explicit table selection and publication still required.",
                    },
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
