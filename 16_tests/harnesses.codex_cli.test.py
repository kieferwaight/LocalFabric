"""Contract tests for harnesses.codex_cli.CodexCliHarness."""

from __future__ import annotations

from typing import Any

import pytest

from harnesses.base import HarnessError
from harnesses.cli_common import CliError, CompletedRun
from harnesses.codex_cli import CodexCliHarness


class _FakeRun:
    def __init__(self, *, stdout: str = "ok") -> None:
        self.stdout = stdout
        self.calls: list[list[str]] = []

    def __call__(
        self, argv: list[str], *, timeout: float | None = None, **_: Any
    ) -> CompletedRun:
        self.calls.append(list(argv))
        return CompletedRun(returncode=0, stdout=self.stdout, stderr="")


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> tuple[CodexCliHarness, _FakeRun]:
    monkeypatch.setattr(
        "harnesses.codex_cli.harness.shutil.which",
        lambda name: f"/usr/local/bin/{name}",
    )
    fake = _FakeRun()
    monkeypatch.setattr("harnesses.codex_cli.harness.run_blocking", fake)
    return CodexCliHarness(), fake


def test_name_is_codex_cli() -> None:
    assert CodexCliHarness().name == "codex_cli"


def test_invoke_uses_exec_subcommand_and_sandbox(
    patched: tuple[CodexCliHarness, _FakeRun],
) -> None:
    h, fake = patched
    h.invoke({"prompt": "refactor this"})
    argv = fake.calls[0]
    # First positional after binary must be the non-interactive subcommand.
    assert argv[1] == "exec"
    assert "--skip-git-repo-check" in argv
    assert "--sandbox" in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert argv[-1] == "refactor this"


def test_invoke_attaches_images_with_image_flag(
    patched: tuple[CodexCliHarness, _FakeRun],
) -> None:
    h, fake = patched
    h.invoke({"prompt": "look", "images": ["/tmp/a.png", "/tmp/b.png"]})
    argv = fake.calls[0]
    # Each image gets its own --image flag.
    image_indices = [i for i, tok in enumerate(argv) if tok == "--image"]
    assert len(image_indices) == 2
    assert argv[image_indices[0] + 1] == "/tmp/a.png"
    assert argv[image_indices[1] + 1] == "/tmp/b.png"


def test_invoke_passes_model(patched: tuple[CodexCliHarness, _FakeRun]) -> None:
    h, fake = patched
    h.invoke({"prompt": "x", "model": "gpt-5-codex"})
    argv = fake.calls[0]
    assert argv[argv.index("--model") + 1] == "gpt-5-codex"


def test_invoke_wraps_cli_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnesses.codex_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/codex",
    )

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise CliError(returncode=1, stderr="bad", argv=["codex"])

    monkeypatch.setattr("harnesses.codex_cli.harness.run_blocking", boom)
    with pytest.raises(HarnessError, match="codex_cli invoke failed"):
        CodexCliHarness().invoke({"prompt": "x"})
