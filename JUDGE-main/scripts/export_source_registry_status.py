#!/usr/bin/env python3
"""Export a canonical source registry status summary for proof artifacts.

The summary is derived from merged source definitions rather than live runtime
state so release proof can validate fail-closed source controls deterministically
in CI and local proof runs.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion.automation_statuses import ENABLEABLE_STATUSES, RUNNABLE_STATUSES
from app.ingestion.source_adapters import ADAPTER_REGISTRY
from app.seed.source_registry import _merged_sources

_PARSER_SECRET_NAMES: dict[str, str] = {
    "canlii_api": "JTA_CANLII_API_KEY",
    "scc_lexum_api": "LEXUM_API_KEY",
}


def _required_secret_name(parser_key: str | None) -> str | None:
    if not parser_key:
        return None
    return _PARSER_SECRET_NAMES.get(parser_key)


def _secret_is_configured(secret_name: str | None) -> bool:
    if not secret_name:
        return True
    if secret_name == "JTA_CANLII_API_KEY":
        return bool(os.getenv("JTA_CANLII_API_KEY") or os.getenv("CANLII_API_KEY"))
    if secret_name == "LEXUM_API_KEY":
        return bool(os.getenv("JTA_LEXUM_API_KEY") or os.getenv("LEXUM_API_KEY"))
    return bool(os.getenv(secret_name))


def _can_enable(source_row: dict) -> tuple[bool, str | None]:
    if source_row["source_class"] != "machine_ingest":
        return False, "source_class_not_machine_ingest"
    if source_row["automation_status"] not in ENABLEABLE_STATUSES:
        return False, "automation_status_not_enableable"
    if not source_row["adapter_exists"]:
        return False, "adapter_missing"
    if not source_row["required_secret_configured"]:
        return False, "missing_secret"
    if not source_row["parser_version"]:
        return False, "missing_parser_version"
    if not source_row["allowed_domains"]:
        return False, "missing_allowed_domains"
    return True, None


def _source_row(source: dict) -> dict:
    parser_key = source.get("parser")
    secret_name = _required_secret_name(parser_key)
    source_id = source.get("id") or source.get("source_key")
    adapter_cls = ADAPTER_REGISTRY.get(parser_key) if parser_key else None
    adapter_name = adapter_cls.__name__ if adapter_cls else None
    automation_status = source.get("automation_status")
    source_class = source.get("source_class")
    source_row = {
        "source_id": source_id,
        "source_key": source.get("source_key"),
        "name": source.get("source_name") or source.get("source_key"),
        "jurisdiction": source.get("jurisdiction") or source.get("country") or "unknown",
        "source_class": source_class,
        "parser": parser_key,
        "parser_version": source.get("parser_version"),
        "allowed_domains": source.get("allowed_domains"),
        "automation_status": automation_status,
        "enabled": bool(source.get("enabled_default", False)),
        "is_machine_ingest": source_class == "machine_ingest",
        "adapter_name": adapter_name,
        "adapter_exists": adapter_name is not None,
        "required_secret_name": secret_name,
        "required_secret_configured": _secret_is_configured(secret_name),
        "can_run_when_active": automation_status in RUNNABLE_STATUSES,
        "requires_secret": secret_name is not None,
        "public_record_authority": source.get("public_record_authority"),
        "public_visibility_policy": {
            "requires_manual_review": bool(source.get("requires_manual_review", True)),
            "public_publish_default": bool(source.get("public_publish_default", False)),
        },
    }
    can_enable, reason = _can_enable(source_row)
    source_row["can_enable"] = can_enable
    source_row["cannot_enable_reason"] = reason
    return source_row


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    output_path = REPO_ROOT / "artifacts" / "proof" / "current" / "source_registry_status.json"
    if "--output" in args:
        output_path = Path(args[args.index("--output") + 1]).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    sources = [_source_row(source) for source in _merged_sources()]
    source_class_counts = Counter(source["source_class"] or "unset" for source in sources)
    automation_counts = Counter(source["automation_status"] or "unset" for source in sources)
    required_secret_counts = Counter(source["required_secret_name"] or "none" for source in sources)

    machine_ingest = [source for source in sources if source["is_machine_ingest"]]
    runnable = [source for source in sources if source["can_run_when_active"]]
    enableable = [source for source in sources if source["can_enable"]]

    payload = {
        "summary": {
            "total_sources": len(sources),
            "machine_ingest_sources": len(machine_ingest),
            "runnable_when_active_sources": len(runnable),
            "enableable_sources": len(enableable),
            "sources_requiring_secrets": len([s for s in sources if s["requires_secret"]]),
        },
        "counts_by_source_class": dict(sorted(source_class_counts.items())),
        "counts_by_automation_status": dict(sorted(automation_counts.items())),
        "counts_by_required_secret": dict(sorted(required_secret_counts.items())),
        "machine_ingest_ready_sources": [
            source["source_key"] for source in machine_ingest if source["can_run_when_active"]
        ],
        "sources_requiring_secret": [
            {
                "source_key": source["source_key"],
                "parser": source["parser"],
                "required_secret_name": source["required_secret_name"],
                "required_secret_configured": source["required_secret_configured"],
            }
            for source in sources
            if source["requires_secret"]
        ],
        "sources": sources,
    }

    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"SOURCE REGISTRY STATUS: PASS")
    print(f"output={output_path}")
    print(f"sources_checked={len(sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())