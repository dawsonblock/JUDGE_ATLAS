"""Shared row-digest helper for the AuditLog integrity chain.

Extracted here to avoid circular imports between admin.py (which writes
log entries) and integrity_chain.py (which verifies them).
"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.entities import AuditLog

GENESIS_HASH = "GENESIS"


def row_digest(row: "AuditLog", prev_hash: str) -> str:
    """Return the SHA-256 hex digest for *row* chained to *prev_hash*."""
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
