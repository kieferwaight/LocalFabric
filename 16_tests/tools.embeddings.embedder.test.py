from __future__ import annotations

from pathlib import Path

from tools.embeddings.embedder import Embedder


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def embed(self, text: str, model: str | None = None) -> list[float]:
        self.calls.append((text, model))
        return [1.0, 2.0]


def test_embedder_delegates_execution_and_reuses_driver_cache(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    cache_path = tmp_path / "embedding-cache.json"
    embedder = Embedder(model="test-model", cache_path=cache_path, executor=executor)

    assert embedder.embed("hello") == [1.0, 2.0]
    embedder.flush_cache()

    reloaded = Embedder(model="test-model", cache_path=cache_path, executor=executor)
    assert reloaded.embed("hello") == [1.0, 2.0]
    assert executor.calls == [("hello", "test-model")]
