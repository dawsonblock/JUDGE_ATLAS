#!/usr/bin/env python3
"""Unified alpha release gate for JUDGE_ATLAS.

This gate executes core proof checks and writes canonical artifacts under
artifacts/proof/current. A non-zero exit code means release is blocked.
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
    command: list[str]
    returncode: int
    log_file: str
    duration_seconds: float
    status: str  # "pass" | "fail"
    exit_code: int  # alias of returncode for explicit schema compliance


def _run(
    repo_root: Path,
    out_dir: Path,
    name: str,
    command: list[str],
) -> GateStep:
    log_path = out_dir / f"release_gate_{name}.log"
    t0 = time.monotonic()
    with log_path.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            command,
            cwd=repo_root,
            stdout=fh,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    duration = round(time.monotonic() - t0, 3)
    passed = proc.returncode == 0
    return GateStep(
        name=name,
        command=command,
        returncode=proc.returncode,
        log_file=str(log_path.relative_to(repo_root)),
        duration_seconds=duration,
        status="pass" if passed else "fail",
        exit_code=proc.returncode,
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "artifacts" / "proof" / "current"
    out_dir.mkdir(parents=True, exist_ok=True)

    backend_venv_python = repo_root / "backend" / ".venv" / "bin" / "python"
    python_exe = str(backend_venv_python) if backend_venv_python.exists() else sys.executable
    gate_steps = [
        # 1 – prepare proof DB FIRST so audit_chain / evidence verifiers see data
        (
            "proof_db_prepare",
            [python_exe, "scripts/prepare_proof_db.py"],
        ),
        # 2 – fast Python byte-compilation check across all backend source
        (
            "backend_compile",
            [python_exe, "-m", "compileall", "-q", "backend/app"],
        ),
        # 3 – full backend pytest suite
        (
            "backend_pytest",
            [python_exe, "-m", "pytest", "backend/app/tests", "-x", "--tb=short", "-q"],
        ),
        # 4 – mutation routes must all declare authority
        (
            "auth_mutation_coverage",
            [
                python_exe, "-m", "pytest",
                "backend/app/tests/test_mutation_route_authority_coverage.py",
                "-v", "--tb=short",
            ],
        ),
        # 5 – existing proof_all orchestration
        (
            "proof_all",
            [python_exe, "scripts/proof_all.py"],
        ),
        # 6 – verify persisted audit chain integrity
        (
            "verify_audit_chain",
            [python_exe, "-m", "backend.tools.verify_audit_chain"],
        ),
        # 7 – verify evidence store integrity
        (
            "verify_evidence_store",
            [python_exe, "-m", "backend.tools.verify_evidence_store"],
        ),
        # 8 – validate source registry entries
        (
            "validate_sources",
            [python_exe, "scripts/check_source_keys.py"],
        ),
        # 9 – scan for false claims in docs and code
        (
            "check_false_claims",
            [python_exe, "scripts/check_false_claims.py"],
        ),
        # 10 – verify no external boundary violations
        (
            "check_external_boundaries",
            [python_exe, "scripts/check_external_boundaries.py"],
        ),
        # 11 – verify no .pyc files committed
        (
            "check_no_pyc",
            ["bash", "scripts/check_no_pyc.sh"],
        ),
        # 12 – verify alembic migration files are present
        (
            "check_migrations",
            [
                python_exe, "-c",
                (
                    "import sys; from pathlib import Path; "
                    "versions = [p for p in Path('backend/alembic/versions').glob('*.py') "
                    "if not p.name.startswith('_')]; "
                    "print(f'migration_files={len(versions)}'); "
                    "sys.exit(0 if versions else 1)"
                ),
            ],
        ),
        # 13 – verify /map route returns correct redirect / reviewed-only data
        (
            "map_route",
            [python_exe, "scripts/check_map_route.py"],
        ),
        # 14 – public API boundary enforcement tests
        (
            "public_api_boundary",
            [
                python_exe, "-m", "pytest",
                "backend/app/tests", "-k", "public_api",
                "--tb=short", "-q",
            ],
        ),
        # 15 – frontend dependencies
        (
            "frontend_install",
            ["npm", "ci", "--prefix", str(repo_root / "frontend")],
        ),
        # 16 – frontend production build
        (
            "frontend_build",
            ["npm", "run", "build", "--prefix", str(repo_root / "frontend")],
        ),
        # 17 – frontend lint
        (
            "frontend_lint",
            ["npm", "run", "lint", "--prefix", str(repo_root / "frontend")],
        ),
        # 18 – frontend type checking
        (
            "frontend_typecheck",
            ["npm", "run", "typecheck", "--prefix", str(repo_root / "frontend")],
        ),
        # 19 – API contract schema validation
        (
            "api_contracts",
            [python_exe, "scripts/check_api_contracts.py"],
        ),
        # 20 – NPM vulnerability triage
        (
            "npm_audit_triage",
            [python_exe, "scripts/check_npm_audit_triage.py"],
        ),
        # 21 – ensure no generated/build artefacts committed
        (
            "repo_generated_files",
            [
                python_exe,
                "scripts/check_no_generated_files.py",
                "--root",
                str(repo_root),
            ],
        ),
    ]

    results: list[GateStep] = []
    for name, command in gate_steps:
        results.append(_run(repo_root, out_dir, name, command))

    ok = all(r.returncode == 0 for r in results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alpha_gate_passed": ok,
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "python_version": sys.version.split()[0],
        "node_version": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() or "unknown",
        "npm_version": subprocess.run(["npm", "--version"], capture_output=True, text=True).stdout.strip() or "unknown",
        "platform": platform.platform(),
        "checks": [asdict(r) for r in results],
        "failed_checks": [r.name for r in results if r.returncode != 0],
        "logs": [r.log_file for r in results],
        "known_limitations": [
            "alpha gate only; not a production release gate",
            "AI outputs are reviewer assistance only — not determinations of guilt or legal conclusions",
            "external HTTP fetch results are not guaranteed current; system operates on cached snapshots",
            "no real-time alerting; proof artifacts must be regenerated manually after each code change",
        ],
        "release_blockers_remaining": (
            [r.name for r in results if r.returncode != 0]
            if not ok
            else [
                "proof artifacts must be manually regenerated after each merge",
                "frontend e2e coverage is not yet part of the release gate",
            ]
        ),
    }

    out_path = out_dir / "release_gate.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if ok:
        print(f"PASS: wrote {out_path.relative_to(repo_root)}")
        return 0

    print(f"BLOCKED: wrote {out_path.relative_to(repo_root)}")
    for result in results:
        if result.returncode != 0:
            print(
                f"- {result.name} rc={result.returncode} "
                f"log={result.log_file}"
            )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
