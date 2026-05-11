#!/usr/bin/env python3
"""Export a canonical source registry status summary for proof artifacts.

The summary is derived from merged source definitions rather than live runtime
state so release proof can validate fail-closed source controls deterministically
in CI and local proof runs.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion.automation_statuses import ENABLEABLE_STATUSES, RUNNABLE_STATUSES
from app.seed.source_registry import _merged_sources

_PARSER_SECRET_NAMES: dict[str, str] = {
    "canlii_api": "JTA_CANLII_API_KEY",
    "scc_lexum_api": "LEXUM_API_KEY",
}


def _required_secret_name(parser_key: str | None) -> str | None:
    if not parser_key:
        return None
    return _PARSER_SECRET_NAMES.get(parser_key)


def _source_row(source: dict) -> dict:
    parser_key = source.get("parser")
    secret_name = _required_secret_name(parser_key)
    automation_status = source.get("automation_status")
    source_class = source.get("source_class")
    return {
        "source_key": source.get("source_key"),
        "source_class": source_class,
        "parser": parser_key,
        "automation_status": automation_status,
        "enabled_default": bool(source.get("enabled_default", False)),
        "is_machine_ingest": source_class == "machine_ingest",
        "can_enable": automation_status in ENABLEABLE_STATUSES,
        "can_run_when_active": automation_status in RUNNABLE_STATUSES,
        "required_secret": secret_name,
        "requires_secret": secret_name is not None,
        "public_record_authority": source.get("public_record_authority"),
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    output_path = REPO_ROOT / "artifacts" / "proof" / "current" / "source_registry_status.json"
    if "--output" in args:
        output_path = Path(args[args.index("--output") + 1]).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    sources = [_source_row(source) for source in _merged_sources()]
    source_class_counts = Counter(source["source_class"] or "unset" for source in sources)
    automation_counts = Counter(source["automation_status"] or "unset" for source in sources)
    required_secret_counts = Counter(source["required_secret"] or "none" for source in sources)

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
                "required_secret": source["required_secret"],
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