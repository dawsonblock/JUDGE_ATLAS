#!/usr/bin/env python3
"""Unified alpha release gate for JUDGE_ATLAS.

This gate executes the required alpha checks, writes canonical logs under
``artifacts/proof/current``, and fails if any referenced log file is missing.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from shutil import move

PROOF_INPUT_PATTERNS = [
    ".github/workflows/**/*",
    "backend/app/**/*",
    "backend/alembic/**/*",
    "backend/pyproject.toml",
    "demo/**/*",
    "frontend/**/*",
    "scripts/**/*",
    "docs/CURRENT_STATUS.md",
    "docs/DB_PROOF.md",
    "docs/LEGACY_AUTH_REMOVAL_PLAN.md",
    "docs/DEPENDENCY_REMEDIATION_PLAN.md",
    "docs/FRONTEND_SECURITY_TRIAGE.md",
    "docs/schema_audit.md",
    "README.md",
    "Makefile",
]


@dataclass
class GateStep:
    name: str
    command: str
    status: str  # "PASS" | "FAIL"
    exit_code: int
    duration_seconds: float
    log_path: str


@dataclass
class GateStepSpec:
    name: str
    log_name: str
    command: list[str]
    timeout_seconds: int | None = None


def _run(
    repo_root: Path,
    out_dir: Path,
    name: str,
    log_name: str,
    command: list[str],
    timeout_seconds: int | None = None,
) -> GateStep:
    log_path = out_dir / log_name
    t0 = time.monotonic()
    with log_path.open("w", encoding="utf-8") as fh:
        try:
            proc = subprocess.run(
                command,
                cwd=repo_root,
                stdout=fh,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
            return_code = proc.returncode
        except subprocess.TimeoutExpired:
            timeout_note = (
                "\n[release_gate] TIMEOUT after "
                f"{timeout_seconds}s for step '{name}'.\n"
            )
            fh.write(timeout_note)
            return_code = 124
    duration = round(time.monotonic() - t0, 3)
    passed = return_code == 0
    return GateStep(
        name=name,
        command=" ".join(command),
        status="PASS" if passed else "FAIL",
        exit_code=return_code,
        duration_seconds=duration,
        log_path=str(log_path.relative_to(repo_root)),
    )


def _missing_logs(repo_root: Path, checks: list[GateStep]) -> list[str]:
    missing: list[str] = []
    for check in checks:
        if not (repo_root / check.log_path).exists():
            missing.append(check.log_path)
    return missing


def _archive_legacy_sidecars(repo_root: Path, out_dir: Path) -> list[str]:
    legacy_names = [
        "manifest.json",
        "proof_all_summary.json",
        "environment_info.txt",
    ]
    history_dir = repo_root / "artifacts" / "proof" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for name in legacy_names:
        src = out_dir / name
        if not src.exists():
            continue
        dst = history_dir / f"{stamp}_{name}"
        move(str(src), str(dst))
        archived.append(str(dst.relative_to(repo_root)))

    readme = history_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Proof History Sidecars\n\n"
            "This directory stores historical sidecar artifacts moved from "
            "`artifacts/proof/current/`.\n\n"
            "Current authoritative proof state is produced by "
            "`artifacts/proof/current/release_gate.json` and "
            "`artifacts/proof/current/CURRENT_PROOF.md`.\n",
            encoding="utf-8",
        )
    return archived


def _extract_pytest_counts(log_path: Path) -> tuple[int | None, int | None]:
    if not log_path.exists():
        return (None, None)
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"(\d+) passed(?:,\s*(\d+) skipped)?", text)
    if not match:
        return (None, None)
    passed = int(match.group(1))
    skipped = int(match.group(2)) if match.group(2) else 0
    return (passed, skipped)


def _extract_vitest_tests_passed(log_path: Path) -> int | None:
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Tests\s+(\d+)\s+passed", text)
    if not match:
        return None
    return int(match.group(1))


def _extract_migration_count(log_path: Path) -> int | None:
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    patterns = [
        r"Alembic migration files:\s*(\d+)",
        r"Total migrations:\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _extract_backend_import_route_count(log_path: Path) -> int | None:
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"app has\s+(\d+)\s+routes", text)
    if not match:
        return None
    return int(match.group(1))


def _check_status_map(payload: dict) -> dict[str, dict]:
    return {check["name"]: check for check in payload.get("checks", [])}


def _write_json(repo_root: Path, path: Path, data: dict) -> str:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(repo_root))


def _read_source_registry_summary(out_dir: Path) -> dict:
    status_path = out_dir / "source_registry_status.json"
    if not status_path.exists():
        return {}
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _proof_db_counts(out_dir: Path) -> dict[str, int]:
    proof_db = out_dir / "proof.db"
    if not proof_db.exists():
        return {}

    counts: dict[str, int] = {}
    with sqlite3.connect(proof_db) as conn:
        cursor = conn.cursor()
        for table_name in ("audit_logs", "source_snapshots", "source_registry"):
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            except sqlite3.Error:
                continue
            row = cursor.fetchone()
            counts[table_name] = int(row[0]) if row else 0
    return counts


def _write_grouped_proof_artifacts(repo_root: Path, out_dir: Path, payload: dict) -> dict[str, str]:
    checks = _check_status_map(payload)
    backend_group = {
        "group": "backend_proof",
        "status": "PASS",
        "checks": [],
        "route_count": payload.get("backend_import_route_count"),
        "pytest_passed": payload.get("backend_pytest_passed"),
        "pytest_skipped": payload.get("backend_pytest_skipped"),
        "proof_db_counts": _proof_db_counts(out_dir),
    }
    backend_names = [
        "backend_compile",
        "backend_import",
        "backend_pytest",
        "check_migrations",
        "prepare_proof_db",
        "verify_evidence_store",
        "verify_audit_chain",
        "auth_mutation_route_coverage",
        "mutation_fail_closed_coverage",
        "validate_sources",
    ]
    for name in backend_names:
        check = checks.get(name)
        if not check:
            continue
        backend_group["checks"].append(
            {
                "name": name,
                "status": check["status"],
                "log": check["log_path"],
                "exit_code": check["exit_code"],
            }
        )
        if check["exit_code"] != 0:
            backend_group["status"] = "FAIL"

    frontend_group = {
        "group": "frontend_proof",
        "status": "PASS",
        "checks": [],
    }
    frontend_names = [
        "frontend_install",
        "frontend_lint",
        "frontend_typecheck",
        "frontend_contracts",
        "frontend_build",
        "check_api_contracts",
        "map_route_check",
        "public_api_boundary",
    ]
    for name in frontend_names:
        check = checks.get(name)
        if not check:
            continue
        frontend_group["checks"].append(
            {
                "name": name,
                "status": check["status"],
                "log": check["log_path"],
                "exit_code": check["exit_code"],
            }
        )
        if check["exit_code"] != 0:
            frontend_group["status"] = "FAIL"

    source_registry_summary = _read_source_registry_summary(out_dir)
    artifacts = {
        "backend_proof_summary": _write_json(
            repo_root,
            out_dir / "backend_proof_summary.json",
            backend_group,
        ),
        "frontend_proof_summary": _write_json(
            repo_root,
            out_dir / "frontend_proof_summary.json",
            frontend_group,
        ),
    }

    lines = [
        "# RELEASE_READINESS",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        f"- alpha_gate_passed: {str(payload.get('alpha_gate_passed', False)).lower()}",
        f"- proof_freshness_result: {payload.get('proof_freshness_result', 'UNKNOWN')}",
        f"- archive_validation_result: {payload.get('archive_validation_result', 'UNKNOWN')}",
        "",
        "## Backend Proof",
        "",
        f"- grouped_status: {backend_group['status']}",
        f"- backend_import_routes: {payload.get('backend_import_route_count', 'unknown')}",
        f"- backend_pytest: {payload.get('backend_pytest_passed', 'unknown')} passed, {payload.get('backend_pytest_skipped', 'unknown')} skipped",
        f"- proof_db_audit_logs: {backend_group['proof_db_counts'].get('audit_logs', 0)}",
        f"- proof_db_source_snapshots: {backend_group['proof_db_counts'].get('source_snapshots', 0)}",
        f"- summary_json: {artifacts['backend_proof_summary']}",
        "",
        "## Frontend Proof",
        "",
        f"- grouped_status: {frontend_group['status']}",
        f"- frontend_build_log: {payload.get('logs', {}).get('frontend_build', 'unknown')}",
        f"- frontend_contracts_passed: {payload.get('frontend_contracts_passed', 'unknown')}",
        f"- summary_json: {artifacts['frontend_proof_summary']}",
        "",
        "## Source Registry",
        "",
        "- source_registry_status_json: artifacts/proof/current/source_registry_status.json",
        f"- total_sources: {source_registry_summary.get('summary', {}).get('total_sources', 'unknown')}",
        f"- machine_ingest_sources: {source_registry_summary.get('summary', {}).get('machine_ingest_sources', 'unknown')}",
        f"- runnable_when_active_sources: {source_registry_summary.get('summary', {}).get('runnable_when_active_sources', 'unknown')}",
        f"- sources_requiring_secrets: {source_registry_summary.get('summary', {}).get('sources_requiring_secrets', 'unknown')}",
        "",
        "## Release Blockers",
        "",
    ]
    blockers = payload.get("release_blockers_remaining", [])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.append("")
    readiness_path = out_dir / "release_readiness.md"
    readiness_path.write_text("\n".join(lines), encoding="utf-8")
    artifacts["release_readiness"] = str(readiness_path.relative_to(repo_root))
    artifacts["source_registry_status"] = str(
        (out_dir / "source_registry_status.json").relative_to(repo_root)
    )
    return artifacts


def _write_current_alpha_status_md(repo_root: Path, out_dir: Path, payload: dict) -> str:
    blockers = payload.get("release_blockers_remaining", [])
    lines = [
        "# CURRENT_ALPHA_STATUS",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        "- operational_posture: alpha",
        "- production_ready: false",
        f"- alpha_gate_passed: {str(payload.get('alpha_gate_passed', False)).lower()}",
        f"- proof_freshness_result: {payload.get('proof_freshness_result', 'UNKNOWN')}",
        f"- release_gate_check_count: {payload.get('check_count', 0)}",
        f"- postgis_proof_result: {payload.get('postgis_proof_result', 'UNKNOWN')}",
        f"- egress_proxy_proof_result: {payload.get('egress_proxy_proof_result', 'UNKNOWN')}",
        f"- demo_proof_result: {payload.get('demo_proof_result', 'UNKNOWN')}",
        "",
        "## Status",
        "",
        "- This repository is in alpha proof-hardened posture.",
        "- This repository is not production-ready.",
        "- Human review remains mandatory for public publication decisions.",
        "",
        "## Current Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.append("")

    output_path = out_dir / "CURRENT_ALPHA_STATUS.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path.relative_to(repo_root))


def _write_source_registry_status_md(
    repo_root: Path,
    out_dir: Path,
    payload: dict,
    source_registry_summary: dict,
) -> str:
    summary = source_registry_summary.get("summary", {})
    sources = source_registry_summary.get("sources", [])
    class_counts = source_registry_summary.get("counts_by_source_class", {})
    blocked_sources = [
        source
        for source in sources
        if source.get("is_machine_ingest") and not source.get("can_enable")
    ]

    lines = [
        "# SOURCE_REGISTRY_STATUS",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        f"- total_sources: {summary.get('total_sources', 'unknown')}",
        f"- machine_ingest_sources: {summary.get('machine_ingest_sources', 'unknown')}",
        f"- runnable_when_active_sources: {summary.get('runnable_when_active_sources', 'unknown')}",
        f"- enableable_sources: {summary.get('enableable_sources', 'unknown')}",
        f"- sources_requiring_secrets: {summary.get('sources_requiring_secrets', 'unknown')}",
        "",
        "## Counts By Source Class",
        "",
    ]
    if class_counts:
        for source_class, count in sorted(class_counts.items()):
            lines.append(f"- {source_class}: {count}")
    else:
        lines.append("- unknown")

    lines.extend([
        "",
        "## Machine-Ingest Blockers",
        "",
    ])
    if blocked_sources:
        for source in sorted(blocked_sources, key=lambda item: str(item.get("source_key", ""))):
            lines.append(
                "- "
                f"{source.get('source_key', 'unknown')}: "
                f"{source.get('cannot_enable_reason', 'unknown')}"
            )
    else:
        lines.append("- none")

    lines.extend([
        "",
        "## Canonical Artifact",
        "",
        "- artifacts/proof/current/source_registry_status.json",
        "",
    ])

    output_path = out_dir / "SOURCE_REGISTRY_STATUS.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path.relative_to(repo_root))


def _write_proof_policy_md(repo_root: Path, out_dir: Path, payload: dict) -> str:
    lines = [
        "# PROOF_POLICY",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        "",
        "## Canonical Current Artifacts",
        "",
        "- Canonical proof output location is artifacts/proof/current/.",
        "- release_gate.json is the machine-readable source of truth for gate state.",
        "- CURRENT_PROOF.md and release_readiness.md are derived summaries from release_gate.json.",
        "- CURRENT_ALPHA_STATUS.md and SOURCE_REGISTRY_STATUS.md are generated per run from the same gate payload.",
        "",
        "## History And Retention",
        "",
        "- Historical sidecars are archived to artifacts/proof/history/.",
        "- artifacts/proof/current/ represents only the latest authoritative run.",
        "",
        "## Truth Boundaries",
        "",
        "- Release recommendation is blocked on any required failed or missing check.",
        "- Operational posture remains alpha; production readiness is false.",
        "- Evidence snapshots are authoritative; memory is derivative and non-authoritative.",
        "",
    ]

    output_path = out_dir / "PROOF_POLICY.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path.relative_to(repo_root))


def _write_repair_report_md(
    repo_root: Path,
    out_dir: Path,
    payload: dict,
    source_registry_summary: dict,
) -> str:
    checks = _check_status_map(payload)

    def phase_status(passed: bool) -> str:
        return "PASS" if passed else "FAIL"

    phases = [
        (
            "1. Alpha Gate Truthfulness",
            phase_status(bool(payload.get("alpha_gate_passed"))),
            "artifacts/proof/current/release_gate.json",
        ),
        (
            "2. Canonical Proof Artifacts",
            phase_status((out_dir / "release_gate.json").exists() and (out_dir / "CURRENT_PROOF.md").exists()),
            "artifacts/proof/current/CURRENT_PROOF.md",
        ),
        (
            "3. Generated Alpha Status",
            phase_status((out_dir / "CURRENT_ALPHA_STATUS.md").exists()),
            "artifacts/proof/current/CURRENT_ALPHA_STATUS.md",
        ),
        (
            "4. Source Registry Governance",
            phase_status(bool(source_registry_summary.get("summary"))),
            "artifacts/proof/current/source_registry_status.json",
        ),
        (
            "5. Generated Source Registry Status",
            phase_status((out_dir / "SOURCE_REGISTRY_STATUS.md").exists()),
            "artifacts/proof/current/SOURCE_REGISTRY_STATUS.md",
        ),
        (
            "6. Proof Policy Generated",
            phase_status((out_dir / "PROOF_POLICY.md").exists()),
            "artifacts/proof/current/PROOF_POLICY.md",
        ),
        (
            "7. Evidence Store Integrity",
            phase_status(checks.get("verify_evidence_store", {}).get("status") == "PASS"),
            "artifacts/proof/current/verify_evidence_store.log",
        ),
        (
            "8. Audit Chain Integrity",
            phase_status(checks.get("verify_audit_chain", {}).get("status") == "PASS"),
            "artifacts/proof/current/verify_audit_chain.log",
        ),
        (
            "9. Justice XML Proof Coverage",
            phase_status(checks.get("backend_pytest", {}).get("status") == "PASS"),
            "artifacts/proof/current/backend_pytest.log",
        ),
        (
            "10. Public Review Gate Coverage",
            phase_status(checks.get("public_api_boundary", {}).get("status") == "PASS"),
            "artifacts/proof/current/public_api_boundary.log",
        ),
        (
            "11. Derivative Memory Boundary Coverage",
            phase_status(checks.get("public_api_boundary", {}).get("status") == "PASS"),
            "artifacts/proof/current/public_api_boundary.log",
        ),
        (
            "12. Frontend Node 20 Gate",
            phase_status(checks.get("frontend_build", {}).get("status") == "PASS"),
            "artifacts/proof/current/frontend_build.log",
        ),
        (
            "13. CI/Local Gate Parity Baseline",
            phase_status((out_dir / "release_readiness.md").exists()),
            "artifacts/proof/current/release_readiness.md",
        ),
        (
            "14. Repair Report Generated",
            phase_status((out_dir / "REPAIR_REPORT.md").exists()),
            "artifacts/proof/current/REPAIR_REPORT.md",
        ),
    ]

    lines = [
        "# REPAIR_REPORT",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        f"- alpha_gate_passed: {str(payload.get('alpha_gate_passed', False)).lower()}",
        "",
        "## Phase Results",
        "",
    ]
    for phase_name, status, evidence in phases:
        lines.append(f"- {phase_name}: {status} ({evidence})")

    lines.extend([
        "",
        "## Remaining Blockers",
        "",
    ])
    blockers = payload.get("release_blockers_remaining", [])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.append("")

    output_path = out_dir / "REPAIR_REPORT.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path.relative_to(repo_root))


def _count_alembic_version_files(repo_root: Path) -> int:
    versions_dir = repo_root / "backend" / "alembic" / "versions"
    if not versions_dir.exists():
        return 0
    return len([p for p in versions_dir.glob("*.py") if p.is_file()])


def _archive_validation_result(out_dir: Path) -> str:
    log_path = out_dir / "archive_validation.log"
    if not log_path.exists():
        return "NOT_RUN"

    text = log_path.read_text(encoding="utf-8", errors="ignore")
    if "[archive_validation] PASS: extracted archive checks completed" in text:
        return "PASS"
    return "FAIL"


def _collect_proof_input_metadata(repo_root: Path, python_exe: str) -> dict:
    cmd = [
        python_exe,
        "scripts/check_proof_freshness.py",
        "--root",
        str(repo_root),
        "--metadata-only",
    ]
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "proof_input_tree_hash": "unknown",
            "proof_input_tree_hash_algorithm": "sha256",
            "proof_input_paths": PROOF_INPUT_PATTERNS,
            "proof_input_file_count": 0,
            "proof_input_file_list": [],
        }
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = {}
    return {
        "proof_input_tree_hash": parsed.get("proof_input_tree_hash", "unknown"),
        "proof_input_tree_hash_algorithm": parsed.get(
            "proof_input_tree_hash_algorithm", "sha256"
        ),
        "proof_input_paths": parsed.get("proof_input_paths", PROOF_INPUT_PATTERNS),
        "proof_input_file_count": parsed.get("proof_input_file_count", 0),
        "proof_input_file_list": parsed.get("proof_input_file_list", []),
    }


def _write_current_proof_md(
    repo_root: Path,
    out_dir: Path,
    payload: dict,
    check_count: int,
) -> str:
    status = "PASS" if payload["alpha_gate_passed"] else "BLOCKED"
    failed_checks = payload.get("failed_checks", [])
    blocked_checks = payload.get("blocked_checks", {})
    lines = [
        "# CURRENT_PROOF",
        "",
        f"- generated_at_utc: {payload.get('timestamp_utc', 'unknown')}",
        f"- commit_hash: {payload.get('commit_hash', 'unknown')}",
        f"- alpha_gate_status: {status}",
        f"- alpha_gate_passed: {str(payload.get('alpha_gate_passed', False)).lower()}",
        f"- release_gate_check_count: {check_count}",
        f"- docker_available: {str(payload.get('docker_available', False)).lower()}",
        f"- postgis_proof_result: {payload.get('postgis_proof_result', 'UNKNOWN')}",
        (
            "- egress_proxy_proof_result: "
            f"{payload.get('egress_proxy_proof_result', 'UNKNOWN')}"
        ),
        (
            "- demo_proof_result: "
            f"{payload.get('demo_proof_result', 'UNKNOWN')}"
        ),
        (
            "- proof_freshness_result: "
            f"{payload.get('proof_freshness_result', 'UNKNOWN')}"
        ),
        (
            "- proof_input_tree_hash: "
            f"{payload.get('proof_input_tree_hash', 'unknown')}"
        ),
        (
            "- proof_input_file_count: "
            f"{payload.get('proof_input_file_count', 0)}"
        ),
        (
            "- egress_proxy_proof_log: "
            f"{payload.get('egress_proxy_proof_log', 'unknown')}"
        ),
        (
            "- demo_proof_log: "
            f"{payload.get('demo_proof_log', 'unknown')}"
        ),
        "",
        "## Runtime Metadata",
        "",
        f"- gate_runner_python_version: {payload.get('gate_runner_python_version', 'unknown')}",
        f"- gate_runner_python_executable: {payload.get('gate_runner_python_executable', 'unknown')}",
        f"- backend_test_python_version: {payload.get('backend_test_python_version', 'unknown')}",
        f"- backend_test_python_executable: {payload.get('backend_test_python_executable', 'unknown')}",
        f"- backend_required_python: {payload.get('backend_required_python', 'unknown')}",
        f"- node_version: {payload.get('node_version', 'unknown')}",
        f"- npm_version: {payload.get('npm_version', 'unknown')}",
        f"- platform: {payload.get('platform', 'unknown')}",
        f"- test_database_backend: {payload.get('test_database_backend', 'unknown')}",
        f"- test_database_url_type: {payload.get('test_database_url_type', 'unknown')}",
        "",
        "## Scope and Safety",
        "",
        "- Current status: proof-hardened alpha.",
        "- Not ready for production deployment.",
        "- Does not hold legal authority.",
        "- Evidence snapshots are authoritative; memory is derivative.",
        "- AI is reviewer assistance only.",
        "- Source ingestion is disabled by default unless explicitly enabled.",
        "- External folders are reference-only.",
        "- JWT mutation authority is current; legacy shared-token compatibility is deprecated.",
        "- make verify = local no-Docker quality checks.",
        "- make release-proof-local = Docker/PostGIS alpha release gate.",
        "- Current alpha release is blocked if Docker/PostGIS proof fails.",
        (
            "- Docker/PostGIS proof "
            + (
                "passed in the current release gate."
                if payload.get("postgis_proof_result") == "PASS"
                else "did not pass in the current release gate."
            )
        ),
        (
            "- Dedicated egress proxy proof "
            + (
                "passed in the current release gate."
                if payload.get("egress_proxy_proof_result") == "PASS"
                else "did not pass in the current release gate."
            )
        ),
        (
            "- Dedicated synthetic demo proof "
            + (
                "passed in the current release gate."
                if payload.get("demo_proof_result") == "PASS"
                else "did not pass in the current release gate."
            )
        ),
        (
            "- Proof freshness passed against the stored proof-input file list and tree hash."
            if payload.get("proof_freshness_result") == "PASS"
            else "- Proof freshness did not pass against the stored proof-input file list and tree hash."
        ),
        (
            "- Archive validation passed against the final distributable archive shape."
            if payload.get("archive_validation_result") == "PASS"
            else "- Archive validation has not yet been recorded for this run."
        ),
        (
            "- archive_validation_log: "
            f"{payload.get('archive_validation_log', 'unknown')}"
        ),
        "- archive_validation_supported_shapes:",
        "  - JUDGE-main/",
        "  - */JUDGE-main/",
        "",
    ]

    lines.extend(
        [
            "## Governance Status",
            "",
            (
                "- legacy_shared_token_status: "
                f"{payload.get('legacy_shared_token_status', 'unknown')}"
            ),
            (
                "- dependency_security_status: "
                f"{payload.get('dependency_security_status', 'unknown')}"
            ),
            "",
        ]
    )

    backend_passed = payload.get("backend_pytest_passed")
    backend_skipped = payload.get("backend_pytest_skipped")
    frontend_contracts_passed = payload.get("frontend_contracts_passed")
    public_api_boundary_passed = payload.get("public_api_boundary_passed")
    backend_import_route_count = payload.get("backend_import_route_count")
    alembic_migrations = payload.get("alembic_migration_count")
    if (
        backend_passed is not None
        or backend_import_route_count is not None
        or frontend_contracts_passed is not None
        or public_api_boundary_passed is not None
        or alembic_migrations is not None
    ):
        lines.extend(["## Current Proof Facts", ""])
        if backend_passed is not None:
            lines.append(
                "- backend pytest: "
                f"{backend_passed} passed, {backend_skipped or 0} skipped"
            )
        if backend_import_route_count is not None:
            lines.append(f"- backend import proof: PASS ({backend_import_route_count} routes)")
        if frontend_contracts_passed is not None:
            lines.append(f"- frontend contracts: {frontend_contracts_passed} passed")
        if public_api_boundary_passed is not None:
            lines.append(f"- public API boundary: {public_api_boundary_passed} passed")
        lines.append(
            f"- Docker runtime preflight: {payload.get('docker_runtime_preflight_result', 'UNKNOWN')}"
        )
        lines.append(
            f"- PostGIS proof: {payload.get('postgis_proof_result', 'UNKNOWN')}"
        )
        lines.append(
            "- egress proxy proof: "
            f"{payload.get('egress_proxy_proof_result', 'UNKNOWN')}"
        )
        lines.append(
            "- demo proof: "
            f"{payload.get('demo_proof_result', 'UNKNOWN')}"
        )
        lines.append(
            "- mutation fail-closed coverage: "
            f"{payload.get('mutation_fail_closed_coverage_result', 'UNKNOWN')}"
        )
        if alembic_migrations is not None:
            lines.append(f"- Alembic migrations: {alembic_migrations}")
        lines.append("")

    if failed_checks:
        lines.extend(
            [
                "## Failed Checks",
                "",
                *[f"- {name}" for name in failed_checks],
                "",
            ]
        )
    if blocked_checks:
        lines.append("## Blocked Checks")
        lines.append("")
        for name, reason in blocked_checks.items():
            lines.append(f"- {name}: {reason}")
        lines.append("")

    lines.extend(
        [
            "## Egress Proxy Coverage",
            "",
            "- Dedicated gate artifact: artifacts/proof/current/egress_proxy_proof.log.",
            "- Production startup proxy policy coverage: backend/app/tests/test_production_fetch_egress_policy.py.",
            "- Runtime proxy opener/wiring coverage: backend/app/tests/test_source_fetcher_proxy.py.",
            "- SSRF defense context coverage remains in backend/app/tests/test_source_fetcher_ssrf.py.",
            "",
            "## Canonical Artifacts",
            "",
            "- artifacts/proof/current/release_gate.json",
            "- artifacts/proof/current/release_gate.log",
            "- artifacts/proof/current/docker_runtime_preflight.log",
            "- artifacts/proof/current/postgis_proof.log",
            "- artifacts/proof/current/egress_proxy_proof.log",
            "- artifacts/proof/current/demo_proof.log",
            "- artifacts/proof/current/proof_freshness.log",
            "- artifacts/proof/current/backend_import.log",
            "- artifacts/proof/current/backend_pytest.log",
            "- artifacts/proof/current/backend_proof_summary.json",
            "- artifacts/proof/current/frontend_proof_summary.json",
            "- artifacts/proof/current/frontend_contracts.log",
            "- artifacts/proof/current/frontend_build.log",
            "- artifacts/proof/current/check_api_contracts.log",
            "- artifacts/proof/current/map_route_check.log",
            "- artifacts/proof/current/public_api_boundary.log",
            "- artifacts/proof/current/mutation_fail_closed_coverage.log",
            "- artifacts/proof/current/source_registry_status.json",
            "- artifacts/proof/current/release_readiness.md",
            "- artifacts/proof/current/CURRENT_ALPHA_STATUS.md",
            "- artifacts/proof/current/SOURCE_REGISTRY_STATUS.md",
            "- artifacts/proof/current/PROOF_POLICY.md",
            "- artifacts/proof/current/REPAIR_REPORT.md",
            "",
        ]
    )

    current_proof_path = out_dir / "CURRENT_PROOF.md"
    current_proof_path.write_text("\n".join(lines), encoding="utf-8")
    return str(current_proof_path.relative_to(repo_root))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "artifacts" / "proof" / "current"
    out_dir.mkdir(parents=True, exist_ok=True)
    proof_db_url = f"sqlite:///{(out_dir / 'proof.db').resolve()}"

    backend_venv_python = repo_root / "backend" / ".venv" / "bin" / "python"
    if backend_venv_python.exists():
        python_exe = str(backend_venv_python)
    else:
        python_exe = sys.executable
    backend_python_version = (
        subprocess.run(
            [python_exe, "-c", "import sys; print(sys.version.split()[0])"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        or "unknown"
    )
    db_backend = "sqlite" if proof_db_url.startswith("sqlite://") else "unknown"
    docker_check_timeout_seconds = int(os.getenv("JTA_DOCKER_CHECK_TIMEOUT", "60"))
    postgis_timeout_seconds = int(os.getenv("JTA_POSTGIS_PROOF_TIMEOUT", "900"))
    proof_input_metadata = _collect_proof_input_metadata(repo_root, python_exe)
    gate_steps: list[GateStepSpec] = [
        GateStepSpec(
            "check_no_pyc",
            "check_no_pyc.log",
            ["bash", "scripts/check_no_pyc.sh"],
        ),
        GateStepSpec(
            "check_false_claims",
            "check_false_claims.log",
            [python_exe, "scripts/check_false_claims.py"],
        ),
        GateStepSpec(
            "check_external_boundaries",
            "check_external_boundaries.log",
            [python_exe, "scripts/check_external_boundaries.py"],
        ),
        GateStepSpec(
            "backend_compile",
            "backend_compile.log",
            [
                python_exe,
                "-m",
                "compileall",
                "-q",
                "backend/app",
                "backend/tools",
            ],
        ),
        GateStepSpec(
            "backend_import",
            "backend_import.log",
            [python_exe, "backend/scripts/proof_backend_import.py"],
        ),
        GateStepSpec(
            "backend_pytest",
            "backend_pytest.log",
            [
                "bash",
                "-lc",
                (
                    f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} '
                    "-m pytest backend/app/tests -x --tb=short -q"
                ),
            ],
            timeout_seconds=900,
        ),
        GateStepSpec(
            "check_migrations",
            "check_migrations.log",
            [python_exe, "backend/tools/check_migrations.py"],
        ),
        GateStepSpec(
            "docker_runtime_preflight",
            "docker_runtime_preflight.log",
            ["bash", "scripts/check_docker_runtime.sh"],
            timeout_seconds=120,
        ),
        GateStepSpec(
            "postgis_proof",
            "postgis_proof.log",
            [
                "bash",
                "-lc",
                (
                    "bash scripts/proof_postgis.sh && cp "
                    "artifacts/proof/postgis_proof.log "
                    "artifacts/proof/current/postgis_proof.log"
                ),
            ],
            timeout_seconds=postgis_timeout_seconds,
        ),
        GateStepSpec(
            "egress_proxy_proof",
            "egress_proxy_proof.log",
            ["bash", "scripts/proof_egress_proxy.sh"],
            timeout_seconds=300,
        ),
        GateStepSpec(
            "demo_proof",
            "demo_proof.log",
            ["bash", "scripts/proof_demo.sh"],
            timeout_seconds=300,
        ),
        GateStepSpec(
            "validate_sources",
            "validate_sources.log",
            [python_exe, "backend/tools/validate_sources.py"],
        ),
        GateStepSpec(
            "source_registry_status",
            "source_registry_status.log",
            [
                python_exe,
                "scripts/export_source_registry_status.py",
                "--output",
                str(out_dir / "source_registry_status.json"),
            ],
        ),
        GateStepSpec(
            "prepare_proof_db",
            "prepare_proof_db.log",
            [
                python_exe,
                "scripts/prepare_proof_db.py",
                "--proof-db",
                str(out_dir / "proof.db"),
            ],
        ),
        GateStepSpec(
            "verify_evidence_store",
            "verify_evidence_store.log",
            [
                "bash",
                "-lc",
                (
                    f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} '
                    "backend/tools/verify_evidence_store.py"
                ),
            ],
        ),
        GateStepSpec(
            "verify_audit_chain",
            "verify_audit_chain.log",
            [
                "bash",
                "-lc",
                (
                    f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} '
                    "backend/tools/verify_audit_chain.py"
                ),
            ],
        ),
        GateStepSpec(
            "auth_mutation_route_coverage",
            "auth_mutation_route_coverage.log",
            [
                python_exe,
                "-m",
                "pytest",
                "backend/app/tests/test_mutation_route_authority_coverage.py",
                "-q",
            ],
        ),
        GateStepSpec(
            "mutation_fail_closed_coverage",
            "mutation_fail_closed_coverage.log",
            [
                python_exe,
                "-m",
                "pytest",
                "backend/app/tests/test_mutation_fail_closed_coverage.py",
                "-q",
            ],
        ),
        GateStepSpec(
            "frontend_install",
            "frontend_install.log",
            ["npm", "ci", "--prefix", str(repo_root / "frontend")],
            timeout_seconds=900,
        ),
        GateStepSpec(
            "frontend_lint",
            "frontend_lint.log",
            ["npm", "run", "lint", "--prefix", str(repo_root / "frontend")],
        ),
        GateStepSpec(
            "frontend_typecheck",
            "frontend_typecheck.log",
            [
                "npm",
                "run",
                "typecheck",
                "--prefix",
                str(repo_root / "frontend"),
            ],
        ),
        GateStepSpec(
            "frontend_contracts",
            "frontend_contracts.log",
            [
                "npm",
                "run",
                "test:contracts",
                "--prefix",
                str(repo_root / "frontend"),
            ],
        ),
        GateStepSpec(
            "frontend_build",
            "frontend_build.log",
            ["npm", "run", "build", "--prefix", str(repo_root / "frontend")],
            timeout_seconds=900,
        ),
        GateStepSpec(
            "check_api_contracts",
            "check_api_contracts.log",
            [python_exe, "scripts/check_api_contracts.py"],
        ),
        GateStepSpec(
            "repo_generated_files",
            "repo_generated_files.log",
            [
                python_exe,
                "scripts/check_no_generated_files.py",
                "--root",
                str(repo_root),
            ],
        ),
        GateStepSpec(
            "check_npm_audit_triage",
            "check_npm_audit_triage.log",
            [python_exe, "scripts/check_npm_audit_triage.py"],
        ),
        GateStepSpec(
            "map_route_check",
            "map_route_check.log",
            [python_exe, "scripts/check_map_route.py"],
        ),
        GateStepSpec(
            "public_api_boundary",
            "public_api_boundary.log",
            [
                python_exe,
                "-m",
                "pytest",
                "backend/app/tests",
                "-k",
                "public_api",
                "-q",
            ],
        ),
    ]

    # proof_freshness runs as a post-write step after the preliminary
    # release_gate.json is written, so the stored manifest is final before
    # validation. Not in gate_steps; handled explicitly below.
    _proof_freshness_spec = GateStepSpec(
        "proof_freshness",
        "proof_freshness.log",
        [python_exe, "scripts/check_proof_freshness.py"],
    )

    archived_sidecars = _archive_legacy_sidecars(repo_root, out_dir)

    # Clear stale gate artifacts before execution so each run is
    # self-contained.
    stale_outputs = [spec.log_name for spec in gate_steps] + [
        _proof_freshness_spec.log_name,
        "release_gate.log",
        "release_gate.json",
        "CURRENT_PROOF.md",
    ]
    for output_name in stale_outputs:
        output_path = out_dir / output_name
        if output_path.exists():
            output_path.unlink()

    results: list[GateStep] = []
    blocked_checks: dict[str, str] = {}
    docker_preflight_failed = False
    for spec in gate_steps:
        command = list(spec.command)
        if spec.name == "postgis_proof" and docker_preflight_failed:
            blocked_log = out_dir / spec.log_name
            blocked_log.write_text(
                "[release_gate] BLOCKED: postgis_proof skipped because "
                "docker_runtime_preflight failed.\n",
                encoding="utf-8",
            )
            blocked_checks["postgis_proof"] = "docker_runtime_preflight failed"
            results.append(
                GateStep(
                    name=spec.name,
                    command="SKIPPED due to failed dependency",
                    status="BLOCKED",
                    exit_code=1,
                    duration_seconds=0.0,
                    log_path=str(blocked_log.relative_to(repo_root)),
                )
            )
            continue

        results.append(
            _run(
                repo_root,
                out_dir,
                spec.name,
                spec.log_name,
                command,
                timeout_seconds=spec.timeout_seconds,
            )
        )
        if spec.name == "docker_runtime_preflight" and results[-1].exit_code != 0:
            docker_preflight_failed = True

    # -----------------------------------------------------------------------
    # Phase 1: collect final proof metadata and write preliminary JSON.
    # proof_freshness runs AFTER this write so check_proof_freshness.py can
    # read the stored manifest. Nothing between here and the freshness step
    # modifies proof-input source files.
    # -----------------------------------------------------------------------
    missing_logs = _missing_logs(repo_root, results)
    proof_input_metadata = _collect_proof_input_metadata(repo_root, python_exe)

    gate_log_path = out_dir / "release_gate.log"
    with gate_log_path.open("w", encoding="utf-8") as gate_log:
        gate_log.write("RELEASE GATE\n")
        for result in results:
            gate_log.write(
                f"{result.name}: {result.status} rc={result.exit_code} "
                f"dur={result.duration_seconds}s log={result.log_path}\n"
            )
        if missing_logs:
            gate_log.write("missing_logs:\n")
            for log in missing_logs:
                gate_log.write(f"- {log}\n")

    checks_map = {r.name: r for r in results}
    backend_pytest_passed, backend_pytest_skipped = _extract_pytest_counts(
        out_dir / "backend_pytest.log"
    )
    frontend_contracts_passed = _extract_vitest_tests_passed(
        out_dir / "frontend_contracts.log"
    )
    public_api_boundary_passed, _public_api_boundary_skipped = _extract_pytest_counts(
        out_dir / "public_api_boundary.log"
    )
    backend_import_route_count = _extract_backend_import_route_count(
        out_dir / "backend_import.log"
    )
    alembic_migration_count = _extract_migration_count(out_dir / "check_migrations.log")
    if alembic_migration_count is None:
        alembic_migration_count = _count_alembic_version_files(repo_root)

    legacy_auth_plan_exists = (
        repo_root / "docs" / "LEGACY_AUTH_REMOVAL_PLAN.md"
    ).exists()
    dependency_plan_exists = (
        repo_root / "docs" / "DEPENDENCY_REMEDIATION_PLAN.md"
    ).exists()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "alpha_gate_passed": False,  # updated after proof_freshness step
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "commit_hash": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        ).stdout.strip()
        or "unknown",
        "python_version": sys.version.split()[0],
        "gate_runner_python_version": sys.version.split()[0],
        "gate_runner_python_executable": sys.executable,
        "backend_test_python_version": backend_python_version,
        "backend_test_python_executable": python_exe,
        "backend_required_python": ">=3.11",
        "node_version": subprocess.run(
            ["node", "--version"], capture_output=True, text=True
        ).stdout.strip()
        or "unknown",
        "npm_version": subprocess.run(
            ["npm", "--version"], capture_output=True, text=True
        ).stdout.strip()
        or "unknown",
        "test_database_backend": db_backend,
        "test_database_url_type": "sqlite_file",
        "platform": platform.platform(),
        "docker_available": not docker_preflight_failed,
        "docker_check_timeout_seconds": docker_check_timeout_seconds,
        "postgis_proof_required": True,
        "postgis_proof_timeout_seconds": postgis_timeout_seconds,
        "check_count": len(results),
        "proof_input_tree_hash": proof_input_metadata["proof_input_tree_hash"],
        "proof_input_tree_hash_algorithm": proof_input_metadata[
            "proof_input_tree_hash_algorithm"
        ],
        "proof_input_paths": proof_input_metadata["proof_input_paths"],
        "proof_input_file_count": proof_input_metadata["proof_input_file_count"],
        "proof_input_file_list": proof_input_metadata["proof_input_file_list"],
        "docker_runtime_preflight_result": checks_map.get(
            "docker_runtime_preflight", GateStep("", "", "UNKNOWN", 1, 0, "")
        ).status,
        "postgis_proof_result": next(
            (r.status for r in results if r.name == "postgis_proof"),
            "UNKNOWN",
        ),
        "egress_proxy_proof_result": next(
            (r.status for r in results if r.name == "egress_proxy_proof"),
            "UNKNOWN",
        ),
        "demo_proof_result": next(
            (r.status for r in results if r.name == "demo_proof"),
            "UNKNOWN",
        ),
        "egress_proxy_proof_log": str(
            (out_dir / "egress_proxy_proof.log").relative_to(repo_root)
        ),
        "demo_proof_log": str((out_dir / "demo_proof.log").relative_to(repo_root)),
        "archive_validation_log": str(
            (out_dir / "archive_validation.log").relative_to(repo_root)
        ),
        "archive_validation_supported_shapes": ["JUDGE-main/", "*/JUDGE-main/"],
        "mutation_fail_closed_coverage_result": checks_map.get(
            "mutation_fail_closed_coverage",
            GateStep("", "", "UNKNOWN", 1, 0, ""),
        ).status,
        "proof_freshness_result": "UNKNOWN",
        "archive_validation_result": _archive_validation_result(out_dir),
        "legacy_shared_token_status": (
            "deprecated, removal plan documented"
            if legacy_auth_plan_exists
            else "deprecated, removal plan missing"
        ),
        "dependency_security_status": (
            "npm audit issues triaged for alpha; remediation plan documented"
            if dependency_plan_exists
            else "npm audit issues triaged for alpha; remediation plan missing"
        ),
        "backend_pytest_passed": backend_pytest_passed,
        "backend_pytest_skipped": backend_pytest_skipped,
        "backend_import_route_count": backend_import_route_count,
        "frontend_contracts_passed": frontend_contracts_passed,
        "public_api_boundary_passed": public_api_boundary_passed,
        "alembic_migration_count": alembic_migration_count,
        "checks": [asdict(r) for r in results],
        "failed_checks": [r.name for r in results if r.exit_code != 0]
        + (["missing_logs"] if missing_logs else []),
        "blocked_checks": blocked_checks,
        "archived_legacy_sidecars": archived_sidecars,
        "logs": {r.name: r.log_path for r in results}
        | {
            _proof_freshness_spec.name: str(
                (out_dir / _proof_freshness_spec.log_name).relative_to(repo_root)
            ),
            "archive_validation": str(
                (out_dir / "archive_validation.log").relative_to(repo_root)
            ),
            "release_gate": str(gate_log_path.relative_to(repo_root)),
        },
        "known_limitations": [
            "alpha gate only; not a production release gate",
            (
                "AI outputs are reviewer assistance only — "
                "not determinations of guilt or legal conclusions"
            ),
            (
                "external HTTP fetch results are not guaranteed current; "
                "system operates on cached snapshots"
            ),
            (
                "no real-time alerting; proof artifacts must be "
                "regenerated manually after each code change"
            ),
        ],
        "release_blockers_remaining": [],  # updated after proof_freshness step
    }

    # -----------------------------------------------------------------------
    # Phase 2a: write preliminary release_gate.json with the final proof hash
    # so check_proof_freshness.py can validate the stored manifest against the
    # live tree. check_count includes the upcoming proof_freshness step (+1).
    # -----------------------------------------------------------------------
    payload["check_count"] = len(results) + 1
    out_path = out_dir / "release_gate.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Phase 2b: run proof_freshness against the now-written stored manifest.
    pf_step = _run(
        repo_root,
        out_dir,
        _proof_freshness_spec.name,
        _proof_freshness_spec.log_name,
        list(_proof_freshness_spec.command),
        timeout_seconds=120,
    )
    results.append(pf_step)

    # Phase 2c: update payload with the real proof_freshness result and recompute
    # ok, failed_checks, release_blockers_remaining, alpha_gate_passed.
    ok = all(r.exit_code == 0 for r in results) and not missing_logs
    payload["alpha_gate_passed"] = ok
    payload["check_count"] = len(results)
    payload["proof_freshness_result"] = pf_step.status
    payload["checks"] = [asdict(r) for r in results]
    payload["failed_checks"] = [r.name for r in results if r.exit_code != 0] + (
        ["missing_logs"] if missing_logs else []
    )
    payload["logs"][_proof_freshness_spec.name] = pf_step.log_path
    payload["release_blockers_remaining"] = (
        [r.name for r in results if r.exit_code != 0]
        + (["missing_logs"] if missing_logs else [])
        if not ok
        else []
    )

    # Phase 3: write final release_gate.json and CURRENT_PROOF.md.
    with gate_log_path.open("a", encoding="utf-8") as gate_log:
        gate_log.write(
            f"{pf_step.name}: {pf_step.status} rc={pf_step.exit_code} "
            f"dur={pf_step.duration_seconds}s log={pf_step.log_path}\n"
        )
        gate_log.write(f"alpha_gate_passed={str(ok).lower()}\n")

    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    current_proof_rel = _write_current_proof_md(
        repo_root,
        out_dir,
        payload,
        check_count=len(results),
    )
    grouped_artifacts = _write_grouped_proof_artifacts(repo_root, out_dir, payload)
    source_registry_summary = _read_source_registry_summary(out_dir)
    current_alpha_status_rel = _write_current_alpha_status_md(repo_root, out_dir, payload)
    source_registry_status_md_rel = _write_source_registry_status_md(
        repo_root,
        out_dir,
        payload,
        source_registry_summary,
    )
    proof_policy_rel = _write_proof_policy_md(repo_root, out_dir, payload)
    repair_report_rel = _write_repair_report_md(
        repo_root,
        out_dir,
        payload,
        source_registry_summary,
    )
    payload["logs"]["current_proof"] = current_proof_rel
    payload["logs"] |= grouped_artifacts
    payload["logs"]["current_alpha_status"] = current_alpha_status_rel
    payload["logs"]["source_registry_status_md"] = source_registry_status_md_rel
    payload["logs"]["proof_policy"] = proof_policy_rel
    payload["logs"]["repair_report"] = repair_report_rel
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if ok:
        print(f"PASS: wrote {out_path.relative_to(repo_root)}")
        return 0

    print(f"BLOCKED: wrote {out_path.relative_to(repo_root)}")
    for result in results:
        if result.exit_code != 0:
            print(f"- {result.name} rc={result.exit_code} " f"log={result.log_path}")
    for missing in missing_logs:
        print(f"- missing_log={missing}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
