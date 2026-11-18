import argparse

import httpx
import uvicorn

from spikes.execution_ui.server import Runtime, create_app


def arguments(description: str, default_port: int) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--stop", action="store_true", help="Stop only the idle owned local UI.")
    return parser


def stop_ui(port: int, expected_service: str) -> None:
    origin = f"http://127.0.0.1:{port}"
    with httpx.Client(base_url=origin, timeout=5, trust_env=False) as client:
        response = client.get("/health")
        response.raise_for_status()
        if response.json()["service"] != expected_service:
            raise ValueError("Port ini bukan UI yang dimaksud; tidak ada proses yang dihentikan.")
        context = client.get("/ui/context")
        context.raise_for_status()
        stopped = client.post(
            "/ui/shutdown",
            headers={
                "Origin": origin,
                "X-Demo-CSRF": context.json()["csrf_token"],
            },
        )
        stopped.raise_for_status()
        if stopped.json() != {"status": "stopping", "scope": "local_ui_only"}:
            raise ValueError("Shutdown acknowledgement tidak sesuai.")
    print(f"Shutdown diterima untuk {origin}; layanan Azure tidak diubah.")


def serve(runtime: Runtime, port: int) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a local port between 1024 and 65535.")
    server: uvicorn.Server

    def shutdown():
        server.should_exit = True

    app = create_app(runtime, on_shutdown=shutdown)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            proxy_headers=False,
            access_log=False,
        )
    )
    server.run()
