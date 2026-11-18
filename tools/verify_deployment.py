import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import httpx
from azure.identity import AzureCliCredential

from demo_common.endpoints import require_demo_app_url

ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTION = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"
ARM = "https://management.azure.com"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/demo_kpp"


def main() -> None:
    receipt = json.loads(
        (ROOT / "evidence" / "preflight" / "foundation-deployment.json").read_text(
            encoding="utf-8-sig"
        )
    )
    if receipt["state"] != "Succeeded":
        raise SystemExit("Foundation deployment has not succeeded.")
    outputs = receipt["outputs"]
    urls = {
        "backing": require_demo_app_url(outputs["backingUrl"]["value"], "kppdemo-data-48254cc6"),
        "maf": require_demo_app_url(outputs["mafUrl"]["value"], "kppdemo-maf-48254cc6"),
    }
    results: dict[str, object] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "new_synthetic_demo_only",
        "workflow_migration_complete": False,
        "work_iq": "blocked_separate_sandbox_not_supplied",
    }
    with AzureCliCredential(subscription=SUBSCRIPTION) as credential:
        with httpx.Client(timeout=100, follow_redirects=False) as client:

            def arm(method: str, resource: str, body: object = None) -> dict:
                token = credential.get_token("https://management.azure.com/.default")
                response = client.request(
                    method,
                    f"{ARM}{resource}?api-version=2024-11-01",
                    headers={"Authorization": f"Bearer {token.token}"},
                    json=body,
                )
                response.raise_for_status()
                return response.json()

            def wait_for_auth(url: str, key: str, expected: int) -> httpx.Response:
                deadline = time.monotonic() + 360
                last_status: int | str = "not_requested"
                while time.monotonic() < deadline:
                    try:
                        response = client.get(
                            f"{url}/openapi.json", headers={"x-api-key": key}, timeout=30
                        )
                    except (httpx.ConnectError, httpx.TimeoutException) as exc:
                        last_status = type(exc).__name__
                    else:
                        last_status = response.status_code
                        if response.status_code == expected:
                            return response
                    time.sleep(10)
                raise RuntimeError(f"Demo auth transition timed out; last status={last_status}.")

            def trial(service: str, checks: Callable[[str, dict[str, str]], dict]) -> None:
                name = f"kppdemo-{'data' if service == 'backing' else 'maf'}-48254cc6"
                resource = f"{GROUP}/providers/Microsoft.Web/sites/{name}"
                deployed = arm("GET", resource)
                if deployed.get("tags", {}).get("demo_id") != "48254cc6":
                    raise RuntimeError("Refusing to configure a non-demo-owned app.")
                original = arm("POST", f"{resource}/config/appsettings/list")["properties"]
                if original.get("DEMO_AUTH_MODE") != "entra":
                    raise RuntimeError("Expected the original app to require Entra authentication.")
                key = secrets.token_urlsafe(48)
                trial_settings = {
                    **original,
                    "DEMO_AUTH_MODE": "key_trial",
                    "DEMO_API_TRIAL_KEY": key,
                }
                try:
                    arm("PUT", f"{resource}/config/appsettings", {"properties": trial_settings})
                    wait_for_auth(urls[service], key, 200)
                    invalid = client.get(
                        f"{urls[service]}/openapi.json", headers={"x-api-key": "invalid"}
                    )
                    if invalid.status_code != 401:
                        raise RuntimeError("The invalid API key was not rejected.")
                    results[service] = checks(urls[service], {"x-api-key": key})
                finally:
                    arm("PUT", f"{resource}/config/appsettings", {"properties": original})
                    wait_for_auth(urls[service], key, 401)
                results[f"{service}_final_auth"] = "entra_key_trial_disabled"

            def check_backing(url: str, headers: dict[str, str]) -> dict:
                stock = client.get(f"{url}/api/stock/MS01/DIESEL", headers=headers)
                stock.raise_for_status()
                value = stock.json()
                if value.get("synthetic") is not True or value["data"]["quantity"] != 18000:
                    raise RuntimeError("Synthetic REST facts did not match the seed.")
                mcp_headers = {**headers, "accept": "application/json, text/event-stream"}
                discovery = client.post(
                    f"{url}/mcp",
                    headers=mcp_headers,
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                )
                discovery.raise_for_status()
                names = {tool["name"] for tool in discovery.json()["result"]["tools"]}
                if names != {
                    "get_equipment",
                    "get_work_orders",
                    "read_synthetic_stock_api",
                    "search_synthetic_documents",
                    "retrieve_native_demo_knowledge",
                }:
                    raise RuntimeError("Unexpected demo MCP tools.")
                call = client.post(
                    f"{url}/mcp",
                    headers=mcp_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_work_orders",
                            "arguments": {"equipment_id": "TRK001"},
                        },
                    },
                )
                call.raise_for_status()
                if call.json()["result"].get("isError") or "WO001" not in call.text:
                    raise RuntimeError("Native MCP tool call did not return the synthetic order.")
                return {"key_trial": "passed", "rest_quantity": 18000, "mcp_order": "WO001"}

            def check_maf(url: str, headers: dict[str, str]) -> dict:
                backend = client.post(f"{url}/api/verify-backend", headers=headers)
                backend.raise_for_status()
                value = backend.json()
                if (
                    value.get("outbound_auth") != "managed_identity"
                    or value["identity"].get("auth_mode") != "entra"
                    or value["identity"].get("caller_id") != outputs["mafPrincipalId"]["value"]
                    or value["stock"]["data"]["quantity"] != 18000
                ):
                    raise RuntimeError("Managed identity backing proof failed.")
                foundry = client.post(f"{url}/api/verify-foundry", headers=headers)
                foundry.raise_for_status()
                native = foundry.json()
                if (
                    native.get("outbound_auth") != "managed_identity"
                    or native["response"].get("status") != "completed"
                    or "KPP native workflow readiness: 48254cc6" not in foundry.text
                ):
                    raise RuntimeError("Managed identity native workflow proof failed.")
                return {
                    "key_trial": "passed",
                    "backing_auth": "managed_identity",
                    "verified_caller_id": value["identity"]["caller_id"],
                    "foundry_auth": "managed_identity",
                    "native_response_id": native["response"]["id"],
                }

            trial("backing", check_backing)
            trial("maf", check_maf)
    target = ROOT / "evidence" / "preflight" / "hosted-foundation-verification.json"
    target.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
