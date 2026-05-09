#!/usr/bin/env python3
"""Verify that the Next.js frontend exposes the expected map routes.

Checks:
  1. frontend/app/map/        — /map page exists
  2. frontend/app/map-v2/     — /map-v2 upgraded page exists
  3. map-v2 must have a page.tsx (or page.js) — not just a directory stub
  4. map-v2 content must not be empty / placeholder-only

Exits 0 on success, 1 on failure.  Writes a summary to stdout.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_APP = REPO_ROOT / "frontend" / "app"

REQUIRED_ROUTES = [
    "map",
    "map-v2",
]

# Tokens that indicate a stub/placeholder page that has not been implemented
PLACEHOLDER_TOKENS = [
    "TODO",
    "Coming soon",
    "Placeholder",
    "under construction",
    "not implemented",
]


def _find_page_file(route_dir: Path) -> Path | None:
    for name in ("page.tsx", "page.jsx", "page.ts", "page.js"):
        candidate = route_dir / name
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    findings: list[str] = []

    for route in REQUIRED_ROUTES:
        route_dir = FRONTEND_APP / route
        if not route_dir.is_dir():
            findings.append(f"MISSING route directory: frontend/app/{route}/")
            continue

        page_file = _find_page_file(route_dir)
        if page_file is None:
            findings.append(f"MISSING page file in frontend/app/{route}/ (expected page.tsx)")
            continue

        content = page_file.read_text(encoding="utf-8")
        if len(content.strip()) < 10:
            findings.append(f"EMPTY page: {page_file.relative_to(REPO_ROOT)}")
            continue

        for token in PLACEHOLDER_TOKENS:
            if token.lower() in content.lower():
                findings.append(
                    f"PLACEHOLDER in {page_file.relative_to(REPO_ROOT)}: found {token!r}"
                )
                break

    if findings:
        print("RESULT: FAIL")
        for f in findings:
            print(f"  {f}")
        return 1

    print("RESULT: PASS")
    for route in REQUIRED_ROUTES:
        page_file = _find_page_file(FRONTEND_APP / route)
        size = page_file.stat().st_size if page_file else 0
        print(f"  OK frontend/app/{route}/ ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
