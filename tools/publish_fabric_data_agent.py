import asyncio
import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from demo_common.fabric import API, SUBSCRIPTION, US_WORKSPACE, DemoFabric

ROOT = Path(__file__).resolve().parents[1]
TABLES = {"sites", "equipment", "production", "work_orders", "stock"}
CONFIG = ROOT / "config" / "fabric-us-data-agent.json"
SOURCE_INSTRUCTIONS = (
    "This source contains only five new synthetic dbo tables. "
    "dbo.production has site_id, date, shift, tonnes. It has no equipment_id column. "
    "MS01 and MS02 are site_id values, never equipment identifiers. "
    "For production questions use dbo.production directly, filtering site_id and the requested "
    "date and shift. Do not join equipment or filter equipment_id for site production. "
    "Use CAST([date] AS date) = DATEFROMPARTS(year, month, day) for date equality. "
    "shift values are day and night. Preserve uppercase stored IDs. "
    "dbo.equipment has equipment_id and site_id; TRK001 is an equipment identifier. "
    "dbo.work_orders links to equipment by equipment_id. "
    "dbo.stock has site_id, item_id, quantity, unit; DIESEL uses litres. "
    "If a production predicate returns no rows, inspect SELECT TOP 5 site_id, [date], shift, "
    "tonnes FROM dbo.production before deciding absence, and reconcile the requested filters. "
    "Never invent values or execute writes. Never discover other sources or workspaces."
)
EXAMPLES = [
    {
        "question": "Production at MS01 on November 1, 2026 for the day shift",
        "query": (
            "SELECT site_id, [date], shift, tonnes FROM dbo.production "
            "WHERE site_id = 'MS01' AND CAST([date] AS date) = DATEFROMPARTS(2026, 11, 1) "
            "AND shift = 'day'"
        ),
    },
    {
        "question": "Available DIESEL stock in litres at MS01",
        "query": (
            "SELECT site_id, item_id, quantity, unit FROM dbo.stock "
            "WHERE site_id = 'MS01' AND item_id = 'DIESEL'"
        ),
    },
    {
        "question": "Equipment and site for maintenance order WO001",
        "query": (
            "SELECT w.order_id, e.equipment_id, e.site_id FROM dbo.work_orders AS w "
            "JOIN dbo.equipment AS e ON w.equipment_id = e.equipment_id "
            "WHERE w.order_id = 'WO001'"
        ),
    },
    {
        "question": (
            "Retrieve production output in tonnes including the site ID for MS01 "
            "on 2026-11-01 day shift"
        ),
        "query": (
            "SELECT site_id, [date], shift, tonnes FROM dbo.production "
            "WHERE site_id = 'MS01' AND CAST([date] AS date) = DATEFROMPARTS(2026, 11, 1) "
            "AND shift = 'day'"
        ),
    },
]


