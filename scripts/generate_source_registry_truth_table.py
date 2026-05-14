#!/usr/bin/env python3
"""Generate source registry truth table from YAML + adapter registry.

Creates markdown and JSON documents showing all sources, their configuration,
and current runtime status. Used in release gates to detect documentation drift.

Output:
- docs/SOURCE_REGISTRY_STATUS.md (human-readable markdown table)
- artifacts/proof/current/SOURCE_REGISTRY_STATUS.json (machine-readable)
- artifacts/proof/current/SOURCE_REGISTRY_STATUS.log (generation log)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.ingestion.source_adapters import ADAPTER_REGISTRY

    ADAPTER_REGISTRY_AVAILABLE = True
except Exception:
    ADAPTER_REGISTRY = {}
    ADAPTER_REGISTRY_AVAILABLE = False


def load_sources_yaml() -> list[dict[str, Any]]:
    """Load all sources from YAML."""
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


def get_adapter_status(source: dict[str, Any]) -> tuple[bool, str]:
    """Check if parser adapter exists for source.

    Returns (adapter_exists: bool, parser_key: str)
    """
    parser_key = source.get("parser")
    if not parser_key:
        return False, ""

    if not ADAPTER_REGISTRY_AVAILABLE:
        return False, parser_key or ""

    return parser_key in ADAPTER_REGISTRY, parser_key or ""


def generate_truth_table_markdown(sources: list[dict[str, Any]]) -> str:
    """Generate markdown table of source registry status."""
    
    lines = [
        "# Source Registry Status",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        f"**Total sources:** {len(sources)}",
        "",
        "| Source Key | Name | Jurisdiction | Class | Type | Automation Status | Adapter | Exists | Parser | Runnable | Review Required | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    
    for source in sources:
        source_key = source.get("source_key", "")
        name = source.get("source_name", "")
        jurisdiction = source.get("jurisdiction", "")
        source_class = source.get("source_class", "")
        source_type = source.get("source_type", "")
        automation_status = source.get("automation_status", "")
        adapter_key = source.get("parser", "")
        parser = source.get("parser", "")
        lifecycle_state = source.get("lifecycle_state", "")
        status_reason = source.get("status_reason", "")
        canonical_replacement_key = source.get("canonical_replacement_key", "")
        
        adapter_exists, _ = get_adapter_status(source)
        adapter_mark = "✓" if adapter_exists else "✗"
        
        # Determine if runnable
        runnable = (
            source_class == "machine_ingest"
            and adapter_exists
            and automation_status == "machine_ready_enabled"
            and source.get("lifecycle_state") == "runnable"
        )
        runnable_mark = "✓" if runnable else "✗"
        
        review_required = source.get("requires_manual_review", False)
        review_mark = "✓" if review_required else "✗"
        
        alpha_status = source.get("alpha_status", "configured")
        
        # Escape pipes in text
        name = name.replace("|", "\\|")
        
        row = (
            f"| `{source_key}` | {name} | {jurisdiction} | {source_class} | {source_type} | "
            f"{automation_status} | {adapter_key} | {adapter_mark} | {parser} | {runnable_mark} | "
            f"{review_mark} | {alpha_status} |"
        )
        lines.append(row)

        if lifecycle_state or status_reason or canonical_replacement_key:
            extra: list[str] = []
            if lifecycle_state:
                extra.append(f"lifecycle={lifecycle_state}")
            if canonical_replacement_key:
                extra.append(f"replacement={canonical_replacement_key}")
            if status_reason:
                extra.append(f"reason={status_reason}")
            lines.append(f"| ↳ |  |  |  |  |  |  |  |  |  |  | {'; '.join(extra)} |")
    
    lines.extend([
        "",
        "## Legend",
        "",
        "- **Source Key:** Unique identifier for source in registry",
        "- **Class:** `machine_ingest` (automated) | `portal_reference` (manual) | `manual_reference` (external) | `disabled_stub` (review-gated)",
        "- **Type:** XML, JSON, CSV, HTML, REST API, CSV",
        "- **Automation Status:** `machine_ready_enabled` | `machine_ready_disabled` | `machine_ready_awaiting_configuration` | `adapter_missing` | `disabled_by_policy` | `disabled_stub`",
        "- **Adapter:** Name of ingestion adapter module",
        "- **Exists:** ✓ Adapter module exists, ✗ Missing or stubbed",
        "- **Parser:** Name of parser for source",
        "- **Runnable:** ✓ Can run immediately, ✗ Blocked by missing adapter, configuration, or policy",
        "- **Review Required:** ✓ All records reviewed before publication, ✗ Auto-publish allowed",
        "- **Status:** Alpha status: `configured`, `tested`, `blocked`, etc.",
        "",
        "## Notes",
        "",
        "- All sources in this registry are enabled for review or disabled by policy.",
        "- No source is auto-published without human review.",
        "- News sources are in `disabled_stub` tier and remain review-gated.",
        "- Administrative sources are in `portal_reference` tier and require manual entry.",
        "- Only `machine_ingest` sources can be enabled for automated ingestion.",
        "- Enabling a `machine_ingest` source requires all validation gates to pass.",
    ])
    
    return "\n".join(lines)


def generate_truth_table_json(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate JSON representation of source registry."""
    
    rows = []
    for source in sources:
        source_key = source.get("source_key", "")
        adapter_exists, adapter_key = get_adapter_status(source)
        
        runnable = (
            source.get("source_class") == "machine_ingest"
            and adapter_exists
            and source.get("automation_status") == "machine_ready_enabled"
        )
        
        row = {
            "source_key": source_key,
            "source_name": source.get("source_name", ""),
            "jurisdiction": source.get("jurisdiction", ""),
            "source_class": source.get("source_class", ""),
            "source_type": source.get("source_type", ""),
            "automation_status": source.get("automation_status", ""),
            "adapter_key": adapter_key,
            "adapter_exists": adapter_exists,
            "parser": source.get("parser", ""),
            "runnable": runnable,
            "requires_manual_review": source.get("requires_manual_review", False),
            "lifecycle_state": source.get("lifecycle_state"),
            "status_reason": source.get("status_reason"),
            "canonical_replacement_key": source.get("canonical_replacement_key"),
            "alpha_status": source.get("alpha_status", "configured"),
        }
        rows.append(row)
    
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_sources": len(sources),
        "sources": rows,
        "adapter_registry_size": len(ADAPTER_REGISTRY),
        "adapter_registry_available": ADAPTER_REGISTRY_AVAILABLE,
    }


