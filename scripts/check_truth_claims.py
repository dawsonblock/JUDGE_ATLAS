#!/usr/bin/env python3
"""Fail if unsupported platform claims are reintroduced.

This guard scans repository text for exact high-risk phrases that previously
blurred the line between alpha/reviewer-assisted functionality and proven
operational capability. Prefer precise wording such as "alpha", "reviewer-
assisted", "evidence-linked", "partially implemented", or "source-dependent".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

BANNED_PHRASES = (
    "production-ready",
    "fully autonomous",
    "real AI judge",
    "fully verified",
    "complete legal coverage",
    "fully automated moderation",
    "fully automated",
    "100% accurate",
    "live nationwide sync",
    "autonomous accountability",
    "verified legal conclusions",
    "complete national coverage",
    "guilt scoring",
    "danger scoring",
    "corruption scoring",
    # Explicit attribution / characterisation phrases
    "is guilty",
    "found guilty",
    "is corrupt",
    "is a corrupt",
    "risk score",
    "danger score",
    "corruption score",
    "criminal record",
    "criminal history",
    "is a criminal",
    "committed corruption",
    "convicted of",
)


class AllowedPolicyPhrase(NamedTuple):
    reason: str
    phrases: tuple[str, ...]


ALLOWED_POLICY_FILES: dict[str, AllowedPolicyPhrase] = {
    "scripts/check_false_claims.py": AllowedPolicyPhrase(
        reason="Compatibility wrapper for policy scanner naming.",
        phrases=BANNED_PHRASES,
    ),
    "scripts/check_truth_claims.py": AllowedPolicyPhrase(
        reason="Policy scanner defines forbidden phrase vocabulary.",
        phrases=BANNED_PHRASES,
    ),
    "scripts/verify_status_consistency.py": AllowedPolicyPhrase(
        reason=(
            "Status consistency checker validates forbidden "
            "production-claim variants."
        ),
        phrases=("production-ready",),
    ),
    # Files that reference banned phrases in a PROHIBITORY or SAFETY context
    # (docstrings, tests verifying suppression, legal docs stating what we
    # are NOT).
    "backend/app/models/entities.py": AllowedPolicyPhrase(
        reason="Docstring explicitly prohibits danger scores.",
        phrases=("danger score",),
    ),
    "backend/app/api/routes/ai_correctness.py": AllowedPolicyPhrase(
        reason="Route docstrings state we do NOT produce danger/guilt scores.",
        phrases=("danger score", "guilt score", "danger scores"),
    ),
    "backend/app/services/source_verifier.py": AllowedPolicyPhrase(
        reason=(
            "Module docstring and function docstrings explicitly prohibit "
            "these fields."
        ),
        phrases=(
            "danger score",
            "danger scores",
            "guilt score",
            "guilt scores",
            "danger_score",
        ),
    ),
    "backend/app/ai/narrative_detection.py": AllowedPolicyPhrase(
        reason=(
            "Detects prohibited phrases spoken by other sources - detection "
            "list, not assertion."
        ),
        phrases=("criminal history",),
    ),
    "backend/app/services/constants.py": AllowedPolicyPhrase(
        reason="Constants list phrases we detect/suppress from external text.",
        phrases=("criminal history",),
    ),
    "backend/app/services/embeddings.py": AllowedPolicyPhrase(
        reason=(
            "Comment-only example string illustrating encoding input - "
            "not a platform claim."
        ),
        phrases=("convicted of",),
    ),
    "backend/app/tests/test_llm_safety.py": AllowedPolicyPhrase(
        reason=(
            "Safety test verifying 'is guilty' is suppressed in LLM output."
        ),
        phrases=("is guilty",),
    ),
    "backend/app/tests/test_ai_correctness.py": AllowedPolicyPhrase(
        reason="Test asserts that danger score is NOT produced.",
        phrases=("danger score",),
    ),
    "backend/app/tests/test_classifier.py": AllowedPolicyPhrase(
        reason=(
            "'criminal history category' is a US Sentencing Guidelines "
            "term used as classifier input."
        ),
        phrases=("criminal history", "criminal history category"),
    ),
    "docs/LEGAL_RISK_BOUNDARIES.md": AllowedPolicyPhrase(
        reason=(
            "Explicitly states what the platform is NOT "
            "(not a criminal records registry)."
        ),
        phrases=("criminal record",),
    ),
    "docs/RELEASE_BLOCKERS.md": AllowedPolicyPhrase(
        reason=(
            "Blocker item states these scores MUST have "
            "requires_human_review guard before ship."
        ),
        phrases=("corruption score", "danger score", "guilt",),
    ),
    "docs/AI_LIMITATIONS.md": AllowedPolicyPhrase(
        reason="Limitations doc documents prohibited outputs.",
        phrases=("danger score",),
    ),
    "docs/JUVENILE_AND_SEALED_RECORDS.md": AllowedPolicyPhrase(
        reason=(
            "Quotes YCJA s.110 - 'criminal offence' is a quoted "
            "statutory term, not a platform claim."
        ),
        phrases=("is a criminal", "criminal offence"),
    ),
    "CURRENT_STATUS.md": AllowedPolicyPhrase(
        reason=(
            "Status doc explicitly states no AI module produces "
            "corruption scores."
        ),
        phrases=("corruption score",),
    ),
    "backend/app/llm/reviewer_assistant.py": AllowedPolicyPhrase(
        reason=(
            "Last-resort output guard: defines the list of "
            "prohibited phrases for suppression."
        ),
        phrases=("is guilty", "found guilty", "convicted of", "is a criminal"),
    ),
    "backend/app/tests/test_llm_safety_boundaries.py": AllowedPolicyPhrase(
        reason=(
            "Safety boundary tests verifying prohibited phrases are "
            "suppressed in LLM output."
        ),
        phrases=("is guilty", "found guilty", "convicted of", "is a criminal"),
    ),
    "backend/app/tests/test_ai_reasoning.py": AllowedPolicyPhrase(
        reason=(
            "Test uses 'criminal history' as classifier input "
            "from external text, not a platform claim."
        ),
        phrases=("criminal history",),
    ),
    "backend/app/tests/test_embeddings.py": AllowedPolicyPhrase(
        reason=(
            "'convicted of' in a test fixture string exercising "
            "the encoder, not a platform claim."
        ),
        phrases=("convicted of",),
    ),
    "backend/app/tests/test_extract_claims.py": AllowedPolicyPhrase(
        reason=(
            "Tests extract-claims parser on prohibited-phrase inputs "
            "to verify suppression."
        ),
        phrases=("convicted of", "found guilty"),
    ),
    "backend/app/tests/test_api.py": AllowedPolicyPhrase(
        reason=(
            "API test uses 'criminal history' as classifier input "
            "string, not a platform claim."
        ),
        phrases=("criminal history",),
    ),
    "backend/app/tests/test_ai_pipeline.py": AllowedPolicyPhrase(
        reason=(
            "Pipeline test uses 'criminal history' as classifier "
            "input string, not a platform claim."
        ),
        phrases=("criminal history",),
    ),
}

SKIP_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "external",
    "node_modules",
    "target",
}

SKIP_SUFFIXES = {
    ".db",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".zip",
}

TRUTH_SENSITIVE_REL_PATHS = {
    "README.md",
    "CURRENT_STATUS.md",
    "PROOF_STATUS.md",
    "RELEASE_BLOCKERS.md",
    "STUBS_AND_PLACEHOLDERS.md",
    "REPO_REALITY.md",
    "COMPLETION_CHECKLIST.md",
}


def _iter_files(root: Path):
    self_path = Path(__file__).resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == self_path:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def get_scanned_paths(root: Path) -> list[Path]:
    """Return all text file paths inspected by the truth-claim scanner."""
    return sorted(_iter_files(root))


def get_truth_sensitive_paths(root: Path) -> list[Path]:
    """Return the subset of scanned files that define release-truth posture."""
    selected: list[Path] = []
    for path in get_scanned_paths(root):
        rel = path.relative_to(root).as_posix()
        if rel in TRUTH_SENSITIVE_REL_PATHS:
            selected.append(path)
    return sorted(selected)


def check(root: Path) -> int:
    violations: list[str] = []
    lowered = tuple(phrase.lower() for phrase in BANNED_PHRASES)
    for path in _iter_files(root):
        rel_path = path.relative_to(root).as_posix()
        allow_rule = ALLOWED_POLICY_FILES.get(rel_path)
        allowed_phrases = {
            phrase.lower() for phrase in allow_rule.phrases
        } if allow_rule else set()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            line_lower = line.lower()
            for phrase in lowered:
                if phrase in allowed_phrases:
                    continue
                if phrase in line_lower:
                    violations.append(
                        (
                            f"{path}:{line_no}: unsupported claim "
                            f"phrase {phrase!r}"
                        )
                    )

    if violations:
        print("ERROR: unsupported platform claim phrases detected:")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print(f"OK: no unsupported platform claim phrases detected in {root}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root to scan")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(2)
    sys.exit(check(root))


if __name__ == "__main__":
    main()
