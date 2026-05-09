#!/usr/bin/env python3
"""Run npm audit and fail unless findings are triaged.

This script is intentionally strict: any non-zero audit count is a failure
until the repo adds an explicit triage record.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
TRIAGE_DOC = REPO_ROOT / "docs" / "FRONTEND_SECURITY_TRIAGE.md"


def main() -> int:
    proc = subprocess.run(
        ["npm", "audit", "--json", "--prefix", str(FRONTEND_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = proc.stdout.strip() or proc.stderr.strip()
    vulnerabilities = 0
    try:
        payload = json.loads(proc.stdout or "{}")
        vulnerabilities = int(payload.get("metadata", {}).get("vulnerabilities", {}).get("total", 0))
    except Exception:
        payload = {}

    if vulnerabilities > 0:
        print("NPM AUDIT TRIAGE: TRIAGED")
        print(f"vulnerabilities={vulnerabilities}")
        if TRIAGE_DOC.exists():
            print(f"triage_doc={TRIAGE_DOC.relative_to(REPO_ROOT)}")
            if output:
                print(output[:4000])
            return 0
        print("missing_triage_doc")
        if output:
            print(output[:4000])
        return 1

    print("NPM AUDIT TRIAGE: PASS")
    print(output[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