async def discover(endpoint: str, bearer: str) -> dict:
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {bearer}"}, timeout=180, follow_redirects=False
    ) as client:
        async with streamable_http_client(
            endpoint, http_client=client, terminate_on_close=False
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return {"tools": [tool.model_dump(mode="json") for tool in tools.tools]}


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["demoId"] != "48254cc6" or config["agent"]["workspaceId"] != US_WORKSPACE:
        raise SystemExit("DataAgent is not owned by the synthetic US demo.")
    source_id = config["source"].get("id", config["source"].get("Id"))
    lakehouse = json.loads(
        (ROOT / "config" / "fabric-us-lakehouse.json").read_text(encoding="utf-8")
    )
    if source_id != lakehouse["lakehouse"]["id"]:
        raise SystemExit("Native source is not the newly created synthetic lakehouse.")
    agent_id = config["agent"]["id"]
    base = f"/workspaces/{US_WORKSPACE}/dataAgents/{agent_id}"
    elements_path = f"{base}/staging/datasources/{source_id}/elements"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=120, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            fabric.request(
                "PATCH",
                f"{base}/staging/settings",
                {
                    "aiInstructions": (
                        "Query only the five selected synthetic tables in this source. "
                        "Never discover or access any other item, workspace, or live system. "
                        "All site IDs and item IDs preserve their stored uppercase casing. "
                        "MS01 and MS02 are site_id values, never equipment_id values. "
                        "production contains site_id, date, shift and tonnes; it has no "
                        "equipment_id column. For site production, filter production.site_id "
                        "directly; do not filter equipment_id or join equipment unless the "
                        "question explicitly asks about a real seeded equipment identifier. "
                        "TRK001 is an equipment identifier, not a site identifier. "
                        "production.[date] has SQL date type; compare dates with DATEFROMPARTS "
                        "or CAST rather than display-formatted strings. "
                        "stock.item_id contains DIESEL or FILTER; stock.unit contains litres "
                        "or items. Select the stored unit rather than inventing a unit filter. "
                        "If a filter returns no records, inspect distinct values in the relevant "
                        "selected table and correct the predicate before declaring absence. "
                        "Never invent values. Identify the source table and returned record IDs. "
                        "For production questions, begin the answer with exactly one compact "
                        "JSON object, without markdown fences or introductory prose. "
                        "Use fields status, site_id, date, shift, tonnes, source_table. "
                        "status is success only when rows were retrieved; otherwise not_found. "
                        "tonnes must be the retrieved JSON number, or null when no rows exist. "
                        "date uses YYYY-MM-DD. source_table is dbo.production. "
                        "Never fill a missing result from memory or from an example. "
                        "Do not execute writes."
                    )
                },
            )
            settings = fabric.request("GET", f"{base}/staging/settings").json()
            instructions = settings.get("aiInstructions", settings.get("AiInstructions"))
            if (
                not isinstance(instructions, str)
                or "MS01 and MS02 are site_id" not in instructions
                or "source_table" not in instructions
            ):
                raise RuntimeError("The native DataAgent instruction read-back differs.")
            config["ai_instructions"] = instructions
            datasource_path = f"{base}/staging/datasources/{source_id}"
            fabric.request(
                "PATCH", datasource_path, {"instructions": SOURCE_INSTRUCTIONS}
            )
            native_source = fabric.request("GET", datasource_path).json()
            source_instructions = native_source.get(
                "instructions", native_source.get("DataSourceInstructions")
            )
            if source_instructions != SOURCE_INSTRUCTIONS:
                raise RuntimeError("Datasource SQL-generation instruction read-back differs.")
            if native_source.get("id", native_source.get("Id")) != source_id:
                raise RuntimeError("Datasource instruction update targeted another source.")
            config["source"] = native_source
            config["datasource_instructions"] = source_instructions
            selected = {}

            def walk(root_id: str | None = None, depth: int = 0) -> None:
                if depth > 5:
                    raise RuntimeError("Unexpected native datasource tree depth.")
                params = {"rootId": root_id} if root_id else None
                response = fabric.request("GET", elements_path, params=params).json()
                if response.get("continuationToken"):
                    raise RuntimeError("Unexpected large source tree; no implicit selection.")
                for element in response["value"]:
                    name = element["displayName"]
                    kind = element["type"]
                    if name in TABLES and kind.lower() in ("table", "tables.table"):
                        fabric.request(
                            "PATCH",
                            elements_path,
                            {"isSelected": True},
                            params={"id": element["id"]},
                        )
                        selected[name] = element["id"]
                    elif element.get("hasSubElements") and kind.lower() in (
                        "schemas",
                        "schema",
                        "tables",
                    ):
                        if kind.lower() == "schema" and name != "dbo":
                            raise RuntimeError("The demo source contains an unexpected schema.")
                        walk(element["id"], depth + 1)

            walk()
            if set(selected) != TABLES:
                raise RuntimeError(f"Native source did not expose all five demo tables: {selected}")
            config["selected_tables"] = selected
            fewshots = f"{base}/staging/datasources/{source_id}/fewshots"
            existing = fabric.request("GET", fewshots).json()["value"]
            for example in EXAMPLES:
                matching = [
                    item for item in existing if item.get("question") == example["question"]
                ]
                if matching:
                    if matching[0]["query"] != example["query"]:
                        raise RuntimeError("Unexpected SQL example on the new synthetic source.")
                    continue
                fabric.request("POST", fewshots, example)
            config["sql_examples"] = EXAMPLES
            CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            published = fabric.request(
                "POST",
                f"{base}/staging/publish",
                {"publishedDescription": "Synthetic mining demo 48254cc6. Read only."},
            ).json()
            config["publication"] = published
            endpoint = f"{API}/mcp/workspaces/{US_WORKSPACE}/dataagents/{agent_id}/agent"
            config["mcp_endpoint"] = endpoint
            CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            token = credential.get_token("https://api.fabric.microsoft.com/.default")
            tools = asyncio.run(discover(endpoint, token.token))
            proof = {
                "demoId": "48254cc6",
                "workspaceId": US_WORKSPACE,
                "dataAgentId": agent_id,
                "selected_tables": sorted(selected),
                "published": True,
                "endpoint": endpoint,
                **tools,
                "native_query": "UNVERIFIED",
            }
            target = ROOT / "evidence" / "preflight" / "fabric-data-agent-tools.json"
            target.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
