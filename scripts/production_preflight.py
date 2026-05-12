#!/usr/bin/env python3
"""Run production-only readiness checks without mutating state."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "artifacts" / "proof" / "current" / "production_preflight.md"

WEAK_SECRET_MARKERS = {
    "changeme",
    "change-me",
    "default",
    "dev",
    "development",
    "test",
    "example",
}


def _is_weak_secret(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.strip().lower()
    if len(value) < 32:
        return True
    return any(marker in lowered for marker in WEAK_SECRET_MARKERS)


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _check(name: str, passed: bool, details: str) -> dict:
    return {"name": name, "passed": passed, "details": details}


def run_checks(allow_repo_evidence_store: bool = False) -> list[dict]:
    env = os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "dev"
    evidence_root = os.getenv("EVIDENCE_STORE_ROOT", "").strip()
    cors_allowlist = os.getenv("CORS_ALLOWLIST", "").strip()
    egress_proxy = os.getenv("JTA_FETCH_EGRESS_PROXY", "").strip()
    db_url = os.getenv("DATABASE_URL", "").strip()
    backup_policy = os.getenv("BACKUP_POLICY", "").strip()

    checks: list[dict] = []
    checks.append(_check("production_environment_selected", env.lower() in {"prod", "production"}, f"ENVIRONMENT={env}"))

    jwt_secret = os.getenv("JTA_JWT_SECRET", "")
    checks.append(_check("strong_jwt_secret", not _is_weak_secret(jwt_secret), "JTA_JWT_SECRET must be set and >= 32 chars, non-default"))

    checks.append(_check("legacy_admin_token_disabled", not _bool_env("JTA_ENABLE_LEGACY_ADMIN_TOKEN"), "JTA_ENABLE_LEGACY_ADMIN_TOKEN must be false in production"))

    checks.append(_check("redis_rate_limit_configured", bool(os.getenv("REDIS_URL", "").strip()), "REDIS_URL must be configured"))

    evidence_path = Path(evidence_root) if evidence_root else None
    checks.append(_check("evidence_store_root_configured", bool(evidence_root), f"EVIDENCE_STORE_ROOT={evidence_root or 'unset'}"))

    if evidence_path:
        checks.append(_check("evidence_store_exists", evidence_path.exists(), str(evidence_path)))
        checks.append(_check("evidence_store_writable", os.access(evidence_path, os.W_OK), str(evidence_path)))
        inside_repo = evidence_path.is_absolute() and evidence_path.resolve().is_relative_to(REPO_ROOT)
        checks.append(_check("evidence_store_outside_repo", (not inside_repo) or allow_repo_evidence_store, f"inside_repo={inside_repo}"))

    checks.append(_check("cors_allowlist_not_wildcard", bool(cors_allowlist) and cors_allowlist != "*", f"CORS_ALLOWLIST={cors_allowlist or 'unset'}"))

    checks.append(
        _check(
            "egress_proxy_configured",
            bool(egress_proxy) or _bool_env("JTA_ALLOW_DIRECT_FETCH_IN_NON_PROD"),
            "JTA_FETCH_EGRESS_PROXY required unless JTA_ALLOW_DIRECT_FETCH_IN_NON_PROD=true",
        )
    )

    checks.append(_check("database_url_configured", bool(db_url), "DATABASE_URL must be set"))
    checks.append(_check("debug_mode_disabled", not _bool_env("DEBUG"), "DEBUG must be false"))
    checks.append(_check("backup_policy_configured", bool(backup_policy), "BACKUP_POLICY must be documented/configured"))

    return checks


def write_report(checks: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for check in checks if check["passed"])
    failed = len(checks) - passed
    lines = [
        "# Production Preflight",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- checks_total: {len(checks)}",
        f"- checks_passed: {passed}",
        f"- checks_failed: {failed}",
        f"- production_preflight_passed: {'true' if failed == 0 else 'false'}",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {status} {check['name']}: {check['details']}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-fail-in-dev", action="store_true")
    parser.add_argument("--allow-repo-evidence-store", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = run_checks(allow_repo_evidence_store=args.allow_repo_evidence_store)
    write_report(checks, OUTPUT_PATH)

    failed = [check for check in checks if not check["passed"]]
    payload = {
        "production_preflight_passed": len(failed) == 0,
        "failed_checks": [check["name"] for check in failed],
        "report": str(OUTPUT_PATH),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Production preflight report written: {OUTPUT_PATH}")
        print("PASS" if not failed else "FAIL")

    if failed and args.expect_fail_in_dev:
        return 0
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
