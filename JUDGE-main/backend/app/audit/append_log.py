"""Write a single immutable AuditLog entry.

All admin mutations MUST call ``append_audit_entry`` before committing.
The caller is responsible for committing the session.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def _hash_payload(payload: dict[str, Any] | None) -> str:
    canonical = json.dumps(payload or {}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def append_audit_entry(
    db: Session,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "user",
    actor_role: str | None = None,
    actor_ip: str | None = None,
    request_id: str | None = None,
    user_agent: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert one AuditLog row and flush (no commit).

    Caller must commit the session to persist.
    """
    full_payload: dict[str, Any] = dict(payload or {})
    full_payload["_payload_hash"] = _hash_payload(payload)
    full_payload["_ts"] = datetime.now(timezone.utc).isoformat()

    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role=actor_role,
        actor_ip=actor_ip,
        request_id=request_id,
        user_agent=user_agent,
        payload=full_payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry
