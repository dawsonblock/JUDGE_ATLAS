#!/usr/bin/env python3
"""Verify source registry integrity: no enabled source may use a stub adapter.

Loads YAML source definitions and the ADAPTER_REGISTRY, then checks that every
source with ``automation_status: machine_ready`` has an adapter whose
``fetch()`` method is implemented (i.e. does NOT raise ``NotImplementedError``).

Exit codes:
  0 — all checks pass
  1 — one or more enabled sources have a stub adapter
  2 — ADAPTER_REGISTRY could not be imported (sys.path/environment issue)

Usage::

    python scripts/verify_source_registry.py          # summary report
    python scripts/verify_source_registry.py --json   # machine-readable JSON
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import yaml  # noqa: E402
except ImportError:
    print("ERROR: PyYAML not installed — run: pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

try:
    from app.ingestion.source_adapters import ADAPTER_REGISTRY
except Exception as exc:  # noqa: BLE001
    print(f"ERROR: Cannot import ADAPTER_REGISTRY: {exc}", file=sys.stderr)
    raise SystemExit(2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_sources() -> list[dict[str, Any]]:
    yaml_path = (
        REPO_ROOT / "backend" / "app" / "ingestion" / "sources" / "canada_saskatchewan_sources.yaml"
    )
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return list(data.get("sources", []))


def _is_stub_adapter(adapter_class: type) -> bool:
    """Return True if the class's fetch() method raises NotImplementedError.

    Done via AST inspection so it works even if the class is not easily
    instantiated (e.g., requires external services at __init__ time).
    """
    try:
        source_file = Path(sys.modules[adapter_class.__module__].__file__)
        src = source_file.read_text(encoding="utf-8")
    except Exception:
        return False

    tree = ast.parse(src)

    # Find class definition matching the adapter's class name
    for class_node in ast.walk(tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        if class_node.name != adapter_class.__name__:
            continue
        for method in class_node.body:
            if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if method.name != "fetch":
                continue
            for stmt in ast.walk(method):
                if isinstance(stmt, ast.Raise) and stmt.exc is not None:
                    exc_node = stmt.exc
                    if isinstance(exc_node, ast.Call):
                        func = exc_node.func
                    elif isinstance(exc_node, ast.Name):
                        func = exc_node
                    else:
                        continue
                    name = (
                        func.id
                        if isinstance(func, ast.Name)
                        else (func.attr if isinstance(func, ast.Attribute) else "")
                    )
                    if name == "NotImplementedError":
                        return True
    return False


def _count_by_status(sources: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in sources:
        st = s.get("automation_status", "unknown")
        counts[st] = counts.get(st, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------


def verify() -> dict[str, Any]:
    sources = _load_sources()
    status_counts = _count_by_status(sources)

    enabled_stubs: list[dict[str, str]] = []
    missing_adapters: list[dict[str, str]] = []
    registry_summary: list[dict[str, Any]] = []

    for source in sources:
        sk = source.get("source_key", "")
        parser_key = source.get("parser") or ""
        auto_status = source.get("automation_status", "unknown")

        in_registry = parser_key in ADAPTER_REGISTRY if parser_key else False
        is_stub = False

        if in_registry:
            is_stub = _is_stub_adapter(ADAPTER_REGISTRY[parser_key])
        elif parser_key and auto_status == "machine_ready":
            missing_adapters.append({"source_key": sk, "parser": parser_key})

        if auto_status == "machine_ready" and in_registry and is_stub:
            enabled_stubs.append(
                {
                    "source_key": sk,
                    "parser": parser_key,
                    "problem": "machine_ready source has a stub adapter",
                }
            )

        registry_summary.append(
            {
                "source_key": sk,
                "automation_status": auto_status,
                "parser": parser_key or None,
                "in_registry": in_registry,
                "is_stub": is_stub if in_registry else None,
            }
        )

    result = {
        "total_sources": len(sources),
        "status_counts": status_counts,
        "registry_summary": registry_summary,
        "enabled_stub_violations": enabled_stubs,
        "missing_adapter_violations": missing_adapters,
        "passed": len(enabled_stubs) == 0,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_output", action="store_true",
                        help="Print machine-readable JSON result instead of prose.")
    args = parser.parse_args()

    result = verify()

    if args.json_output:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"Source registry verification")
        print(f"  Total sources: {result['total_sources']}")
        print(f"  Status counts: {result['status_counts']}")
        print(f"  Enabled stub violations: {len(result['enabled_stub_violations'])}")
        for v in result["enabled_stub_violations"]:
            print(f"    VIOLATION: {v['source_key']} / {v['parser']} — {v['problem']}")
        if result["passed"]:
            print("PASS: no enabled source uses a stub adapter")
        else:
            print("FAIL: enabled sources with stub adapters detected (see above)")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
