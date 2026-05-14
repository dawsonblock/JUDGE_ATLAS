#!/usr/bin/env python3
"""Validate source-registry documentation claims against YAML + adapter registry."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.ingestion.source_adapters import ADAPTER_REGISTRY  # noqa: E402
except Exception:  # pragma: no cover - gate runner compatibility fallback
    ADAPTER_REGISTRY = {}

ROOT_MD_EXCLUDE = {
    "REPAIR_REPORT.md",
    "CURRENT_ALPHA_STATUS.md",
    "SOURCE_REGISTRY_STATUS.md",
    "PROOF_POLICY.md",
}


def _load_yaml_sources() -> list[dict]:
    yaml_path = (
        REPO_ROOT
        / "backend"
        / "app"
        / "ingestion"
        / "sources"
        / "canada_saskatchewan_sources.yaml"
    )
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return list(data.get("sources", []))


def _collect_doc_texts() -> list[tuple[Path, str]]:
    paths = [REPO_ROOT / "README.md"]
    for path in REPO_ROOT.glob("*.md"):
        if path.name in ROOT_MD_EXCLUDE:
            continue
        paths.append(path)
    paths.extend((REPO_ROOT / "docs").glob("**/*.md"))
    out: list[tuple[Path, str]] = []
    for path in paths:
        if path.exists():
            out.append((path, path.read_text(encoding="utf-8", errors="ignore")))
    return out


def _validate_source_registry_status_doc(sources: list[dict]) -> list[str]:
    errors: list[str] = []
    doc_path = REPO_ROOT / "docs" / "SOURCE_REGISTRY_STATUS.md"
    if not doc_path.exists():
        errors.append("docs/SOURCE_REGISTRY_STATUS.md:missing")
        return errors

    text = doc_path.read_text(encoding="utf-8", errors="ignore")
    yaml_keys = {str(source.get("source_key")) for source in sources}

    row_keys = set()
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0].strip("`").strip()
        first_lower = first.lower()
        if first_lower in {"source key", "source_key", "---"}:
            continue
        if first.startswith(":"):
            continue
        if first in {"↳", "->"}:
            continue
        if first:
            row_keys.add(first)

    if row_keys:
        missing = sorted(yaml_keys - row_keys)
        extra = sorted(row_keys - yaml_keys)
        if missing:
            errors.append(
                f"docs/SOURCE_REGISTRY_STATUS.md:missing_source_keys:{','.join(missing)}"
            )
        if extra:
            errors.append(
                f"docs/SOURCE_REGISTRY_STATUS.md:unknown_source_keys:{','.join(extra)}"
            )

    count_match = re.search(r"-\s*total_sources:\s*(\d+)", text)
    if count_match:
        documented_count = int(count_match.group(1))
        if documented_count != len(sources):
            errors.append(
                f"docs/SOURCE_REGISTRY_STATUS.md:source_count_mismatch:{documented_count}!={len(sources)}"
            )

    return errors


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    sources = _load_yaml_sources()
    sources_by_key = {str(source.get("source_key")): source for source in sources}

    adapter_files = {
        path.name
        for path in (REPO_ROOT / "backend" / "app" / "ingestion" / "source_adapters").glob("*.py")
    }

    doc_entries = _collect_doc_texts()
    for path, text in doc_entries:
        rel = path.relative_to(REPO_ROOT)

        if re.search(r"source_adapters/justice_laws_xml\.py", text):
            errors.append(f"{rel}:stale_adapter_path:source_adapters/justice_laws_xml.py")

        if re.search(r"source_adapters/justice_laws_pit_xml\.py", text):
            errors.append(f"{rel}:stale_adapter_path:source_adapters/justice_laws_pit_xml.py")

        if re.search(
            r"justice_canada_laws_pit_xml.*(implemented|adapter\s+exists:\s+yes|can\s+run\s+now:\s+yes|current\s+alpha\s+status:\s+runnable)",
            text,
            re.IGNORECASE,
        ):
            pit = sources_by_key.get("justice_canada_laws_pit_xml", {})
            if pit.get("automation_status") == "adapter_missing":
                errors.append(f"{rel}:pit_xml_claims_implemented_but_adapter_missing")

        if re.search(r"complete\s+canadian\s+coverage", text, re.IGNORECASE):
            errors.append(f"{rel}:forbidden_complete_coverage_claim")

    if "laws_justice_xml.py" not in adapter_files:
        errors.append("backend/app/ingestion/source_adapters/laws_justice_xml.py:missing")

    errors.extend(_validate_source_registry_status_doc(sources))

    if errors:
        print("SOURCE REGISTRY DOCS: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("SOURCE REGISTRY DOCS: PASS")
    print(f"sources_checked={len(sources)}")
    for warning in warnings:
        print(f"warning={warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
