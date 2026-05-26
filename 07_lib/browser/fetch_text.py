"""Fetch readable page text from a URL or a lightweight search result page."""

from __future__ import annotations

from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

TEXT_CAP = 8000
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def target_url(topic_or_url: str) -> tuple[str, str]:
    """Return the URL to retrieve and a human-readable source label."""
    if topic_or_url.startswith("http"):
        return topic_or_url, "url"
    return f"https://lite.duckduckgo.com/lite/?q={quote_plus(topic_or_url)}", "duckduckgo-lite"


def fetch_readable_text(topic_or_url: str) -> tuple[str, str, str]:
    """Retrieve and clean readable text for a URL or search topic."""
    url, source_label = target_url(topic_or_url)
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = "\n".join(chunk for chunk in chunks if chunk)[:TEXT_CAP]
    return clean_text, source_label, url
