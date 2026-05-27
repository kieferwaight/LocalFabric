"""Contract tests for harnesses.gemini_cli.GeminiCliHarness."""

from __future__ import annotations

from typing import Any

import pytest

from harnesses.base import HarnessError, HarnessStatus
from harnesses.cli_common import CliError, CompletedRun
from harnesses.gemini_cli import GeminiCliHarness


class _FakeRun:
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
def patched_harness(monkeypatch: pytest.MonkeyPatch) -> tuple[GeminiCliHarness, _FakeRun]:
    monkeypatch.setattr(
        "harnesses.gemini_cli.harness.shutil.which",
        lambda name: f"/usr/local/bin/{name}",
    )
    fake = _FakeRun(stdout="response\n")
    monkeypatch.setattr("harnesses.gemini_cli.harness.run_blocking", fake)
    return GeminiCliHarness(), fake


def test_name_is_gemini_cli() -> None:
    assert GeminiCliHarness().name == "gemini_cli"


def test_invoke_includes_non_interactive_flags(
    patched_harness: tuple[GeminiCliHarness, _FakeRun],
) -> None:
    h, fake = patched_harness
    h.invoke({"prompt": "hi"})
    argv = fake.calls[0]
    assert "--skip-trust" in argv
    assert "--yolo" in argv
    assert "--prompt" in argv
    assert argv[argv.index("--prompt") + 1] == "hi"


def test_invoke_passes_model_flag(patched_harness: tuple[GeminiCliHarness, _FakeRun]) -> None:
    h, fake = patched_harness
    h.invoke({"prompt": "hi", "model": "gemini-1.5-pro"})
    argv = fake.calls[0]
    assert argv[argv.index("--model") + 1] == "gemini-1.5-pro"


def test_invoke_splices_image_path_into_prompt(
    patched_harness: tuple[GeminiCliHarness, _FakeRun],
) -> None:
    h, fake = patched_harness
    h.invoke({"prompt": "describe", "images": ["/tmp/with space.png"]})
    argv = fake.calls[0]
    prompt_arg = argv[argv.index("--prompt") + 1]
    # The path is shlex-escaped and appended to the prompt body.
    assert "describe" in prompt_arg
    assert "with space.png" in prompt_arg


def test_health_calls_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnesses.gemini_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/gemini",
    )
    fake = _FakeRun(stdout="gemini 0.1\n")
    monkeypatch.setattr("harnesses.gemini_cli.harness.run_blocking", fake)
    snap = GeminiCliHarness().health()
    assert isinstance(snap, HarnessStatus)
    assert snap.state == "ready"
    assert fake.calls == [["/usr/local/bin/gemini", "--version"]]


def test_invoke_wraps_cli_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnesses.gemini_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/gemini",
    )

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise CliError(returncode=2, stderr="auth failed", argv=["gemini"])

    monkeypatch.setattr("harnesses.gemini_cli.harness.run_blocking", boom)
    with pytest.raises(HarnessError, match="gemini_cli invoke failed"):
        GeminiCliHarness().invoke({"prompt": "hi"})
