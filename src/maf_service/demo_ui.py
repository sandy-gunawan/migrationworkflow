import ast
import asyncio
import hashlib
import inspect
import json
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Callable

import httpx
from agent_framework.exceptions import WorkflowException
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from demo_common.contracts import DemoRequest, Route
from demo_common.fabric import SUBSCRIPTION, US_WORKSPACE, DemoFabric
from demo_common.foundry import DemoFoundry, DemoFoundryError
from demo_common.normalization import normalize_specialist_result
from maf_service.progress import ProgressObserver, ProgressStatus, ProgressUpdate
from maf_service.workflow import (
    MiningWorkflow,
    OutcomeExecutor,
    RouterExecutor,
    SpecialistExecutor,
    WorkflowAgents,
    WorkflowExecutionError,
    load_mapping,
)

ROOT = Path(__file__).resolve().parents[2]
UI = Path(__file__).parent / "ui"
logger = logging.getLogger(__name__)
CODE: dict[str, tuple[Callable, str]] = {
    "workflow": (MiningWorkflow.run, "Graph MAF dan hasil akhir"),
    "router": (RouterExecutor.route, "Percakapan dan klasifikasi router"),
    "switch": (MiningWorkflow.build, "Kondisi branch dan executor yang dipilih"),
    "specialist": (SpecialistExecutor.retrieve, "Agent specialist dan evidence tool"),
    "normalization": (normalize_specialist_result, "Verifikasi fakta dan sumber"),
    "outcome": (OutcomeExecutor.finish, "Blocked, klarifikasi dan unsupported"),
    "capacity": (DemoFabric.active_capacity, "Lifecycle US F2 dummy"),
}
ROUTE_LABELS = {
    "mcp": "Maintenance MCP", "rest_api": "Stok REST API", "knowledge": "Dokumen Search",
    "foundry_iq": "Native knowledge base", "fabric_data": "Produksi Fabric",
    "fabric_iq": "Ontology belum tersedia", "work_iq": "Work IQ belum tersedia",
    "clarification": "Perlu klarifikasi", "unsupported": "Di luar batas demo",
}
LESSONS: dict[str, list[tuple[str, str, str, str, str]]] = {
    "workflow": [
        (
            "execute", "execution = await workflow.run(", "Jalankan prosedur MAF",
            "MAF (Microsoft Agent Framework) menjalankan urutan kerja. Pertanyaan asli "
            "dan catatan run masuk ke graph; graph mengembalikan hasil setelah branch selesai.",
            "Seperti petugas pos kontrol mengikuti prosedur permintaan perawatan TRK001, "
            "bukan membaca laporan run kemarin.",
        ),
        (
            "output", "if len(outputs)", "Pastikan hanya satu hasil",
            "Output adalah hasil akhir. Kode menolak hasil kosong atau lebih dari satu "
            "agar UI tidak menampilkan jawaban yang belum jelas asalnya.",
            "Pos kontrol menerima satu laporan untuk satu permintaan TRK001, bukan "
            "menggabungkan laporan tim lain tanpa pemeriksaan.",
        ),
    ],
    "router": [
        (
            "conversation", "conversation = await asyncio.to_thread(", "Buka percakapan",
            "Conversation adalah catatan percakapan untuk satu run. Pertanyaan TRK001 "
            "disimpan; nomor percakapan dipakai kembali oleh router dan specialist.",
            "Pos kontrol membuka satu berkas permintaan TRK001 supaya semua tim "
            "membaca pertanyaan yang sama.",
        ),
        (
            "agent_call", "response = await asyncio.to_thread(", "Tanya router",
            "Router adalah agent pemilih tujuan, bukan pembaca data. Nama, versi dan "
            "pertanyaan dikirim ke Foundry; await berarti menunggu respons tanpa "
            "menghentikan layanan UI.",
            "Petugas dispatch memutuskan bahwa TRK001 perlu tim perawatan, "
            "bukan tim persediaan.",
        ),
        (
            "decision", "try:", "Periksa pilihan route",
            "Route adalah tujuan yang diperbolehkan. JSON, yaitu format data terstruktur, "
            "divalidasi sebelum MAF memilih branch; respons yang salah tidak boleh "
            "memicu specialist sembarang.",
            "Pos kontrol memeriksa kode tujuan pada berkas TRK001 sebelum meneruskannya.",
        ),
    ],
    "switch": [
        (
            "branch", "for branch in self.mapping.branches:", "Siapkan pilihan if/else",
            "Branch adalah satu jalur kerja. MAF menyiapkan specialist atau hasil "
            "non-dispatch untuk setiap route pada konfigurasi source yang dibekukan.",
            "Pos kontrol memiliki daftar tim yang sah; tidak membuat tujuan baru "
            "hanya karena isi permintaan menyuruhnya.",
        ),
        (
            "fallback", "builder.add_switch_case_edge_group(", "Pasang kondisi dan fallback",
            "Kondisi route memilih satu tujuan. Fallback adalah hasil aman jika pilihan "
            "tidak cocok; ia bukan jawaban data pengganti.",
            "Berkas TRK001 dikirim ke satu tim yang cocok. Berkas yang tidak valid "
            "ditahan di pos, bukan dikirim ke seluruh tim.",
        ),
    ],
    "specialist": [
        (
            "agent_call", "response = await asyncio.to_thread(", "Panggil specialist",
            "Specialist adalah agent untuk satu bidang. Kode mengirim nama, versi, "
            "pertanyaan asli dan nomor percakapan ke Foundry; respons native disimpan "
            "di response. Agent perawatan memakai MCP, protokol komunikasi tool, "
            "untuk mengambil work order. Jawaban belum dianggap terverifikasi.",
            "Pos kontrol menyerahkan berkas TRK001 ke tim perawatan dan menunggu "
            "laporan WO001 beserta buktinya.",
        ),
        (
            "route_marker", "await asyncio.to_thread(", "Catat tujuan pada percakapan",
            "Activity adalah catatan tambahan dalam percakapan. Penanda route ditulis "
            "pada berkas yang sama agar specialist menerima konteks dan pertanyaan asli.",
            "Petugas menandai berkas TRK001 dengan tujuan tim perawatan, "
            "bukan membuat permintaan baru.",
        ),
        (
            "tool_evidence", 'for item in response.get("output"', "Baca bukti tool aktual",
            "Tool adalah koneksi agent ke sumber data. Kode membaca nama, versi dan "
            "status tool dari respons yang sudah kembali. Ini bukan streaming "
            "pikiran agent atau tebakan tool yang sedang berjalan.",
            "Petugas melihat bukti pembacaan work order setelah laporan tim "
            "perawatan kembali, bukan menebak aktivitas tim.",
        ),
        (
            "grounding", "result = normalize_specialist_result(", "Verifikasi jawaban",
            "Grounding berarti jawaban ditopang bukti sumber. Respons, route, run ID "
            "dan versi agent diperiksa; hanya fakta dan sumber yang lolos dapat "
            "menjadi hasil sukses.",
            "Pos kontrol mencocokkan WO001 dengan TRK001 dan catatan sumber "
            "sebelum mengesahkan laporan.",
        ),
    ],
    "normalization": [
        (
            "grounding", "for item in calls:", "Periksa bukti dan versi",
            "Setiap panggilan tool harus berasal dari agent/versi yang diharapkan, "
            "selesai tanpa error dan membawa data yang valid. Pemeriksaan ini "
            "mencegah kalimat agent dianggap sebagai bukti retrieval.",
            "Pos kontrol memeriksa identitas tim dan catatan WO001, "
            "bukan hanya percaya pada kalimat 'sudah diperiksa'.",
        ),
        (
            "sources", "if not answer or not references:", "Wajib ada jawaban dan sumber",
            "Source reference adalah penunjuk catatan asal. Tanpa jawaban atau "
            "penunjuk sumber, hasil ditolak; kode tidak membuat sumber palsu.",
            "Laporan TRK001 tanpa nomor catatan asal tidak disahkan oleh pos kontrol.",
        ),
    ],
    "outcome": [
        (
            "blocked_result", "result = DemoResult(", "Kembalikan hasil tanpa specialist",
            "Blocked berarti capability belum tersedia. Klarifikasi berarti "
            "pertanyaan perlu dipersempit. Kode mengembalikan status dan alasan, "
            "bukan menjalankan tool atau membuat data sukses.",
            "Pos kontrol memberi alasan mengapa permintaan belum dapat diteruskan; "
            "tidak membuat laporan perawatan palsu.",
        ),
    ],
    "capacity": [
        (
            "resume", 'active = self.capacity("resume")', "Aktifkan Fabric jika diperlukan",
            "Capacity adalah fasilitas komputasi Fabric. Hanya capacity US milik "
            "demo diaktifkan untuk membaca data Fabric. Pertanyaan work order TRK001 "
            "melalui MCP tidak memakai langkah ini.",
            "Pos kontrol membuka fasilitas laporan hanya saat tim yang dipilih "
            "memerlukannya.",
        ),
        (
            "pause", 'paused = self.capacity("suspend")', "Pause dalam finally",
            "Finally adalah bagian yang tetap dijalankan setelah operasi selesai "
            "atau gagal. Capacity demo dipause; ini berbeda dari menghentikan "
            "proses UI lokal atau menghapus resource.",
            "Petugas menutup fasilitas sementara sesudah tugas, "
            "termasuk ketika laporan gagal diperoleh.",
        ),
        (
            "idle_proof", "proof = {", "Simpan bukti Paused",
            "State Paused dan pengaturan overage dibaca balik dari Azure "
            "dan dicatat. Status tidak sekadar berubah warna di UI.",
            "Pos kontrol mencatat hasil pemeriksaan fasilitas, "
            "bukan hanya memasang papan 'tutup'.",
        ),
    ],
}


