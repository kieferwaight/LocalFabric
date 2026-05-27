"""Tests for lib.pdf.meta — page_count.

The function shells out to `pdfinfo`, so tests mock subprocess.run
to stay offline and deterministic.
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.pdf.meta import page_count

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_page_count_parses_pages_line() -> None:
    stdout = "Producer: pdfTeX\nPages: 12\nEncrypted: no\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ):
        result = page_count(Path("doc.pdf"))
    assert result == 12


def test_page_count_parses_single_page() -> None:
    stdout = "Pages: 1\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ):
        result = page_count(Path("single.pdf"))
    assert result == 1


def test_page_count_parses_large_count() -> None:
    stdout = "Pages: 999\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ):
        result = page_count(Path("big.pdf"))
    assert result == 999


# ---------------------------------------------------------------------------
# pdfinfo not available / error paths
# ---------------------------------------------------------------------------


def test_page_count_returns_none_on_nonzero_returncode() -> None:
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(
            args=["pdfinfo"], returncode=1, stdout="", stderr="not found"
        ),
    ):
        result = page_count(Path("missing.pdf"))
    assert result is None


def test_page_count_returns_none_when_no_pages_line() -> None:
    stdout = "Creator: Writer\nEncrypted: no\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ):
        result = page_count(Path("doc.pdf"))
    assert result is None


def test_page_count_returns_none_on_malformed_pages_value() -> None:
    stdout = "Pages: not_a_number\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ):
        result = page_count(Path("doc.pdf"))
    assert result is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_page_count_passes_path_string_to_pdfinfo() -> None:
    stdout = "Pages: 5\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ) as mock_run:
        page_count(Path("/some/path/doc.pdf"))
    call_args = mock_run.call_args[0][0]
    assert "/some/path/doc.pdf" in call_args


def test_page_count_uses_check_false() -> None:
    """subprocess.run must be called with check=False so nonzero exit doesn't raise."""
    stdout = "Pages: 3\n"
    with patch(
        "subprocess.run",
        return_value=CompletedProcess(args=["pdfinfo"], returncode=0, stdout=stdout, stderr=""),
    ) as mock_run:
        page_count(Path("doc.pdf"))
    call_kwargs = mock_run.call_args[1]
    assert call_kwargs.get("check") is False
