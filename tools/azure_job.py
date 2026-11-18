"""One-shot Azure-side ZIP publisher and MI verifier for the isolated demo."""

import base64
import ctypes
import hashlib
import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from importlib.metadata import distributions
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SUBSCRIPTION = "5a7c13bd-9a15-4380-ba67-4d972838bc0b"
AUDIENCE = "api://551b356f-3265-4a3e-8b87-95704b5f503c"
MAF = "https://kppdemo-maf-48254cc6.azurewebsites.net"
BACKING = "https://kppdemo-data-48254cc6.azurewebsites.net"
SCM = "https://kppdemo-maf-48254cc6.scm.azurewebsites.net"
MAF_PRINCIPAL = "a3e7b9e6-4908-4b10-a0a6-ad14587b6bb3"
SOURCE_SHA256 = "8a1b3b54903f26864bf81fad662e847cc97df18a945f536db9ff78b90aa4a8e1"
CORPUS_SHA256 = "b4faabfcff03c37b2e99a3c890d309b5f9e8e42b2d53d85e0a83b87e1ed86c77"
PIP_URL = (
    "https://files.pythonhosted.org/packages/44/3c/"
    "d717024885424591d5376220b5e836c2d5293ce2011523c9de23ff7bf068/"
    "pip-25.3-py3-none-any.whl"
)
PIP_SHA256 = "9655943313a94722b7774661c21049070f6bbb0a1516bf02f7c8d5d9201514cd"
LOGIC_ID = (
    f"/subscriptions/{SUBSCRIPTION}/resourceGroups/demo_kpp"
    "/providers/Microsoft.Logic/workflows/kppdemo-mining-48254cc6"
)


