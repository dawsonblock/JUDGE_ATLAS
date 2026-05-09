"""Verify append-only audit log ordering and compute a replay digest.

This verifier does not require additional DB columns. It enforces monotonic
ordering and stable deterministic replay hashing over immutable row content.

Usage:
  python -m backend.tools.verify_audit_chain
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# Ensure the backend directory is importable as top-level `app` when running
# `python -m backend.tools.*` from repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.entities import AuditLog


def _row_payload(row: AuditLog) -> dict:
    created = row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at)
    return {
        "id": row.id,
        "action": row.action,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "payload": row.payload,
        "actor_id": row.actor_id,
        "actor_type": row.actor_type,
        "actor_role": row.actor_role,
        "actor_ip": row.actor_ip,
        "created_at": created,
    }


def main() -> int:
    try:
        with SessionLocal() as db:
            rows = db.scalars(select(AuditLog).order_by(AuditLog.id.asc())).all()
    except SQLAlchemyError as exc:
        print("AUDIT CHAIN VERIFICATION")
        print("entries_checked=0")
        print(f"RESULT: FAIL database_error={exc.__class__.__name__}")
        print(str(exc))
        return 1

    print("AUDIT CHAIN VERIFICATION")
    print(f"entries_checked={len(rows)}")

    last_id = 0
    last_created = None
    chain = ""
    errors: list[str] = []

    for row in rows:
        if row.id <= last_id:
            errors.append(f"non_monotonic_id:{row.id}")
        last_id = row.id

        if last_created is not None and row.created_at is not None and row.created_at < last_created:
            errors.append(f"non_monotonic_timestamp:id={row.id}")
        if row.created_at is not None:
            last_created = row.created_at

        if row.action and "." in row.action and not row.actor_id:
            errors.append(f"missing_actor_id_for_mutation:id={row.id}")

        data = json.dumps(_row_payload(row), sort_keys=True, separators=(",", ":"))
        chain = hashlib.sha256((chain + data).encode("utf-8")).hexdigest()

    print(f"chain_head={chain or 'EMPTY'}")
    print(f"violations={len(errors)}")

    if errors:
        for err in errors:
            print(f"- {err}")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
