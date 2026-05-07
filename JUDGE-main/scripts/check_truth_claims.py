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

BANNED_PHRASES = (
    "production-ready",
    "fully autonomous",
    "real AI judge",
    "fully verified",
    "complete legal coverage",
    "fully automated moderation",
    "100% accurate",
    "live nationwide sync",
)

SKIP_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
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


def check(root: Path) -> int:
    violations: list[str] = []
    lowered = tuple(phrase.lower() for phrase in BANNED_PHRASES)
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            line_lower = line.lower()
            for phrase in lowered:
                if phrase in line_lower:
                    violations.append(
                        f"{path}:{line_no}: unsupported claim phrase {phrase!r}"
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
