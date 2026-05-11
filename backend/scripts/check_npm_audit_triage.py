#!/usr/bin/env python3
"""Run npm audit and fail unless EVERY vulnerable package is covered in the triage doc.

Per-package triage matching: each package name reported by `npm audit` must
appear literally in FRONTEND_SECURITY_TRIAGE.md. A triage document that merely
exists is not sufficient — coverage must be explicit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
TRIAGE_DOC = REPO_ROOT / "docs" / "FRONTEND_SECURITY_TRIAGE.md"


def _triaged_packages(triage_text: str) -> set[str]:
    """Return the set of package names mentioned in the triage document.

    Looks for backtick-quoted package names, e.g. `glob` or `@next/eslint-plugin-next`.
    """
    import re
    return set(re.findall(r"`([^`]+)`", triage_text))


def _section_for_package(triage_text: str, package_name: str) -> str:
    pattern = re.compile(
        r"(^###\s+.*?`" + re.escape(package_name) + r"`.*?$)(.*?)(?=^###\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(triage_text)
    if not m:
        return ""
    return (m.group(1) + "\n" + m.group(2)).strip()


def _missing_required_fields(section_text: str) -> list[str]:
    required = {
        "severity": ["**Severity**", "severity"],
        "via_chain": ["via", "dependency chain", "transitive via"],
        "fix_availability": ["fix", "patch", "availability"],
        "dependency_scope": ["direct", "transitive"],
        "runtime_scope": ["runtime", "dev-only", "build-time", "production"],
        "owner": ["**Owner**", "owner"],
        "rationale": ["rationale", "decision", "accepted"],
        "target_fix": ["target", "date", "condition", "upstream"],
    }
    text = section_text.lower()
    missing: list[str] = []
    for key, tokens in required.items():
        if not any(token.lower() in text for token in tokens):
            missing.append(key)
    return missing


def main() -> int:
    print("NPM AUDIT TRIAGE")

    proc = subprocess.run(
        ["npm", "audit", "--json", "--prefix", str(FRONTEND_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )

    total = 0
    vulnerable_packages: list[str] = []
    try:
        payload = json.loads(proc.stdout or "{}")
        meta = payload.get("metadata", {}).get("vulnerabilities", {})
        total = int(meta.get("total", 0))
        vulnerable_packages = list(payload.get("vulnerabilities", {}).keys())
    except Exception:
        payload = {}

    print(f"vulnerabilities={total}")

    if total == 0:
        print("RESULT: PASS no_vulnerabilities")
        return 0

    # Vulnerabilities found — verify every package is in the triage doc
    if not TRIAGE_DOC.exists():
        print(f"RESULT: FAIL missing_triage_doc={TRIAGE_DOC.relative_to(REPO_ROOT)}")
        return 1

    triage_text = TRIAGE_DOC.read_text(encoding="utf-8")
    triaged = _triaged_packages(triage_text)
    print(f"triage_doc={TRIAGE_DOC.relative_to(REPO_ROOT)}")
    print(f"triaged_packages_in_doc={len(triaged)}")
    print(f"vulnerable_packages={len(vulnerable_packages)}")

    untriaged = [pkg for pkg in vulnerable_packages if pkg not in triaged]
    if untriaged:
        print("RESULT: FAIL untriaged_packages")
        for pkg in untriaged:
            print(f"  - untriaged: {pkg}")
        return 1

    incomplete_sections: list[str] = []
    for pkg in vulnerable_packages:
        section = _section_for_package(triage_text, pkg)
        if not section:
            incomplete_sections.append(f"{pkg}:missing_section")
            continue
        missing = _missing_required_fields(section)
        if missing:
            incomplete_sections.append(f"{pkg}:missing_fields={','.join(missing)}")

    if incomplete_sections:
        print("RESULT: FAIL incomplete_triage_metadata")
        for item in incomplete_sections:
            print(f"  - {item}")
        return 1

    print("RESULT: PASS all_packages_triaged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
