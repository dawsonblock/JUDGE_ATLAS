"""Simple role-based access control helpers for FastAPI dependencies."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.security.permissions import can


def require_role(role: str, action: str) -> None:
    """Raise HTTP 403 if *role* cannot perform *action*."""
    if not can(role, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not permitted to perform '{action}'",
        )
