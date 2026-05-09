"""Verify the hash-linked integrity of the AuditLog chain."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.audit.chain_digest import GENESIS_HASH, row_digest
from app.models.entities import AuditLog


@dataclass
class ChainVerificationResult:
    ok: bool
    entries_checked: int
    chain_head: str | None  # SHA-256 of last row
    violations: list[str] = field(default_factory=list)


# Kept as a thin wrapper so existing callers are not broken.
_row_digest = row_digest


def verify_chain(db: Session) -> ChainVerificationResult:
    """Read all AuditLog rows in id-ascending order and check chain integrity."""
    rows = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not rows:
        return ChainVerificationResult(ok=True, entries_checked=0, chain_head=None)

    violations: list[str] = []
    prev_hash = GENESIS_HASH
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

        recomputed = row_digest(row, prev_hash)

        # If the row carries a stored hash, verify it matches the recomputed one.
        if row.entry_hash is not None and row.entry_hash != recomputed:
            violations.append(
                f"stored entry_hash mismatch at row {row.id}: "
                f"stored={row.entry_hash!r} recomputed={recomputed!r}"
            )

        prev_hash = recomputed
        prev_id = row.id
        if row.created_at is not None:
            prev_ts = row.created_at

    return ChainVerificationResult(
        ok=len(violations) == 0,
        entries_checked=len(rows),
        chain_head=prev_hash,
        violations=violations,
    )
