#!/usr/bin/env python3
"""Unified alpha release gate for JUDGE_ATLAS.

This gate executes core proof checks and writes canonical artifacts under
artifacts/proof/current. A non-zero exit code means release is blocked.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class GateStep:
    name: str
    command: list[str]
    returncode: int
    log_file: str


def _run(
    repo_root: Path,
    out_dir: Path,
    name: str,
    command: list[str],
) -> GateStep:
    log_path = out_dir / f"release_gate_{name}.log"
    with log_path.open("w", encoding="utf-8") as fh:
        proc = subprocess.run(
            command,
            cwd=repo_root,
            stdout=fh,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    return GateStep(
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
        "ok": ok,
        "steps": [asdict(r) for r in results],
        "policy": {
            "release_ready": False if not ok else True,
            "note": "Gate pass is required before any release-ready claim.",
        },
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
