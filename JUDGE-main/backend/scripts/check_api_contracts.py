#!/usr/bin/env python3
"""Validate backend/frontend API contract fixture presence and schema structure.

This is intentionally strict:
  - Missing contract files are a gate failure.
  - Files that do not contain a JSON Schema (missing $schema, required, or
    properties / items) are a gate failure.
  - Files that are not valid JSON are a gate failure.
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

# Minimum keys that every top-level JSON Schema object must contain.
_REQUIRED_SCHEMA_KEYS = {"$schema", "required", "type"}
# At least one of these must be present to describe the shape.
_SHAPE_KEYS = {"properties", "items"}


def _validate_schema(data: dict) -> list[str]:
    """Return a list of structural violations for *data*."""
    errors: list[str] = []
    missing_top = _REQUIRED_SCHEMA_KEYS - data.keys()
    if missing_top:
        errors.append(f"missing top-level schema keys: {sorted(missing_top)}")
    if not (_SHAPE_KEYS & data.keys()):
        errors.append(f"schema must have at least one of {sorted(_SHAPE_KEYS)}")
    return errors


def main() -> int:
    missing: list[str] = []
    invalid: list[str] = []
    schema_errors: list[str] = []

    for name in EXPECTED:
        path = CONTRACT_DIR / name
        if not path.exists():
            missing.append(name)
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            invalid.append(f"{name}: {exc}")
            continue

        if not isinstance(data, dict):
            schema_errors.append(f"{name}: top-level value must be a JSON object")
            continue

        violations = _validate_schema(data)
        for v in violations:
            schema_errors.append(f"{name}: {v}")

    if missing or invalid or schema_errors:
        print("API CONTRACTS: FAIL")
        for name in missing:
            print(f"  missing:{name}")
        for item in invalid:
            print(f"  invalid:{item}")
        for item in schema_errors:
            print(f"  schema:{item}")
        return 1

    print("API CONTRACTS: PASS")
    print(f"contracts_checked={len(EXPECTED)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
