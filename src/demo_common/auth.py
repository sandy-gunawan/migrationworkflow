import asyncio
import logging
import os
import secrets
from dataclasses import dataclass
from typing import Callable, Literal
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)
KeyResolver = Callable[[str], str | RSAPublicKey]


@dataclass(frozen=True)
class AuthSettings:
    tenant_id: str
    audience: str
    allowed_callers: frozenset[str]
    mode: Literal["entra", "key_trial"] = "entra"
    trial_key: str | None = None

    def __post_init__(self) -> None:
        UUID(self.tenant_id)
        UUID(self.audience)
        if not self.allowed_callers:
            raise ValueError("An explicit demo caller allowlist is required.")
        for caller in self.allowed_callers:
            UUID(caller)
        if self.mode not in ("entra", "key_trial"):
            raise ValueError("Unsupported authentication mode.")
        if self.mode == "key_trial" and (not self.trial_key or len(self.trial_key) < 32):
            raise ValueError("Key trial requires an explicitly configured strong temporary key.")

    @classmethod
    def from_env(cls) -> "AuthSettings":
        mode = os.environ.get("DEMO_AUTH_MODE", "entra")
        if mode not in ("entra", "key_trial"):
            raise ValueError("DEMO_AUTH_MODE must be entra or key_trial.")
        return cls(
            tenant_id=os.environ["DEMO_TENANT_ID"],
            audience=os.environ["DEMO_API_AUDIENCE"],
            allowed_callers=frozenset(
                item.strip()
                for item in os.environ["DEMO_ALLOWED_CALLER_IDS"].split(",")
                if item.strip()
            ),
            mode=mode,
            trial_key=os.environ.get("DEMO_API_TRIAL_KEY"),
        )


class Authorizer:
    def __init__(self, settings: AuthSettings, key_resolver: KeyResolver | None = None):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{settings.tenant_id}/discovery/v2.0/keys",
            timeout=5,
        )
        self.key_resolver = key_resolver

    def authorize(self, headers: Headers) -> str:
        if self.settings.mode == "key_trial":
            supplied = headers.get("x-api-key", "")
            configured = self.settings.trial_key
            if not configured or not supplied or not secrets.compare_digest(supplied, configured):
                raise HTTPException(401, "A valid temporary demo key is required.")
            return "temporary-key-trial"

        scheme, _, token = headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(401, "A Microsoft Entra bearer token is required.")
        try:
            key = (
                self.key_resolver(token)
                if self.key_resolver
                else self.jwks.get_signing_key_from_jwt(token).key
            )
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=f"https://login.microsoftonline.com/{self.settings.tenant_id}/v2.0",
                leeway=30,
                options={"require": ["exp", "iat", "aud", "iss", "oid", "tid"]},
            )
        except PyJWKClientConnectionError as exc:
            logger.error("Demo authentication key service is unavailable.")
            raise HTTPException(503, "Authentication key service is unavailable.") from exc
        except (jwt.InvalidTokenError, PyJWKClientError) as exc:
            raise HTTPException(401, "Invalid or expired demo access token.") from exc
        if claims["tid"] != self.settings.tenant_id:
            raise HTTPException(401, "Token tenant is not the configured demo tenant.")
        caller = claims["oid"]
        if caller not in self.settings.allowed_callers:
            raise HTTPException(403, "Caller is not authorized for this isolated demo.")
        return caller


class DemoAuthMiddleware:
    def __init__(self, app: ASGIApp, authorizer: Authorizer):
        self.app = app
        self.authorizer = authorizer

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope["path"] == "/health" and scope["method"] in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return
        try:
            caller = await asyncio.to_thread(self.authorizer.authorize, Headers(scope=scope))
        except HTTPException as exc:
            logger.warning("Demo request denied: status=%s path=%s", exc.status_code, scope["path"])
            headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {}
            await JSONResponse(
                {"error": {"code": "access_denied", "message": exc.detail}},
                status_code=exc.status_code,
                headers=headers,
            )(scope, receive, send)
            return
        scope.setdefault("state", {})["demo_caller"] = caller
        await self.app(scope, receive, send)
