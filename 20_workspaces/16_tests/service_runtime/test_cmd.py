from __future__ import annotations

import importlib.util
from pathlib import Path

from harnesses.base import HarnessStatus


SCRIPT = Path(__file__).resolve().parents[2] / "10_service_runtime" / "cmd.py"
SPEC = importlib.util.spec_from_file_location("service_runtime_cmd", SCRIPT)
assert SPEC and SPEC.loader
CMD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CMD)


def test_run_action_delegates_lifecycle_to_harness(tmp_path: Path, monkeypatch) -> None:
    observed = {}

    class FakeHarness:
        def __init__(self, config):
            observed.update(config)

        def start(self):
            return HarnessStatus(name="docker:test", state="running", detail="started")

    service_dir = tmp_path / "service"
    service_dir.mkdir()
    (service_dir / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    monkeypatch.setattr(CMD, "DockerServiceHarness", FakeHarness)

    result = CMD._run_action("up", "postgres", service_dir, tmp_path / "data")

    assert result == 0
    assert observed["env"]["DATA_PATH"].endswith("/data")
