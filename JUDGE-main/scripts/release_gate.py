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
    db_backend = (
        "sqlite" if proof_db_url.startswith("sqlite://") else "unknown"
    )
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
            timeout_seconds=900,
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

    # Clear stale gate artifacts before execution so each run is
    # self-contained.
    stale_outputs = [spec.log_name for spec in gate_steps] + [
        "release_gate.log",
        "release_gate.json",
    ]
    for output_name in stale_outputs:
        output_path = out_dir / output_name
        if output_path.exists():
            output_path.unlink()

    results: list[GateStep] = []
    for spec in gate_steps:
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
        "alpha_gate_passed": ok,
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "python_version": sys.version.split()[0],
        "gate_runner_python_version": sys.version.split()[0],
        "gate_runner_python_executable": sys.executable,
        "backend_test_python_version": backend_python_version,
        "backend_test_python_executable": python_exe,
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
        "checks": [asdict(r) for r in results],
        "failed_checks": [r.name for r in results if r.exit_code != 0]
        + (["missing_logs"] if missing_logs else []),
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

    if ok:
        print(f"PASS: wrote {out_path.relative_to(repo_root)}")
        return 0

    print(f"BLOCKED: wrote {out_path.relative_to(repo_root)}")
    for result in results:
        if result.exit_code != 0:
            print(
                f"- {result.name} rc={result.exit_code} "
                f"log={result.log_path}"
            )
    for missing in missing_logs:
        print(f"- missing_log={missing}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
