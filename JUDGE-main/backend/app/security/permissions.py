"""Permission constants and capability checks for JUDGE_ATLAS admin actions."""
from __future__ import annotations

# Action → required role mapping
MUTATION_PERMISSIONS: dict[str, set[str]] = {
    "source:create": {"admin", "superadmin"},
    "source:update": {"admin", "superadmin"},
    "source:delete": {"superadmin"},
    "review:approve": {"reviewer", "admin", "superadmin"},
    "review:reject": {"reviewer", "admin", "superadmin"},
    "review:flag": {"reviewer", "admin", "superadmin"},
    "review:override": {"admin", "superadmin"},
    "incident:publish": {"admin", "superadmin"},
    "incident:unpublish": {"admin", "superadmin"},
    "ingestion:run": {"admin", "superadmin"},
    "audit:read": {"admin", "superadmin"},
}

READ_PERMISSIONS: dict[str, set[str]] = {
    "source:read": {"viewer", "reviewer", "admin", "superadmin"},
    "review:read": {"reviewer", "admin", "superadmin"},
    "audit:read": {"admin", "superadmin"},
}


def can(role: str, action: str) -> bool:
    """Return True if *role* is allowed to perform *action*."""
    allowed = MUTATION_PERMISSIONS.get(action) or READ_PERMISSIONS.get(action)
    if allowed is None:
        return False
    return role in allowed


def assert_can(role: str, action: str) -> None:
    """Raise PermissionError if *role* cannot perform *action*."""
    if not can(role, action):
        raise PermissionError(f"Role '{role}' is not permitted to perform '{action}'")
