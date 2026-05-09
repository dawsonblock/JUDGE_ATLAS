"""Mutation-route authority coverage checks.

This suite inspects real FastAPI route objects (not just source strings)
and enforces actor role-floor dependencies on mutation endpoints.
"""

from __future__ import annotations

import inspect
from typing import Iterable

from fastapi.routing import APIRoute

import app.api.routes.admin_ingest as admin_ingest
import app.api.routes.admin_ingestion as admin_ingestion
import app.api.routes.admin_memory as admin_memory
import app.api.routes.admin_quarantine as admin_quarantine
import app.api.routes.admin_review as admin_review
import app.api.routes.ai_review as ai_review
import app.api.routes.ingestion as ingestion
import app.api.routes.admin_sources as admin_sources
from app.security.mutation_route_allowlist import ALLOWLIST, find_allowlist_entry


MUTATION_ROUTE_MODULES = [
    admin_ingest,
    admin_ingestion,
    admin_memory,
    admin_quarantine,
    admin_review,
    ai_review,
    ingestion,
    admin_sources,
]

FORBIDDEN_DEPENDENCIES = (
    "require_admin_token",
    "require_system_admin",
    "require_admin_imports",
    "require_admin_review",
)

REQUIRED_DEPENDENCIES = (
    "require_import_actor",
    "require_source_admin_actor",
    "require_ai_review_actor",
    "require_admin_actor",
)

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TARGET_PREFIXES = (
    "/api/admin",
    "/api/ingestion",
    "/api/ingest",
    "/api/ai-review",
    "/api/review",
    "/api/sources",
)


def _dependency_names(route: APIRoute) -> set[str]:
    names: set[str] = set()
    for dep in route.dependant.dependencies:
        call = dep.call
        if call is None:
            continue
        name = getattr(call, "__name__", None)
        if name:
            names.add(name)
    return names


def _iter_target_mutation_routes() -> Iterable[tuple[str, APIRoute, str]]:
    for module in MUTATION_ROUTE_MODULES:
        for route in module.router.routes:
            if not isinstance(route, APIRoute):
                continue
            if not route.path.startswith(TARGET_PREFIXES):
                continue
            for method in sorted(route.methods & MUTATION_METHODS):
                yield module.__name__, route, method


def _has_audit_signal(route: APIRoute) -> bool:
    source = inspect.getsource(route.endpoint)
    return "log_mutation(" in source or "AuditLog(" in source


def _is_allowlisted(path: str, method: str) -> bool:
    return find_allowlist_entry(path, method) is not None


def test_allowlist_entries_are_specific_and_documented() -> None:
    findings: list[str] = []
    for entry in ALLOWLIST:
        if "*" in entry.path or "*" in entry.method:
            findings.append(
                f"allowlist {entry.method} {entry.path}: wildcard not allowed"
            )
        if not entry.path.startswith(TARGET_PREFIXES):
            findings.append(
                f"allowlist {entry.method} {entry.path}: path outside monitored prefixes"
            )
        if not entry.reason.strip():
            findings.append(f"allowlist {entry.method} {entry.path}: missing reason")
        if not entry.owner.strip():
            findings.append(f"allowlist {entry.method} {entry.path}: missing owner")
        if not entry.expires_on.strip():
            findings.append(f"allowlist {entry.method} {entry.path}: missing expires_on")

    assert not findings, "\n".join(findings)


def test_mutation_routes_use_explicit_role_floors() -> None:
    findings: list[str] = []
    for module_name, route, method in _iter_target_mutation_routes():
        dep_names = _dependency_names(route)
        route_id = f"{method} {route.path} ({module_name}.{route.endpoint.__name__})"

        for forbidden in FORBIDDEN_DEPENDENCIES:
            if forbidden in dep_names and not _is_allowlisted(route.path, method):
                findings.append(f"{route_id}: forbidden dependency {forbidden}")

        if not any(required in dep_names for required in REQUIRED_DEPENDENCIES):
            findings.append(f"{route_id}: missing explicit role-floor helper")

        if not _has_audit_signal(route) and not _is_allowlisted(route.path, method):
            findings.append(f"{route_id}: missing audit signal (log_mutation or AuditLog)")

    assert not findings, "\n".join(findings)
