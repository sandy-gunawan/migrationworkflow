"""Explicit, separately authorized setup; never invoked by the UI server."""

import argparse
import base64
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx
from azure.core.credentials import TokenCredential
from azure.identity import AzureCliCredential

SUBSCRIPTION = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"
RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/demo_kpp"
    "/providers/Microsoft.Logic/workflows/kppdemo-mining-48254cc6"
)
ISSUER = "https://sts.windows.net/020201e2-0ae9-446c-8981-55a2bdecc00d/"
AUDIENCE = "https://management.azure.com"
POLICY_NAME = "demoLocalUiUser"
ROOT = Path(__file__).resolve().parents[2]


def configure_access(
    client: httpx.Client,
    credential: TokenCredential,
    approved_oid: str,
    *,
    apply: bool = False,
) -> dict:
    approved_oid = str(UUID(approved_oid))
    token = credential.get_token(AUDIENCE + "/.default")
    headers = {"Authorization": "Bearer " + token.token}
    url = AUDIENCE + RESOURCE_ID
    params = {"api-version": "2019-05-01"}
    response = client.get(url, params=params, headers=headers)
    response.raise_for_status()
    before = response.json()

    # This only confirms the approved CLI identity; Azure authorizes the bearer token.
    encoded = token.token.split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    if (
        claims.get("oid") != approved_oid
        or claims.get("iss") != ISSUER
        or claims.get("aud") != AUDIENCE
    ):
        raise ValueError("The current identity is not the specifically approved caller.")
    if before.get("tags", {}).get("demo_id") != "48254cc6":
        raise ValueError("Refusing to configure an unrelated workflow.")
    if before["identity"]["type"] != "SystemAssigned":
        raise ValueError("The approved workflow managed-identity type changed.")
    access = before["properties"]["accessControl"]
    trigger = access["triggers"]
    if trigger["sasAuthenticationPolicy"]["state"] != "Disabled":
        raise ValueError("SAS must already be Disabled.")
    policies = trigger["openAuthenticationPolicies"]["policies"]
    if "demoSetupManagedIdentity" not in policies:
        raise ValueError("The original setup-MI policy must already exist.")
    policy = {
        "type": "AAD",
        "claims": [
            {"name": "iss", "value": ISSUER},
            {"name": "aud", "value": AUDIENCE},
            {"name": "oid", "value": approved_oid},
        ],
    }
    if POLICY_NAME in policies and policies[POLICY_NAME] != policy:
        raise ValueError("Refusing to overwrite an existing different caller policy.")
    report = {
        "resource_id": RESOURCE_ID,
        "added_policy": POLICY_NAME,
        "pinned_claims": policy["claims"],
        "operation": "proposal_only",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not apply:
        return report
    updated = copy.deepcopy(access)
    updated["triggers"]["openAuthenticationPolicies"]["policies"][POLICY_NAME] = policy
    if POLICY_NAME not in policies:
        writable = {
            key: value
            for key, value in before["properties"].items()
            if key
            in (
                "definition",
                "parameters",
                "state",
                "integrationAccount",
                "integrationServiceEnvironment",
                "sku",
            )
        }
        writable["accessControl"] = updated
        body = {
            "location": before["location"],
            "tags": before["tags"],
            "identity": {"type": "SystemAssigned"},
            "properties": writable,
        }
        conditional = dict(headers)
        etag = response.headers.get("etag") or before.get("etag")
        if etag:
            conditional["If-Match"] = etag
        # Logic Apps rejects PATCH properties. PUT retains the existing definition.
        changed = client.put(url, params=params, headers=conditional, json=body)
        changed.raise_for_status()
        report["operation"] = "approved_existing_resource_access_update"
    else:
        report["operation"] = "approved_policy_already_present_no_write"
    readback = client.get(url, params=params, headers=headers)
    readback.raise_for_status()
    after = readback.json()
    for key in (
        "definition",
        "parameters",
        "state",
        "integrationAccount",
        "integrationServiceEnvironment",
        "sku",
    ):
        if before["properties"].get(key) != after["properties"].get(key):
            raise RuntimeError("A non-access workflow property changed: " + key)
    for key in ("identity", "location", "tags"):
        if before.get(key) != after.get(key):
            raise RuntimeError("An existing workflow resource property changed: " + key)
    if after["properties"]["accessControl"] != updated:
        raise RuntimeError("The authentication-policy read-back differs from the approved change.")
    report.update(
        {
            "workflow_definition_unchanged": True,
            "managed_identity_unchanged": True,
            "original_policies_preserved": True,
            "sas_authentication": "Disabled",
            "workflow_definition_sha256": hashlib.sha256(
                json.dumps(
                    after["properties"]["definition"],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        }
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-object-id", required=True)
    parser.add_argument(
        "--apply", action="store_true", help="Requires explicit administrator approval."
    )
    args = parser.parse_args()
    with (
        AzureCliCredential(subscription=SUBSCRIPTION) as credential,
        httpx.Client(timeout=60, follow_redirects=False) as client,
    ):
        try:
            report = configure_access(
                client,
                credential,
                args.approved_object_id,
                apply=args.apply,
            )
        except httpx.HTTPStatusError as error:
            parser.exit(
                1,
                f"Azure rejected access setup: {error.response.status_code} "
                f"{error.response.text[:1800]}\n",
            )
    if args.apply:
        folder = ROOT / "evidence" / "local-ui"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "logicapps-access.json").write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
