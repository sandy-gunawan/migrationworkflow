import asyncio
import logging
import os
from contextlib import asynccontextmanager
from importlib.metadata import version
from uuid import UUID

import httpx
from agent_framework.exceptions import WorkflowException
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential, ManagedIdentityCredential
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from demo_common.auth import Authorizer, AuthSettings, DemoAuthMiddleware
from demo_common.contracts import DemoRequest, NormalizationRequest
from demo_common.endpoints import require_demo_app_url
from demo_common.environment import ENVIRONMENT
from demo_common.fabric import SUBSCRIPTION
from demo_common.foundry import DemoFoundry, DemoFoundryError
from demo_common.normalization import normalize_specialist_result
from maf_service.workflow import MiningWorkflow, WorkflowExecutionError, load_mapping

logger = logging.getLogger(__name__)
FOUNDRY_ENDPOINT = ENVIRONMENT.foundry_endpoint


def create_app(
    settings: AuthSettings | None = None, *, workflow: MiningWorkflow | None = None
) -> FastAPI:
    settings = settings or AuthSettings.from_env()
    backing_url = require_demo_app_url(os.environ["DEMO_BACKING_URL"], ENVIRONMENT.backing_app)
    endpoint = os.environ["DEMO_FOUNDRY_ENDPOINT"].rstrip("/")
    if endpoint != FOUNDRY_ENDPOINT:
        raise ValueError("Refusing access to an existing or non-demo Foundry endpoint.")
    resource = os.environ["DEMO_API_RESOURCE"]
    if resource != f"api://{settings.audience}":
        raise ValueError("Demo API audience and resource disagree.")
    hostname = os.environ.get("WEBSITE_HOSTNAME")
    if hostname:
        require_demo_app_url(f"https://{hostname}", ENVIRONMENT.maf_app)
    normalizer_caller = os.environ.get("DEMO_NORMALIZER_CALLER_ID")
    if normalizer_caller:
        UUID(normalizer_caller)
        if normalizer_caller not in settings.allowed_callers:
            raise ValueError("The normalization identity must be in the explicit caller allowlist.")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        credential = (
            ManagedIdentityCredential()
            if hostname
            else AzureCliCredential(subscription=SUBSCRIPTION)
        )
        with (
            credential,
            httpx.Client(timeout=300, follow_redirects=False) as native_client,
        ):
            engine = workflow or MiningWorkflow(
                load_mapping(),
                DemoFoundry(credential, native_client),
                identity_mode="managed_identity" if hostname else "azure_cli",
            )
            engine.build()
            async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
                app.state.credential = credential
                app.state.client = client
                app.state.workflow = engine
                yield

    app = FastAPI(title="KPP demo orchestration host", lifespan=lifespan)
    app.add_middleware(DemoAuthMiddleware, authorizer=Authorizer(settings))

    def orchestration_caller(request: Request) -> None:
        if normalizer_caller and request.state.demo_caller == normalizer_caller:
            logger.warning("Normalization-only identity denied orchestration access.")
            raise HTTPException(
                403, "This identity may normalize evidence, not run MAF orchestration."
            )

    def normalization_caller(request: Request) -> None:
        if not normalizer_caller:
            logger.error("The normalization-only caller identity is not configured.")
            raise HTTPException(503, "The normalization caller identity is not configured.")
        if request.state.demo_caller != normalizer_caller:
            logger.warning("Caller denied access to the Logic Apps normalization boundary.")
            raise HTTPException(
                403, "Only the configured Logic Apps identity may normalize evidence."
            )

    async def call(
        request: Request,
        scope: str,
        method: str,
        url: str,
        body: dict[str, object] | None = None,
    ) -> dict[str, object]:
        try:
            token = await asyncio.to_thread(request.app.state.credential.get_token, scope)
            headers = {"Authorization": f"Bearer {token.token}"}
            if url.startswith(f"{FOUNDRY_ENDPOINT}/"):
                headers["Foundry-Features"] = "WorkflowAgents=V1Preview"
            response = await request.app.state.client.request(
                method, url, json=body, headers=headers
            )
        except ClientAuthenticationError as exc:
            logger.error("Demo managed identity token acquisition failed.")
            raise HTTPException(502, "Demo managed identity authentication failed.") from exc
        except httpx.RequestError as exc:
            logger.error("Demo dependency transport failed: %s", type(exc).__name__)
            raise HTTPException(502, "Demo dependency transport failed.") from exc
        if response.status_code >= 400:
            logger.error("Demo dependency returned status=%s", response.status_code)
            raise HTTPException(
                502, {"code": "dependency_error", "upstream_status": response.status_code}
            )
        value = response.json()
        if not isinstance(value, dict):
            raise HTTPException(502, "Demo dependency returned an invalid object.")
        return value

    @app.get("/health")
    def health(request: Request) -> dict[str, object]:
        return {
            "status": "ready",
            "service": "agent-framework",
            "workflow_configured": True,
            "framework_version": version("agent-framework-core"),
            "source_sha256": request.app.state.workflow.mapping.source_sha256,
            "synthetic_only": True,
        }

    @app.get("/api/identity-check")
    def identity(request: Request) -> dict[str, object]:
        return {
            "authenticated": True,
            "caller_id": request.state.demo_caller,
            "auth_mode": settings.mode,
            "outbound_auth": request.app.state.workflow.identity_mode,
            "synthetic_only": True,
        }

    @app.post("/api/verify-backend", dependencies=[Depends(orchestration_caller)])
    async def verify_backend(request: Request) -> dict[str, object]:
        identity = await call(
            request, f"{resource}/.default", "GET", f"{backing_url}/api/identity-check"
        )
        stock = await call(
            request, f"{resource}/.default", "GET", f"{backing_url}/api/stock/MS01/DIESEL"
        )
        if stock.get("synthetic") is not True:
            raise HTTPException(502, "Backing response did not identify synthetic data.")
        return {
            "status": "verified",
            "outbound_auth": "managed_identity",
            "identity": identity,
            "stock": stock,
        }

    @app.post("/api/verify-foundry", dependencies=[Depends(orchestration_caller)])
    async def verify_foundry(request: Request) -> dict[str, object]:
        conversation = await call(
            request,
            "https://ai.azure.com/.default",
            "POST",
            f"{endpoint}/openai/v1/conversations",
            {"metadata": {"demo": "48254cc6", "purpose": "managed-identity-readiness"}},
        )
        if not isinstance(conversation.get("id"), str):
            raise HTTPException(502, "Native demo conversation identifier was not returned.")
        response = await call(
            request,
            "https://ai.azure.com/.default",
            "POST",
            f"{endpoint}/openai/v1/responses",
            {
                "conversation": conversation["id"],
                "input": "Run the synthetic-only readiness probe.",
                "stream": False,
                "agent_reference": {
                    "type": "agent_reference",
                    "name": "kppdemo-isolated-readiness-48254cc6",
                    "version": "1",
                },
            },
        )
        if response.get("status") != "completed":
            raise HTTPException(502, "Native demo workflow did not complete.")
        return {"status": "verified", "outbound_auth": "managed_identity", "response": response}

    @app.post("/api/normalize-result", dependencies=[Depends(normalization_caller)])
    def normalize_result(body: NormalizationRequest, request: Request) -> JSONResponse:
        mapping = request.app.state.workflow.mapping
        branch = next(item for item in mapping.branches if item.route == body.route)
        if branch.agent is None:
            raise RuntimeError("The frozen data branch does not bind a specialist.")
        result = normalize_specialist_result(
            body.response.model_dump(exclude_none=True), body.route, body.run_id,
            branch.agent.model_dump(),
        )
        return JSONResponse(
            result.model_dump(mode="json"),
            status_code=502 if result.status == "failed" else 200,
            headers={
                "x-kpp-provider-calls": "0",
                "x-kpp-source-sha256": mapping.source_sha256,
                "x-kpp-adapter": "normalization-only",
            },
        )

    @app.post("/api/run", dependencies=[Depends(orchestration_caller)])
    async def run_workflow(body: DemoRequest, request: Request) -> JSONResponse:
        try:
            output = await request.app.state.workflow.run(body)
        except (
            ClientAuthenticationError,
            DemoFoundryError,
            httpx.RequestError,
            WorkflowException,
            WorkflowExecutionError,
        ) as exc:
            logger.error("Demo workflow failed: %s run_id=%s", type(exc).__name__, body.run_id)
            raise HTTPException(
                502, {"code": "dependency_error", "run_id": str(body.run_id)}
            ) from exc
        return JSONResponse(
            output.result.model_dump(mode="json"),
            status_code=502 if output.result.status == "failed" else 200,
            headers={
                "x-kpp-framework": output.trace.framework_version,
                "x-kpp-source-sha256": output.trace.source_sha256,
                "x-kpp-conversation": output.trace.conversation_id,
                "x-kpp-executors": ",".join(output.trace.executors),
                "x-kpp-source-actions": ",".join(output.trace.source_actions),
                "x-kpp-native-responses": ",".join(
                    item.response_id for item in output.trace.agent_calls
                ),
                "x-kpp-outbound-auth": output.trace.outbound_auth,
            },
        )

    return app
