"""Proof tests for reviewed/public-only map route behavior contracts."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_public_map_route_redirects_to_map_v2() -> None:
    map_page = REPO_ROOT / "frontend" / "app" / "map" / "page.tsx"
    text = map_page.read_text(encoding="utf-8")
    assert "redirect(" in text
    assert "/map-v2" in text or "/map/v2" in text


def test_public_map_backend_requires_reviewed_public_filters() -> None:
    route_file = REPO_ROOT / "backend" / "app" / "api" / "routes" / "map.py"
    text = route_file.read_text(encoding="utf-8")

    assert "CrimeIncident.is_public.is_(True)" in text
    assert "CrimeIncident.review_status.in_(PUBLIC_REVIEW_STATUSES)" in text


def test_public_map_event_query_requires_public_reviewed_filters() -> None:
    serializer_file = REPO_ROOT / "backend" / "app" / "serializers" / "public.py"
    text = serializer_file.read_text(encoding="utf-8")

    assert "Event.public_visibility.is_(True)" in text
    assert "Event.review_status.in_(PUBLIC_REVIEW_STATUSES)" in text


def test_public_map_does_not_use_ai_only_or_memory_only_fields() -> None:
    map_workspace = REPO_ROOT / "frontend" / "app" / "map-v2" / "MapV2Workspace.tsx"
    text = map_workspace.read_text(encoding="utf-8").lower()

    assert "ai-only" not in text
    assert "memory-only" not in text
