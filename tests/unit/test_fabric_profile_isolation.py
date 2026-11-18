import time

import httpx
import pytest
from azure.core.credentials import AccessToken

from demo_common.fabric import (
    US_CAPACITY,
    US_WORKSPACE,
    WORKSPACE,
    DemoFabric,
    require_demo_fabric_path,
)


def test_us_native_calls_cannot_read_the_retained_singapore_workspace():
    with pytest.raises(ValueError):
        require_demo_fabric_path(f"/workspaces/{WORKSPACE}/items", US_WORKSPACE)


def test_scope_cannot_be_set_to_an_unowned_existing_workspace():
    other = "00000000-0000-0000-0000-000000000001"
    with pytest.raises(ValueError, match="receipt"):
        require_demo_fabric_path(f"/workspaces/{other}/items", other)


@pytest.mark.parametrize("failure_at", ["native", "active", "pausing"])
def test_native_failure_still_pauses_only_the_owned_us_capacity(tmp_path, failure_at):
    state = "Paused"
    actions = []

    class Credential:
        def get_token(self, *scopes, **kwargs):
            return AccessToken("local-unit-fixture", int(time.time()) + 600)

    def handle(request):
        nonlocal state
        assert request.url.path.startswith(US_CAPACITY)
        if request.method == "POST":
            action = request.url.path.rsplit("/", 1)[-1]
            actions.append(action)
            state = "Active" if action == "resume" else "Paused"
            return httpx.Response(200)
        return httpx.Response(
            200,
            json={
                "id": US_CAPACITY,
                "sku": {"name": "F2"},
                "tags": {"demo_id": "48254cc6"},
                "properties": {"state": state, "overage": {"state": "Disabled"}},
            },
        )

    def observer(stage, value):
        if stage == failure_at:
            raise RuntimeError("native failure")

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        fabric = DemoFabric(Credential(), client, tmp_path, US_WORKSPACE)
        with pytest.raises(RuntimeError, match="native failure"):
            with fabric.active_capacity(observer=observer):
                assert state == "Active"
                if failure_at == "native":
                    raise RuntimeError("native failure")
    assert actions == ["resume", "suspend"]
    assert state == "Paused"
