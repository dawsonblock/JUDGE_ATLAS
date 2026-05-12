#!/usr/bin/env python3
"""Verify that repository status and proof references resolve to the current truth layer."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CANONICAL_CURRENT_PROOF = "artifacts/proof/current/CURRENT_PROOF.md"
CANONICAL_RELEASE_READINESS = "artifacts/proof/current/release_readiness.md"
CANONICAL_STATUS = "STATUS.md"
LEGACY_RELEASE_READINESS = "artifacts/proof/release_readiness.md"
ARCHIVED_HEADER = "ARCHIVED / NOT CURRENT"

DOCS_TO_CHECK = (
    "README.md",
    "CURRENT_STATUS.md",
    "docs/RELEASE_READINESS.md",
    "docs/REPO_REALITY.md",
    "docs/DEPLOYMENT.md",
)

POSITIVE_PRODUCTION_READY_PATTERNS = (
    re.compile(r"production\s+ready\s*:\s*true", re.IGNORECASE),
    re.compile(r"\bproduction-ready\b", re.IGNORECASE),
    re.compile(r"ready\s+for\s+production\s+deployment", re.IGNORECASE),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_line_value(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _has_positive_production_ready_claim(text: str) -> bool:
    lowered = text.lower()
    if "production ready: false" in lowered:
        lowered = lowered.replace("production ready: false", "")
    if "not ready for production deployment" in lowered:
        lowered = lowered.replace("not ready for production deployment", "")
    if "not production ready" in lowered:
        lowered = lowered.replace("not production ready", "")
    return any(pattern.search(lowered) for pattern in POSITIVE_PRODUCTION_READY_PATTERNS)


def verify(root: Path) -> list[str]:
    errors: list[str] = []

    status_path = root / CANONICAL_STATUS
    if not status_path.exists():
        errors.append(f"missing:{CANONICAL_STATUS}")
        return errors

    status_text = _read(status_path)
    if "Alpha proof status: PASS" not in status_text:
        errors.append("STATUS.md:missing_alpha_pass_line")
    if "Production ready: FALSE" not in status_text:
        errors.append("STATUS.md:missing_production_false_line")
    if (
        "This repository is an alpha/research-grade platform, not a production legal system."
        not in status_text
    ):
        errors.append("STATUS.md:missing_required_research_grade_disclaimer")

    status_alpha = _extract_line_value(status_text, "- Alpha proof status")
    status_prod = _extract_line_value(status_text, "- Production ready")

    production_proof = root / "artifacts" / "proof" / "current" / "production_preflight.md"

    for rel_path in DOCS_TO_CHECK:
        path = root / rel_path
        if not path.exists():
            errors.append(f"missing:{rel_path}")
            continue
        text = _read(path)
        if LEGACY_RELEASE_READINESS in text:
            errors.append(f"{rel_path}:stale_release_readiness_reference")
        if CANONICAL_STATUS not in text:
            errors.append(f"{rel_path}:missing_status_reference")
        if CANONICAL_CURRENT_PROOF not in text:
            errors.append(f"{rel_path}:missing_current_proof_reference")
        if CANONICAL_RELEASE_READINESS not in text:
            errors.append(f"{rel_path}:missing_current_release_readiness_reference")
        if _has_positive_production_ready_claim(text) and not production_proof.exists():
            errors.append(f"{rel_path}:production_ready_claim_without_proof")

    current_status_path = root / "CURRENT_STATUS.md"
    if current_status_path.exists():
        current_status_text = _read(current_status_path)
        current_alpha = _extract_line_value(current_status_text, "- Alpha proof status")
        current_prod = _extract_line_value(current_status_text, "- Production ready")
        if current_alpha is not None and status_alpha is not None and current_alpha != status_alpha:
            errors.append("CURRENT_STATUS.md:alpha_status_contradicts_STATUS.md")
        if current_prod is not None and status_prod is not None and current_prod != status_prod:
            errors.append("CURRENT_STATUS.md:production_status_contradicts_STATUS.md")

    legacy_release_path = root / LEGACY_RELEASE_READINESS
    if legacy_release_path.exists():
        legacy_text = _read(legacy_release_path)
        if ARCHIVED_HEADER not in legacy_text:
            errors.append("artifacts/proof/release_readiness.md:live_unarchived_legacy_file")

    proof_policy_path = root / "docs" / "PROOF_POLICY.md"
    if proof_policy_path.exists() and _has_positive_production_ready_claim(_read(proof_policy_path)) and not production_proof.exists():
        errors.append("docs/PROOF_POLICY.md:production_ready_claim_without_proof")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors = verify(root)
    if errors:
        print("STATUS CONSISTENCY: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("STATUS CONSISTENCY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())