import base64
import hashlib
import io
import json
from types import SimpleNamespace

import pytest

from tools import azure_job, run_azure_job


def test_job_evidence_round_trip_and_missing_chunk_rejection(capsys):
    evidence = {"results": [{"answer": "synthetic fact " * 400}], "status": "PASS"}
    azure_job.emit(evidence)
    log = capsys.readouterr().out
    assert run_azure_job.decode_evidence(log) == evidence
    with pytest.raises(ValueError, match="complete test evidence"):
        run_azure_job.decode_evidence("\n".join(log.splitlines()[1:]))


def test_job_evidence_rejects_modified_payload():
    encoded = base64.b64encode(json.dumps({"status": "altered"}).encode()).decode()
    log = f"KPP_EVIDENCE:0:1:{encoded}\nKPP_EVIDENCE_SHA256:{hashlib.sha256(b'other').hexdigest()}"
    with pytest.raises(ValueError, match="checksum"):
        run_azure_job.decode_evidence(log)


def test_runner_rejects_non_demo_http_target():
    with pytest.raises(ValueError, match="owned demo"):
        azure_job.request("GET", "/health", host="https://existing.example")


def test_runner_does_not_log_failed_token_command_output(monkeypatch):
    monkeypatch.setattr(
        azure_job.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stderr="sensitive-token-output", stdout="other-token",
        ),
    )
    with pytest.raises(RuntimeError) as failure:
        azure_job.command(["az", "account", "get-access-token"])
    assert "sensitive-token" not in str(failure.value)
    assert "other-token" not in str(failure.value)


@pytest.mark.parametrize(
    "effective,no_new_privs", [("00000001", "1"), ("00000000", "0")]
)
def test_bootstrap_refuses_retained_privileges(monkeypatch, effective, no_new_privs):
    monkeypatch.setattr(azure_job, "os", SimpleNamespace(
        geteuid=lambda: 1000, getegid=lambda: 1000, getgroups=lambda: [],
    ))
    monkeypatch.setattr(
        azure_job.ctypes, "CDLL", lambda *args, **kwargs: SimpleNamespace(prctl=lambda *args: 0),
    )
    status = (
        f"CapEff:\t{effective}\nCapPrm:\t00000000\nCapAmb:\t00000000\n"
        f"NoNewPrivs:\t{no_new_privs}\n"
    )
    monkeypatch.setattr(
        azure_job, "Path", lambda *args: SimpleNamespace(read_text=lambda: status),
    )
    with pytest.raises(RuntimeError, match="retained Linux privileges"):
        azure_job.drop_setup_privileges()


def test_missing_pip_bootstrap_rejects_modified_public_wheel(monkeypatch, tmp_path):
    monkeypatch.setattr(
        azure_job.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"modified wheel"),
    )
    with pytest.raises(RuntimeError, match="SHA-256"):
        azure_job.pip_environment(tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("url", [
    "https://existing.example/workflows/demo/triggers/kpp_mining_start/paths/invoke?api-version=2016-10-01",
    "https://prod.southeastasia.logic.azure.com/workflows/demo/triggers/kpp_mining_start/paths/invoke?sig=secret",
])
def test_logic_verifier_refuses_other_hosts_or_signed_callbacks(url):
    with pytest.raises(ValueError, match="unsigned owned"):
        azure_job.require_logic_callback(url)


def test_native_action_history_collects_every_page_without_retaining_links(monkeypatch):
    next_page = (
        f"https://management.azure.com{azure_job.LOGIC_ID}"
        "/runs/native_run/actions?api-version=2016-06-01&$skiptoken=page2"
    )
    monkeypatch.setattr(azure_job, "logic_management", lambda path: {
        "value": [{"name": "classify_question"}], "nextLink": next_page,
    })
    monkeypatch.setattr(
        azure_job, "az", lambda *args, **kwargs: {"value": [{"name": "invoke_mcp"}]},
    )
    assert azure_job.logic_actions("native_run") == [
        {"name": "classify_question"}, {"name": "invoke_mcp"},
    ]


def test_native_action_paging_cannot_follow_another_workflow(monkeypatch):
    monkeypatch.setattr(azure_job, "logic_management", lambda path: {
        "value": [], "nextLink": "https://management.azure.com/existing-business-workflow/actions",
    })
    with pytest.raises(ValueError, match="owned action"):
        azure_job.logic_actions("native_run")
