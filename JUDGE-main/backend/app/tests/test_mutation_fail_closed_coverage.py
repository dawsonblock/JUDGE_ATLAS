"""Enforce fail-closed audit semantics on monitored mutation routes."""

from __future__ import annotations

import ast
import inspect
import textwrap

from fastapi.routing import APIRoute

from app.main import app
from app.security.mutation_route_allowlist import find_allowlist_entry

MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TARGET_PREFIXES = (
    "/api/admin",
    "/api/ingestion",
    "/api/ingest",
    "/api/ai-review",
    "/api/review",
    "/api/sources",
    "/api/evidence",
    "/api/graph",
    "/api/events",
    "/api/chat",
    "/api/evidence-store",
    "/api/map",
)


def _iter_target_mutation_routes() -> list[tuple[str, str, APIRoute]]:
    routes: list[tuple[str, str, APIRoute]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(TARGET_PREFIXES):
            continue
        for method in sorted((route.methods or set()) & MUTATION_METHODS):
            routes.append((method, route.path, route))
    return routes


def _log_mutation_calls(route: APIRoute) -> list[ast.Call]:
    source = textwrap.dedent(inspect.getsource(route.endpoint))
    tree = ast.parse(source)
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "log_mutation":
            calls.append(node)
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "log_mutation":
            calls.append(node)
    return calls


def _has_auditlog_call(route: APIRoute) -> bool:
    source = textwrap.dedent(inspect.getsource(route.endpoint))
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "AuditLog":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "AuditLog":
            return True
    return False


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(kw.arg == name for kw in call.keywords if kw.arg is not None)


def _has_fail_closed_true(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg != "fail_closed":
            continue
        return isinstance(kw.value, ast.Constant) and kw.value.value is True
    return False


def _has_db_session_keyword(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg != "db":
            continue
        return isinstance(kw.value, ast.Name) and kw.value.id == "db"
    return False


def test_monitored_mutation_routes_use_fail_closed_audit_logging() -> None:
    findings: list[str] = []

    for method, path, route in _iter_target_mutation_routes():
        if find_allowlist_entry(path, method) is not None:
            continue

        calls = _log_mutation_calls(route)
        has_auditlog = _has_auditlog_call(route)
        if not calls and not has_auditlog:
            findings.append(
                f"{method} {path}: missing audit write (log_mutation or AuditLog)"
            )
            continue

        for idx, call in enumerate(calls, start=1):
            if not _has_keyword(call, "db"):
                findings.append(
                    f"{method} {path}: log_mutation call #{idx} missing db=db"
                )
            elif not _has_db_session_keyword(call):
                findings.append(
                    f"{method} {path}: log_mutation call #{idx} db keyword must pass session variable 'db'"
                )

            if not _has_fail_closed_true(call):
                findings.append(
                    f"{method} {path}: log_mutation call #{idx} missing fail_closed=True"
                )

    assert not findings, "\n".join(findings)
