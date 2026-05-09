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

    python_exe = sys.executable
    gate_steps = [
        (
            "proof_all",
            [python_exe, "scripts/proof_all.py"],
        ),
        (
            "frontend_install",
            ["npm", "ci", "--prefix", str(repo_root / "frontend")],
        ),
        (
            "frontend_build",
            ["npm", "run", "build", "--prefix", str(repo_root / "frontend")],
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
            "api_contracts",
            [python_exe, "scripts/check_api_contracts.py"],
        ),
        (
            "npm_audit_triage",
            [python_exe, "scripts/check_npm_audit_triage.py"],
        ),
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
        "known_limitations": ["alpha gate only; not a production release gate"],
        "release_blockers_remaining": [] if ok else [r.name for r in results if r.returncode != 0],
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
