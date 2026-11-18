import argparse
import asyncio
import json
from importlib.metadata import version
from pathlib import Path

from agent_framework.foundry import FoundryAgent
from azure.identity import AzureCliCredential
from trial_support import ENDPOINT, native_evidence


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("kppdemo-router", "kppdemo-mcp"), required=True)
    parser.add_argument("--question", default="Show work orders for equipment TRK001.")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    credential = AzureCliCredential()
    agent = FoundryAgent(
        project_endpoint=ENDPOINT,
        agent_name=args.agent,
        agent_version="1",
        credential=credential,
        allow_preview=False,
        default_headers={"Foundry-Features": "WorkflowAgents=V1Preview"},
        default_options={"max_output_tokens": 2048},
        env_file_path=str(Path(__file__).with_name(".env.example")),
        timeout=120,
    )
    try:
        response = await agent.run(args.question)
        native = native_evidence(response)
        report = {
            "connector_version": version("agent-framework-foundry"),
            "core_version": version("agent-framework-core"),
            "agent": args.agent,
            "agent_version": "1",
            "response_id": response.response_id,
            "text": response.text,
            "native": native,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
    finally:
        await agent.close()
        credential.close()


if __name__ == "__main__":
    asyncio.run(main())
