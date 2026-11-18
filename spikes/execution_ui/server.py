import asyncio
import hashlib
import json
import logging
import os
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import field_validator
from starlette.background import BackgroundTask

from demo_common.contracts import DemoRequest
from spikes.execution_ui.sources import python_source

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).parent / "assets"
logger = logging.getLogger(__name__)
ROUTE_LABELS = {
    "mcp": "Maintenance MCP",
    "rest_api": "Stok REST API",
    "knowledge": "Dokumen Search",
    "foundry_iq": "Native knowledge base",
    "fabric_data": "Produksi Fabric",
    "fabric_iq": "Ontology belum tersedia",
    "work_iq": "Work IQ belum tersedia",
    "clarification": "Perlu klarifikasi",
    "unsupported": "Di luar batas demo",
}


class UiRequest(DemoRequest):
    @field_validator("question")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Isi pertanyaan, bukan spasi saja.")
        return value


class RunFailure(RuntimeError):
    def __init__(self, message: str, *, upstream_status: int | None = None):
        super().__init__(message)
        self.upstream_status = upstream_status


class Runtime(Protocol):
    info: dict
    sources: dict[str, dict]
    definition: dict

    async def execute(self, request: DemoRequest, emit: Callable[[dict], None]) -> dict: ...
    async def close(self) -> None: ...


