import base64
import copy
import json

import httpx
import pytest
from azure.core.credentials import AccessToken

from spikes.logicapps_ui.access import AUDIENCE, ISSUER, POLICY_NAME, configure_access

OID = "00000000-0000-4000-8000-000000000001"


class FixtureCredential:
    def get_token(self, *scopes):
        payload = (
            base64.urlsafe_b64encode(
                json.dumps({"iss": ISSUER, "aud": AUDIENCE, "oid": OID}).encode()
            )
            .decode()
            .rstrip("=")
        )
        return AccessToken("fixture." + payload + ".fixture", 9999999999)


def original_workflow():
    return {
        "id": "owned-fixture",
        "location": "southeastasia",
        "tags": {"demo_id": "48254cc6"},
        "identity": {"type": "SystemAssigned", "principalId": "fixture-mi"},
        "properties": {
            "state": "Enabled",
            "definition": {"actions": {"fixture": {"type": "Compose", "inputs": "unchanged"}}},
            "parameters": {},
            "accessControl": {
                "triggers": {
                    "sasAuthenticationPolicy": {"state": "Disabled"},
                    "openAuthenticationPolicies": {
                        "policies": {
                            "demoSetupManagedIdentity": {
                                "type": "AAD",
                                "claims": [{"name": "oid", "value": "fixture-setup-mi"}],
                            }
                        }
                    },
                }
            },
        },
    }


def test_approved_policy_update_preserves_definition_identity_and_existing_policies():
    current = original_workflow()
    before = copy.deepcopy(current)
    writes = []

    def handle(request):
        if request.method == "PUT":
            body = json.loads(request.content)
            writes.append(body)
            current["properties"] = body["properties"]
            return httpx.Response(200, json=current)
        return httpx.Response(200, json=current)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        report = configure_access(client, FixtureCredential(), OID, apply=True)
    assert len(writes) == 1
    assert writes[0]["properties"]["definition"] == before["properties"]["definition"]
    assert current["identity"] == before["identity"]
    trigger = current["properties"]["accessControl"]["triggers"]
    policies = trigger["openAuthenticationPolicies"]["policies"]
    assert (
        policies["demoSetupManagedIdentity"]
        == (
            before["properties"]["accessControl"]["triggers"]["openAuthenticationPolicies"][
                "policies"
            ]["demoSetupManagedIdentity"]
        )
    )
    assert {claim["name"]: claim["value"] for claim in policies[POLICY_NAME]["claims"]} == {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "oid": OID,
    }
    assert trigger["sasAuthenticationPolicy"]["state"] == "Disabled"
    assert report["workflow_definition_unchanged"] is True


def test_unapproved_caller_cannot_change_cloud_access():
    requests = []

    def handle(request):
        requests.append(request.method)
        return httpx.Response(200, json=original_workflow())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="approved"):
            configure_access(
                client,
                FixtureCredential(),
                "00000000-0000-4000-8000-000000000002",
                apply=True,
            )
    assert "PUT" not in requests


def test_default_inspection_does_not_grant_access():
    methods = []

    def handle(request):
        methods.append(request.method)
        return httpx.Response(200, json=original_workflow())

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        report = configure_access(client, FixtureCredential(), OID)
    assert methods == ["GET"]
    assert report["operation"] == "proposal_only"
