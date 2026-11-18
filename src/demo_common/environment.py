import logging
import os
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)
Guid = Annotated[
    str, Field(pattern=r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
]
ResourceName = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._()-]{0,89}$")]
HostName = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")]


class DemoEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    subscription_id: Guid = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"
    tenant_id: Guid = "020201e2-0ae9-446c-8981-55a2bdecc00d"
    resource_group: ResourceName = "demo_kpp"
    foundry_resource_group: ResourceName = "foundry"
    foundry_account: HostName = "kppfoundry48254cc6"
    foundry_project: ResourceName = "kpp-mining-demo"
    backing_app: HostName = "kppdemo-data-48254cc6"
    maf_app: HostName = "kppdemo-maf-48254cc6"
    search_service: HostName = "kppsearch48254cc6"
    api_audience: Guid = "551b356f-3265-4a3e-8b87-95704b5f503c"
    verification_caller_id: Guid = "50d57e04-3ed5-4123-bf9f-e3a8739009c9"
    fabric_workspace_id: Guid = "401a89de-027b-4eda-96f0-fc47ab759fe2"
    fabric_lakehouse_id: Guid = "b8a09a09-36ae-4fc3-a71c-7a60404d25bb"
    fabric_us_workspace_id: Guid = "d4c8c862-17ae-47ef-8b96-5c763494d2b8"
    fabric_capacity: ResourceName = "kppfabric48254cc6"
    fabric_us_capacity: ResourceName = "kppfabricus48254cc6"
    logicapp_name: ResourceName = "kppdemo-mining-48254cc6"

    @property
    def foundry_endpoint(self) -> str:
        return (
            f"https://{self.foundry_account}.services.ai.azure.com"
            f"/api/projects/{self.foundry_project}"
        )

    @property
    def foundry_project_id(self) -> str:
        return (
            f"/subscriptions/{self.subscription_id}/resourceGroups/{self.foundry_resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.foundry_account}"
            f"/projects/{self.foundry_project}"
        )

    @property
    def backing_url(self) -> str:
        return f"https://{self.backing_app}.azurewebsites.net"

    @property
    def maf_url(self) -> str:
        return f"https://{self.maf_app}.azurewebsites.net"

    @property
    def search_url(self) -> str:
        return f"https://{self.search_service}.search.windows.net"


def load_environment(path: Path | None = None) -> DemoEnvironment:
    configured = os.environ.get("DEMO_ENVIRONMENT_FILE")
    if path is None and configured is None:
        return DemoEnvironment()
    if path is None:
        if not configured or not configured.strip():
            raise ValueError("DEMO_ENVIRONMENT_FILE must name an existing configuration file.")
        path = Path(configured)
    try:
        environment = DemoEnvironment.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except ValidationError as error:
        fields = sorted({".".join(map(str, item["loc"])) or "JSON" for item in error.errors()})
        logger.error("Invalid demo environment configuration fields: %s", ", ".join(fields))
        raise ValueError(
            "Invalid demo environment configuration; check fields: " + ", ".join(fields)
        ) from None
    missing = DemoEnvironment.model_fields.keys() - environment.model_fields_set
    if missing:
        raise ValueError(
            "A custom environment must specify every field; missing: " + ", ".join(sorted(missing))
        )
    if environment.fabric_workspace_id == environment.fabric_us_workspace_id:
        raise ValueError("The retained and native Fabric workspaces must be different.")
    return environment


ENVIRONMENT = load_environment()
