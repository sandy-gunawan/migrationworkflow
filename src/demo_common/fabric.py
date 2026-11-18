import json
import logging
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from uuid import UUID

import httpx
from azure.core.credentials import TokenCredential

from demo_common.environment import ENVIRONMENT

logger = logging.getLogger(__name__)
API = "https://api.fabric.microsoft.com/v1"
SUBSCRIPTION = ENVIRONMENT.subscription_id
WORKSPACE = ENVIRONMENT.fabric_workspace_id
LAKEHOUSE = ENVIRONMENT.fabric_lakehouse_id
US_WORKSPACE = ENVIRONMENT.fabric_us_workspace_id
CAPACITY = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{ENVIRONMENT.resource_group}"
    f"/providers/Microsoft.Fabric/capacities/{ENVIRONMENT.fabric_capacity}"
)
US_CAPACITY = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{ENVIRONMENT.resource_group}"
    f"/providers/Microsoft.Fabric/capacities/{ENVIRONMENT.fabric_us_capacity}"
)


def require_demo_fabric_path(path: str, workspace: str = WORKSPACE) -> str:
    if workspace not in (WORKSPACE, US_WORKSPACE):
        raise ValueError("Fabric workspace has no demo creation receipt.")
    if "?" in path or "#" in path or "\\" in path or ".." in path or "%" in path:
        raise ValueError("Unsafe Fabric path.")
    if path == f"/workspaces/{workspace}" or path.startswith(f"/workspaces/{workspace}/"):
        if any(part.lower() in ("delete", "deleteall", "reset") for part in path.split("/")):
            raise ValueError("Destructive Fabric operations are not allowed.")
        return f"{API}{path}"
    if re.fullmatch(r"/operations/[0-9a-fA-F-]{36}(/result)?", path):
        UUID(path.split("/")[2])
        return f"{API}{path}"
    raise ValueError("Only the newly created demo workspace and its operations are allowed.")


class DemoFabric:
    def __init__(
        self,
        credential: TokenCredential,
        client: httpx.Client,
        evidence_root: Path,
        workspace: str = WORKSPACE,
    ) -> None:
        require_demo_fabric_path(f"/workspaces/{workspace}", workspace)
        self.credential = credential
        self.client = client
        self.evidence_root = evidence_root
        self.workspace = workspace
        self.capacity_id = US_CAPACITY if workspace == US_WORKSPACE else CAPACITY

    def request(
        self, method: str, path: str, body: object = None, params: dict | None = None
    ) -> httpx.Response:
        if method not in ("GET", "POST", "PATCH"):
            raise ValueError("Only demo read/create/configuration operations are allowed.")
        url = require_demo_fabric_path(path, self.workspace)
        token = self.credential.get_token("https://api.fabric.microsoft.com/.default")
        response = self.client.request(
            method,
            url,
            json=body,
            params=params,
            headers={"Authorization": f"Bearer {token.token}"},
        )
        if response.is_error:
            raise RuntimeError(
                f"Demo Fabric {method} {path}: HTTP {response.status_code}: {response.text[:2000]}"
            )
        return response

    def finish(self, response: httpx.Response, *, resource: bool) -> dict:
        if response.status_code == 202:
            operation = response.headers.get("x-ms-operation-id")
            if not operation:
                location = urlparse(response.headers.get("location", ""))
                if location.hostname != "api.fabric.microsoft.com":
                    raise RuntimeError("Fabric did not return a canonical operation identifier.")
                operation = location.path.rsplit("/", 1)[-1]
            operation = str(UUID(operation))
            deadline = time.monotonic() + 420
            while time.monotonic() < deadline:
                status = self.request("GET", f"/operations/{operation}").json()
                if status.get("status") == "Succeeded":
                    if resource:
                        return self.request("GET", f"/operations/{operation}/result").json()
                    return status
                if status.get("status") in ("Failed", "Cancelled"):
                    raise RuntimeError(f"Native demo operation failed: {status}")
                time.sleep(5)
            raise TimeoutError("Native demo Fabric operation did not complete in 420 seconds.")
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(f"Unexpected Fabric completion status {response.status_code}.")
        if resource:
            value = response.json()
            if not isinstance(value, dict):
                raise RuntimeError("Expected a native Fabric resource object.")
            return value
        return {"http_status": response.status_code}

    def capacity(self, action: str | None = None) -> dict:
        token = self.credential.get_token("https://management.azure.com/.default")
        url = f"https://management.azure.com{self.capacity_id}"
        headers = {"Authorization": f"Bearer {token.token}"}
        current = self.client.get(
            url, params={"api-version": "2026-09-01-preview"}, headers=headers
        )
        current.raise_for_status()
        data = current.json()
        if data.get("tags", {}).get("demo_id") != "48254cc6" or data["sku"]["name"] != "F2":
            raise RuntimeError("Refusing to configure an unrelated or non-demo Fabric capacity.")
        if action is None:
            return data
        if action not in ("resume", "suspend"):
            raise ValueError("Only resume/pause is permitted for the owned demo capacity.")
        wanted = "Active" if action == "resume" else "Paused"
        if data["properties"]["state"] != wanted:
            response = self.client.post(
                f"{url}/{action}", params={"api-version": "2023-11-01"}, headers=headers
            )
            response.raise_for_status()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            response = self.client.get(
                url, params={"api-version": "2026-09-01-preview"}, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            if data["properties"]["state"] == wanted:
                return data
            time.sleep(5)
        raise TimeoutError(f"Demo capacity did not enter {wanted} state.")

    @contextmanager
    def active_capacity(self, *, observer: Callable[[str, dict | None], None] | None = None):
        try:
            if observer:
                observer("resuming", None)
            active = self.capacity("resume")
            if observer:
                observer("active", active)
            logger.info("Owned demo F2 is Active.")
            yield
        finally:
            try:
                if observer:
                    observer("pausing", None)
            finally:
                paused = self.capacity("suspend")
                proof = {
                    "resourceId": paused["id"],
                    "sku": paused["sku"]["name"],
                    "state": paused["properties"]["state"],
                    "overage": paused["properties"]["overage"],
                    "checked_at_unix": time.time(),
                    "reason": "Pause only new demo capacity after the bounded native operation.",
                }
                filename = (
                    "fabric-us-idle.json" if self.workspace == US_WORKSPACE else "fabric-idle.json"
                )
                target = self.evidence_root / "cost" / filename
                target.parent.mkdir(exist_ok=True, parents=True)
                target.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
                logger.info("Owned demo F2 is Paused.")
                if observer:
                    observer("paused", paused)