def drop_setup_privileges() -> dict:
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(1000)
        os.setuid(1000)
    if os.geteuid() != 1000 or os.getegid() != 1000 or 0 in os.getgroups():
        raise RuntimeError("The deployment job must run as non-root UID/GID 1000.")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Unable to set Linux no_new_privs.")
    status = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        key, _, value = line.partition(":")
        status[key] = value.strip()
    if (
        any(int(status[name], 16) != 0 for name in ("CapEff", "CapPrm", "CapAmb"))
        or status["NoNewPrivs"] != "1"
    ):
        raise RuntimeError("The deployment process retained Linux privileges.")
    return {"uid": 1000, "gid": 1000, "effective_capabilities": 0, "no_new_privs": True}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def command(args: list[str], *, timeout: int = 900, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    if completed.returncode:
        diagnostic = ""
        if not any(value in args for value in ("login", "get-access-token")):
            diagnostic = re.sub(
                r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
                "[REDACTED_TOKEN]", completed.stderr[-1800:],
            )
        raise RuntimeError(
            f"Command {args[0]} {args[1]} exited {completed.returncode}. {diagnostic}"
        )
    return completed.stdout


def az(*args: str, timeout: int = 900):
    output = command(["az", *args, "--only-show-errors", "-o", "json"], timeout=timeout)
    return json.loads(output) if output.strip() else None


def token(resource: str) -> str:
    result = az(
        "account", "get-access-token", "--resource", resource,
        "--subscription", SUBSCRIPTION, timeout=90,
    )
    return result["accessToken"]


def request(method: str, path: str, *, access_token: str | None = None, body=None, host=MAF):
    if host not in (MAF, BACKING) or not path.startswith("/"):
        raise ValueError("Only the two owned demo endpoints may be probed.")
    headers = {"Content-Type": "application/json"}
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    req = urllib.request.Request(
        f"{host}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(req, timeout=240)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        text = response.read().decode("utf-8")
        try:
            body = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"Demo endpoint returned non-JSON HTTP {response.status}."
            ) from error
        return response.status, body, dict(response.headers.items())


def pip_environment(work: Path) -> dict[str, str]:
    # The official CLI image has no system pip; use an isolated, verified public wheel.
    with urllib.request.urlopen(PIP_URL, timeout=60) as response:
        wheel = response.read()
    if hashlib.sha256(wheel).hexdigest() != PIP_SHA256:
        raise RuntimeError("The official pip wheel failed SHA-256 verification.")
    path = work / "pip-25.3-py3-none-any.whl"
    path.write_bytes(wheel)
    return {**os.environ, "PYTHONPATH": str(path)}


def prepare_package(work: Path) -> tuple[Path, dict]:
    source = base64.b64decode(os.environ["KPP_SOURCE_ZIP"], validate=True)
    requirements = base64.b64decode(os.environ["KPP_REQUIREMENTS"], validate=True)
    root = work / "site"
    root.mkdir()
    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        for name in archive.namelist():
            path = Path(name)
            if (
                path.is_absolute() or ".." in path.parts or "\\" in name
                or name.startswith(".python_packages/") or ".env" in name
            ):
                raise ValueError("Unsafe or unexpected source ZIP member.")
        if archive.testzip() is not None:
            raise ValueError("Source ZIP integrity failed.")
        archive.extractall(root)
    source_path = root / "maf_service" / "resources" / "source.workflow.yaml"
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("The package does not contain the frozen native source.")
    lock = work / "requirements.linux.txt"
    lock.write_bytes(requirements)
    dependencies = root / ".python_packages" / "lib" / "site-packages"
    command(
        [
            sys.executable, "-m", "pip", "install", "--target", str(dependencies),
            "--no-deps", "--no-compile", "--only-binary=:all:",
            "--platform", "manylinux_2_28_x86_64", "--platform", "manylinux_2_17_x86_64",
            "--platform", "manylinux2014_x86_64", "--implementation", "cp",
            "--python-version", "3.13", "--abi", "cp313", "--abi", "abi3",
            "--disable-pip-version-check", "-r", str(lock),
        ],
        timeout=1200,
        env=pip_environment(work),
    )
    expected = {}
    for line in requirements.decode("ascii").splitlines():
        name, exact_version = line.split("==")
        expected[re.sub(r"[-_.]+", "-", name).lower()] = exact_version
    installed = {
        re.sub(r"[-_.]+", "-", item.metadata["Name"]).lower(): item.version
        for item in distributions(path=[str(dependencies)])
    }
    if installed != expected:
        raise RuntimeError("Azure Linux wheel versions do not match the verified lock.")
    destination = work / "maf-linux.zip"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if not path.is_file() or "__pycache__" in relative.parts or path.suffix == ".pyc":
                continue
            if relative.parts[:3] == (".python_packages", "lib", "site-packages"):
                if len(relative.parts) > 3 and relative.parts[3].lower() in ("bin", "scripts"):
                    continue
            if path.suffix.lower() in (".pyd", ".dll", ".exe"):
                raise RuntimeError("A Windows binary cannot enter the Linux deployment.")
            archive.write(path, relative)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Azure-built deployment ZIP integrity failed.")
    return destination, {
        "source_zip_sha256": hashlib.sha256(source).hexdigest(),
        "linux_zip_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "linux_requirements_sha256": hashlib.sha256(requirements).hexdigest(),
        "package_count": len(installed),
        "versions_match_verified_linux_lock": True,
    }


def require_status(response, expected: int, step: str):
    status, body, headers = response
    if status != expected:
        raise RuntimeError(f"{step}: expected HTTP {expected}, received {status}.")
    return body, {name.lower(): value for name, value in headers.items()}


def compare_result(case: dict, result: dict, seconds: float) -> dict:
    text = re.sub(
        r"(?<=\d),(?=\d)", "",
        json.dumps({"answer": result["answer"], "sources": result["sources"]}),
    ).upper()
    sources = {
        item["id"].removeprefix("urn:kppdemo:knowledge/") for item in result["sources"]
    }
    return {
        "case_id": case["id"],
        "route_match": result["route"] == case["route"],
        "status_match": result["status"] == case["expected_status"],
        "facts_pass": all(item.upper() in text for item in case["facts"]),
        "sources_pass": all(
            item.removeprefix("urn:kppdemo:knowledge/") in sources for item in case["sources"]
        ),
        "seconds": round(seconds, 2),
        "result": result,
    }


def verify_maf(test_data: dict) -> dict:
    cases_bytes = base64.b64decode(test_data["corpus_base64"], validate=True)
    if hashlib.sha256(cases_bytes).hexdigest() != CORPUS_SHA256:
        raise ValueError("The original 50-case corpus changed.")
    cases = json.loads(cases_bytes)["cases"]
    if len(cases) != 50:
        raise ValueError("The original 50 cases are required.")
    ready_deadline = time.monotonic() + 180
    while True:
        try:
            health, _ = require_status(request("GET", "/health"), 200, "MAF readiness")
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            if time.monotonic() >= ready_deadline:
                raise
            time.sleep(10)
            continue
        if health.get("workflow_configured") and health.get("source_sha256") == SOURCE_SHA256:
            break
        if time.monotonic() >= ready_deadline:
            raise RuntimeError(f"Hosted source-derived readiness failed: {json.dumps(health)}")
        time.sleep(10)
    payload = {"question": "Tell me about MS01."}
    require_status(request("POST", "/api/run", body=payload), 401, "anonymous access")
    require_status(
        request("POST", "/api/run", body=payload, access_token="invalid"),
        401, "invalid bearer",
    )
    require_status(
        request(
            "POST", "/api/run", body=payload,
            access_token=token("https://management.azure.com/"),
        ),
        401, "wrong-audience token",
    )
    api_token = token(AUDIENCE)
    identity, _ = require_status(
        request("GET", "/api/identity-check", access_token=api_token), 200, "incoming MI",
    )
    if (
        identity["caller_id"] != test_data["principal_id"]
        or identity["auth_mode"] != "entra" or identity["outbound_auth"] != "managed_identity"
    ):
        raise RuntimeError("The hosted caller/runtime is not the expected Managed Identity.")
    require_status(
        request("GET", "/api/identity-check", host=BACKING, access_token=api_token),
        403, "setup identity denied direct backing access",
    )
    require_status(
        request(
            "POST", "/api/run", access_token=api_token,
            body={**payload, "route": "mcp"},
        ),
        422, "route override",
    )
    backend, _ = require_status(
        request("POST", "/api/verify-backend", access_token=api_token), 200, "outgoing MI",
    )
    if (
        backend["identity"]["caller_id"] != MAF_PRINCIPAL
        or backend["stock"].get("synthetic") is not True
        or backend["stock"].get("data", {}).get("quantity") != 18000
    ):
        raise RuntimeError("MAF did not retrieve the expected backing record using its own MI.")
    foundry, _ = require_status(
        request("POST", "/api/verify-foundry", access_token=api_token),
        200, "Foundry MI readiness",
    )
    records = []
    started = time.monotonic()
    for case in cases:
        if time.monotonic() - started > 1800:
            raise RuntimeError("The hosted MAF gate exceeded its 30-minute test budget.")
        case_started = time.monotonic()
        run_id = test_data["run_ids"][case["id"]]
        result, headers = require_status(
            request(
                "POST", "/api/run", access_token=api_token,
                body={"question": case["question"], "run_id": run_id},
            ),
            200, f"case {case['id']}",
        )
        proof = {name: value for name, value in headers.items() if name.startswith("x-kpp-")}
        if (
            proof.get("x-kpp-framework") != "1.11.0"
            or proof.get("x-kpp-source-sha256") != SOURCE_SHA256
            or proof.get("x-kpp-outbound-auth") != "managed_identity"
            or result["run_id"] != run_id
        ):
            raise RuntimeError(
                "Hosted execution lacks the expected SDK/source/MI/correlation proof."
            )
        expected_calls = 2 if case["expected_status"] == "success" else 1
        if len(proof["x-kpp-native-responses"].split(",")) != expected_calls:
            raise RuntimeError("Unexpected specialist dispatch count in hosted execution.")
        record = compare_result(case, result, time.monotonic() - case_started)
        record["execution_headers"] = proof
        records.append(record)
        print(f"Hosted MAF {case['id']}: {result['route']} / {result['status']}", flush=True)
        if not all(record[key] for key in ("status_match", "facts_pass", "sources_pass")):
            raise RuntimeError(f"Hosted factual/status/source parity failed for {case['id']}.")
    accuracy = sum(item["route_match"] for item in records) / 50
    if accuracy < 0.98:
        raise RuntimeError("Hosted routing accuracy is below the original threshold.")
    return {
        "hosted_managed_identity_gate": "PASS",
        "case_count": 50,
        "classification_accuracy": accuracy,
        "actual_status_counts": dict(Counter(item["result"]["status"] for item in records)),
        "source_sha256": SOURCE_SHA256,
        "corpus_sha256": CORPUS_SHA256,
        "framework_version": "1.11.0",
        "incoming_identity": identity,
        "outgoing_identity": backend["identity"],
        "foundry_readiness_response_id": foundry["response"]["id"],
        "anonymous_invalid_and_wrong_audience": "REJECTED",
        "setup_identity_direct_backing_access": "REJECTED_403",
        "route_override": "REJECTED_422",
        "full_seven_provider_status": "BLOCKED",
        "results": records,
    }


def require_logic_callback(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or not parsed.hostname
        or not parsed.hostname.endswith(".logic.azure.com")
        or parsed.username or parsed.password or parsed.fragment
        or not re.fullmatch(
            r"/workflows/[A-Za-z0-9_-]+/triggers/kpp_mining_start/paths/invoke", parsed.path
        )
        or set(parse_qs(parsed.query, keep_blank_values=True)) != {"api-version"}
    ):
        raise ValueError("Only the unsigned owned Logic Apps callback is permitted.")
    return url


def logic_request(url: str, body: dict, access_token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    req = urllib.request.Request(
        require_logic_callback(url), data=json.dumps(body).encode(), headers=headers, method="POST",
    )
    try:
        response = urllib.request.build_opener(NoRedirect).open(req, timeout=240)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        text = response.read().decode("utf-8")
        try:
            value = json.loads(text) if text else None
        except json.JSONDecodeError as error:
            if response.status < 400:
                raise RuntimeError(
                    f"Logic Apps returned non-JSON HTTP {response.status}."
                ) from error
            value = {"error": {"code": "non_json_error_response"}}
        return response.status, value, dict(response.headers.items())


def logic_management(path: str = "") -> dict:
    if path and not re.fullmatch(
        r"/runs/[A-Za-z0-9_-]+(/actions)?", path,
    ):
        raise ValueError("Only the new Logic App and its native run/action metadata may be read.")
    return az(
        "rest", "--method", "get", "--url",
        f"https://management.azure.com{LOGIC_ID}{path}?api-version=2016-06-01",
        timeout=90,
    )


def logic_actions(native_run: str) -> list[dict]:
    path = f"/runs/{native_run}/actions"
    page = logic_management(path)
    actions = []
    seen = set()
    for _ in range(10):
        actions.extend(page["value"])
        link = page.get("nextLink")
        if not link:
            return actions
        parsed = urlsplit(link)
        if (
            parsed.scheme != "https" or parsed.hostname != "management.azure.com"
            or parsed.username or parsed.password or parsed.fragment
            or parsed.path.lower() != f"{LOGIC_ID}{path}".lower()
        ):
            raise ValueError("Pagination may only follow the same owned action history.")
        if link in seen:
            raise RuntimeError("The native action-history pagination repeated a page.")
        seen.add(link)
        page = az("rest", "--method", "get", "--url", link, timeout=90)
    raise RuntimeError("Native action-history pagination exceeded ten pages.")


def verify_logic(test_data: dict) -> dict:
    callback = require_logic_callback(test_data["logic_callback"])
    native = logic_management()
    properties = native["properties"]
    access = properties["accessControl"]["triggers"]
    if (
        native.get("tags", {}).get("demo_id") != "48254cc6"
        or native["identity"]["principalId"] != test_data["logic_principal_id"]
        or properties["state"] != "Enabled"
        or access["sasAuthenticationPolicy"]["state"] != "Disabled"
    ):
        raise RuntimeError("The live Logic App does not have the owned identity/security state.")
    definition_text = json.dumps(properties["definition"])
    if (
        "/api/run" in definition_text or "/api/normalize-result" not in definition_text
        or SOURCE_SHA256 not in definition_text
    ):
        raise RuntimeError("The actual Logic Apps definition is not source-bound native routing.")
    claims = access["openAuthenticationPolicies"]["policies"]["demoSetupManagedIdentity"]["claims"]
    if {item["name"]: item["value"] for item in claims}.get("oid") != test_data["principal_id"]:
        raise RuntimeError("The request policy does not pin the intended setup MI.")
    corpus_bytes = base64.b64decode(test_data["corpus_base64"], validate=True)
    if hashlib.sha256(corpus_bytes).hexdigest() != CORPUS_SHA256:
        raise RuntimeError("The frozen Logic Apps comparison corpus changed.")
    cases = json.loads(corpus_bytes)["cases"]
    if len(cases) != 50:
        raise RuntimeError("All original 50 cases are required.")
    payload = {"question": "Tell me about MS01."}
    for label, credential in (("anonymous", None), ("invalid", "invalid")):
        response = logic_request(callback, payload, credential)
        if response[0] not in (401, 403):
            raise RuntimeError(f"Logic Apps {label} access was not rejected: HTTP {response[0]}.")
    wrong_audience = token(AUDIENCE)
    if logic_request(callback, payload, wrong_audience)[0] not in (401, 403):
        raise RuntimeError("Logic Apps accepted a wrong-audience bearer token.")
    normalizer_deadline = time.monotonic() + 180
    while True:
        rejected = request(
            "POST", "/api/normalize-result", access_token=wrong_audience,
            body={"route": "mcp", "run_id": next(iter(test_data["run_ids"].values())),
                  "response": {"status": "completed", "output": []}},
        )
        if rejected[0] == 503 and time.monotonic() < normalizer_deadline:
            print("Waiting for the configured normalization-only boundary to start.", flush=True)
            time.sleep(10)
            continue
        require_status(rejected, 403, "setup identity denied normalization-only access")
        break
    arm_token = token("https://management.azure.com/")
    overridden = logic_request(callback, {**payload, "route": "mcp"}, arm_token)
    if overridden[0] != 400:
        raise RuntimeError(f"Route override returned HTTP {overridden[0]}, expected 400.")
    records = []
    started = time.monotonic()
    for case in cases:
        if time.monotonic() - started > 1800:
            raise RuntimeError("The Logic Apps comparison exceeded 30 minutes.")
        case_started = time.monotonic()
        run_id = test_data["run_ids"][case["id"]]
        response = logic_request(
            callback, {"question": case["question"], "run_id": run_id}, arm_token,
        )
        if response[0] != 200:
            failed_headers = {name.lower(): value for name, value in response[2].items()}
            failed_run = failed_headers.get("x-kpp-logic-run", "")
            details = []
            if re.fullmatch(r"[A-Za-z0-9_-]+", failed_run):
                details = [
                    {"name": item["name"], "status": item["properties"]["status"],
                     "code": item["properties"].get("code")}
                    for item in logic_actions(failed_run)
                    if item["properties"]["status"] not in ("Succeeded", "Skipped")
                ]
            raise RuntimeError(
                f"Logic Apps {case['id']}: HTTP {response[0]}, run={failed_run}, "
                f"failed_actions={details}."
            )
        result, headers = require_status(response, 200, f"Logic Apps {case['id']}")
        proof = {name: value for name, value in headers.items() if name.startswith("x-kpp-")}
        native_run = proof.get("x-kpp-logic-run", "")
        if (
            proof.get("x-kpp-orchestrator") != "logic_apps"
            or proof.get("x-kpp-source-sha256") != SOURCE_SHA256
            or result["run_id"] != run_id
            or not re.fullmatch(r"[A-Za-z0-9_-]+", native_run)
        ):
            raise RuntimeError("Logic Apps returned no actual native/source/correlation proof.")
        actions = [
            {"name": item["name"], "status": item["properties"]["status"],
             "code": item["properties"].get("code")}
            for item in logic_actions(native_run)
        ]
        completed = {item["name"] for item in actions if item["status"] == "Succeeded"}
        invoked = completed.intersection(test_data["logic_actions"].values())
        expected = (
            {test_data["logic_actions"][result["route"]]}
            if result["status"] == "success" else set()
        )
        if invoked != expected or "classify_question" not in completed:
            raise RuntimeError(
                f"Native action dispatch differs from the selected route: {case['id']} {actions}."
            )
        normalized = {name for name in completed if name.startswith("normalize_")}
        expected_normalized = (
            {f"normalize_{result['route']}"} if result["status"] == "success" else set()
        )
        if normalized != expected_normalized:
            raise RuntimeError("Unexpected normalization/business dependency on a native branch.")
        ids = proof.get("x-kpp-native-responses", "").split(",")
        if len(ids) != (2 if result["status"] == "success" else 1):
            raise RuntimeError("Native agent response count does not match the selected branch.")
        record = compare_result(case, result, time.monotonic() - case_started)
        record.update({"execution_headers": proof, "native_actions": actions})
        records.append(record)
        print(
            f"Logic Apps {case['id']}: {result['route']} / {result['status']} run={native_run}",
            flush=True,
        )
        if not all(record[key] for key in ("status_match", "facts_pass", "sources_pass")):
            raise RuntimeError(f"Logic Apps factual/source/status parity failed: {case['id']}.")
    accuracy = sum(item["route_match"] for item in records) / 50
    if accuracy < 0.98:
        raise RuntimeError("Logic Apps routing accuracy is below the original threshold.")
    return {
        "native_logic_apps_gate": "PASS",
        "case_count": 50, "classification_accuracy": accuracy,
        "actual_status_counts": dict(Counter(item["result"]["status"] for item in records)),
        "source_sha256": SOURCE_SHA256, "corpus_sha256": CORPUS_SHA256,
        "inbound_auth": "managed_identity_oid_policy",
        "outbound_auth": "logic_apps_system_assigned_managed_identity",
        "logic_principal_id": test_data["logic_principal_id"],
        "sas_authentication": "Disabled",
        "anonymous_invalid_and_wrong_audience": "REJECTED",
        "setup_identity_normalizer_access": "REJECTED_403",
        "route_override": "REJECTED_400",
        "orchestration_delegated_to_maf": False,
        "normalization_only_adapter": True,
        "full_seven_provider_status": "BLOCKED",
        "results": records,
    }


def rehearse_core(test_data: dict) -> dict:
    corpus = base64.b64decode(test_data["corpus_base64"], validate=True)
    if hashlib.sha256(corpus).hexdigest() != CORPUS_SHA256:
        raise RuntimeError("The rehearsal must use the original corpus.")
    cases = {}
    for case in json.loads(corpus)["cases"]:
        cases.setdefault(case["route"], case)
    if len(cases) != 9:
        raise RuntimeError("The live core rehearsal requires all nine source routes.")
    callback = require_logic_callback(test_data["logic_callback"])
    api_token = token(AUDIENCE)
    arm_token = token("https://management.azure.com/")
    records = []
    for case in cases.values():
        payload = {"question": case["question"], "run_id": test_data["run_ids"][case["id"]]}
        for target in ("maf", "logicapps"):
            started = time.monotonic()
            response = (
                request("POST", "/api/run", access_token=api_token, body=payload)
                if target == "maf" else logic_request(callback, payload, arm_token)
            )
            result, headers = require_status(response, 200, f"rehearsal {target} {case['id']}")
            proof = {name: value for name, value in headers.items() if name.startswith("x-kpp-")}
            if (
                result["run_id"] != payload["run_id"]
                or proof.get("x-kpp-source-sha256") != SOURCE_SHA256
            ):
                raise RuntimeError("Rehearsal source/correlation proof is invalid.")
            if target == "maf":
                if (
                    proof.get("x-kpp-framework") != "1.11.0"
                    or proof.get("x-kpp-outbound-auth") != "managed_identity"
                ):
                    raise RuntimeError("Rehearsal did not execute the actual MI SDK runtime.")
                native_actions = []
            else:
                run = proof.get("x-kpp-logic-run", "")
                native_actions = [
                    {"name": item["name"], "status": item["properties"]["status"]}
                    for item in logic_actions(run)
                ]
                succeeded = {
                    item["name"] for item in native_actions if item["status"] == "Succeeded"
                }
                invoked = succeeded.intersection(test_data["logic_actions"].values())
                expected = (
                    {test_data["logic_actions"][case["route"]]}
                    if case["expected_status"] == "success" else set()
                )
                if invoked != expected or proof.get("x-kpp-orchestrator") != "logic_apps":
                    raise RuntimeError("Rehearsal Logic Apps native dispatch proof failed.")
            record = compare_result(case, result, time.monotonic() - started)
            if not all(record[key] for key in (
                "route_match", "status_match", "facts_pass", "sources_pass",
            )):
                raise RuntimeError(f"Live rehearsal parity failed: {target} {case['id']}.")
            record.update({
                "orchestrator": target, "execution_headers": proof,
                "native_actions": native_actions,
            })
            records.append(record)
            print(f"Rehearsal {target} {case['id']}: {result['status']}", flush=True)
    return {
        "remote_core_rehearsal": "PASS", "cases_per_target": 9,
        "source_sha256": SOURCE_SHA256, "corpus_sha256": CORPUS_SHA256,
        "production_auth": "managed_identity", "full_seven_provider_status": "BLOCKED",
        "results": records,
    }


def diagnose_maf() -> dict:
    health, _ = require_status(request("GET", "/health"), 200, "diagnostic readiness")
    access_token = token("https://management.azure.com/")

    def scm(path: str) -> bytes:
        if not path.startswith("/api/vfs/") or ".." in path:
            raise ValueError("Only owned-site VFS diagnostics are permitted.")
        req = urllib.request.Request(
            f"{SCM}{path}", headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
            value = response.read(500001)
        if len(value) > 500000:
            raise RuntimeError("The diagnostic file exceeds its bounded read limit.")
        return value

    listing = json.loads(scm("/api/vfs/site/wwwroot/"))
    source = scm("/api/vfs/site/wwwroot/maf_service/app.py")
    diagnostic = {
        "health": health,
        "deployed_app_sha256": hashlib.sha256(source).hexdigest(),
        "root_entries": [item["name"] for item in listing],
    }
    logs = json.loads(scm("/api/vfs/LogFiles/"))
    selected = sorted(
        (
            item for item in logs
            if item["name"].endswith("default_docker.log") and item.get("size", 0) <= 500000
        ),
        key=lambda item: item["name"],
    )[-1:]
    for item in selected:
        text = scm(f"/api/vfs/LogFiles/{item['name']}").decode("utf-8", errors="replace")
        diagnostic["startup_lines"] = [
            line for line in text.splitlines()
            if any(word in line for word in (
                "App path", "manifest", "Extract", "virtual environment", "Uvicorn",
                "Error", "Traceback", "uvicorn", "oryx",
            ))
        ][-35:]
    return diagnostic


def emit(proof: dict) -> None:
    encoded = base64.b64encode(json.dumps(proof, separators=(",", ":")).encode()).decode("ascii")
    chunks = [encoded[index:index + 3500] for index in range(0, len(encoded), 3500)]
    for index, value in enumerate(chunks):
        print(f"KPP_EVIDENCE:{index}:{len(chunks)}:{value}", flush=True)
    print(f"KPP_EVIDENCE_SHA256:{hashlib.sha256(encoded.encode()).hexdigest()}", flush=True)


def main() -> None:
    security = drop_setup_privileges()
    print(json.dumps({"process_security": security}), flush=True)

    def expired(signum, frame):
        raise TimeoutError("The deployment job exceeded its one-hour process budget.")

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(3600)
    Path(os.environ["HOME"]).mkdir(exist_ok=True)
    az("login", "--identity", "--client-id", os.environ["KPP_IDENTITY_CLIENT_ID"], timeout=180)
    az("account", "set", "--subscription", SUBSCRIPTION)
    mode = os.environ["KPP_JOB_MODE"]
    if mode not in ("deploy-maf", "verify-maf", "diagnose-maf", "verify-logic", "rehearse-core"):
        raise ValueError("Unsupported deployment-job mode.")
    proof = {"demo_id": "48254cc6", "mode": mode, "process_security": security}
    if mode == "diagnose-maf":
        proof["diagnostics"] = diagnose_maf()
        emit(proof)
        return
    if mode == "deploy-maf":
        with tempfile.TemporaryDirectory(prefix="kpp-demo-") as directory:
            package, proof["package"] = prepare_package(Path(directory))
            print("Pinned Linux package built; deploying only the owned MAF app.", flush=True)
            deployment = az(
                "webapp", "deploy", "--subscription", SUBSCRIPTION,
                "--resource-group", "demo_kpp", "--name", "kppdemo-maf-48254cc6",
                "--src-path", str(package), "--type", "zip", "--clean", "false",
                "--restart", "true", "--timeout", "900000", "--track-status", "false",
                timeout=1100,
            )
            proof["deployment"] = {
                key: deployment.get(key)
                for key in ("id", "status", "complete", "active", "end_time")
            }
            if (
                not proof["deployment"]["id"]
                or proof["deployment"]["status"] != 4
                or proof["deployment"]["complete"] is not True
            ):
                raise RuntimeError("ZIP publisher returned no completed deployment receipt.")
    data = json.loads(base64.b64decode(os.environ["KPP_TEST_DATA"], validate=True))
    if mode == "rehearse-core":
        proof.update(rehearse_core(data))
    else:
        proof.update(verify_logic(data) if mode == "verify-logic" else verify_maf(data))
    emit(proof)


if __name__ == "__main__":
    main()
