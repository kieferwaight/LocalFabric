"""Contract tests for harnesses.claude_cli.ClaudeCliHarness.

Patches ``run_blocking``/``stream_pty`` at the harness's module
namespace so no real subprocess is spawned. The assertions focus on
argv composition (non-interactive flags, model, image attachment) and
the lifecycle/health behavior.
"""

from __future__ import annotations

from typing import Any

import pytest

from harnesses.base import HarnessError, HarnessStatus
from harnesses.cli_common import CliError, CompletedRun
from harnesses.claude_cli import ClaudeCliHarness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeRun:
    """Drop-in replacement for ``run_blocking`` that captures argv."""

    def __init__(self, *, stdout: str = "ok", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(
        self, argv: list[str], *, timeout: float | None = None, **_: Any
    ) -> CompletedRun:
        self.calls.append(list(argv))
        if self.returncode != 0:
            raise CliError(returncode=self.returncode, stderr=self.stderr, argv=argv)
        return CompletedRun(returncode=0, stdout=self.stdout, stderr=self.stderr)


@pytest.fixture
def patched_harness(monkeypatch: pytest.MonkeyPatch) -> tuple[ClaudeCliHarness, _FakeRun]:
    monkeypatch.setattr(
        "harnesses.claude_cli.harness.shutil.which",
        lambda name: f"/usr/local/bin/{name}",
    )
    fake = _FakeRun(stdout="response\n")
    monkeypatch.setattr("harnesses.claude_cli.harness.run_blocking", fake)
    return ClaudeCliHarness(), fake


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_name_is_claude_cli() -> None:
    assert ClaudeCliHarness().name == "claude_cli"


def test_default_timeout() -> None:
    assert ClaudeCliHarness().timeout == 120.0


# ---------------------------------------------------------------------------
# Binary resolution
# ---------------------------------------------------------------------------


def test_resolve_binary_uses_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnesses.claude_cli.harness.shutil.which",
        lambda name: "/opt/bin/claude",
    )
    h = ClaudeCliHarness()
    assert h._resolve_binary() == "/opt/bin/claude"


def test_resolve_binary_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("harnesses.claude_cli.harness.shutil.which", lambda name: None)
    h = ClaudeCliHarness()
    with pytest.raises(HarnessError, match="could not locate"):
        h._resolve_binary()


# ---------------------------------------------------------------------------
# argv shape
# ---------------------------------------------------------------------------


def test_invoke_includes_non_interactive_flags(
    patched_harness: tuple[ClaudeCliHarness, _FakeRun],
) -> None:
    h, fake = patched_harness
    h.invoke({"prompt": "hi"})
    argv = fake.calls[0]
    assert "--print" in argv
    assert "--permission-mode" in argv
    assert argv[argv.index("--permission-mode") + 1] == "bypassPermissions"
    assert argv[-1] == "hi"


def test_invoke_passes_model_flag(patched_harness: tuple[ClaudeCliHarness, _FakeRun]) -> None:
    h, fake = patched_harness
    h.invoke({"prompt": "hi", "model": "claude-opus-4-7"})
    argv = fake.calls[0]
    assert argv[argv.index("--model") + 1] == "claude-opus-4-7"


def test_invoke_attaches_images_as_mentions_and_add_dir(
    patched_harness: tuple[ClaudeCliHarness, _FakeRun],
    tmp_path: Any,
) -> None:
    h, fake = patched_harness
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG\r\n")
    h.invoke({"prompt": "describe", "images": [str(img)]})
    argv = fake.calls[0]
    # The image parent dir should appear in an --add-dir flag.
    assert "--add-dir" in argv
    assert str(tmp_path) in argv
    # The prompt body (last positional) should carry the @<path> mention.
    assert f"@{img}" in argv[-1]


def test_add_dir_is_followed_by_another_flag_not_the_prompt(
    patched_harness: tuple[ClaudeCliHarness, _FakeRun],
    tmp_path: Any,
) -> None:
    """``--add-dir`` is variadic — the token after its value must be another
    ``--flag`` or commander.js will swallow the prompt as a directory.
    """
    h, fake = patched_harness
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG\r\n")
    h.invoke({"prompt": "describe", "images": [str(img)]})
    argv = fake.calls[0]
    add_dir_idx = argv.index("--add-dir")
    # idx+1 is the directory; idx+2 must be a flag-looking token, never a
    # bare positional like the prompt body.
    next_token = argv[add_dir_idx + 2]
    assert next_token.startswith("--"), (
        f"argv[{add_dir_idx + 2}]={next_token!r} would be eaten by --add-dir's "
        f"variadic. Full argv: {argv}"
    )


def test_invoke_returns_expected_keys(
    patched_harness: tuple[ClaudeCliHarness, _FakeRun],
) -> None:
    h, _ = patched_harness
    result = h.invoke({"prompt": "hi"})
    assert set(result.keys()) >= {"id", "model", "text", "returncode"}
    assert result["text"] == "response\n"


# ---------------------------------------------------------------------------
# Error wrapping
# ---------------------------------------------------------------------------


def test_invoke_wraps_cli_error_in_harness_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "harnesses.claude_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/claude",
    )

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise CliError(returncode=1, stderr="rate limited", argv=["claude"])

    monkeypatch.setattr("harnesses.claude_cli.harness.run_blocking", boom)
    h = ClaudeCliHarness()
    with pytest.raises(HarnessError, match="claude_cli invoke failed"):
        h.invoke({"prompt": "hi"})


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def test_health_calls_version_not_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "harnesses.claude_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/claude",
    )
    fake = _FakeRun(stdout="claude 1.0\n")
    monkeypatch.setattr("harnesses.claude_cli.harness.run_blocking", fake)
    h = ClaudeCliHarness()
    snap = h.health()
    assert isinstance(snap, HarnessStatus)
    assert snap.state == "ready"
    # The only subprocess call must be `--version`, never a real prompt.
    assert fake.calls == [["/usr/local/bin/claude", "--version"]]


def test_health_returns_error_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("harnesses.claude_cli.harness.shutil.which", lambda name: None)
    snap = ClaudeCliHarness().health()
    assert snap.state == "error"
    assert "could not locate" in snap.detail
