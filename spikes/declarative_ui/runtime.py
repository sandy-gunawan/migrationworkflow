import sys
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import yaml
from agent_framework.exceptions import WorkflowException
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential
from openai import APIError
from pydantic import ValidationError
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / "spikes" / "official-migration"
sys.path.insert(0, str(SUPPORT))

from trial_support import (  # noqa: E402
    AgentPool,
    verify_native_context,
    verify_run,
)

from demo_common.contracts import DemoRequest, DemoResult, Route  # noqa: E402
from spikes.declarative_ui.loader import WorkflowFile  # noqa: E402
from spikes.execution_ui.server import RunFailure  # noqa: E402
from spikes.execution_ui.sources import python_source  # noqa: E402
from spikes.logicapps_ui.access import SUBSCRIPTION  # noqa: E402

EXPECTED = {
    "agent-framework-core": "1.26.0",
    "agent-framework-declarative": "1.5.1",
    "agent-framework-foundry": "1.16.2",
}


def canonical_result(request: DemoRequest, report: dict) -> DemoResult:
    value = report["result"]
    if value["status"] == "success":
        result = DemoResult.model_validate(value)
        if result.run_id != request.run_id:
            raise ValueError("The normalization run ID differs from the UI request.")
        return result
    text = "\n".join(
        line
        for line in value["answer"].splitlines()
        if not line.startswith(("KPP_ROUTE:", "KPP_STATUS:"))
    ).strip()
    if not text:
        raise ValueError("The YAML terminal output contains no explanation.")
    blocked = value["status"] in ("blocked", "failed")
    return DemoResult(
        run_id=request.run_id,
        route=Route(value["route"]),
        status=value["status"],
        answer=None if blocked else text,
        error=text if blocked else None,
        sources=[],
    )


def yaml_sources(snapshot: WorkflowFile) -> tuple[dict, dict]:
    sources, agent_steps = {}, {}
    rows = snapshot.text.splitlines()

    def visit(node):
        if isinstance(node, MappingNode):
            fields = {key.value: value for key, value in node.value}
            if "id" in fields and isinstance(fields["id"], ScalarNode):
                key = fields["id"].value
                kind = fields["kind"].value if "kind" in fields else "Condition"
                start = node.start_mark.line + 1
                end = node.end_mark.line + (1 if node.end_mark.column else 0)
                explanation = (
                    f"WorkflowFactory resmi menjalankan blok {kind} ini dari snapshot YAML. "
                    "Tidak ada terjemahan manual ke WorkflowBuilder pada jalur ini."
                )
                if "agent" in fields:
                    agent = {name.value: value.value for name, value in fields["agent"].value}
                    if agent["name"] in agent_steps:
                        raise ValueError("The demo needs an unambiguous source step per agent.")
                    agent_steps[agent["name"]] = key
                    explanation += (
                        f" Referensi {agent['name']}:{agent['version']} menemukan binding "
                        "FoundryAgent; tidak membuat agent baru."
                    )
                sources[key] = {
                    "key": key,
                    "label": key,
                    "symbol": key,
                    "language": "yaml",
                    "path": snapshot.definition()["path"],
                    "line": start,
                    "end_line": end,
                    "text": "\n".join(rows[start - 1 : end]) + "\n",
                    "lessons": [
                        {
                            "id": "explain",
                            "title": key,
                            "line": start,
                            "end_line": end,
                            "explanation": explanation,
                            "analogy": "SOP tetap dalam berkas; petugas tidak menulis ulang SOP "
                            "menjadi prosedur berbeda setiap kali ada permintaan.",
                        }
                    ],
                }
            for _, value in node.value:
                visit(value)
        elif isinstance(node, SequenceNode):
            for value in node.value:
                visit(value)

    visit(yaml.compose(snapshot.text))
    return sources, agent_steps


