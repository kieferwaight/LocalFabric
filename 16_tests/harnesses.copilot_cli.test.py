"""Contract tests for harnesses.copilot_cli.CopilotCliHarness."""

from __future__ import annotations

from typing import Any

import pytest

from harnesses.base import HarnessError
from harnesses.cli_common import CliError, CompletedRun
from harnesses.copilot_cli import CopilotCliHarness


class _FakeRun:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(
        self, argv: list[str], *, timeout: float | None = None, **_: Any
    ) -> CompletedRun:
        self.calls.append(list(argv))
        return CompletedRun(returncode=0, stdout="ok", stderr="")


@pytest.fixture
def patched(monkeypatch: pytest.MonkeyPatch) -> tuple[CopilotCliHarness, _FakeRun]:
    monkeypatch.setattr(
        "harnesses.copilot_cli.harness.shutil.which",
        lambda name: f"/usr/local/bin/{name}",
    )
    fake = _FakeRun()
    monkeypatch.setattr("harnesses.copilot_cli.harness.run_blocking", fake)
    return CopilotCliHarness(), fake


def test_name_is_copilot_cli() -> None:
    assert CopilotCliHarness().name == "copilot_cli"


def test_invoke_requires_allow_all_tools_flag(
    patched: tuple[CopilotCliHarness, _FakeRun],
) -> None:
    h, fake = patched
    h.invoke({"prompt": "hi"})
    argv = fake.calls[0]
    # Per `copilot --help`, --allow-all-tools is required for non-interactive mode.
    assert "--allow-all-tools" in argv
    assert "--prompt" in argv
    assert argv[argv.index("--prompt") + 1] == "hi"


def test_invoke_attaches_images_with_attachment_flag(
    patched: tuple[CopilotCliHarness, _FakeRun],
) -> None:
    h, fake = patched
    h.invoke({"prompt": "look", "images": ["/tmp/a.png", "/tmp/b.png"]})
    argv = fake.calls[0]
    attachments = [i for i, tok in enumerate(argv) if tok == "--attachment"]
    assert len(attachments) == 2
    assert argv[attachments[0] + 1] == "/tmp/a.png"


def test_invoke_wraps_cli_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnesses.copilot_cli.harness.shutil.which",
        lambda name: "/usr/local/bin/copilot",
    )

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise CliError(returncode=2, stderr="nope", argv=["copilot"])

    monkeypatch.setattr("harnesses.copilot_cli.harness.run_blocking", boom)
    with pytest.raises(HarnessError, match="copilot_cli invoke failed"):
        CopilotCliHarness().invoke({"prompt": "hi"})
