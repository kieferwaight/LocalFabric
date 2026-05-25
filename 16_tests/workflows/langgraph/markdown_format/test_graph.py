import tempfile
from pathlib import Path
from workflows.langgraph.markdown_format.graph import run_markdown_format_workflow

def test_run_markdown_format_workflow(monkeypatch):
    # Patch format_markdown_with_lmstudio to avoid real API call
    import workflows.langgraph.markdown_format.nodes as nodes
    monkeypatch.setattr(nodes, "format_markdown_with_lmstudio", lambda file_path, model=None: "# Fixed\n\nContent.")

    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "a.md"
        file1.write_text("#bad\ncontent")
        outdir = Path(tmpdir) / "out"
        run_markdown_format_workflow([str(file1)], in_place=False, output_dir=str(outdir))
        out_file = outdir / "a.md"
        assert out_file.exists()
        assert out_file.read_text().startswith("# Fixed")

        # In-place
        file2 = Path(tmpdir) / "b.md"
        file2.write_text("#bad2\ncontent")
        run_markdown_format_workflow([str(file2)], in_place=True)
        assert file2.read_text().startswith("# Fixed")
