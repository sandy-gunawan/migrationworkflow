import hashlib
import json
import zipfile

import pytest

from tools import package_app, prepare_linux_dependencies


@pytest.fixture
def package_root(tmp_path, monkeypatch):
    monkeypatch.setattr(package_app, "ROOT", tmp_path)
    monkeypatch.setattr(prepare_linux_dependencies, "ROOT", tmp_path)
    for folder in (
        "src/maf_service/resources", "src/maf_service/ui", "data/seed", "build/linux_site_packages",
    ):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / "src/maf_service/app.py").write_text("print('synthetic')\n")
    (tmp_path / "src/maf_service/resources/mapping.json").write_text('{"source": "frozen"}')
    (tmp_path / "src/maf_service/resources/source.workflow.yaml").write_text("kind: workflow\n")
    (tmp_path / "src/maf_service/ui/index.html").write_text("<main>MAF UI</main>")
    (tmp_path / "src/maf_service/ui/app.js").write_text("console.log('synthetic');")
    (tmp_path / "src/maf_service/ui/style.css").write_text("body { color: steelblue; }")
    (tmp_path / "data/seed/mining.json").write_text('{"synthetic": true}')
    (tmp_path / ".deployment").write_text("[config]\nSCM_DO_BUILD_DURING_DEPLOYMENT=false\n")
    (tmp_path / "requirements.txt").write_text("example==1.0\n")
    return tmp_path


def test_source_package_includes_runtime_resources_without_dependencies(package_root):
    destination = package_root / "build" / "source.zip"
    package_app.main(["--source-only", "--output", str(destination)])
    with zipfile.ZipFile(destination) as archive:
        assert archive.read("maf_service/resources/mapping.json") == b'{"source": "frozen"}'
        assert archive.read("maf_service/resources/source.workflow.yaml") == (
            package_root / "src/maf_service/resources/source.workflow.yaml"
        ).read_bytes()
        assert "data/seed/mining.json" in archive.namelist()
        assert archive.read("maf_service/ui/index.html") == b"<main>MAF UI</main>"
        assert "maf_service/ui/app.js" in archive.namelist()
        assert "maf_service/ui/style.css" in archive.namelist()
        assert not any(name.startswith(".python_packages/") for name in archive.namelist())


def test_package_rejects_proof_for_a_different_lock(package_root):
    proof = {
        "target": "Linux x86_64 CPython 3.13",
        "dependency_closure_checked": True,
        "requirements_sha256": "stale",
    }
    (package_root / "build/linux-dependency-proof.json").write_text(json.dumps(proof))
    with pytest.raises(SystemExit, match="dependency proof"):
        package_app.main([])


def test_linux_preparation_reuses_exact_target_metadata(package_root, monkeypatch):
    info = package_root / "build/linux_site_packages/example-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: example\nVersion: 1.0\n")
    (info / "WHEEL").write_text("Wheel-Version: 1.0\nTag: py3-none-any\n")

    def unexpected_install(*args, **kwargs):
        pytest.fail("An unchanged installed Linux wheel must not be downloaded again.")

    monkeypatch.setattr(prepare_linux_dependencies.subprocess, "run", unexpected_install)
    prepare_linux_dependencies.main([])
    proof = json.loads((package_root / "build/linux-dependency-proof.json").read_text())
    assert proof["package_count"] == 1
    assert proof["requirements_sha256"] == hashlib.sha256(
        (package_root / "requirements.txt").read_bytes()
    ).hexdigest()


def test_linux_preparation_rejects_incomplete_target_closure(package_root):
    info = package_root / "build/linux_site_packages/example-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: example\nVersion: 1.0\nRequires-Dist: missing>=2\n"
    )
    (info / "WHEEL").write_text("Wheel-Version: 1.0\nTag: py3-none-any\n")
    with pytest.raises(SystemExit, match="dependency missing"):
        prepare_linux_dependencies.main([])
