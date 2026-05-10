"""Tests for egress proxy wiring in source_fetcher."""

from __future__ import annotations

from contextlib import AbstractContextManager
from unittest.mock import MagicMock, patch

from app.services.source_fetcher import _build_fetch_opener, fetch_source


class _FakeHeaders:
    def get_content_type(self) -> str:
        return "text/plain"

    def items(self):
        return []


class _FakeResponse(AbstractContextManager):
    status = 200

    def __init__(self) -> None:
        self.headers = _FakeHeaders()

    def geturl(self) -> str:
        return "https://example.com/final"

    def read(self, _n: int) -> bytes:
        return b"ok"

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_fetch_opener_includes_proxy_handler_when_configured() -> None:
    with patch("app.services.source_fetcher.urllib.request.build_opener") as build_opener:
        _build_fetch_opener("http://proxy.local:8080")

    assert build_opener.called
    args = build_opener.call_args[0]
    assert any(type(arg).__name__ == "ProxyHandler" for arg in args)
    assert any(type(arg).__name__ == "_SSRFRedirectHandler" for arg in args)


def test_fetch_source_uses_proxy_config_for_runtime_requests(monkeypatch) -> None:
    monkeypatch.setenv("JTA_FETCH_EGRESS_PROXY", "http://proxy.local:8080")

    fake_opener = MagicMock()
    fake_opener.open.return_value = _FakeResponse()

    with (
        patch("app.services.source_fetcher._is_safe_url", return_value=(True, "")),
        patch("app.services.source_fetcher._build_fetch_opener", return_value=fake_opener) as build_opener,
    ):
        result = fetch_source("https://example.com/resource", store_snapshot=False)

    build_opener.assert_called_once_with("http://proxy.local:8080")
    assert result.error is None
    assert result.raw_content == b"ok"
