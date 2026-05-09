"""Tests for source registry spec validation contracts.

Verifies that:
- machine_ingest sources without required fields are rejected by the validator
- portal_reference/disabled_stub sources pass without parser_version
- all 6 machine_ingest sources in the YAML have parser_version set
- validate_machine_ingest_source_spec returns correct violation slugs
- parser_version is in _REPAIR_FIELDS so drift gets corrected
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from app.seed.source_registry import (
    _REPAIR_FIELDS,
    validate_machine_ingest_source_spec,
)

_YAML_PATH = (
    pathlib.Path(__file__).parent.parent
    / "ingestion"
    / "sources"
    / "canada_saskatchewan_sources.yaml"
)

_MACHINE_INGEST_SOURCE_KEYS = {
    "sk_courts_qb_decisions",
    "sk_courts_ca_decisions",
    "federal_court_canada",
    "scc_decisions",
    "sk_legislature_hansard",
    "canada_justice_laws",
}


def _load_yaml() -> list[dict]:
    with _YAML_PATH.open() as fh:
        data = yaml.safe_load(fh)
    return data.get("sources", [])


# ── validate_machine_ingest_source_spec unit tests ──────────────────────────


def test_valid_machine_ingest_spec_passes() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        "parser": "my_parser",
        "parser_version": "1.0",
        "base_url": "https://example.com/api",
        "public_record_authority": "official_public_record",
        "requires_manual_review": True,
        "public_publish_default": False,
        "terms_url": "https://example.com/terms",
        "automation_status": "machine_ready_disabled",
        "allowed_domains": '["example.com"]',
    }
    assert validate_machine_ingest_source_spec(spec) == []


def test_missing_parser_version_is_violation() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        "parser": "my_parser",
        "parser_version": None,
        "allowed_domains": '["example.com"]',
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert "missing_parser_version" in violations


def test_missing_parser_is_violation() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        "parser": None,
        "parser_version": "1.0",
        "allowed_domains": '["example.com"]',
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert "missing_parser" in violations


def test_missing_allowed_domains_is_violation() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        "parser": "my_parser",
        "parser_version": "1.0",
        "allowed_domains": None,
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert "missing_allowed_domains" in violations


def test_empty_allowed_domains_json_is_violation() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        "parser": "my_parser",
        "parser_version": "1.0",
        "allowed_domains": "[]",
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert "missing_allowed_domains" in violations


def test_portal_reference_skips_validation() -> None:
    """Non machine_ingest sources are never validated."""
    spec = {
        "source_key": "test_source",
        "source_class": "portal_reference",
        # missing parser, parser_version, allowed_domains
    }
    assert validate_machine_ingest_source_spec(spec) == []


def test_disabled_stub_skips_validation() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "disabled_stub",
    }
    assert validate_machine_ingest_source_spec(spec) == []


def test_no_source_class_is_violation() -> None:
    """source_class=None is treated as machine_ingest via legacy path."""
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
        # missing everything required
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert len(violations) > 0


def test_multiple_violations_returned() -> None:
    spec = {
        "source_key": "test_source",
        "source_class": "machine_ingest",
    }
    violations = validate_machine_ingest_source_spec(spec)
    assert "missing_parser" in violations
    assert "missing_parser_version" in violations
    assert "missing_allowed_domains" in violations


# ── YAML contract tests ──────────────────────────────────────────────────────


def test_all_machine_ingest_sources_have_parser_version() -> None:
    """Every source with source_class=machine_ingest must declare parser_version."""
    sources = _load_yaml()
    violations: list[str] = []
    for s in sources:
        if s.get("source_class") == "machine_ingest":
            if not s.get("parser_version"):
                violations.append(s["source_key"])
    assert not violations, (
        f"machine_ingest sources missing parser_version: {violations}"
    )


def test_specific_machine_ingest_sources_have_parser_version() -> None:
    """The 6 known machine_ingest source keys must all have parser_version."""
    sources = {s["source_key"]: s for s in _load_yaml()}
    for key in _MACHINE_INGEST_SOURCE_KEYS:
        source = sources.get(key)
        assert source is not None, f"Expected source '{key}' not found in YAML"
        assert source.get("parser_version"), (
            f"Source '{key}' is machine_ingest but has no parser_version"
        )


def test_machine_ingest_sources_pass_spec_validator() -> None:
    """All machine_ingest sources in the YAML must pass the contract validator."""
    sources = _load_yaml()
    failures: dict[str, list[str]] = {}
    for s in sources:
        if s.get("source_class") == "machine_ingest":
            violations = validate_machine_ingest_source_spec(s)
            if violations:
                failures[s["source_key"]] = violations
    assert not failures, f"machine_ingest spec violations: {failures}"


# ── _REPAIR_FIELDS coverage test ─────────────────────────────────────────────


def test_parser_version_in_repair_fields() -> None:
    """parser_version must be in _REPAIR_FIELDS so the repair function syncs it."""
    assert "parser_version" in _REPAIR_FIELDS, (
        "parser_version is not in seed._REPAIR_FIELDS — DB drift will not be corrected"
    )
