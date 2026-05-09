#!/usr/bin/env python3
"""Run core proof checks.

Canonical outputs are written under artifacts/proof/current.
"""

from __future__ import annotations

import json
import subprocess
import sys
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
