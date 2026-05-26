import tempfile
from pathlib import Path
from lib.text.format_markdown import format_markdown_with_lmstudio

def test_format_markdown_with_lmstudio(monkeypatch):
    # Patch LMStudioHarness to avoid real API call
    class DummyHarness:
        def __init__(self, config): pass
        def invoke(self, request):
            return {"choices": [{"message": {"content": "# Formatted\n\nContent."}}]}
    monkeypatch.setattr("harnesses.lmstudio.harness.LMStudioHarness", DummyHarness)

    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write("#test\ncontent")
        tf.flush()
        result = format_markdown_with_lmstudio(tf.name)
        assert result.startswith("# Formatted")
    Path(tf.name).unlink()