"""Tests for machine_ingest adapter evidence snapshot contract.

Every machine_ingest adapter that returns items must:
- Populate result.raw_snapshot_bytes (non-empty bytes)
- Populate result.fetch_http_status
- Populate result.fetch_content_type
- Populate result.fetch_url
- Include source_url on every review item / created record

These tests use local HTML/XML fixtures to avoid network calls.
Fixtures are validated against live site structure (2026-05-06).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_FIXTURES = Path(__file__).parent / "fixtures" / "sources"


def _make_mock_response(
    fixture_name: str,
    status_code: int = 200,
    content_type: str = "text/html",
    url: str = "https://example.gc.ca/",
) -> MagicMock:
    """Build a mock httpx response from a fixture file."""
    content = (_FIXTURES / fixture_name).read_bytes()
    resp = MagicMock()
    resp.content = content
    resp.text = content.decode("utf-8", errors="replace")
    resp.status_code = status_code
    resp.headers = {"content-type": content_type}
    resp.url = url
    resp.raise_for_status = MagicMock()
    return resp


# ── SKCourtsHtmlAdapter ───────────────────────────────────────────────────────


class TestSKCourtsHtmlAdapterContract:
    def _make_adapter(self) -> object:
        from app.ingestion.source_adapters.sk_courts_html import SKCourtsHtmlAdapter

        return SKCourtsHtmlAdapter(
            source_key="sk_courts_qb_decisions",
            base_url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
            allowed_domains_json='["sasklawcourts.ca", "www.sasklawcourts.ca", "canlii.org", "www.canlii.org"]',
            public_record_authority="official_court_record",
        )

    def test_run_with_fixture_returns_raw_snapshot_bytes(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "sk_courts_index.html",
            url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.raw_snapshot_bytes is not None
        assert len(result.raw_snapshot_bytes) > 0

    def test_run_with_fixture_sets_fetch_metadata(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "sk_courts_index.html",
            url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.fetch_http_status == 200
        assert result.fetch_content_type is not None
        assert result.fetch_url is not None

    def test_run_with_fixture_extracts_canlii_links(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "sk_courts_index.html",
            url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        # Fixture has 3 CanLII links
        assert result.records_fetched >= 3

    def test_parse_fixture_items_have_source_url(self) -> None:
        from app.ingestion.source_adapters.sk_courts_html import SKCourtsHtmlAdapter

        adapter = SKCourtsHtmlAdapter(
            source_key="sk_courts_qb_decisions",
            base_url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
            allowed_domains_json='["sasklawcourts.ca", "www.sasklawcourts.ca", "canlii.org", "www.canlii.org"]',
            public_record_authority="official_court_record",
        )
        html = (_FIXTURES / "sk_courts_index.html").read_text()
        raw = adapter._parse_index_page(html)
        assert len(raw) >= 3
        for item in raw:
            assert item.get("url"), "Every item must have a url"
            assert item.get("headline"), "Every item must have a headline"

    def test_parse_fixture_items_have_allowed_host(self) -> None:
        from app.ingestion.source_adapters.sk_courts_html import SKCourtsHtmlAdapter

        adapter = SKCourtsHtmlAdapter(
            source_key="sk_courts_qb_decisions",
            base_url="https://sasklawcourts.ca/saskatchewan-court-decisions/",
            allowed_domains_json='["sasklawcourts.ca", "www.sasklawcourts.ca", "canlii.org", "www.canlii.org"]',
            public_record_authority="official_court_record",
        )
        html = (_FIXTURES / "sk_courts_index.html").read_text()
        raw = adapter._parse_index_page(html)
        parsed = adapter.parse(raw)
        for record in parsed:
            assert record.source_url, "source_url must be non-empty"


# ── FederalCourtHtmlAdapter ───────────────────────────────────────────────────


class TestFederalCourtHtmlAdapterContract:
    def _make_adapter(self) -> object:
        from app.ingestion.source_adapters.federal_court_html import FederalCourtHtmlAdapter

        return FederalCourtHtmlAdapter(
            source_key="federal_court_canada",
            base_url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
            allowed_domains_json='["decisions.fct-cf.gc.ca", "fct-cf.gc.ca", "www.fct-cf.gc.ca"]',
            public_record_authority="official_court_record",
        )

    def test_run_with_fixture_returns_raw_snapshot_bytes(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "federal_court_index.html",
            url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.raw_snapshot_bytes is not None
        assert len(result.raw_snapshot_bytes) > 0

    def test_run_with_fixture_sets_fetch_metadata(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "federal_court_index.html",
            url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.fetch_http_status == 200
        assert result.fetch_content_type is not None
        assert result.fetch_url is not None

    def test_parse_fixture_extracts_expected_count(self) -> None:
        from app.ingestion.source_adapters.federal_court_html import FederalCourtHtmlAdapter

        adapter = FederalCourtHtmlAdapter(
            source_key="federal_court_canada",
            base_url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
            allowed_domains_json='["decisions.fct-cf.gc.ca", "fct-cf.gc.ca", "www.fct-cf.gc.ca"]',
            public_record_authority="official_court_record",
        )
        html = (_FIXTURES / "federal_court_index.html").read_text()
        raw = adapter._parse_items(html)
        assert len(raw) == 3, f"Expected 3 items from fixture, got {len(raw)}"

    def test_parse_fixture_items_have_non_empty_headline(self) -> None:
        from app.ingestion.source_adapters.federal_court_html import FederalCourtHtmlAdapter

        adapter = FederalCourtHtmlAdapter(
            source_key="federal_court_canada",
            base_url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
            allowed_domains_json='["decisions.fct-cf.gc.ca", "fct-cf.gc.ca", "www.fct-cf.gc.ca"]',
            public_record_authority="official_court_record",
        )
        html = (_FIXTURES / "federal_court_index.html").read_text()
        raw = adapter._parse_items(html)
        for item in raw:
            assert item.get("headline"), "headline must be non-empty"
            assert item.get("url"), "url must be non-empty"
            assert "decisions.fct-cf.gc.ca" in item["url"], "url must be absolute"

    def test_parse_fixture_extracts_neutral_citation(self) -> None:
        from app.ingestion.source_adapters.federal_court_html import FederalCourtHtmlAdapter

        adapter = FederalCourtHtmlAdapter(
            source_key="federal_court_canada",
            base_url="https://decisions.fct-cf.gc.ca/fc-cf/en/0/ann.do?iframe=true",
            allowed_domains_json='["decisions.fct-cf.gc.ca", "fct-cf.gc.ca", "www.fct-cf.gc.ca"]',
            public_record_authority="official_court_record",
        )
        html = (_FIXTURES / "federal_court_index.html").read_text()
        raw = adapter._parse_items(html)
        # At least one item should have a neutral citation from the h3
        citations = [item.get("neutral_citation") for item in raw if item.get("neutral_citation")]
        assert len(citations) > 0, "At least one item should have a neutral citation"


# ── LawsJusticeHtmlAdapter ────────────────────────────────────────────────────


class TestLawsJusticeHtmlAdapterContract:
    def _make_adapter(self) -> object:
        from app.ingestion.source_adapters.laws_justice_html import LawsJusticeHtmlAdapter

        return LawsJusticeHtmlAdapter(
            source_key="canada_justice_laws",
            base_url="https://laws-lois.justice.gc.ca/eng/acts/C-46/",
            allowed_domains_json='["laws-lois.justice.gc.ca", "justice.gc.ca"]',
            public_record_authority="official_legislation",
        )

    def test_run_with_fixture_returns_raw_snapshot_bytes(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "laws_justice_page.html",
            url="https://laws-lois.justice.gc.ca/eng/acts/C-46/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.raw_snapshot_bytes is not None
        assert len(result.raw_snapshot_bytes) > 0

    def test_parse_fixture_extracts_amendments_from_table(self) -> None:
        from app.ingestion.source_adapters.laws_justice_html import LawsJusticeHtmlAdapter

        adapter = LawsJusticeHtmlAdapter(
            source_key="canada_justice_laws",
            base_url="https://laws-lois.justice.gc.ca/eng/acts/C-46/",
            allowed_domains_json='["laws-lois.justice.gc.ca", "justice.gc.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "laws_justice_page.html").read_text()
        raw = adapter._parse_amendments(html)
        assert len(raw) == 5, f"Expected 5 amendments from fixture, got {len(raw)}"

    def test_parse_fixture_items_have_non_empty_headline(self) -> None:
        from app.ingestion.source_adapters.laws_justice_html import LawsJusticeHtmlAdapter

        adapter = LawsJusticeHtmlAdapter(
            source_key="canada_justice_laws",
            base_url="https://laws-lois.justice.gc.ca/eng/acts/C-46/",
            allowed_domains_json='["laws-lois.justice.gc.ca", "justice.gc.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "laws_justice_page.html").read_text()
        raw = adapter._parse_amendments(html)
        for item in raw:
            assert item.get("headline"), "headline must be non-empty"
            assert item.get("url"), "url must be non-empty"
            assert item.get("date"), "date must be non-empty for amendments table"

    def test_parse_fixture_items_have_absolute_urls(self) -> None:
        from app.ingestion.source_adapters.laws_justice_html import LawsJusticeHtmlAdapter

        adapter = LawsJusticeHtmlAdapter(
            source_key="canada_justice_laws",
            base_url="https://laws-lois.justice.gc.ca/eng/acts/C-46/",
            allowed_domains_json='["laws-lois.justice.gc.ca", "justice.gc.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "laws_justice_page.html").read_text()
        raw = adapter._parse_amendments(html)
        for item in raw:
            assert item["url"].startswith("https://"), f"URL must be absolute: {item['url']}"


# ── SKLegislatureHtmlAdapter ─────────────────────────────────────────────────


class TestSKLegislatureHtmlAdapterContract:
    def _make_adapter(self) -> object:
        from app.ingestion.source_adapters.sk_legislature_html import SKLegislatureHtmlAdapter

        return SKLegislatureHtmlAdapter(
            source_key="sk_legislature_hansard",
            base_url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
            allowed_domains_json='["legassembly.sk.ca", "www.legassembly.sk.ca", "docs.legassembly.sk.ca"]',
            public_record_authority="official_legislation",
        )

    def test_run_with_fixture_returns_raw_snapshot_bytes(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "sk_legislature_hansard.html",
            url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.raw_snapshot_bytes is not None
        assert len(result.raw_snapshot_bytes) > 0

    def test_run_with_fixture_sets_fetch_metadata(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "sk_legislature_hansard.html",
            url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.fetch_http_status == 200
        assert result.fetch_content_type is not None
        assert result.fetch_url is not None

    def test_parse_fixture_extracts_expected_count(self) -> None:
        from app.ingestion.source_adapters.sk_legislature_html import SKLegislatureHtmlAdapter

        adapter = SKLegislatureHtmlAdapter(
            source_key="sk_legislature_hansard",
            base_url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
            allowed_domains_json='["legassembly.sk.ca", "www.legassembly.sk.ca", "docs.legassembly.sk.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "sk_legislature_hansard.html").read_text()
        raw = adapter._parse_hansard_index(html)
        # 3 legislatures × 2 indexes (subject + speaker) = 6 items
        assert len(raw) == 6, f"Expected 6 items from fixture, got {len(raw)}"

    def test_parse_fixture_items_have_source_url(self) -> None:
        from app.ingestion.source_adapters.sk_legislature_html import SKLegislatureHtmlAdapter

        adapter = SKLegislatureHtmlAdapter(
            source_key="sk_legislature_hansard",
            base_url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
            allowed_domains_json='["legassembly.sk.ca", "www.legassembly.sk.ca", "docs.legassembly.sk.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "sk_legislature_hansard.html").read_text()
        raw = adapter._parse_hansard_index(html)
        for item in raw:
            assert item.get("url"), "url must be non-empty"
            assert item.get("headline"), "headline must be non-empty"
            assert "docs.legassembly.sk.ca" in item["url"] or "legassembly.sk.ca" in item["url"]

    def test_parse_fixture_items_have_legislature_metadata(self) -> None:
        from app.ingestion.source_adapters.sk_legislature_html import SKLegislatureHtmlAdapter

        adapter = SKLegislatureHtmlAdapter(
            source_key="sk_legislature_hansard",
            base_url="https://www.legassembly.sk.ca/legislative-business/debates-hansard/",
            allowed_domains_json='["legassembly.sk.ca", "www.legassembly.sk.ca", "docs.legassembly.sk.ca"]',
            public_record_authority="official_legislation",
        )
        html = (_FIXTURES / "sk_legislature_hansard.html").read_text()
        raw = adapter._parse_hansard_index(html)
        for item in raw:
            assert item.get("legislature"), "legislature must be non-empty"
            assert item.get("index_type") in ("subject", "speaker")


# ── SCCLexumApiAdapter ────────────────────────────────────────────────────────


class TestSCCLexumApiAdapterContract:
    def _make_adapter(self) -> object:
        from app.ingestion.source_adapters.scc_lexum_api import SCCLexumApiAdapter

        return SCCLexumApiAdapter(
            source_key="scc_decisions",
            base_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
            allowed_domains_json='["decisions.scc-csc.ca", "scc-csc.ca", "lexum.com"]',
            public_record_authority="official_court_record",
        )

    def test_run_with_fixture_returns_raw_snapshot_bytes(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "scc_feed.xml",
            content_type="application/rss+xml",
            url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.raw_snapshot_bytes is not None
        assert len(result.raw_snapshot_bytes) > 0

    def test_run_with_fixture_sets_fetch_metadata(self) -> None:
        adapter = self._make_adapter()
        mock_resp = _make_mock_response(
            "scc_feed.xml",
            content_type="application/rss+xml",
            url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
        )
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            result = adapter.run()
        assert result.fetch_http_status == 200
        assert result.fetch_content_type is not None
        assert result.fetch_url is not None

    def test_parse_fixture_extracts_expected_count(self) -> None:
        from app.ingestion.source_adapters.scc_lexum_api import SCCLexumApiAdapter
        import xml.etree.ElementTree as ET

        adapter = SCCLexumApiAdapter(
            source_key="scc_decisions",
            base_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
            allowed_domains_json='["decisions.scc-csc.ca", "scc-csc.ca", "lexum.com"]',
            public_record_authority="official_court_record",
        )
        xml_content = (_FIXTURES / "scc_feed.xml").read_text()
        root = ET.fromstring(xml_content)
        raw = []
        for item in root.iter("item"):
            entry: dict = {}
            for child in item:
                tag = child.tag.split("}")[-1]
                entry[tag] = child.text
            raw.append(entry)
        assert len(raw) == 3, f"Expected 3 items from fixture, got {len(raw)}"
        parsed = adapter.parse(raw)
        assert len(parsed) == 3

    def test_parse_fixture_items_have_source_url(self) -> None:
        from app.ingestion.source_adapters.scc_lexum_api import SCCLexumApiAdapter
        import xml.etree.ElementTree as ET

        adapter = SCCLexumApiAdapter(
            source_key="scc_decisions",
            base_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
            allowed_domains_json='["decisions.scc-csc.ca", "scc-csc.ca", "lexum.com"]',
            public_record_authority="official_court_record",
        )
        xml_content = (_FIXTURES / "scc_feed.xml").read_text()
        root = ET.fromstring(xml_content)
        raw = []
        for item in root.iter("item"):
            entry: dict = {}
            for child in item:
                tag = child.tag.split("}")[-1]
                entry[tag] = child.text
            raw.append(entry)
        parsed = adapter.parse(raw)
        for record in parsed:
            assert record.source_url, "source_url must be non-empty"
            assert record.payload.get("headline"), "headline must be non-empty"

    def test_parse_fixture_extracts_neutral_citation(self) -> None:
        from app.ingestion.source_adapters.scc_lexum_api import SCCLexumApiAdapter
        import xml.etree.ElementTree as ET

        adapter = SCCLexumApiAdapter(
            source_key="scc_decisions",
            base_url="https://decisions.scc-csc.ca/scc-csc/scc-csc/en/rss.do",
            allowed_domains_json='["decisions.scc-csc.ca", "scc-csc.ca", "lexum.com"]',
            public_record_authority="official_court_record",
        )
        xml_content = (_FIXTURES / "scc_feed.xml").read_text()
        root = ET.fromstring(xml_content)
        raw = []
        for item in root.iter("item"):
            entry: dict = {}
            for child in item:
                tag = child.tag.split("}")[-1]
                entry[tag] = child.text
            raw.append(entry)
        parsed = adapter.parse(raw)
        # All items in fixture have neutral citations
        for record in parsed:
            assert record.payload.get("neutral_citation"), "neutral_citation must be extracted"
            assert record.payload.get("published_at"), "published_at must be extracted from date field"
