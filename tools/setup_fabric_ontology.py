import base64
import json
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
from azure.identity import AzureCliCredential

from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric

ROOT = Path(__file__).resolve().parents[1]
NAME = "kpp_mining_ontology_us_48254cc6"
TABLES = {
    "sites": ("MineSite", "site_id", ("site_id", "name")),
    "equipment": ("Equipment", "equipment_id", ("equipment_id", "site_id", "category", "status")),
    "work_orders": (
        "MaintenanceOrder",
        "order_id",
        ("order_id", "equipment_id", "priority", "status"),
    ),
}


def lineage(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"urn:kppdemo:48254cc6:ontology:{name}"))


def definition(sql_host: str, database: str) -> dict:
    if not re.fullmatch(r"[a-z0-9-]+\.datawarehouse\.fabric\.microsoft\.com", sql_host):
        raise ValueError("Invalid owned lakehouse SQL endpoint.")
    if database != "kpp_mining_us_48254cc6":
        raise ValueError("Only the newly created US lakehouse database may be bound.")
    platform = {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/"
            "gitIntegration/platformProperties/2.0.0/schema.json"
        ),
        "metadata": {"type": "Ontology", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": lineage("platform")},
    }
    files = {
        ".platform": json.dumps(platform, indent=2),
        "database.tmdl": "database\n\tcompatibilityLevel: 1000000\n",
        "namespaces/default.tmdl": "namespace default\n\tlineageTag: default\n",
        "expressions.tmdl": (
            "expression DatabaseQuery =\n"
            f'\t\tSql.Database("{sql_host}", "{database}")\n'
            f"\tlineageTag: {lineage('DatabaseQuery')}\n"
        ),
    }
    refs = []
    for table, (entity, key, columns) in TABLES.items():
        table_text = f"table {table}\n\tlineageTag: {lineage(table)}\n"
        entity_text = (
            f"entity {entity}\n\tlineageTag: {lineage(entity)}\n"
            f"\tbackingTable: {table}\n\tkeyProperty: {key}\n"
        )
        for column in columns:
            table_text += (
                f"\n\tcolumn {column}\n\t\tdataType: string\n"
                f"\t\tlineageTag: {lineage(f'{table}.{column}')}\n"
                f"\t\tsourceColumn: {column}\n"
            )
            entity_text += (
                f"\n\tproperty {column}\n\t\tdataType: string\n"
                f"\t\tlineageTag: {lineage(f'{entity}.{column}')}\n"
                f"\n\t\tbackingConfiguration\n\t\t\tvalueColumn: {table}.{column}\n"
            )
        table_text += (
            f"\n\tpartition {table} = entity\n\t\tmode: directLake\n"
            f"\t\tsource\n\t\t\tentityName: {table}\n"
            "\t\t\tschemaName: dbo\n\t\t\texpressionSource: DatabaseQuery\n"
        )
        files[f"tables/{table}.tmdl"] = table_text
        files[f"entities/{entity}.tmdl"] = entity_text
        refs.extend([f"ref table {table}", f"ref entity {entity}"])
    files["model.tmdl"] = "model Model\n\n" + "\n".join(refs + ["ref namespace default"]) + "\n"
    files["relationships.tmdl"] = (
        "relationship equipment_site\n\tfromColumn: equipment.site_id\n"
        "\ttoColumn: sites.site_id\n\n"
        "relationship order_equipment\n\tfromColumn: work_orders.equipment_id\n"
        "\ttoColumn: equipment.equipment_id\n"
    )
    files["entityRelationships.tmdl"] = (
        "entityRelationship 'Equipment At Site'\n"
        f"\tlineageTag: {lineage('Equipment At Site')}\n"
        "\tfromEntity: Equipment\n\ttoEntity: MineSite\n"
        "\n\tbackingConfiguration\n\t\trelationship: equipment_site\n\n"
        "entityRelationship 'Order For Equipment'\n"
        f"\tlineageTag: {lineage('Order For Equipment')}\n"
        "\tfromEntity: MaintenanceOrder\n\ttoEntity: Equipment\n"
        "\n\tbackingConfiguration\n\t\trelationship: order_equipment\n"
    )
    destination = ROOT / "source" / "fabric" / "ontology-us"
    for path, content in files.items():
        target = destination / path
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_text(content + "\n", encoding="utf-8")
    return {
        "parts": [
            {
                "path": path,
                "payload": base64.b64encode(text.encode()).decode(),
                "payloadType": "InlineBase64",
            }
            for path, text in files.items()
        ]
    }


def main() -> None:
    record = json.loads(
        (ROOT / "config" / "fabric-us-lakehouse.json").read_text(encoding="utf-8-sig")
    )
    if record["demoId"] != "48254cc6" or record["workspaceId"] != US_WORKSPACE:
        raise SystemExit("US lakehouse has no matching demo creation receipt.")
    config_path = ROOT / "config" / "fabric-us-ontology.json"
    if config_path.exists():
        raise SystemExit("Ontology creation receipt exists; refusing an implicit replacement.")
    base = f"/workspaces/{US_WORKSPACE}"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=90, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            lakehouse = fabric.request(
                "GET", f"{base}/lakehouses/{record['lakehouse']['id']}"
            ).json()
            source = lakehouse["properties"]["sqlEndpointProperties"]
            payload = definition(source["connectionString"], lakehouse["displayName"])
            ontology = fabric.finish(
                fabric.request(
                    "POST",
                    f"{base}/ontologies",
                    {
                        "displayName": NAME,
                        "description": "Native ontology bound only to three synthetic demo tables.",
                        "definition": payload,
                    },
                ),
                resource=True,
            )
            receipt = {
                "demoId": "48254cc6",
                "workspaceId": US_WORKSPACE,
                "lakehouseId": lakehouse["id"],
                "ontology": ontology,
                "definitionFormat": "TMDL",
                "native_query": "UNVERIFIED",
            }
            config_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            returned = fabric.finish(
                fabric.request("POST", f"{base}/ontologies/{ontology['id']}/getDefinition"),
                resource=True,
            )
            exported = ROOT / "evidence" / "preflight" / "fabric-us-ontology-definition.json"
            exported.write_text(json.dumps(returned, indent=2) + "\n", encoding="utf-8")
            if not any(
                part["path"] == "entityRelationships.tmdl"
                for part in returned["definition"]["parts"]
            ):
                raise RuntimeError("Persisted native ontology did not retain its relationships.")
            print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