def prompt_catalog() -> tuple[list[dict], list[dict]]:
    baseline = json.loads(
        (ROOT / "src" / "maf_service" / "resources" / "baseline.json").read_text(encoding="utf-8")
    )
    raw = (ROOT / "tests" / "golden" / "cases.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != baseline["corpus_sha256"]:
        raise ValueError("The original prompt corpus changed.")
    cases = json.loads(raw)["cases"]
    presets = {}
    for case in cases:
        presets.setdefault(case["route"], {**case, "label": ROUTE_LABELS[case["route"]]})
    return list(presets.values()), cases


def create_app(runtime: Runtime, *, on_shutdown: Callable[[], None] | None = None) -> FastAPI:
    if os.environ.get("WEBSITE_HOSTNAME"):
        raise ValueError("This UI is local only; it has no anonymous cloud hosting mode.")
    presets, cases = prompt_catalog()
    if "workflow" not in runtime.sources:
        raise ValueError("The runtime must expose its actual workflow entrypoint source.")
    catalog = dict(runtime.sources)
    for key, symbol, label, explanation in (
        (
            "http",
            "create_app.run",
            "Browser memanggil HTTP Python",
            "POST /ui/runs memvalidasi pertanyaan, mengunci satu run dan mengirim event NDJSON. "
            "Browser tidak mengeksekusi file Python secara langsung.",
        ),
        (
            "boundary",
            "create_app.local_boundary",
            "Batas UI lokal dan Origin/CSRF",
            "Host loopback, Origin dan anti-CSRF diperiksa sebelum menjalankan request. "
            "Token Azure tidak pernah diberikan kepada JavaScript.",
        ),
    ):
        catalog[key] = {"key": key, **python_source(Path(__file__), symbol, label, explanation)}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        try:
            if app.state.tasks:
                await asyncio.gather(*app.state.tasks)
        finally:
            await runtime.close()

    app = FastAPI(title=runtime.info["title"], lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.csrf = secrets.token_urlsafe(48)
    app.state.lock = asyncio.Lock()
    app.state.tasks = set()
    app.state.stopping = False

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.url.hostname not in ("127.0.0.1", "localhost"):
            logger.warning("Non-loopback UI host rejected.")
            return JSONResponse({"error": "UI hanya tersedia pada loopback."}, status_code=403)
        if request.method not in ("GET", "HEAD") and (
            request.headers.get("origin") != str(request.base_url).rstrip("/")
            or not secrets.compare_digest(
                request.headers.get("x-demo-csrf", ""),
                app.state.csrf,
            )
        ):
            logger.warning("Origin/CSRF rejected before upstream work.")
            return JSONResponse(
                {"error": "Origin atau token browser tidak valid."}, status_code=403
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            if request.url.path == "/guide" or request.url.path.endswith(".html")
            else "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.get("/")
    def index():
        return FileResponse(ASSETS / "index.html")

    @app.get("/assets/{name}")
    def asset(name: str):
        files = {
            "app.js": ASSETS / "app.js",
            "style.css": ASSETS / "style.css",
            "base.css": ROOT / "src" / "maf_service" / "ui" / "style.css",
        }
        if name not in files:
            raise HTTPException(404, "Asset tidak tersedia.")
        return FileResponse(files[name])

    @app.get("/health")
    def health():
        return {
            "status": "stopping" if app.state.stopping else "ready",
            "service": runtime.info["service"],
            "synthetic_only": True,
            "source_sha256": runtime.info["source_sha256"],
        }

    @app.get("/ui/context")
    def context():
        return {
            **runtime.info,
            "csrf_token": app.state.csrf,
            "busy": app.state.lock.locked(),
            "stopping": app.state.stopping,
            "presets": presets,
            "cases": cases,
            "definition": {
                key: value for key, value in runtime.definition.items() if key != "text"
            },
            "code": [
                {
                    "key": key,
                    **{
                        name: value
                        for name, value in source.items()
                        if name not in ("text", "lessons")
                    },
                }
                for key, source in catalog.items()
            ],
        }

    @app.get("/ui/code/{key}")
    def source(key: str):
        if key not in catalog:
            logger.warning("Unknown source-code key rejected: %s", key)
            raise HTTPException(404, "Source key tidak tersedia.")
        return {"key": key, **catalog[key]}

    @app.get("/ui/definition")
    def definition():
        return runtime.definition

    @app.get("/guide")
    def guide():
        filename = runtime.info["guide_name"]
        if filename not in ("logicapps-ui-walkthrough.html", "maf-declarative-walkthrough.html"):
            raise RuntimeError("The runtime guide is not whitelisted.")
        path = ROOT / "docs" / "how-to" / filename
        if not path.is_file():
            logger.error("The requested runtime guide has not been generated: %s", filename)
            raise HTTPException(503, "Panduan HTML belum dibangun.")
        return FileResponse(path)

    @app.get("/{filename}.html")
    def related_guide(filename: str):
        allowed = {
            "logicapps-alur-request",
            "logicapps-node-walkthrough",
            "maf-code-first-walkthrough",
            "logicapps-ui-walkthrough",
            "maf-declarative-walkthrough",
        }
        if filename not in allowed:
            raise HTTPException(404, "Panduan tidak tersedia.")
        path = ROOT / "docs" / "how-to" / (filename + ".html")
        if not path.is_file():
            raise HTTPException(503, "Panduan belum dibangun.")
        return FileResponse(path)

    @app.get("/diagrams/local-ui/declarative-ui-flow.png")
    @app.get("/diagrams/local-ui/declarative-ui-flow.drawio")
    @app.get("/screenshots/local-ui/declarative-mcp.png")
    def declarative_guide_asset(request: Request):
        relative = Path(*request.url.path.lstrip("/").split("/"))
        path = ROOT / "docs" / "how-to" / relative
        if not path.is_file():
            logger.error("A declarative guide asset is missing: %s", relative)
            raise HTTPException(503, "Aset panduan belum tersedia.")
        if path.suffix == ".png":
            return FileResponse(path, media_type="image/png")
        return FileResponse(path, media_type="application/xml", filename=path.name)

    @app.get("/diagrams/maf/{filename}")
    def maf_source_diagram(filename: str):
        if filename not in ("07-yaml-python-paired.png", "07-yaml-python-paired.drawio"):
            raise HTTPException(404, "Diagram tidak tersedia.")
        path = ROOT / "docs" / "how-to" / "diagrams" / "maf" / filename
        if not path.is_file():
            logger.error("A configured MAF documentation diagram is missing: %s", filename)
            raise HTTPException(503, "Diagram belum tersedia.")
        if filename.endswith(".png"):
            return FileResponse(path, media_type="image/png")
        return FileResponse(path, media_type="application/xml", filename=filename)

    @app.get("/screenshots/logicapps-designer-20261117/{filename}")
    def designer_capture(filename: str):
        folder = ROOT / "docs" / "how-to" / "screenshots" / "logicapps-designer-20261117"
        manifest = json.loads((folder / "captures.json").read_text(encoding="utf-8"))
        allowed = {manifest["overview"]["file"], *(item["file"] for item in manifest["parameters"])}
        if filename not in allowed or Path(filename).name != filename:
            raise HTTPException(404, "Capture tidak tersedia.")
        path = folder / filename
        if not path.is_file():
            logger.error("A configured documentation capture is missing: %s", filename)
            raise HTTPException(503, "Capture belum tersedia.")
        return FileResponse(path, media_type="image/png")

    @app.post("/ui/shutdown")
    async def shutdown():
        if app.state.lock.locked():
            logger.warning("Shutdown refused during an active run.")
            raise HTTPException(409, "Tunggu run dan cleanup selesai sebelum menghentikan UI.")
        if on_shutdown is None:
            raise HTTPException(409, "Shutdown hanya tersedia melalui launcher lokal.")
        app.state.stopping = True
        return JSONResponse(
            {"status": "stopping", "scope": "local_ui_only"},
            background=BackgroundTask(on_shutdown),
        )

    @app.post("/ui/runs")
    async def run(body: UiRequest):
        if app.state.stopping:
            raise HTTPException(503, "UI sedang dihentikan.")
        if app.state.lock.locked():
            logger.warning("Concurrent UI request rejected.")
            raise HTTPException(409, "Run sebelumnya masih berjalan.")
        await app.state.lock.acquire()
        queue: asyncio.Queue[dict] = asyncio.Queue()
        loop = asyncio.get_running_loop()
        sequence = 0

        def send(payload: dict):
            def enqueue():
                nonlocal sequence
                sequence += 1
                queue.put_nowait(
                    {
                        "sequence": sequence,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        **payload,
                    }
                )

            loop.call_soon_threadsafe(enqueue)

        def observe(update: dict):
            if update["code_key"] not in catalog:
                raise ValueError("An execution event references unknown source code.")
            send({"type": "progress", "update": {**update, "run_id": str(body.run_id)}})

        async def execute():
            try:
                output = await runtime.execute(body, observe)
                send({"type": "result", "output": output})
            except RunFailure as error:
                logger.exception("UI execution failed: run=%s", body.run_id)
                send(
                    {
                        "type": "error",
                        "run_id": str(body.run_id),
                        "message": str(error),
                        "error_type": type(error).__name__,
                        "upstream_status": error.upstream_status,
                    }
                )
            finally:
                app.state.lock.release()

        send(
            {
                "type": "started",
                "run_id": str(body.run_id),
                "identity_mode": runtime.info["identity_mode"],
            }
        )
        task = asyncio.create_task(execute())
        app.state.tasks.add(task)

        def finished(done: asyncio.Task):
            app.state.tasks.discard(done)
            if not done.cancelled() and done.exception() is not None:
                logger.error("Unexpected UI execution error: %r", done.exception())
                send(
                    {
                        "type": "error",
                        "run_id": str(body.run_id),
                        "message": "Kesalahan eksekusi; periksa log. Tidak ada hasil pengganti.",
                        "error_type": type(done.exception()).__name__,
                        "upstream_status": None,
                    }
                )

        task.add_done_callback(finished)

        async def stream():
            while True:
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=12)
                except TimeoutError:
                    yield '{"type":"heartbeat"}\n'
                    continue
                yield json.dumps(frame, separators=(",", ":")) + "\n"
                if frame["type"] in ("result", "error"):
                    break

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app
