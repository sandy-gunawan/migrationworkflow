import argparse
import hashlib
import json
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence" / "official-migration"
PROTECTED = (
    "src",
    "source",
    "targets",
    "tools",
    "migration",
    "tests",
    "config",
    "contracts",
    "data",
    "infra",
    ".vscode",
    "pyproject.toml",
    "requirements.txt",
    ".deployment",
)


def snapshot() -> dict:
    files = {}
    for name in PROTECTED:
        location = ROOT / name
        candidates = sorted(location.rglob("*")) if location.is_dir() else [location]
        for path in candidates:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "files": files,
        "packages": dict(
            sorted((item.metadata["Name"].lower(), item.version) for item in distributions())
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("capture", "verify"))
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    baseline_path = EVIDENCE / "isolation-before.json"
    actual = snapshot()
    if args.action == "capture":
        if baseline_path.exists():
            raise FileExistsError("An isolation baseline already exists; refusing to overwrite it.")
        baseline_path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
        print(f"Captured {len(actual['files'])} protected files and original environment packages.")
        return

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    changed = [
        name
        for name in sorted(baseline["files"].keys() | actual["files"].keys())
        if baseline["files"].get(name) != actual["files"].get(name)
    ]
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "protected_files": len(baseline["files"]),
        "changed_files": changed,
        "original_packages_unchanged": baseline["packages"] == actual["packages"],
        "status": "PASS" if not changed and baseline["packages"] == actual["packages"] else "FAIL",
    }
    (EVIDENCE / "isolation-after.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
