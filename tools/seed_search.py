import json
import time
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://kppsearch48254cc6.search.windows.net"
INDEX = "kppdemo-documents"
VERSION = "2024-07-01"
SUBSCRIPTION = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"


def main() -> None:
    receipt = json.loads(
        (ROOT / "evidence" / "preflight" / "foundation-deployment.json").read_text(
            encoding="utf-8-sig"
        )
    )
    if receipt["state"] != "Succeeded" or receipt["outputs"]["searchEndpoint"]["value"] != ENDPOINT:
        raise SystemExit("The new demo Search service has not been verified.")
    proof_path = ROOT / "evidence" / "preflight" / "search-seed.json"
    if proof_path.exists():
        raise SystemExit("Search seed proof already exists; refusing an implicit reload.")
    documents = json.loads((ROOT / "data" / "seed" / "documents.json").read_text(encoding="utf-8"))
    if not documents or any(
        item.get("demo_id") != "48254cc6" or item.get("synthetic") is not True for item in documents
    ):
        raise SystemExit("Refusing to upload non-demo Search content.")
    definition = {
        "name": INDEX,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True},
            {"name": "content", "type": "Edm.String", "searchable": True},
            {"name": "source_uri", "type": "Edm.String", "filterable": True},
            {"name": "demo_id", "type": "Edm.String", "filterable": True},
            {"name": "synthetic", "type": "Edm.Boolean", "filterable": True},
        ],
        "semantic": {
            "configurations": [
                {
                    "name": "default",
                    "prioritizedFields": {
                        "titleField": {"fieldName": "title"},
                        "prioritizedContentFields": [{"fieldName": "content"}],
                    },
                }
            ]
        },
    }
    with AzureCliCredential(subscription=SUBSCRIPTION) as credential:
        with httpx.Client(timeout=60, follow_redirects=False) as client:

            def search(method: str, path: str, body: object = None) -> httpx.Response:
                token = credential.get_token("https://search.azure.com/.default")
                response = client.request(
                    method,
                    f"{ENDPOINT}{path}",
                    params={"api-version": VERSION},
                    headers={"Authorization": f"Bearer {token.token}"},
                    json=body,
                )
                response.raise_for_status()
                return response

            search("POST", "/indexes", definition)
            upload = search(
                "POST",
                f"/indexes/{INDEX}/docs/index",
                {"value": [{"@search.action": "upload", **item} for item in documents]},
            ).json()
            if any(item.get("status") is not True for item in upload["value"]):
                raise RuntimeError(f"Synthetic Search upload failed: {upload}")
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                response = search(
                    "POST",
                    f"/indexes/{INDEX}/docs/search",
                    {
                        "search": "DEMO-COPPER-17",
                        "filter": "demo_id eq '48254cc6' and synthetic eq true",
                        "select": "id,title,content,source_uri,demo_id,synthetic",
                        "top": 3,
                    },
                ).json()
                found = [
                    item
                    for item in response["value"]
                    if item["id"] == "DMO-DOC-01" and "DEMO-COPPER-17" in item["content"]
                ]
                if found:
                    break
                time.sleep(5)
            else:
                raise TimeoutError("New synthetic Search content was not retrievable.")
            proof = {
                "demoId": "48254cc6",
                "endpoint": ENDPOINT,
                "index": INDEX,
                "uploaded": len(documents),
                "verified_document_id": found[0]["id"],
                "verified_source": found[0]["source_uri"],
                "authentication": "entra_setup_user",
                "ordinary_retrieval": "PASS",
                "foundry_iq_knowledge_base": "UNVERIFIED",
            }
            proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
