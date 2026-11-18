import json
from pathlib import Path

import httpx
from azure.identity import AzureCliCredential

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://kppsearch48254cc6.search.windows.net"
VERSION = "2026-04-01"
SOURCE = "kppdemo-mining-source"
KNOWLEDGE_BASE = "kppdemo-mining-knowledge"


def main() -> None:
    seed = json.loads(
        (ROOT / "evidence" / "preflight" / "search-seed.json").read_text(encoding="utf-8")
    )
    if seed["demoId"] != "48254cc6" or seed["endpoint"] != ENDPOINT:
        raise SystemExit("Refusing to connect a non-demo Search index.")
    if seed["index"] != "kppdemo-documents":
        raise SystemExit("Only the newly seeded synthetic index is allowed.")
    proof_path = ROOT / "evidence" / "preflight" / "foundry-iq.json"
    if proof_path.exists():
        raise SystemExit("Knowledge proof already exists; refusing an implicit reconfiguration.")
    source = {
        "name": SOURCE,
        "kind": "searchIndex",
        "description": "New synthetic KPP mining index only; no existing data sources.",
        "searchIndexParameters": {
            "searchIndexName": seed["index"],
            "semanticConfigurationName": "default",
            "sourceDataFields": [
                {"name": name} for name in ("id", "title", "content", "source_uri", "demo_id")
            ],
        },
    }
    knowledge = {
        "name": KNOWLEDGE_BASE,
        "description": "Native extractive knowledge over new synthetic demo documents only.",
        "knowledgeSources": [{"name": SOURCE}],
    }
    with AzureCliCredential(subscription="5a7c13bd-9a15-4380-ba67-4d972838bc0b") as credential:
        with httpx.Client(timeout=90, follow_redirects=False) as client:

            def request(method: str, path: str, body: object, *, create: bool = False) -> dict:
                token = credential.get_token("https://search.azure.com/.default")
                headers = {"Authorization": f"Bearer {token.token}"}
                if create:
                    headers["If-None-Match"] = "*"
                response = client.request(
                    method,
                    f"{ENDPOINT}{path}",
                    params={"api-version": VERSION},
                    headers=headers,
                    json=body,
                )
                response.raise_for_status()
                return response.json()

            request("PUT", f"/knowledgesources/{SOURCE}", source, create=True)
            request("PUT", f"/knowledgebases/{KNOWLEDGE_BASE}", knowledge, create=True)
            retrieved = request(
                "POST",
                f"/knowledgebases/{KNOWLEDGE_BASE}/retrieve",
                {
                    "intents": [
                        {
                            "type": "semantic",
                            "search": "What is the synthetic reporting code for Copper Ridge MS01?",
                        }
                    ],
                    "knowledgeSourceParams": [
                        {
                            "knowledgeSourceName": SOURCE,
                            "kind": "searchIndex",
                            "includeReferences": True,
                        }
                    ],
                },
            )
            text = json.dumps(retrieved)
            references = retrieved.get("references")
            if (
                "DEMO-COPPER-17" not in text
                or "DMO-DOC-01" not in text
                or not isinstance(references, list)
                or not references
            ):
                raise RuntimeError("Native knowledge retrieval lacked expected facts/references.")
            (ROOT / "evidence" / "preflight" / "foundry-iq-retrieve.json").write_text(
                json.dumps(retrieved, indent=2) + "\n", encoding="utf-8"
            )
            proof = {
                "demoId": "48254cc6",
                "endpoint": ENDPOINT,
                "knowledgeSource": SOURCE,
                "knowledgeBase": KNOWLEDGE_BASE,
                "apiVersion": VERSION,
                "native_retrieval": "PASS",
                "mode": "GA minimal extractive retrieval; no LLM planning or answer synthesis",
                "fact": "DEMO-COPPER-17",
                "source_document": "DMO-DOC-01",
                "reference_count": len(references),
                "foundry_specialist_attachment": "UNVERIFIED",
            }
            proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
