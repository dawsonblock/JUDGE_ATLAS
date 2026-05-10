from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _seed_minimal_repo(root: Path) -> None:
    (root / "backend" / "app").mkdir(parents=True, exist_ok=True)
    (root / "backend" / "alembic" / "versions").mkdir(parents=True, exist_ok=True)
    (root / "frontend").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "artifacts" / "proof" / "current").mkdir(parents=True, exist_ok=True)
    (root / "artifacts" / "proof" / "history").mkdir(parents=True, exist_ok=True)

    (root / "backend" / "app" / "sample.py").write_text("x = 1\n", encoding="utf-8")
    (root / "backend" / "alembic" / "versions" / "0001_init.py").write_text(
        "# migration\n", encoding="utf-8"
    )
    (root / "backend" / "pyproject.toml").write_text(
        "[project]\nname='x'\n", encoding="utf-8"
    )
    (root / "frontend" / "package.json").write_text("{}\n", encoding="utf-8")
    (root / "scripts" / "helper.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "docs" / "CURRENT_STATUS.md").write_text("status\n", encoding="utf-8")
    (root / "docs" / "DB_PROOF.md").write_text("db\n", encoding="utf-8")
    (root / "docs" / "FRONTEND_SECURITY_TRIAGE.md").write_text(
        "triage\n", encoding="utf-8"
    )
    (root / "docs" / "schema_audit.md").write_text("historical\n", encoding="utf-8")
    (root / "Makefile").write_text("all:\n\t@echo ok\n", encoding="utf-8")


def test_proof_freshness_passes_when_hash_matches(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_minimal_repo(repo_root)

    module = _load_module(
        "check_proof_freshness_module",
        Path(__file__).resolve().parents[3] / "scripts" / "check_proof_freshness.py",
    )

    proof_hash, _ = module.compute_proof_input_tree_hash(repo_root)
    release_gate = {
        "proof_input_tree_hash": proof_hash,
        "proof_input_tree_hash_algorithm": "sha256",
    }
    (repo_root / "artifacts" / "proof" / "current" / "release_gate.json").write_text(
        json.dumps(release_gate), encoding="utf-8"
    )
    (repo_root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md").write_text(
        f"- proof_input_tree_hash: {proof_hash}\n", encoding="utf-8"
    )

    ok, _message = module.check_against_artifacts(repo_root)
    assert ok


def test_proof_freshness_fails_when_tracked_file_changes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_minimal_repo(repo_root)

    module = _load_module(
        "check_proof_freshness_module",
        Path(__file__).resolve().parents[3] / "scripts" / "check_proof_freshness.py",
    )

    proof_hash, _ = module.compute_proof_input_tree_hash(repo_root)
    release_gate = {
        "proof_input_tree_hash": proof_hash,
        "proof_input_tree_hash_algorithm": "sha256",
    }
    (repo_root / "artifacts" / "proof" / "current" / "release_gate.json").write_text(
        json.dumps(release_gate), encoding="utf-8"
    )
    (repo_root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md").write_text(
        f"- proof_input_tree_hash: {proof_hash}\n", encoding="utf-8"
    )

    (repo_root / "backend" / "app" / "sample.py").write_text(
        "x = 2\n", encoding="utf-8"
    )

    ok, message = module.check_against_artifacts(repo_root)
    assert not ok
    assert "hash mismatch" in message


def test_proof_freshness_ignores_artifacts_history_and_pyc(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_minimal_repo(repo_root)

    module = _load_module(
        "check_proof_freshness_module",
        Path(__file__).resolve().parents[3] / "scripts" / "check_proof_freshness.py",
    )

    before_hash, _ = module.compute_proof_input_tree_hash(repo_root)

    (repo_root / "artifacts" / "proof" / "history" / "old.txt").write_text(
        "old\n", encoding="utf-8"
    )
    pycache_dir = repo_root / "backend" / "app" / "__pycache__"
    pycache_dir.mkdir(parents=True, exist_ok=True)
    (pycache_dir / "sample.cpython-311.pyc").write_bytes(b"pyc")

    after_hash, _ = module.compute_proof_input_tree_hash(repo_root)
    assert before_hash == after_hash


def test_release_gate_writes_proof_input_tree_hash() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    release_gate = _load_module(
        "release_gate_module",
        repo_root / "scripts" / "release_gate.py",
    )
    check_proof_freshness = _load_module(
        "check_proof_freshness_module",
        repo_root / "scripts" / "check_proof_freshness.py",
    )

    metadata = release_gate._collect_proof_input_metadata(repo_root, sys.executable)
    expected_hash, _ = check_proof_freshness.compute_proof_input_tree_hash(repo_root)

    assert metadata["proof_input_tree_hash"] == expected_hash
    assert metadata["proof_input_tree_hash_algorithm"] == "sha256"
    assert "backend/app/**/*" in metadata["proof_input_paths"]
