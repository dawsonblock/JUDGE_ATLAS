#!/usr/bin/env python3
"""AST guard: assert no source adapter imports a direct HTTP client library.

Every outbound HTTP call from ingestion adapters must route through
``app.ingestion.fetcher.fetch_for_ingestion`` (which in turn calls
``app.security.safe_fetch.safe_fetch``).  Direct use of ``httpx``,
``requests``, ``aiohttp``, or ``urllib.request`` in adapter source files
bypasses SSRF protection and is therefore forbidden.

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

_ADAPTERS_DIR = (
    Path(__file__).parent.parent
    / "app"
    / "ingestion"
    / "source_adapters"
)

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

# Files explicitly allowlisted (relative to _ADAPTERS_DIR / parent).
_ALLOWLIST = frozenset({"fetcher.py"})


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


def main() -> int:
    adapter_files = sorted(_ADAPTERS_DIR.glob("*.py"))
    all_violations: list[str] = []

    for path in adapter_files:
        if path.name in _ALLOWLIST:
            continue
        all_violations.extend(_check_file(path))

    if all_violations:
        print("ERROR: Direct network client imports found in ingestion adapters:")
        for v in all_violations:
            print(f"  {v}")
        print(
            "\nAll outbound HTTP calls must route through "
            "app.ingestion.fetcher.fetch_for_ingestion."
        )
        return 1

    print(
        f"OK: {len(adapter_files)} adapter file(s) checked — "
        "no direct network client imports found."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
