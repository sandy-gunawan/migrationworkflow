"""Scan exactly the public working-tree and index contents without exposing secrets."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        input=data, capture_output=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Git publication check failed: {args[0]} ({result.returncode}).")
    return result.stdout


def public_files(root: Path) -> tuple[list[str], set[str]]:
    staged = {
        name.decode("utf-8")
        for name in git(root, "ls-files", "--cached", "-z").split(b"\0") if name
    }
    untracked = {
        name.decode("utf-8")
        for name in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
        if name
    }
    names = sorted(staged | untracked)
    if not names:
        raise ValueError("No public files were found; an empty scan is not a successful check.")
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root),
         "check-ignore", "--no-index", "--stdin", "-z"],
        input=b"\0".join(name.encode("utf-8") for name in names) + b"\0",
        capture_output=True, check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("Unable to verify publication ignore rules.")
    ignored = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    private = {
        name for name in names
        if any(part == ".git" for part in PurePosixPath(name).parts)
        or PurePosixPath(name).name.casefold().startswith(".env")
        or PurePosixPath(name).name.casefold() in ("id_rsa", "id_ed25519", "credentials.json")
        or PurePosixPath(name).name.casefold().endswith(
            (".env", ".pem", ".key", ".pfx", ".p12", ".jks", ".keystore", ".publishsettings")
        )
    }
    forbidden = sorted(set(ignored) | private)
    if forbidden:
        raise ValueError("Private/ignored files are in the Git index: " + ", ".join(forbidden))
    return names, staged


def snapshot(root: Path, destination: Path) -> int:
    root = root.resolve()
    names, staged = public_files(root)
    for name in names:
        source = root / Path(name)
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError("Publication does not follow symlinks or external paths: " + name)
        if source.is_file():
            target = destination / "working" / Path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if name in staged:
            target = destination / "index" / Path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(git(root, "show", ":" + name))
    return len(names)


def check(root: Path) -> bool:
    scanner = shutil.which("gitleaks")
    if scanner is None:
        raise RuntimeError("Gitleaks is required; install it before running this publication gate.")
    with tempfile.TemporaryDirectory(prefix="publication-check-") as directory:
        temporary = Path(directory)
        payload = temporary / "public"
        payload.mkdir()
        count = snapshot(root, payload)
        config = temporary / "scanner.toml"
        config.write_text("[extend]\nuseDefault = true\n", encoding="utf-8")
        report = temporary / "findings.json"
        result = subprocess.run(
            [
                scanner, "dir", str(payload), "--config", str(config),
                "--redact=100", "--no-banner", "--no-color", "--log-level=error",
                "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(temporary),
                "--max-decode-depth=5", "--max-archive-depth=2",
                "--report-format=json", "--report-path", str(report),
            ],
            capture_output=True, check=False,
        )
        if result.returncode not in (0, 1) or not report.is_file():
            raise RuntimeError(
                "Gitleaks did not complete successfully; publication is not cleared."
            )
        findings = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(findings, list):
            raise RuntimeError("Gitleaks returned an invalid report.")
        for finding in findings:
            path = Path(finding["File"])
            location = path.relative_to(payload) if path.is_absolute() else path
            print(f"{location}:{finding['StartLine']}: {finding['RuleID']}")
        if result.returncode or findings:
            print("FAIL: review scanner findings locally; no secret values were printed.")
            return False
        print(f"PASS: {count} public files checked, including index blobs; no secrets detected.")
        print("Local env/config files were not exported. Private Git refs were not scanned.")
        print("Do not use git push --mirror or copy the existing .git directory for publication.")
        return True


def main() -> None:
    try:
        passed = check(ROOT)
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Publication check failed: {error}") from None
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
