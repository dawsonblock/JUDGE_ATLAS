from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "validate_release_archive.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_release_archive", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_zip(path: Path, files: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)


def _valid_files(root: str = "JUDGE_ATLAS-main") -> dict[str, str]:
    prefix = f"{root}/"
    return {
        prefix + "backend/app/main.py": "print('ok')\n",
        prefix + "frontend/package.json": "{}\n",
        prefix + "docs/README.md": "docs\n",
        prefix + "scripts/release_gate.py": "print('gate')\n",
        prefix + "artifacts/proof/current/CURRENT_PROOF.md": "current proof\n",
        prefix + "artifacts/proof/current/release_readiness.md": "current readiness\n",
        prefix + "README.md": "repo readme\n",
    }


def test_validate_release_archive_accepts_valid_archive(tmp_path: Path) -> None:
    module = _load_module()
    archive = tmp_path / "valid.zip"
    _write_zip(archive, _valid_files())

    report = module.inspect_archive(archive, expected_root="JUDGE_ATLAS-main")

    assert report["valid"] is True
    assert report["top_level_roots"] == ["JUDGE_ATLAS-main"]


def test_validate_release_archive_rejects_wrong_root(tmp_path: Path) -> None:
    module = _load_module()
    archive = tmp_path / "wrong-root.zip"
    _write_zip(archive, _valid_files(root="JUDGE-main"))

    report = module.inspect_archive(archive, expected_root="JUDGE_ATLAS-main")

    assert report["valid"] is False
    assert "archive_root_mismatch:JUDGE-main!=JUDGE_ATLAS-main" in report["errors"]


def test_validate_release_archive_rejects_node_modules(tmp_path: Path) -> None:
    module = _load_module()
    archive = tmp_path / "node-modules.zip"
    files = _valid_files()
    files["JUDGE_ATLAS-main/frontend/node_modules/react/index.js"] = "module.exports = {}\n"
    _write_zip(archive, files)

    report = module.inspect_archive(archive, expected_root="JUDGE_ATLAS-main")

    assert report["valid"] is False
    assert any(error.startswith("forbidden_path:") for error in report["errors"])


def test_validate_release_archive_rejects_external_by_default(tmp_path: Path) -> None:
    module = _load_module()
    archive = tmp_path / "external.zip"
    files = _valid_files()
    files["JUDGE_ATLAS-main/external/reference/README.md"] = "external ref\n"
    _write_zip(archive, files)

    report = module.inspect_archive(archive, expected_root="JUDGE_ATLAS-main")

    assert report["valid"] is False
    assert any(error.startswith("forbidden_external_path:") for error in report["errors"])


def test_validate_release_archive_rejects_missing_current_proof_dir(tmp_path: Path) -> None:
    module = _load_module()
    archive = tmp_path / "missing-proof.zip"
    files = _valid_files()
    files.pop("JUDGE_ATLAS-main/artifacts/proof/current/CURRENT_PROOF.md")
    files.pop("JUDGE_ATLAS-main/artifacts/proof/current/release_readiness.md")
    _write_zip(archive, files)

    report = module.inspect_archive(archive, expected_root="JUDGE_ATLAS-main")

    assert report["valid"] is False
    assert "missing_required_directory:artifacts/proof/current/" in report["errors"] or any(
        error.startswith("missing_required_proof_file:") for error in report["errors"]
    )