def source_lessons(key: str, text: str, start_line: int) -> list[dict]:
    lines = text.splitlines()
    statements = [node for node in ast.walk(ast.parse(dedent(text)))
                  if isinstance(node, ast.stmt)]
    lessons = []
    for lesson_id, anchor, title, explanation, analogy in LESSONS[key]:
        matches = [index + 1 for index, line in enumerate(lines)
                   if line.lstrip().startswith(anchor)]
        if len(matches) != 1:
            raise RuntimeError(f"Source lesson anchor is not unique: {key}/{lesson_id}.")
        nodes = [node for node in statements if node.lineno == matches[0]]
        if len(nodes) != 1 or nodes[0].end_lineno is None:
            raise RuntimeError(f"Source lesson has no exact statement: {key}/{lesson_id}.")
        lessons.append({
            "id": lesson_id, "title": title, "explanation": explanation, "analogy": analogy,
            "line": start_line + matches[0] - 1,
            "end_line": start_line + nodes[0].end_lineno - 1,
        })
    return lessons


def code_reference(key: str, *, include_text: bool = False) -> dict:
    if key not in CODE:
        logger.warning("Unknown local source-code key rejected: %s", key)
        raise HTTPException(404, "Source key tidak tersedia.")
    function, label = CODE[key]
    function = inspect.unwrap(function)
    filename = inspect.getsourcefile(function)
    if filename is None:
        raise RuntimeError("Whitelisted code has no source file.")
    lines, line = inspect.getsourcelines(function)
    value = {
        "key": key, "label": label, "path": Path(filename).relative_to(ROOT).as_posix(),
        "symbol": function.__qualname__, "line": line, "end_line": line + len(lines) - 1,
    }
    if include_text:
        value["text"] = "".join(lines)
        value["lessons"] = source_lessons(key, value["text"], line)
    return value


