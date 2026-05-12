"""Write a single immutable AuditLog entry.

All admin mutations MUST call ``append_audit_entry`` before committing.
The caller is responsible for committing the session.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.audit.chain_digest import (
    CURRENT_CHAIN_VERSION,
    GENESIS_HASH,
    compute_payload_hash,
    row_digest,
)
from app.models.entities import AuditLog


def append_audit_entry(
    db: Session,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "user",
    actor_role: str | None = None,
    actor_auth_method: str | None = None,
    actor_ip: str | None = None,
    request_id: str | None = None,
    user_agent: str | None = None,
    payload: dict[str, Any] | None = None,
    before_hash: str | None = None,
    after_hash: str | None = None,
) -> AuditLog:
    """Insert one AuditLog row and flush (no commit).

    Computes and stores the full chain-v2 integrity hashes:
    - payload_hash: SHA-256 of canonical payload JSON
    - previous_entry_hash: entry_hash of the last committed row (GENESIS if none)
    - entry_hash: SHA-256 of this row's full canonical representation
    - before_hash / after_hash: caller-supplied pre/post state digests
    - chain_version: always CURRENT_CHAIN_VERSION

    Caller must commit the session to persist.
    """
    now = datetime.now(timezone.utc)

    # Determine previous entry hash from the most recently committed row.
    last = (
        db.query(AuditLog.entry_hash)
        .order_by(AuditLog.id.desc())
        .first()
    )
    prev_hash: str = (last[0] if last and last[0] else GENESIS_HASH)

    # Compute payload hash independently of the payload column content.
    p_hash = compute_payload_hash(payload)

    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role=actor_role,
        actor_auth_method=actor_auth_method,
        actor_ip=actor_ip,
        request_id=request_id,
        user_agent=user_agent,
        payload=payload,
        created_at=now,
        payload_hash=p_hash,
        before_hash=before_hash,
        after_hash=after_hash,
        previous_entry_hash=prev_hash,
        chain_version=CURRENT_CHAIN_VERSION,
    )
    db.add(entry)
    db.flush()  # get entry.id assigned

    # Now compute entry_hash using the flushed row (id is available).
    entry.entry_hash = row_digest(entry, prev_hash)
    db.flush()
    return entry
