import argparse

import httpx
import uvicorn

from maf_service.demo_ui import create_ui_app


def stop_ui(port: int) -> None:
    origin = f"http://127.0.0.1:{port}"
    with httpx.Client(base_url=origin, timeout=5, trust_env=False) as client:
        health = client.get("/health")
        health.raise_for_status()
        if health.json().get("service") != "local-maf-ui":
            raise ValueError("Port ini bukan server MAF UI; tidak ada proses yang dihentikan.")
        context = client.get("/ui/context")
        context.raise_for_status()
        response = client.post(
            "/ui/shutdown",
            headers={"Origin": origin, "X-Demo-CSRF": context.json()["csrf_token"]},
        )
        response.raise_for_status()
        if response.json() != {"status": "stopping", "scope": "local_ui_only"}:
            raise ValueError("Shutdown acknowledgement tidak sesuai dengan server UI lokal.")
        print(f"Shutdown MAF UI pada {origin} diterima. Tunggu terminal server selesai.")
        print("Layanan Azure tidak diubah.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the loopback-only MAF execution UI.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--stop", action="store_true", help="Stop the idle local UI safely.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError("Choose a local port between 1024 and 65535.")
    if args.stop:
        try:
            stop_ui(args.port)
        except httpx.HTTPStatusError as error:
            parser.exit(1, f"UI tidak dihentikan: {error.response.json()}\n")
        except httpx.RequestError as error:
            parser.exit(1, f"UI tidak dapat dihubungi pada port {args.port}: {error}\n")
        return

    server: uvicorn.Server

    def request_shutdown() -> None:
        server.should_exit = True

    app = create_ui_app(on_shutdown=request_shutdown)
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=args.port, proxy_headers=False, access_log=False,
    ))
    server.run()


if __name__ == "__main__":
    main()
