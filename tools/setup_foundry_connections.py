import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = (
    "/subscriptions/5a7c13bd-9a15-4380-ba67-4d972838bc0b/resourceGroups/foundry"
    "/providers/Microsoft.CognitiveServices/accounts/kppfoundry48254cc6/projects/kpp-mining-demo"
)
NEW_CONNECTIONS = {
    "kppdemo-rest-mi": {
        "target": "https://kppdemo-data-48254cc6.azurewebsites.net/",
        "audience": "api://551b356f-3265-4a3e-8b87-95704b5f503c",
    },
    "kppdemo-knowledge-mi": {
        "target": "https://kppsearch48254cc6.search.windows.net/",
        "audience": "https://search.azure.com",
    },
}


def main() -> None:
    receipts = {}
    with (
        AzureCliCredential(subscription=PROJECT_ID.split("/")[2]) as credential,
        httpx.Client(timeout=90, follow_redirects=False) as client,
    ):
        token = credential.get_token("https://management.azure.com/.default")
        for name, connection in NEW_CONNECTIONS.items():
            path = f"{PROJECT_ID}/connections/{name}"
            url = f"https://management.azure.com{path}"
            headers = {"Authorization": f"Bearer {token.token}"}
            params = {"api-version": "2025-06-01"}
            current = client.get(url, params=params, headers=headers)
            if current.status_code == 404:
                body = {
                    "properties": {
                        "category": "OpenAPI",
                        "authType": "ProjectManagedIdentity",
                        **connection,
                        "metadata": {"type": "openapi", "demo_id": "48254cc6"},
                    }
                }
                response = client.put(
                    url, params=params, headers={**headers, "If-None-Match": "*"}, json=body
                )
                response.raise_for_status()
            else:
                current.raise_for_status()
            verified = client.get(url, params=params, headers=headers)
            verified.raise_for_status()
            value = verified.json()
            properties = value["properties"]
            if (
                properties["target"] != connection["target"]
                or properties["authType"] != "ProjectManagedIdentity"
                or properties["metadata"].get("demo_id") != "48254cc6"
            ):
                raise RuntimeError("Refusing to adopt a different project connection.")
            receipts[name] = {
                "id": value["id"],
                "target": properties["target"],
                "authType": properties["authType"],
                "audience": connection["audience"],
                "secretCreated": False,
            }
    (ROOT / "config" / "foundry-openapi-connections.json").write_text(
        json.dumps(receipts, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
