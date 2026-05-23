from __future__ import annotations

import json
from pathlib import Path

from drivers.file import copy_asset, write_json_artifact


def test_artifact_driver_copies_and_writes_nested_targets(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")
    copied = copy_asset(source, tmp_path / "inputs" / "copy.txt")
    report = write_json_artifact(tmp_path / "reports" / "item.json", {"ok": True})

    assert copied.read_text(encoding="utf-8") == "payload"
    assert json.loads(report.read_text(encoding="utf-8")) == {"ok": True}
