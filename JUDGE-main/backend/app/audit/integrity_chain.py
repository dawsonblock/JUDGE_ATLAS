"""Verify the hash-linked integrity of the AuditLog chain."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


@dataclass
class ChainVerificationResult:
    ok: bool
    entries_checked: int
    chain_head: str | None  # SHA-256 of last row
    violations: list[str] = field(default_factory=list)


def _row_digest(row: AuditLog, prev_hash: str) -> str:
    canonical = json.dumps(
        {
            "id": row.id,
            "action": row.action,
            "actor_id": row.actor_id,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "payload": row.payload,
            "prev": prev_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_chain(db: Session) -> ChainVerificationResult:
    """Read all AuditLog rows in id-ascending order and check chain integrity."""
    rows = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not rows:
        return ChainVerificationResult(ok=True, entries_checked=0, chain_head=None)

    violations: list[str] = []
    prev_hash = "GENESIS"
    prev_id: int | None = None
    prev_ts = None

    for row in rows:
        # Monotonic ID check
        if prev_id is not None and row.id <= prev_id:
            violations.append(f"non-monotonic id at row {row.id}")

        # Monotonic timestamp check
        if prev_ts is not None and row.created_at is not None:
            if row.created_at < prev_ts:
                violations.append(f"timestamp regression at row {row.id}")

        # Actor present
        if not row.actor_id:
            violations.append(f"missing actor_id at row {row.id}")

        prev_hash = _row_digest(row, prev_hash)
        prev_id = row.id
        if row.created_at is not None:
            prev_ts = row.created_at

    return ChainVerificationResult(
        ok=len(violations) == 0,
        entries_checked=len(rows),
        chain_head=prev_hash,
        violations=violations,
    )
