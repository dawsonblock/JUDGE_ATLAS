#!/usr/bin/env python3
"""AST guard: assert no source adapter imports a direct HTTP client library.

Every outbound HTTP call from ingestion adapters must route through
``app.ingestion.fetcher.fetch_for_ingestion`` (which in turn calls
``app.security.safe_fetch.safe_fetch``).  Direct use of ``httpx``,
``requests``, ``aiohttp``, or ``urllib.request`` in adapter source files
bypasses SSRF protection and is therefore forbidden.

This script also checks for **experimental cross-imports**: production runtime
modules (anything under ``app/`` that is not a test and not inside an
experimental directory) may not import from the experimental packages
``app.ingestion.crime_sources`` or ``app.ingestion.laws``.  The only
authorised callers of those packages are listed in ``_EXPERIMENTAL_CALLERS``.

Usage::

    python scripts/check_no_direct_ingestion_network_clients.py

Exit code 0 = all clear.  Exit code 1 = violation(s) found.

``fetcher.py`` itself is allowlisted because it *is* the thin shim that
calls ``safe_fetch``; it is the only file permitted to import ``httpx``
indirectly via that call chain.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_ADAPTERS_DIR = _REPO_ROOT / "app" / "ingestion" / "source_adapters"
_APP_DIR = _REPO_ROOT / "app"

# Modules that must not appear as top-level imports in adapter files.
_FORBIDDEN_MODULES = frozenset(
    {
        "httpx",
        "requests",
        "aiohttp",
        "urllib.request",
        "http.client",
    }
)

# Files explicitly allowlisted for the HTTP-client check (by filename only).
_ALLOWLIST = frozenset({"fetcher.py"})

# Experimental package prefixes (dotted module paths).
# Files inside these directories are not subject to the cross-import check;
# only calls FROM production code TO these prefixes are flagged.
_EXPERIMENTAL_PREFIXES = frozenset(
    {
        "app.ingestion.crime_sources",
        "app.ingestion.laws",
    }
)

# Production (non-test) files that are explicitly permitted to import from
# experimental packages because they are the narrow, gated entry-points.
# To add a new authorised caller, put its path relative to _REPO_ROOT here
# and document why the exception is warranted.
_EXPERIMENTAL_CALLERS: frozenset[Path] = frozenset(
    {
        # Manual CSV/JSON upload endpoint gated by JTA_ENABLE_ADMIN_IMPORTS.
        _REPO_ROOT / "app" / "api" / "routes" / "admin_ingest.py",
    }
)


def _check_file(path: Path) -> list[str]:
    """Return a list of violation strings found in *path*."""
    violations: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        violations.append(f"{path}: SyntaxError: {exc}")
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if alias.name in _FORBIDDEN_MODULES or top in _FORBIDDEN_MODULES:
                    violations.append(
                        f"{path}:{node.lineno}: forbidden import '{alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if module in _FORBIDDEN_MODULES or top in _FORBIDDEN_MODULES:
                violations.append(
                    f"{path}:{node.lineno}: forbidden 'from {module} import ...'"
                )
    return violations


def _is_experimental_path(path: Path) -> bool:
    """Return True if *path* lives inside an experimental package directory."""
    try:
        rel = path.relative_to(_APP_DIR)
    except ValueError:
        return False
    parts = rel.parts
    # e.g. ("ingestion", "crime_sources", "foo.py") → prefix "app.ingestion.crime_sources"
    if len(parts) >= 2:
        dotted = "app." + ".".join(parts[:-1])
        for prefix in _EXPERIMENTAL_PREFIXES:
            if dotted == prefix or dotted.startswith(prefix + "."):
                return True
    return False


def _check_experimental_cross_imports(path: Path) -> list[str]:
    """Return violations if *path* imports from an experimental package."""
    violations: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return violations  # SyntaxError already reported in the HTTP check.

    for node in ast.walk(tree):
        module = ""
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in _EXPERIMENTAL_PREFIXES:
                    if alias.name == prefix or alias.name.startswith(prefix + "."):
                        violations.append(
                            f"{path}:{node.lineno}: "
                            f"runtime import from experimental package '{alias.name}'"
                        )
            continue
        if module:
            for prefix in _EXPERIMENTAL_PREFIXES:
                if module == prefix or module.startswith(prefix + "."):
                    violations.append(
                        f"{path}:{node.lineno}: "
                        f"runtime import from experimental package '{module}'"
                    )
    return violations


def main() -> int:
    # ── Check 1: direct HTTP client imports in source_adapters/ ─────────────
    adapter_files = sorted(_ADAPTERS_DIR.glob("*.py"))
    http_violations: list[str] = []

    for path in adapter_files:
        if path.name in _ALLOWLIST:
            continue
        http_violations.extend(_check_file(path))

    # ── Check 2: experimental cross-imports from production runtime code ─────
    # Scan all .py files under app/ that are not test files and not inside an
    # experimental directory themselves.
    xp_violations: list[str] = []
    for path in sorted(_APP_DIR.rglob("*.py")):
        rel = path.relative_to(_REPO_ROOT)
        rel_str = str(rel)
        # Skip test files — they are permitted to exercise experimental code.
        if "test" in rel_str or "__pycache__" in rel_str:
            continue
        # Skip files that live inside the experimental packages themselves.
        if _is_experimental_path(path):
            continue
        # Skip explicitly authorised callers.
        if path in _EXPERIMENTAL_CALLERS:
            continue
        xp_violations.extend(_check_experimental_cross_imports(path))

    # ── Report ───────────────────────────────────────────────────────────────
    rc = 0

    if http_violations:
        print("ERROR: Direct network client imports found in ingestion adapters:")
        for v in http_violations:
            print(f"  {v}")
        print(
            "\nAll outbound HTTP calls must route through "
            "app.ingestion.fetcher.fetch_for_ingestion."
        )
        rc = 1
    else:
        print(
            f"OK: {len(adapter_files)} adapter file(s) checked — "
            "no direct network client imports found."
        )

    if xp_violations:
        print(
            "\nERROR: Runtime code imports from experimental packages "
            "(app.ingestion.crime_sources / app.ingestion.laws):"
        )
        for v in xp_violations:
            print(f"  {v}")
        print(
            "\nAdd an explicit entry to _EXPERIMENTAL_CALLERS in this script "
            "if the import is intentional and gated behind a feature flag."
        )
        rc = 1
    else:
        print(
            "OK: No unauthorised runtime imports from experimental packages found."
        )

    return rc


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
