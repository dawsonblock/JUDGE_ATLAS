"""Enforce fail-closed audit semantics on critical mutation routes."""

from __future__ import annotations

import ast
import inspect
import textwrap

from fastapi.routing import APIRoute

from app.main import app
from app.security.mutation_route_allowlist import find_allowlist_entry

CRITICAL_MUTATION_ROUTES: tuple[tuple[str, str], ...] = (
    ("POST", "/api/admin/import/crime-incidents/manual-csv"),
    ("POST", "/api/admin/ingestion-runs/{run_id}/retry"),
    ("POST", "/api/ingest/courtlistener"),
    ("POST", "/api/events"),
    ("POST", "/api/admin/memory/claims/{claim_id}/invalidate"),
    ("POST", "/api/admin/correctness/run/incident/{incident_id}"),
    ("POST", "/api/admin/correctness/run/event/{event_id}"),
    ("POST", "/api/admin/ai/verify-source/{record_type}/{record_id}"),
)


def _find_route(path: str, method: str) -> APIRoute | None:
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path != path:
            continue
        if method.upper() in (route.methods or set()):
            return route
    return None


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


def test_critical_mutation_routes_use_fail_closed_audit_logging() -> None:
    findings: list[str] = []

    for method, path in CRITICAL_MUTATION_ROUTES:
        route = _find_route(path, method)
        if route is None:
            findings.append(f"{method} {path}: route not found")
            continue

        if find_allowlist_entry(path, method) is not None:
            continue

        calls = _log_mutation_calls(route)
        if not calls:
            findings.append(f"{method} {path}: missing log_mutation call")
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
