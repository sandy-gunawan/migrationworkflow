import argparse
import asyncio
import json
import time
from pathlib import Path

from agent_framework.exceptions import ChatClientException
from agent_framework.foundry import FoundryAgent
from azure.core.credentials import AccessToken
from openai import AuthenticationError
from trial_support import ENDPOINT


class InvalidCredential:
    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        return AccessToken("invalid-for-isolated-auth-negative-test", int(time.time()) + 300)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    agent = FoundryAgent(
        project_endpoint=ENDPOINT,
        agent_name="kppdemo-router",
        agent_version="1",
        credential=InvalidCredential(),
        allow_preview=False,
        default_headers={"Foundry-Features": "WorkflowAgents=V1Preview"},
        timeout=30,
    )
    try:
        try:
            await agent.run("Show work orders for equipment TRK001.")
        except ChatClientException as exc:
            if not isinstance(exc.__cause__, AuthenticationError):
                raise
            report = {
                "status": "PASS",
                "boundary": "real Foundry project Responses API",
                "invalid_credential_rejected": True,
                "http_status": exc.__cause__.status_code,
                "expected_http_status": 401,
            }
            assert report["http_status"] == 401
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, indent=2))
        else:
            raise AssertionError("The live API accepted an invalid credential.")
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
