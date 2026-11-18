import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "kppdemo-app.zip")
    args = parser.parse_args(argv)
    requirements = ROOT / "requirements.txt"
    deployment_config = ROOT / ".deployment"
    dependency_proof = ROOT / "build" / "linux-dependency-proof.json"
    dependencies = ROOT / "build" / "linux_site_packages"
    if not requirements.is_file() or not deployment_config.is_file():
        raise SystemExit("Generate the tested dependency lock before packaging.")
    if not args.source_only:
        if not dependency_proof.is_file() or not dependencies.is_dir():
            raise SystemExit("Prepare verified Linux dependencies before packaging.")
        proof = json.loads(dependency_proof.read_text(encoding="utf-8"))
        if (
            proof["target"] != "Linux x86_64 CPython 3.13"
            or not proof["dependency_closure_checked"]
            or proof.get("requirements_sha256")
            != hashlib.sha256(requirements.read_bytes()).hexdigest()
        ):
            raise SystemExit("Linux dependency proof does not match this application's lock.")
    source_files = sorted((ROOT / "src").rglob("*.py"))
    resource_root = ROOT / "src" / "maf_service" / "resources"
    source_files.extend(
        sorted(
            item
            for item in resource_root.glob("*")
            if item.is_file() and item.suffix in (".json", ".yaml")
        )
    )
    source_files.extend(
        sorted(
            item for item in (ROOT / "src" / "maf_service" / "ui").glob("*")
            if item.is_file() and item.suffix in (".html", ".css", ".js")
        )
    )
    seed = ROOT / "data" / "seed" / "mining.json"
    if not source_files or not seed.is_file():
        raise SystemExit("The synthetic application or seed is missing.")
    destination = args.output
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files:
            archive.write(path, path.relative_to(ROOT / "src"))
        archive.write(seed, "data/seed/mining.json")
        archive.write(requirements, "requirements.txt")
        archive.write(deployment_config, ".deployment")
        for path in [] if args.source_only else sorted(dependencies.rglob("*")):
            relative = path.relative_to(dependencies)
            if (
                not path.is_file()
                or "__pycache__" in relative.parts
                or relative.parts[0].lower() in ("bin", "scripts")
            ):
                continue
            if path.suffix in (".pyd", ".dll", ".exe"):
                raise SystemExit(f"Refusing a Windows binary in the Linux artifact: {relative}")
            if path.suffix == ".pyc":
                continue
            archive.write(path, Path(".python_packages") / "lib" / "site-packages" / relative)
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Archive integrity failed: {bad}")
        entries = archive.namelist()
        if any(
            ".env" in name or ".local." in name or name.startswith("config/") for name in entries
        ):
            raise SystemExit("Refusing to package local configuration or credentials.")
    print(
        json.dumps(
            {
                "artifact": str(destination),
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "file_count": len(entries),
                "content": "demo source, pinned Linux-only dependencies, and synthetic seed",
                "mode": "source_only_for_azure_build" if args.source_only else "prebuilt_linux",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
