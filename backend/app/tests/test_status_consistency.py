from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "verify_status_consistency.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_status_consistency", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_valid_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _write_file(
        root / "STATUS.md",
        "\n".join(
            [
                "# STATUS",
                "- Alpha proof status: PASS",
                "- Production ready: FALSE",
                "This repository is an alpha/research-grade platform, not a production legal system.",
            ]
        )
        + "\n",
    )
    shared_doc = "\n".join(
        [
            "See STATUS.md for canonical status.",
            "Current proof: artifacts/proof/current/CURRENT_PROOF.md",
            "Current release readiness: artifacts/proof/current/release_readiness.md",
        ]
    )
    _write_file(
        root / "CURRENT_STATUS.md",
        shared_doc + "\n- Alpha proof status: PASS\n- Production ready: FALSE\n",
    )
    _write_file(root / "README.md", shared_doc + "\n")
    _write_file(root / "docs" / "RELEASE_READINESS.md", shared_doc + "\n")
    _write_file(root / "docs" / "REPO_REALITY.md", shared_doc + "\n")
    _write_file(root / "docs" / "DEPLOYMENT.md", shared_doc + "\n")
    _write_file(root / "docs" / "PROOF_POLICY.md", "Current proof only.\n")
    _write_file(
        root / "artifacts" / "proof" / "current" / "CURRENT_PROOF.md",
        "current proof\n",
    )
    _write_file(
        root / "artifacts" / "proof" / "current" / "release_gate.json",
        json.dumps({"alpha_gate_passed": True, "checks": []}) + "\n",
    )
    _write_file(
        root / "artifacts" / "proof" / "current" / "release_readiness.md",
        "current readiness\n",
    )
    _write_file(
        root / "artifacts" / "proof" / "release_readiness.md",
        "ARCHIVED / NOT CURRENT — see artifacts/proof/current/\n",
    )
    return root


def test_status_consistency_passes_on_canonical_layout(tmp_path: Path) -> None:
    module = _load_module()
    root = _seed_valid_repo(tmp_path)

    assert module.verify(root) == []


def test_status_consistency_rejects_stale_release_path_reference(tmp_path: Path) -> None:
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "docs" / "RELEASE_READINESS.md",
        "See STATUS.md\nartifacts/proof/release_readiness.md\nartifacts/proof/current/CURRENT_PROOF.md\n",
    )

    errors = module.verify(root)

    assert "docs/RELEASE_READINESS.md:stale_release_readiness_reference" in errors


def test_status_consistency_rejects_unarchived_legacy_release_file(tmp_path: Path) -> None:
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(root / "artifacts" / "proof" / "release_readiness.md", "legacy live file\n")

    errors = module.verify(root)

    assert "artifacts/proof/release_readiness.md:live_unarchived_legacy_file" in errors


def test_status_consistency_rejects_current_status_contradiction(tmp_path: Path) -> None:
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "CURRENT_STATUS.md",
        "See STATUS.md\nartifacts/proof/current/CURRENT_PROOF.md\nartifacts/proof/current/release_readiness.md\n- Alpha proof status: FAIL\n- Production ready: FALSE\n",
    )

    errors = module.verify(root)

    assert "CURRENT_STATUS.md:alpha_status_contradicts_STATUS.md" in errors


def test_status_consistency_rejects_production_ready_claim_without_proof(tmp_path: Path) -> None:
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "README.md",
        "See STATUS.md\nartifacts/proof/current/CURRENT_PROOF.md\nartifacts/proof/current/release_readiness.md\nProduction ready: TRUE\n",
    )

    errors = module.verify(root)

    assert "README.md:production_ready_claim_without_proof" in errors


# ── New proof-honesty tests ───────────────────────────────────────────────────

def test_missing_release_gate_json_is_an_error(tmp_path: Path) -> None:
    """Checker must flag a missing release_gate.json (proof not generated)."""
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    (root / "artifacts" / "proof" / "current" / "release_gate.json").unlink()

    errors = module.verify(root)

    assert any("missing:artifacts/proof/current/release_gate.json" in e for e in errors)


def test_status_pass_contradicts_release_gate_false_is_an_error(tmp_path: Path) -> None:
    """STATUS.md claiming PASS while release_gate.json says false must be flagged."""
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "artifacts" / "proof" / "current" / "release_gate.json",
        json.dumps({"alpha_gate_passed": False, "checks": []}) + "\n",
    )
    # STATUS.md still says PASS (from seed)
    errors = module.verify(root)

    assert any("false_pass_claim" in e for e in errors)


def test_status_blocked_with_release_gate_false_is_clean(tmp_path: Path) -> None:
    """STATUS.md saying BLOCKED while release_gate.json says false must NOT produce a contradiction error."""
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "artifacts" / "proof" / "current" / "release_gate.json",
        json.dumps({"alpha_gate_passed": False, "checks": []}) + "\n",
    )
    # Rewrite STATUS.md to say BLOCKED
    _write_file(
        root / "STATUS.md",
        "\n".join([
            "# STATUS",
            "- Alpha proof status: BLOCKED",
            "- Alpha readiness status: BLOCKED",
            "- Production ready: FALSE",
            "This repository is an alpha/research-grade platform, not a production legal system.",
        ]) + "\n",
    )
    errors = module.verify(root)

    assert not any("false_pass_claim" in e for e in errors)
    assert not any("false_readiness_claim" in e for e in errors)


def test_gate_summary_pass_with_frontend_not_run_is_an_error(tmp_path: Path) -> None:
    """alpha_gate_summary.json claiming pass while frontend_tests_passed=not_run must be flagged."""
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "artifacts" / "proof" / "current" / "alpha_gate_summary.json",
        json.dumps({"alpha_gate_pass": True, "frontend_tests_passed": "not_run"}) + "\n",
    )
    errors = module.verify(root)

    assert any("false_pass:alpha_gate_pass=true but frontend_tests_passed=not_run" in e for e in errors)


def test_gate_summary_pass_with_frontend_true_is_clean(tmp_path: Path) -> None:
    """alpha_gate_summary.json with alpha_gate_pass=true and frontend_tests_passed=true must be OK."""
    module = _load_module()
    root = _seed_valid_repo(tmp_path)
    _write_file(
        root / "artifacts" / "proof" / "current" / "alpha_gate_summary.json",
        json.dumps({"alpha_gate_pass": True, "frontend_tests_passed": True}) + "\n",
    )
    errors = module.verify(root)

    assert not any("alpha_gate_summary.json" in e for e in errors)