class UiFoundryGateway:
    def __init__(
        self, native: DemoFoundry, fabric: DemoFabric,
        observer: ProgressObserver, request: DemoRequest,
    ):
        self.native = native
        self.fabric = fabric
        self.observer = observer
        self.request = request

    def start_conversation(self, question: str, run_id: str) -> str:
        return self.native.start_conversation(question, run_id)

    def append_activity(self, conversation_id: str, text: str) -> None:
        self.native.append_activity(conversation_id, text)

    def capacity_progress(self, stage: str, value: dict | None) -> None:
        labels: dict[str, tuple[ProgressStatus, str, str]] = {
            "resuming": ("running", "Menyiapkan Fabric dummy", "Resume hanya US F2 milik demo."),
            "active": ("done", "Fabric sudah Active", "DataAgent dapat membaca tabel dummy."),
            "pausing": ("running", "Fabric menuju idle", "Pause dijalankan dalam finally."),
            "paused": ("done", "Fabric kembali Paused", "State Paused dibaca balik dari Azure."),
        }
        status, label, detail = labels[stage]
        self.observer(ProgressUpdate(
            run_id=self.request.run_id, phase="capacity", status=status,
            step_id="fabric_capacity_resume" if stage in ("resuming", "active")
            else "fabric_capacity_pause",
            code_key="capacity", label=label, detail=detail,
            route=Route.FABRIC_DATA,
        ))

    def invoke(
        self, name: str, question: str, version: str | None = None, *,
        conversation_id: str | None = None,
    ) -> dict:
        if name == "kppdemo-fabric-data":
            with self.fabric.active_capacity(observer=self.capacity_progress):
                return self.native.invoke(
                    name, question, version, conversation_id=conversation_id,
                )
        return self.native.invoke(name, question, version, conversation_id=conversation_id)


