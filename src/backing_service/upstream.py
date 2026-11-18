import logging

import httpx
from azure.core.credentials_async import AsyncTokenCredential

from demo_common.environment import ENVIRONMENT

logger = logging.getLogger(__name__)
BACKING_URL = ENVIRONMENT.backing_url
SEARCH_URL = ENVIRONMENT.search_url


class DemoUpstream:
    def __init__(
        self, credential: AsyncTokenCredential, client: httpx.AsyncClient, api_audience: str
    ) -> None:
        self.credential = credential
        self.client = client
        self.api_audience = api_audience

    async def request(
        self, method: str, url: str, scope: str, body: object = None, params: dict | None = None
    ) -> dict:
        allowed = (
            url.startswith(f"{BACKING_URL}/api/stock/")
            or url == f"{SEARCH_URL}/indexes/kppdemo-documents/docs/search"
            or url == f"{SEARCH_URL}/knowledgebases/kppdemo-mining-knowledge/retrieve"
        )
        if not allowed or method not in ("GET", "POST"):
            raise ValueError("Adapter is restricted to the new read-only demo endpoints.")
        token = await self.credential.get_token(scope)
        response = await self.client.request(
            method,
            url,
            json=body,
            params=params,
            headers={"Authorization": f"Bearer {token.token}"},
        )
        if response.is_error:
            logger.error("Owned demo upstream failed: status=%s url=%s", response.status_code, url)
            response.raise_for_status()
        return response.json()

    async def stock(self, site_id: str, item_id: str) -> dict:
        if site_id not in ("MS01", "MS02") or item_id not in ("DIESEL", "FILTER"):
            raise ValueError("Only seeded synthetic stock identifiers may be queried.")
        value = await self.request(
            "GET",
            f"{BACKING_URL}/api/stock/{site_id}/{item_id}",
            f"api://{self.api_audience}/.default",
        )
        if value.get("synthetic") is not True or value.get("demo_id") != "48254cc6":
            raise RuntimeError("REST response is not the isolated synthetic demo.")
        return {"upstream_protocol": "https_rest", "outbound_auth": "managed_identity", **value}

    async def search(self, question: str) -> dict:
        value = await self.request(
            "POST",
            f"{SEARCH_URL}/indexes/kppdemo-documents/docs/search",
            "https://search.azure.com/.default",
            {
                "search": question,
                "filter": "demo_id eq '48254cc6' and synthetic eq true",
                "select": "id,title,content,source_uri,demo_id,synthetic",
                "top": 3,
            },
            {"api-version": "2024-07-01"},
        )
        documents = value["value"]
        if any(
            item.get("demo_id") != "48254cc6" or item.get("synthetic") is not True
            for item in documents
        ):
            raise RuntimeError("Search returned an out-of-scope document.")
        return {
            "upstream_protocol": "azure_ai_search_rest",
            "outbound_auth": "managed_identity",
            "documents": documents,
            "sources": [{"kind": "demo_document", "id": item["source_uri"]} for item in documents],
        }

    async def knowledge(self, question: str) -> dict:
        value = await self.request(
            "POST",
            f"{SEARCH_URL}/knowledgebases/kppdemo-mining-knowledge/retrieve",
            "https://search.azure.com/.default",
            {"intents": [{"type": "semantic", "search": question}]},
            {"api-version": "2026-04-01"},
        )
        if not isinstance(value.get("references"), list):
            raise RuntimeError("Native knowledge retrieval returned no reference collection.")
        return {
            "upstream_protocol": "native_knowledge_base_rest",
            "outbound_auth": "managed_identity",
            "knowledge_base": "kppdemo-mining-knowledge",
            "result": value,
        }
