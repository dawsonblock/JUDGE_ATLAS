from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "production_preflight.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("production_preflight", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dev_defaults_fail_preflight(monkeypatch):
    module = _load_module()
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("JTA_JWT_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOWLIST", raising=False)
    monkeypatch.delenv("EVIDENCE_STORE_ROOT", raising=False)

    checks = module.run_checks()

    failed = {check["name"] for check in checks if not check["passed"]}
    assert "production_environment_selected" in failed
    assert "strong_jwt_secret" in failed
    assert "cors_allowlist_not_wildcard" in failed
    assert "evidence_store_root_configured" in failed


def test_weak_secret_fails(monkeypatch):
    module = _load_module()
    monkeypatch.setenv("JTA_JWT_SECRET", "changeme")

    checks = module.run_checks()

    result = next(check for check in checks if check["name"] == "strong_jwt_secret")
    assert result["passed"] is False


def test_wildcard_cors_fails(monkeypatch):
    module = _load_module()
    monkeypatch.setenv("CORS_ALLOWLIST", "*")

    checks = module.run_checks()

    result = next(check for check in checks if check["name"] == "cors_allowlist_not_wildcard")
    assert result["passed"] is False
