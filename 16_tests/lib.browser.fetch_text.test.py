"""Tests for lib.browser.fetch_text.

All network calls are mocked via unittest.mock.patch — no real HTTP.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from lib.browser.fetch_text import TEXT_CAP, fetch_readable_text, target_url

# ---------------------------------------------------------------------------
# target_url
# ---------------------------------------------------------------------------


def test_target_url_returns_url_unchanged_for_http() -> None:
    url, label = target_url("https://example.com/page")
    assert url == "https://example.com/page"
    assert label == "url"


def test_target_url_returns_url_unchanged_for_http_scheme() -> None:
    url, label = target_url("http://example.com")
    assert url == "http://example.com"
    assert label == "url"


def test_target_url_converts_topic_to_duckduckgo_search() -> None:
    url, label = target_url("python asyncio")
    assert "duckduckgo" in url
    assert "python" in url
    assert label == "duckduckgo-lite"


def test_target_url_url_encodes_special_chars() -> None:
    url, _ = target_url("hello world & stuff")
    # spaces and & must be encoded
    assert " " not in url
    assert "&" not in url.split("?", 1)[-1].replace("&q=", "")


# ---------------------------------------------------------------------------
# fetch_readable_text — happy path (mocked)
# ---------------------------------------------------------------------------


def _make_response(html: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


def test_fetch_readable_text_returns_three_values() -> None:
    html = "<html><body><p>Hello world</p></body></html>"
    with patch("requests.get", return_value=_make_response(html)):
        result = fetch_readable_text("https://example.com")
    assert len(result) == 3
    text, label, url = result
    assert isinstance(text, str)
    assert isinstance(label, str)
    assert isinstance(url, str)


def test_fetch_readable_text_strips_script_tags() -> None:
    html = "<html><body><p>Hello</p><script>alert('bad')</script></body></html>"
    with patch("requests.get", return_value=_make_response(html)):
        text, _, _ = fetch_readable_text("https://example.com")
    assert "alert" not in text


def test_fetch_readable_text_strips_style_tags() -> None:
    html = "<html><body><style>body{color:red}</style><p>visible</p></body></html>"
    with patch("requests.get", return_value=_make_response(html)):
        text, _, _ = fetch_readable_text("https://example.com")
    assert "body{color:red}" not in text
    assert "visible" in text


def test_fetch_readable_text_caps_at_text_cap() -> None:
    big_html = "<p>" + ("word " * 10000) + "</p>"
    with patch("requests.get", return_value=_make_response(big_html)):
        text, _, _ = fetch_readable_text("https://example.com")
    assert len(text) <= TEXT_CAP


def test_fetch_readable_text_label_is_url_for_http_input() -> None:
    with patch("requests.get", return_value=_make_response("<p>ok</p>")):
        _, label, _ = fetch_readable_text("https://example.com")
    assert label == "url"


def test_fetch_readable_text_label_is_duckduckgo_for_topic() -> None:
    with patch("requests.get", return_value=_make_response("<p>results</p>")):
        _, label, _ = fetch_readable_text("some search topic")
    assert label == "duckduckgo-lite"


# ---------------------------------------------------------------------------
# fetch_readable_text — error paths
# ---------------------------------------------------------------------------


def test_fetch_readable_text_propagates_http_error() -> None:
    import requests as req_module

    with patch(
        "requests.get",
        side_effect=req_module.exceptions.ConnectionError("refused"),
    ):
        with pytest.raises(req_module.exceptions.ConnectionError):
            fetch_readable_text("https://example.com")


def test_fetch_readable_text_raises_for_non_200_status() -> None:
    import requests as req_module

    resp = _make_response("<p>not found</p>", status_code=404)
    resp.raise_for_status.side_effect = req_module.exceptions.HTTPError("404")
    with patch("requests.get", return_value=resp):
        with pytest.raises(req_module.exceptions.HTTPError):
            fetch_readable_text("https://example.com/missing")


# ---------------------------------------------------------------------------
# fetch_readable_text — empty content edge case
# ---------------------------------------------------------------------------


def test_fetch_readable_text_empty_page_returns_empty_string() -> None:
    with patch("requests.get", return_value=_make_response("<html><body></body></html>")):
        text, _, _ = fetch_readable_text("https://example.com")
    assert isinstance(text, str)
    # May be empty — no crash