def create_ui_app(
    *, agents: WorkflowAgents | None = None, on_shutdown: Callable[[], None] | None = None,
) -> FastAPI:
    if os.environ.get("WEBSITE_HOSTNAME"):
        raise ValueError("This UI is local only; cloud Entra authentication must not be bypassed.")
    mapping = load_mapping()
    corpus_path = ROOT / "tests" / "golden" / "cases.json"
    baseline = json.loads(
        (Path(__file__).parent / "resources" / "baseline.json").read_text(encoding="utf-8")
    )
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != baseline["corpus_sha256"]:
        raise ValueError("The local UI prompt corpus differs from the frozen baseline.")
    cases = json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]
    presets = {}
    for case in cases:
        presets.setdefault(case["route"], {**case, "label": ROUTE_LABELS[case["route"]]})

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with (
            AzureCliCredential(subscription=SUBSCRIPTION) as credential,
            httpx.Client(timeout=300, follow_redirects=False) as client,
        ):
            app.state.native = DemoFoundry(credential, client)
            app.state.fabric = DemoFabric(credential, client, ROOT / "evidence", US_WORKSPACE)
            yield
            if app.state.tasks:
                await asyncio.gather(*app.state.tasks)

    app = FastAPI(
        title="Local MAF execution bench", lifespan=lifespan, docs_url=None, redoc_url=None,
    )
    app.state.csrf = secrets.token_urlsafe(48)
    app.state.run_lock = asyncio.Lock()
    app.state.tasks = set()
    app.state.stopping = False

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.url.hostname not in ("127.0.0.1", "localhost"):
            logger.warning("Non-loopback UI host denied.")
            return JSONResponse({"error": "UI hanya tersedia pada loopback."}, status_code=403)
        if request.method not in ("GET", "HEAD"):
            origin = str(request.base_url).rstrip("/")
            if (
                request.headers.get("origin") != origin
                or not secrets.compare_digest(
                    request.headers.get("x-demo-csrf", ""), app.state.csrf
                )
            ):
                logger.warning("Local UI origin/CSRF request denied.")
                return JSONResponse(
                    {"error": "Origin atau token browser tidak valid."}, status_code=403,
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.get("/")
    def index():
        return FileResponse(UI / "index.html")

    @app.get("/assets/{name}")
    def asset(name: str):
        if name not in ("app.js", "style.css"):
            raise HTTPException(404, "Asset tidak tersedia.")
        return FileResponse(UI / name)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "stopping" if app.state.stopping else "ready",
            "service": "local-maf-ui", "synthetic_only": True,
            "source_sha256": mapping.source_sha256,
        }

    @app.get("/ui/context")
    def context() -> dict:
        return {
            "csrf_token": app.state.csrf,
            "identity_mode": "unit_fixture" if agents is not None else "azure_cli",
            "framework_version": "1.11.0", "source_sha256": mapping.source_sha256,
            "busy": app.state.run_lock.locked(),
            "stopping": app.state.stopping,
            "presets": list(presets.values()), "cases": cases,
            "code": [code_reference(key) for key in CODE],
        }

    @app.get("/ui/code/{key}")
    def code(key: str) -> dict:
        return code_reference(key, include_text=True)

    @app.post("/ui/shutdown")
    async def shutdown() -> JSONResponse:
        if app.state.run_lock.locked():
            logger.warning("Local UI shutdown rejected while a run is active.")
            raise HTTPException(409, "Run masih berjalan. Tunggu hasil dan cleanup Fabric selesai.")
        if on_shutdown is None:
            logger.warning("Local UI shutdown is unavailable without the owned launcher.")
            raise HTTPException(
                409, "Gunakan launcher run_maf_ui.py atau Ctrl+C di terminal server.",
            )
        app.state.stopping = True
        return JSONResponse(
            {"status": "stopping", "scope": "local_ui_only"},
            background=BackgroundTask(on_shutdown),
        )

    @app.post("/ui/runs")
    async def run(body: DemoRequest) -> StreamingResponse:
        if app.state.stopping:
            logger.warning("New run rejected during local UI shutdown.")
            raise HTTPException(
                503, "UI sedang dihentikan. Jalankan server kembali sebelum bertanya.",
            )
        if app.state.run_lock.locked():
            logger.warning("Concurrent local UI run rejected.")
            raise HTTPException(409, "Run sebelumnya masih berjalan; tunggu sampai selesai.")
        await app.state.run_lock.acquire()
        queue: asyncio.Queue[dict] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        sequence = 0

        def send(payload: dict) -> None:
            def enqueue():
                nonlocal sequence
                sequence += 1
                queue.put_nowait({
                    "sequence": sequence, "timestamp": datetime.now(timezone.utc).isoformat(),
                    **payload,
                })

            loop.call_soon_threadsafe(enqueue)

        def observe(update: ProgressUpdate) -> None:
            send({"type": "progress", "update": update.model_dump(mode="json")})

        async def execute() -> None:
            try:
                gateway = agents if agents is not None else UiFoundryGateway(
                    app.state.native, app.state.fabric, observe, body,
                )
                engine = MiningWorkflow(
                    mapping, gateway,
                    identity_mode="unit_fixture" if agents is not None else "azure_cli",
                    on_progress=observe,
                )
                output = await engine.run(body)
                send({"type": "result", "output": output.model_dump(mode="json")})
            except (
                ClientAuthenticationError, DemoFoundryError, httpx.RequestError,
                WorkflowException, WorkflowExecutionError,
            ) as error:
                logger.exception(
                    "Local MAF UI failed: %s run=%s", type(error).__name__, body.run_id,
                )
                message = (
                    "Identitas Azure CLI tidak siap. Jalankan az login pada tenant demo."
                    if isinstance(error, ClientAuthenticationError) else
                    "Panggilan workflow/dependency gagal. Tidak ada jawaban yang dinyatakan sukses."
                )
                send({
                    "type": "error", "run_id": str(body.run_id), "message": message,
                    "error_type": type(error).__name__,
                    "upstream_status": (
                        error.status_code if isinstance(error, DemoFoundryError) else None
                    ),
                })
            finally:
                app.state.run_lock.release()

        send({
            "type": "started", "run_id": str(body.run_id), "question": body.question,
            "identity_mode": "unit_fixture" if agents is not None else "azure_cli",
        })
        task = asyncio.create_task(execute())
        app.state.tasks.add(task)

        def finished(done: asyncio.Task) -> None:
            app.state.tasks.discard(done)
            if not done.cancelled() and done.exception() is not None:
                logger.error(
                    "Unexpected local UI execution failure: %s", type(done.exception()).__name__,
                )
                send({
                    "type": "error", "run_id": str(body.run_id),
                    "message": "Kesalahan eksekusi. Periksa log lokal; hasil belum terverifikasi.",
                    "error_type": type(done.exception()).__name__,
                })

        task.add_done_callback(finished)

        async def stream():
            while True:
                event = await queue.get()
                yield json.dumps(event, separators=(",", ":")) + "\n"
                if event["type"] in ("result", "error"):
                    break

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app
