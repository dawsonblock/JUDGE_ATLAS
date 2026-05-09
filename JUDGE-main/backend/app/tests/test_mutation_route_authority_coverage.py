"""Coverage checks for mutation-route authority on the touched admin modules."""

from __future__ import annotations

import inspect

import app.api.routes.admin_ingest as admin_ingest
import app.api.routes.admin_ingestion as admin_ingestion
import app.api.routes.admin_memory as admin_memory
import app.api.routes.admin_quarantine as admin_quarantine
import app.api.routes.admin_review as admin_review
import app.api.routes.ai_review as ai_review
import app.api.routes.ingestion as ingestion
import app.api.routes.admin_sources as admin_sources


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


def test_mutation_routes_use_explicit_role_floors() -> None:
    findings: list[str] = []
    for module in MUTATION_ROUTE_MODULES:
        for _, fn in inspect.getmembers(module, inspect.isfunction):
            source = inspect.getsource(fn)
            mutation_markers = (
                "@router.post",
                "@router.put",
                "@router.patch",
                "@router.delete",
            )
            if not any(marker in source for marker in mutation_markers):
                continue
            for forbidden in FORBIDDEN_DEPENDENCIES:
                if f"Depends({forbidden})" in source:
                    findings.append(
                        f"{module.__name__}.{fn.__name__}: found forbidden dependency Depends({forbidden})"
                    )
            if not any(required in source for required in REQUIRED_DEPENDENCIES):
                findings.append(
                    f"{module.__name__}.{fn.__name__}: missing explicit role-floor helper"
                )

    assert not findings, "\n".join(findings)
