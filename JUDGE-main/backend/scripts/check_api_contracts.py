#!/usr/bin/env python3
"""Validate backend/frontend API contract fixture presence and shape.

This is intentionally strict: missing contract fixtures are a gate failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO_ROOT / "artifacts" / "contracts"
EXPECTED = [
    "public_map_markers.json",
    "public_entity_detail.json",
    "source_registry.json",
    "review_queue_item.json",
    "evidence_snapshot.json",
    "ai_review_result.json",
    "error_response.json",
]


def main() -> int:
    missing = []
    invalid = []
    for name in EXPECTED:
        path = CONTRACT_DIR / name
        if not path.exists():
            missing.append(name)
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            invalid.append(f"{name}: {exc}")
    if missing or invalid:
        print("API CONTRACTS: FAIL")
        for name in missing:
            print(f"- missing:{name}")
        for item in invalid:
            print(f"- invalid:{item}")
        return 1
    print("API CONTRACTS: PASS")
    print(f"contracts_checked={len(EXPECTED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
