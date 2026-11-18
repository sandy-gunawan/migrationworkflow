import argparse
import hashlib
import json
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-directory", type=Path)
    args = parser.parse_args(argv)
    environment = default_environment()
    environment.update(
        {
            "sys_platform": "linux",
            "os_name": "posix",
            "platform_system": "Linux",
            "platform_machine": "x86_64",
            "python_version": "3.13",
            "python_full_version": "3.13.18",
            "extra": "",
        }
    )
    requirements = [
        Requirement(line)
        for line in (ROOT / "requirements.txt").read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    selected = {
        canonicalize_name(item.name): item
        for item in requirements
        if item.marker is None or item.marker.evaluate(environment)
    }
    path = ROOT / "build" / "requirements.linux.txt"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "\n".join(f"{item.name}{item.specifier}" for item in selected.values()) + "\n",
        encoding="ascii",
    )
    destination = ROOT / "build" / "linux_site_packages"
    destination.mkdir(exist_ok=True)

    def installed():
        return {
            canonicalize_name(item.metadata["Name"]): item
            for item in distributions(path=[str(destination)])
        }

    present = installed()
    if set(present) - set(selected):
        raise SystemExit("Unexpected distributions in the Linux runtime target.")
    for name, info in present.items():
        if not selected[name].specifier.contains(info.version):
            raise SystemExit(f"Existing Linux wheel version disagrees with the lock: {name}")
    missing = [
        f"{item.name}{item.specifier}" for name, item in selected.items() if name not in present
    ]
    if missing:
        offline = (
            ["--no-index", "--find-links", str(args.wheel_directory)]
            if args.wheel_directory
            else []
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                str(destination),
                "--no-deps",
                "--only-binary=:all:",
                "--platform",
                "manylinux_2_28_x86_64",
                "--platform",
                "manylinux_2_17_x86_64",
                "--platform",
                "manylinux2014_x86_64",
                "--implementation",
                "cp",
                "--python-version",
                "3.13",
                "--abi",
                "cp313",
                "--abi",
                "abi3",
                "--disable-pip-version-check",
                *offline,
                *missing,
            ],
            check=True,
        )
    present = installed()
    if set(present) != set(selected):
        raise SystemExit("The Linux runtime target is incomplete.")
    for name, info in present.items():
        if not selected[name].specifier.contains(info.version):
            raise SystemExit(f"Installed Linux wheel version disagrees with the lock: {name}")
        wheel = info.read_text("WHEEL")
        if not wheel or "win_amd64" in wheel or "win32" in wheel:
            raise SystemExit(f"Missing or non-Linux wheel metadata: {name}")
        for raw in info.metadata.get_all("Requires-Dist", []):
            dependency = Requirement(raw)
            if dependency.marker is not None and not dependency.marker.evaluate(environment):
                continue
            name = canonicalize_name(dependency.name)
            if name not in selected:
                raise SystemExit(f"Linux dependency missing from the tested lock: {dependency}")
            version = present[name].version
            if not dependency.specifier.contains(version):
                raise SystemExit(f"Linux lock version does not satisfy {dependency}")
    if any(
        item.suffix.lower() in (".pyd", ".dll", ".exe")
        for item in destination.rglob("*")
        if item.relative_to(destination).parts[0].lower() not in ("bin", "scripts")
    ):
        raise SystemExit("A Windows binary exists in the Linux runtime target.")
    proof = {
        "target": "Linux x86_64 CPython 3.13",
        "dependency_closure_checked": True,
        "binary_wheels_only": True,
        "package_count": len(selected),
        "windows_binaries_included": False,
        "requirements_sha256": hashlib.sha256((ROOT / "requirements.txt").read_bytes()).hexdigest(),
        "packages": {name: item.version for name, item in sorted(present.items())},
    }
    (ROOT / "build" / "linux-dependency-proof.json").write_text(
        json.dumps(proof, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
