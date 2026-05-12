from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "build_release_archive.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_release_archive", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_repo(root: Path) -> None:
    _write_file(root / "README.md", "readme\n")
    _write_file(root / "STATUS.md", "Production ready: FALSE\n")
    _write_file(root / "backend" / "app" / "main.py", "print('ok')\n")
    _write_file(root / "frontend" / "package.json", "{}\n")
    _write_file(root / "docs" / "README.md", "docs\n")
    _write_file(root / "scripts" / "release_gate.py", "print('gate')\n")
    _write_file(root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md", "proof\n")
    _write_file(root / "artifacts" / "proof" / "current" / "release_readiness.md", "ready\n")
    _write_file(root / "external" / "reference" / "README.md", "external\n")
    _write_file(root / "artifacts" / "proof" / "archive" / "old.txt", "old\n")


def test_build_release_archive_excludes_external_and_proof_archive_by_default(tmp_path: Path) -> None:
    module = _load_module()
    root = tmp_path / "repo"
    _seed_repo(root)
    module.REPO_ROOT = root

    output = tmp_path / "dist" / "clean.zip"
    result = module.build_archive(
        output=output,
        root_name="JUDGE_ATLAS-main",
        include_external=False,
        include_proof_archive=False,
    )

    assert output.exists()
    assert len(result["archive_sha256"]) == 64

    with zipfile.ZipFile(output, "r") as zf:
        names = set(zf.namelist())
        assert "JUDGE_ATLAS-main/RELEASE_MANIFEST.json" in names
        assert "JUDGE_ATLAS-main/artifacts/proof/current/CURRENT_PROOF.md" in names
        assert all("/external/" not in name for name in names)
        assert all("/artifacts/proof/archive/" not in name for name in names)

        manifest = json.loads(zf.read("JUDGE_ATLAS-main/RELEASE_MANIFEST.json").decode("utf-8"))
        assert manifest["production_ready"] is False
        assert manifest["proof_path"] == "artifacts/proof/current"
        assert isinstance(manifest["archive_sha256"], str)
        assert len(manifest["archive_sha256"]) == 64