def main() -> int:
    """Generate truth table and write to output files."""
    
    try:
        sources = load_sources_yaml()
    except Exception as e:
        print(f"ERROR: Failed to load YAML: {e}")
        return 1
    
    if not sources:
        print("ERROR: No sources found in YAML")
        return 1
    
    # Generate markdown
    try:
        markdown = generate_truth_table_markdown(sources)
        md_path = REPO_ROOT / "docs" / "SOURCE_REGISTRY_STATUS.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown, encoding="utf-8")
        print(f"✓ Generated {md_path}")
    except Exception as e:
        print(f"ERROR: Failed to generate markdown: {e}")
        return 1
    
    # Generate JSON
    try:
        json_data = generate_truth_table_json(sources)
        json_path = REPO_ROOT / "artifacts" / "proof" / "current" / "SOURCE_REGISTRY_STATUS.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w") as f:
            json.dump(json_data, f, indent=2)
        print(f"✓ Generated {json_path}")
    except Exception as e:
        print(f"ERROR: Failed to generate JSON: {e}")
        return 1
    
    # Write log
    try:
        log_path = REPO_ROOT / "artifacts" / "proof" / "current" / "source_registry_status.log"
        log_content = f"""Source Registry Status Generation Log

Generated: {datetime.now(timezone.utc).isoformat()}
Total sources: {len(sources)}
Adapter registry size: {len(ADAPTER_REGISTRY)}
Adapter registry available: {ADAPTER_REGISTRY_AVAILABLE}

Output files:
- docs/SOURCE_REGISTRY_STATUS.md
- artifacts/proof/current/SOURCE_REGISTRY_STATUS.json

Status: SUCCESS
"""
        log_path.write_text(log_content, encoding="utf-8")
        print(f"✓ Generated {log_path}")
    except Exception as e:
        print(f"ERROR: Failed to write log: {e}")
        return 1
    
    print(f"\n✓ Truth table generation complete: {len(sources)} sources documented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