class DeclarativeRuntime:
    def __init__(self, path: Path):
        actual = {name: version(name) for name in EXPECTED}
        if actual != EXPECTED:
            raise ValueError(
                "Use the isolated b-declarative environment; do not upgrade the original venv. "
                f"Expected {EXPECTED}, found {actual}."
            )
        self.snapshot = WorkflowFile.load(path)
        self.definition = self.snapshot.definition()
        self.sources, self.agent_steps = yaml_sources(self.snapshot)
        for key, file, symbol, label, explanation in (
            (
                "workflow",
                Path(__file__),
                "DeclarativeRuntime.execute",
                "Jalankan workflow YAML",
                "Setiap request memakai pool agent dan graph baru. Snapshot file tetap sama; "
                "state dan conversation tidak dipakai silang antarpertanyaan.",
            ),
            (
                "loader",
                Path(__file__).with_name("loader.py"),
                "WorkflowFile.create",
                "WorkflowFactory resmi membaca snapshot",
                "File dibaca saat startup. Factory resmi membangun graph baru dari teks "
                "snapshot untuk request ini; bukan WorkflowBuilder tulisan tangan.",
            ),
            (
                "bindings",
                SUPPORT / "trial_support.py",
                "AgentPool.__init__",
                "Binding ke agent Foundry yang sudah ada",
                "Nama/version dipin pada registry. Model, instructions dan tools tetap "
                "di Foundry. Registry ini tidak membuat agent atau permission.",
            ),
            (
                "context",
                SUPPORT / "trial_support.py",
                "PreserveNativeContext.process",
                "Adapter konteks native",
                "Adapter demo memulihkan pertanyaan asli, conversation ID yang sama dan "
                "marker route. Jangan menganggapnya perilaku otomatis semua YAML loader.",
            ),
            (
                "conversation",
                SUPPORT / "trial_support.py",
                "AgentPool.__aenter__",
                "Conversation native baru",
                "Satu conversation dibuat untuk satu request. Tidak ada replay history run lama.",
            ),
            (
                "activity",
                SUPPORT / "trial_support.py",
                "AgentPool.append_activity",
                "Catat activity yang benar-benar dikirim",
                "Marker/outcome ditulis ke conversation native. Status done baru diterbitkan "
                "setelah SDK mengembalikan hasil.",
            ),
            (
                "verification",
                SUPPORT / "trial_support.py",
                "verify_run",
                "Periksa agent, jumlah panggilan dan sumber",
                "Response native diverifikasi dengan normalizer yang sama. Kalimat model "
                "atau nama tool yang diharapkan saja tidak cukup untuk menyatakan retrieval.",
            ),
            (
                "native_context",
                SUPPORT / "trial_support.py",
                "verify_native_context",
                "Baca kembali conversation",
                "Read-back memeriksa pertanyaan asli, satu conversation dan marker route aktual.",
            ),
            (
                "agent_observer",
                SUPPORT / "trial_support.py",
                "RecordAgent.process",
                "Middleware progress pada panggilan aktual",
                "Start terbit sebelum call_next; completed sesudah response native dan versi "
                "berhasil diperiksa. Event bukan simulasi progress atau pikiran agent.",
            ),
        ):
            self.sources[key] = {"key": key, **python_source(file, symbol, label, explanation)}
        self.info = {
            "kind": "declarative",
            "title": "Cara 1: YAML execution bench",
            "service": "local-maf-declarative-ui",
            "identity_mode": "azure_cli",
            "engine": "Official WorkflowFactory / Core 1.26.0 / Declarative 1.5.1",
            "run_label": "Jalankan YAML",
            "description": "Python memuat file YAML terpisah sebagai snapshot startup. "
            "WorkflowFactory resmi menjalankan alurnya; agent tetap di Foundry.",
            "waiting_note": "Progress berasal dari middleware panggilan agent dan verifier "
            "aktual. Tool ditampilkan sesudah response kembali, bukan "
            "streaming pikiran/internal aktivitas agent.",
            "guide_name": "maf-declarative-walkthrough.html",
            "source_sha256": self.snapshot.sha256,
            "framework_versions": actual,
        }

    def observe(self, event: str, data: dict, emit: Callable[[dict], None]):
        if event.startswith("agent_"):
            name, agent_version = data["agent"], data["version"]
            if name not in self.agent_steps:
                raise RunFailure("Agent call does not belong to the frozen YAML registry.")
            source = self.agent_steps[name]
            started = event == "agent_started"
            native = data.get("native", {})
            emit(
                {
                    "phase": "router" if name == "kppdemo-router" else "specialist",
                    "status": "running" if started else "done",
                    "step_id": source,
                    "code_key": source,
                    "label": ("Memanggil " if started else "Respons dari ") + name,
                    "detail": "Panggilan SDK aktual; menunggu respons."
                    if started
                    else "Response native dan versi sudah diperiksa oleh middleware.",
                    "agent_name": name,
                    "agent_version": agent_version,
                    "native_response_id": native.get("id"),
                }
            )
            if not started:
                for item in native.get("output", []):
                    if item.get("type") == "mcp_call":
                        emit(
                            {
                                "phase": "tool",
                                "status": "done" if item.get("status") == "completed" else "failed",
                                "step_id": source + "_tool",
                                "code_key": "agent_observer",
                                "label": "Bukti tool aktual: " + item["name"],
                                "detail": "Dibaca dari response yang sudah kembali.",
                                "agent_name": name,
                                "agent_version": agent_version,
                                "tool_name": item["name"],
                                "native_response_id": native["id"],
                            }
                        )
        elif event in ("conversation_started", "conversation_ready"):
            emit(
                {
                    "phase": "context",
                    "status": "running" if event.endswith("started") else "done",
                    "step_id": "native_conversation",
                    "code_key": "conversation",
                    "label": "Menyiapkan conversation native",
                    "detail": "Conversation baru, tidak memakai run sebelumnya.",
                }
            )
        elif event in ("activity_started", "activity_ready"):
            emit(
                {
                    "phase": "activity",
                    "status": "running" if event.endswith("started") else "done",
                    "step_id": "native_activity_" + str(data["index"]),
                    "code_key": "activity",
                    "label": "Mencatat activity native",
                    "detail": data["text"],
                }
            )
        else:
            raise RunFailure("Unsupported SDK observation event: " + event)

    async def execute(self, request: DemoRequest, emit: Callable[[dict], None]) -> dict:
        emit(
            {
                "phase": "workflow",
                "status": "running",
                "step_id": "declarative_workflow",
                "code_key": "loader",
                "label": "Menjalankan snapshot YAML dengan factory resmi",
                "detail": "File tidak dibaca ulang; graph dan agent pool dibuat untuk request ini.",
            }
        )
        credential = AzureCliCredential(subscription=SUBSCRIPTION)
        pool = None
        try:
            pool = AgentPool(
                question=request.question,
                credential=credential,
                on_progress=lambda event, data: self.observe(event, data, emit),
            )
            await pool.__aenter__()
            workflow = self.snapshot.create(pool.agents)
            execution = await workflow.run(request.question)
            outputs = execution.get_outputs()
            if not all(isinstance(item, str) for item in outputs):
                raise ValueError("The source produced a non-text output.")
            emit(
                {
                    "phase": "normalization",
                    "status": "running",
                    "step_id": "verify_yaml_result",
                    "code_key": "verification",
                    "label": "Memeriksa hasil dan evidence",
                    "detail": "Tidak ada jawaban sukses sebelum verifikasi agent/tool/sumber.",
                }
            )
            report = verify_run(request.question, outputs, pool.calls, run_id=request.run_id)
            await verify_native_context(pool, outputs, report)
            result = canonical_result(request, report)
            emit(
                {
                    "phase": "normalization",
                    "status": "done",
                    "step_id": "verify_yaml_result",
                    "code_key": "native_context",
                    "label": "Evidence dan conversation terverifikasi",
                    "detail": "Read-back pertanyaan, conversation dan marker route lulus.",
                }
            )
            emit(
                {
                    "phase": "workflow",
                    "status": "done",
                    "step_id": "declarative_workflow",
                    "code_key": "workflow",
                    "label": "Workflow YAML selesai",
                    "detail": "Hasil dikembalikan ke UI; blocked tetap bukan retrieval.",
                }
            )
            return {
                "result": result.model_dump(mode="json"),
                "trace": {
                    "orchestrator": "official_maf_declarative",
                    "source_file": self.definition["path"],
                    "source_sha256": self.snapshot.sha256,
                    "yaml_loaded_at": self.snapshot.loaded_at,
                    "framework_versions": self.info["framework_versions"],
                    "native_response_ids": [item["native"]["id"] for item in pool.calls],
                    "native_context": {
                        "conversation_id": pool.conversation_id,
                        "checks": report["native_context"]["checks"],
                        "activity_item_ids": pool.activity_ids,
                    },
                    "agent_calls": [
                        {"name": item["agent"], "version": item["version"]} for item in pool.calls
                    ],
                    "manual_adapter": "PreserveNativeContext",
                },
            }
        except (
            ClientAuthenticationError,
            APIError,
            WorkflowException,
            ValidationError,
            ValueError,
        ) as error:
            raise RunFailure(
                "Eksekusi YAML/identity/evidence gagal; tidak ada hasil pengganti. "
                f"Jenis: {type(error).__name__}.",
            ) from error
        finally:
            if pool is not None:
                await pool.__aexit__(None, None, None)
            else:
                credential.close()

    async def close(self):
        pass
