#!/usr/bin/env python3
"""Run core proof checks.

Canonical outputs are written under artifacts/proof/current.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    log_file: str


def _run_step(
    repo_root: Path,
    out_dir: Path,
    name: str,
    command: list[str],
) -> StepResult:
    log_path = out_dir / f"{name}.log"
    with log_path.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            command,
            cwd=repo_root,
            stdout=fh,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    return StepResult(
        name=name,
        command=command,
        returncode=proc.returncode,
        log_file=str(log_path.relative_to(repo_root)),
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = repo_root / "artifacts" / "proof" / "current"
    out_dir.mkdir(parents=True, exist_ok=True)
    proof_db_url = f"sqlite:///{(out_dir / 'proof.db').resolve()}"

    python_exe = sys.executable
    steps = [
        ("check_no_pyc", ["bash", "scripts/check_no_pyc.sh"]),
        (
            "check_source_keys",
            [
                python_exe,
                "scripts/check_source_keys.py",
                "--root",
                "backend/app",
                "--repo-root",
                ".",
            ],
        ),
        (
            "check_statuses",
            [python_exe, "scripts/check_statuses.py", "--root", "backend/app"],
        ),
        ("check_false_claims", [python_exe, "scripts/check_false_claims.py"]),
        (
            "check_external_boundaries",
            [python_exe, "scripts/check_external_boundaries.py"],
        ),
        (
            "validate_sources",
            [python_exe, "backend/tools/validate_sources.py"],
        ),
        (
            "prepare_proof_db",
            [
                "bash",
                "-lc",
                f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} scripts/prepare_proof_db.py',
            ],
        ),
        (
            "verify_evidence_store",
            [
                "bash",
                "-lc",
                f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} backend/tools/verify_evidence_store.py',
            ],
        ),
        (
            "verify_audit_chain",
            [
                "bash",
                "-lc",
                f'JTA_DATABASE_URL="{proof_db_url}" {python_exe} backend/tools/verify_audit_chain.py',
            ],
        ),
        (
            "check_map_route",
            [python_exe, "scripts/check_map_route.py"],
        ),
        (
            "check_api_contracts",
            [python_exe, "scripts/check_api_contracts.py"],
        ),
        (
            "check_npm_audit_triage",
            [python_exe, "scripts/check_npm_audit_triage.py"],
        ),
        (
            "backend_compile",
            [
                python_exe,
                "-m",
                "compileall",
                "-q",
                "backend/app",
                "backend/tools",
            ],
        ),
        (
            "check_migrations",
            [python_exe, "backend/tools/check_migrations.py"],
        ),
        (
            "backend_pytest",
            [
                "uv",
                "run",
                "--directory",
                str(repo_root / "backend"),
                "pytest",
                "-q",
            ],
        ),
        (
            "frontend_lint",
            ["npm", "run", "lint", "--prefix", str(repo_root / "frontend")],
        ),
        (
            "frontend_typecheck",
            ["npm", "run", "typecheck", "--prefix", str(repo_root / "frontend")],
        ),
        (
            "frontend_build",
            ["npm", "run", "build", "--prefix", str(repo_root / "frontend")],
        ),
    ]

    results: list[StepResult] = []
    for step_name, command in steps:
        results.append(_run_step(repo_root, out_dir, step_name, command))

    summary_path = out_dir / "proof_all_summary.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "steps": [asdict(r) for r in results],
        "ok": all(r.returncode == 0 for r in results),
    }
    summary_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest_path = out_dir / "manifest.json"
    manifest_payload = {
        "generated_at": payload["generated_at"],
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "repo_name": "JUDGE_ATLAS",
        "python_version": sys.version.split()[0],
        "node_version": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() or "unknown",
        "npm_version": subprocess.run(["npm", "--version"], capture_output=True, text=True).stdout.strip() or "unknown",
        "platform": platform.platform(),
        "backend_test_command": "uv run --directory backend pytest -q",
        "frontend_build_command": "npm run build --prefix frontend",
        "migration_command": "python backend/tools/check_migrations.py",
        "source_validation_command": "python backend/tools/validate_sources.py",
        "evidence_verification_command": "python backend/tools/verify_evidence_store.py",
        "audit_verification_command": "python backend/tools/verify_audit_chain.py",
        "contract_validation_command": "python scripts/check_api_contracts.py",
        "release_gate_command": "python scripts/release_gate.py",
        "result": "pass" if payload["ok"] else "fail",
        "logs": [r.log_file for r in results],
        "known_failures": [],
        "known_limitations": ["alpha gate only; not a production release gate"],
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")

    env_path = out_dir / "environment_info.txt"
    env_lines = [
        f"OS={platform.platform()}",
        f"Python={sys.version.split()[0]}",
        f"pip={subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True, text=True).stdout.strip()}",
        f"Node={manifest_payload['node_version']}",
        f"npm={manifest_payload['npm_version']}",
        f"WorkingDirectory={repo_root}",
        f"JTA_APP_ENV={os.environ.get('JTA_APP_ENV', 'unset')}",
        f"JTA_DATABASE_URL={os.environ.get('JTA_DATABASE_URL', 'unset')}",
        f"JTA_JWT_AUTH_ENABLED={os.environ.get('JTA_JWT_AUTH_ENABLED', 'unset')}",
        f"JTA_ENABLE_LEGACY_ADMIN_TOKEN={os.environ.get('JTA_ENABLE_LEGACY_ADMIN_TOKEN', 'unset')}",
        f"JTA_ENFORCE_JWT_MUTATIONS={os.environ.get('JTA_ENFORCE_JWT_MUTATIONS', 'unset')}",
    ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    if payload["ok"]:
        print(f"PASS: wrote {summary_path.relative_to(repo_root)}")
        return 0

    print(f"FAIL: wrote {summary_path.relative_to(repo_root)}")
    for r in results:
        if r.returncode != 0:
            print(f"- {r.name} rc={r.returncode} log={r.log_file}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
