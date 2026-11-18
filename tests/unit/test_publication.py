import re
import secrets
import shutil
import subprocess

import pytest

from tools.check_publication import check, public_files, snapshot


def repository(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".env*\n*.local.json\n", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("name", [".env.example", ".ENV.PRODUCTION", "deploy.PFX"])
def test_force_staged_environment_file_is_rejected_even_when_git_ignores_it(tmp_path, name):
    root = repository(tmp_path)
    (root / name).write_text("EXAMPLE=synthetic-test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-f", name], check=True)
    with pytest.raises(ValueError, match=re.escape(name)):
        public_files(root)


def test_clean_working_file_cannot_hide_different_staged_contents(tmp_path):
    root = repository(tmp_path / "repo")
    source = root / "example.txt"
    source.write_text("synthetic staged contents\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "example.txt"], check=True)
    source.write_text("clean working contents\n", encoding="utf-8")
    destination = tmp_path / "snapshot"
    snapshot(root, destination)
    assert (destination / "index" / "example.txt").read_text() == "synthetic staged contents\n"
    assert (destination / "working" / "example.txt").read_text() == "clean working contents\n"


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="Gitleaks is an optional local tool.")
def test_secret_scanner_rejects_a_synthetic_token_without_printing_it(tmp_path, capsys):
    root = repository(tmp_path)
    synthetic_token = "ghp_" + secrets.token_hex(18)
    (root / "example.py").write_text(f'token = "{synthetic_token}"\n', encoding="utf-8")
    assert check(root) is False
    output = capsys.readouterr().out
    assert "example.py" in output
    assert synthetic_token not in output
