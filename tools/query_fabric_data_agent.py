import argparse
import asyncio
import json
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from azure.identity import AzureCliCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from demo_common.fabric import API, SUBSCRIPTION, US_WORKSPACE, DemoFabric

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    (
        "production",
        "What was production in tonnes at site MS01 on 2026-11-01 for the day shift? "
        "Use the production table and state the site, date, shift, and exact tonnes.",
        ["1250", "MS01"],
    ),
    (
        "stock",
        "How many litres of DIESEL stock are available at site MS01 in the synthetic stock table?",
        ["18000", "MS01"],
    ),
    (
        "maintenance",
        "Which equipment does synthetic maintenance order WO001 refer to, and what is its site? "
        "Use work_orders and equipment.",
        ["TRK001", "MS01"],
    ),
]


async def query(
    endpoint: str, bearer: str, tool: str, destination: Path, cases: list
) -> list[dict]:
    results = []
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {bearer}"},
        timeout=httpx.Timeout(300),
        follow_redirects=False,
    ) as client:
        for case_id, question, facts in cases:
            async with streamable_http_client(
                endpoint, http_client=client, terminate_on_close=False
            ) as (read, write, _):
                async with ClientSession(
                    read, write, read_timeout_seconds=timedelta(seconds=300)
                ) as session:
                    await session.initialize()
                    available = await session.list_tools()
                    if [item.name for item in available.tools] != [tool]:
                        raise RuntimeError("Native tool does not match the owned demo agent.")
                    response = await session.call_tool(tool, {"userQuestion": question})
                    body = response.model_dump(mode="json")
                    response_file = f"fabric-data-agent-{case_id}-{uuid4().hex[:8]}.json"
                    (destination / response_file).write_text(
                        json.dumps(body, indent=2) + "\n", encoding="utf-8"
                    )
                    text = "\n".join(item.text for item in response.content if item.type == "text")
                    normalized = re.sub(r"(?<=\d),(?=\d)", "", text).upper()
                    if response.isError or any(fact.upper() not in normalized for fact in facts):
                        raise RuntimeError(
                            f"Native data-agent case {case_id} did not return the required facts; "
                            "inspect its saved synthetic response."
                        )
                    results.append(
                        {
                            "case": case_id,
                            "status": "PASS",
                            "required_facts": facts,
                            "tool": tool,
                            "response_file": response_file,
                            "answer": text,
                        }
                    )
                    print(f"Native Fabric retrieval PASS: {case_id}", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Test only the native synthetic Fabric agent.")
    parser.add_argument("--inspect-production", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "config" / "fabric-us-data-agent.json").read_text(encoding="utf-8"))
    agent = config["agent"]
    if config["demoId"] != "48254cc6" or agent["workspaceId"] != US_WORKSPACE:
        raise SystemExit("DataAgent ownership check failed.")
    if set(config["selected_tables"]) != {
        "sites",
        "equipment",
        "production",
        "work_orders",
        "stock",
    }:
        raise SystemExit("Only the five seeded tables can be queried.")
    if "publication" not in config:
        raise SystemExit("Native data agent is not published.")
    endpoint = f"{API}/mcp/workspaces/{US_WORKSPACE}/dataagents/{agent['id']}/agent"
    if config["mcp_endpoint"] != endpoint:
        raise SystemExit("Refusing to query a different native endpoint.")
    destination = ROOT / "evidence" / "preflight"
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=120, follow_redirects=False) as client,
    ):
        fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
        with fabric.active_capacity():
            definition = fabric.finish(
                fabric.request(
                    "POST", f"/workspaces/{US_WORKSPACE}/dataAgents/{agent['id']}/getDefinition"
                ),
                resource=True,
            )
            (destination / "fabric-us-data-agent-definition.json").write_text(
                json.dumps(definition, indent=2) + "\n", encoding="utf-8"
            )
            token = credential.get_token("https://api.fabric.microsoft.com/.default")
            cases = CASES
            if args.inspect_production:
                cases = [
                    (
                        "production_snapshot",
                        "Read the production table without a WHERE clause. Show its row count "
                        "and first five actual rows, including site_id, date, shift, and tonnes. "
                        "Do not infer or fabricate missing rows.",
                        ["MS01"],
                    )
                ]
            results = asyncio.run(
                query(
                    endpoint, token.token, f"DataAgent_{agent['displayName']}", destination, cases
                )
            )
            proof = {
                "demoId": "48254cc6",
                "workspaceId": US_WORKSPACE,
                "dataAgentId": agent["id"],
                "native_retrieval": "PASS",
                "authentication": "entra_setup_user",
                "cloud_managed_identity": "UNVERIFIED",
                "cases": results,
            }
            name = (
                "fabric-production-diagnostic.json"
                if args.inspect_production
                else ("fabric-native-retrieval.json")
            )
            (destination / name).write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
