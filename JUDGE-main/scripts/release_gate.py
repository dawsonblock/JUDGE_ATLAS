#!/usr/bin/env python3
"""Unified alpha release gate for JUDGE_ATLAS.

This gate executes the required alpha checks, writes canonical logs under
``artifacts/proof/current``, and fails if any referenced log file is missing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from shutil import move


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
        "",
    ]

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
            "- Covered by backend tests for production proxy policy and runtime proxy opener wiring.",
            "",
            "## Canonical Artifacts",
            "",
            "- artifacts/proof/current/release_gate.json",
            "- artifacts/proof/current/release_gate.log",
            "- artifacts/proof/current/docker_runtime_preflight.log",
            "- artifacts/proof/current/postgis_proof.log",
            "- artifacts/proof/current/backend_pytest.log",
            "- artifacts/proof/current/frontend_contracts.log",
            "- artifacts/proof/current/check_api_contracts.log",
            "- artifacts/proof/current/map_route_check.log",
            "- artifacts/proof/current/public_api_boundary.log",
            "- artifacts/proof/current/mutation_fail_closed_coverage.log",
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
            "validate_sources",
            "validate_sources.log",
            [python_exe, "backend/tools/validate_sources.py"],
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

    archived_sidecars = _archive_legacy_sidecars(repo_root, out_dir)

    # Clear stale gate artifacts before execution so each run is
    # self-contained.
    stale_outputs = [spec.log_name for spec in gate_steps] + [
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
                spec.command,
                timeout_seconds=spec.timeout_seconds,
            )
        )
        if spec.name == "docker_runtime_preflight" and results[-1].exit_code != 0:
            docker_preflight_failed = True

    missing_logs = _missing_logs(repo_root, results)
    ok = all(r.exit_code == 0 for r in results) and not missing_logs

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
        gate_log.write(f"alpha_gate_passed={str(ok).lower()}\n")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "alpha_gate_passed": ok,
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
        "postgis_proof_result": next(
            (r.status for r in results if r.name == "postgis_proof"),
            "UNKNOWN",
        ),
        "checks": [asdict(r) for r in results],
        "failed_checks": [r.name for r in results if r.exit_code != 0]
        + (["missing_logs"] if missing_logs else []),
        "blocked_checks": blocked_checks,
        "archived_legacy_sidecars": archived_sidecars,
        "logs": {r.name: r.log_path for r in results}
        | {"release_gate": str(gate_log_path.relative_to(repo_root))},
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
        "release_blockers_remaining": (
            [r.name for r in results if r.exit_code != 0]
            + (["missing_logs"] if missing_logs else [])
            if not ok
            else []
        ),
    }

    out_path = out_dir / "release_gate.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    current_proof_rel = _write_current_proof_md(
        repo_root,
        out_dir,
        payload,
        check_count=len(results),
    )
    payload["logs"]["current_proof"] = current_proof_rel
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
