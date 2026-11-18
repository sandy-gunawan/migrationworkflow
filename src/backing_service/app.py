import os
from contextlib import asynccontextmanager

import httpx
from azure.identity.aio import ManagedIdentityCredential
from fastapi import FastAPI, HTTPException, Request
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from backing_service.upstream import DemoUpstream
from demo_common.auth import Authorizer, AuthSettings, DemoAuthMiddleware
from demo_common.data import MiningSeed, result
from demo_common.endpoints import require_demo_app_url
from demo_common.environment import ENVIRONMENT


def create_app(
    settings: AuthSettings | None = None,
    seed: MiningSeed | None = None,
    authorizer: Authorizer | None = None,
    upstream: DemoUpstream | None = None,
) -> FastAPI:
    settings = settings or AuthSettings.from_env()
    seed = seed or MiningSeed.load()
    hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*"]
    origins = [
        "http://127.0.0.1",
        "http://127.0.0.1:*",
        "http://localhost",
        "http://localhost:*",
    ]
    hostname = os.environ.get("WEBSITE_HOSTNAME")
    if hostname:
        require_demo_app_url(f"https://{hostname}", ENVIRONMENT.backing_app)
        hosts.append(hostname)
        origins.append(f"https://{hostname}")
    mcp = FastMCP(
        "KPP synthetic mining tools",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        ),
    )

    @mcp.tool()
    def get_equipment(equipment_id: str) -> dict[str, object]:
        """Read an equipment record from the isolated synthetic mining fixture."""
        for item in seed.equipment:
            if item.equipment_id == equipment_id:
                return result(item.model_dump(), f"equipment/{equipment_id}")
        raise ValueError("Synthetic equipment was not found.")

    @mcp.tool()
    def get_work_orders(equipment_id: str) -> dict[str, object]:
        """Read synthetic work orders; this tool does not contact an operational system."""
        if not any(item.equipment_id == equipment_id for item in seed.equipment):
            raise ValueError("Synthetic equipment was not found.")
        orders = [
            item.model_dump() for item in seed.work_orders if item.equipment_id == equipment_id
        ]
        return result(orders, f"maintenance/{equipment_id}")

    @mcp.tool()
    async def read_synthetic_stock_api(site_id: str, item_id: str) -> dict:
        """Call the protected synthetic REST API over HTTPS using Managed Identity."""
        return await app.state.upstream.stock(site_id, item_id)

    @mcp.tool()
    async def search_synthetic_documents(question: str) -> dict:
        """Query only the new dummy Azure AI Search index using Managed Identity."""
        return await app.state.upstream.search(question)

    @mcp.tool()
    async def retrieve_native_demo_knowledge(question: str) -> dict:
        """Call the real native knowledge-base retrieve API on new synthetic documents."""
        return await app.state.upstream.knowledge(question)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with mcp.session_manager.run():
            if upstream is not None:
                app.state.upstream = upstream
                yield
            else:
                async with (
                    ManagedIdentityCredential() as credential,
                    httpx.AsyncClient(timeout=90, follow_redirects=False) as client,
                ):
                    app.state.upstream = DemoUpstream(credential, client, settings.audience)
                    yield

    app = FastAPI(title="KPP synthetic mining backing service", lifespan=lifespan)
    app.add_middleware(DemoAuthMiddleware, authorizer=authorizer or Authorizer(settings))

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ready", "service": "backing", "synthetic_only": True}

    @app.get("/api/identity-check")
    def identity(request: Request) -> dict[str, object]:
        return {
            "authenticated": True,
            "caller_id": request.state.demo_caller,
            "auth_mode": settings.mode,
            "synthetic_only": True,
        }

    @app.get("/api/sites")
    def sites() -> dict[str, object]:
        return result([item.model_dump() for item in seed.sites], "sites")

    @app.get("/api/equipment/{equipment_id}")
    def equipment(equipment_id: str) -> dict[str, object]:
        for item in seed.equipment:
            if item.equipment_id == equipment_id:
                return result(item.model_dump(), f"equipment/{equipment_id}")
        raise HTTPException(404, "Synthetic equipment was not found.")

    @app.get("/api/stock/{site_id}/{item_id}")
    def stock(site_id: str, item_id: str) -> dict[str, object]:
        for item in seed.stock:
            if item.site_id == site_id and item.item_id == item_id:
                return result(item.model_dump(), f"stock/{site_id}/{item_id}")
        raise HTTPException(404, "Synthetic stock record was not found.")

    app.mount("/", mcp.streamable_http_app())
    return app
