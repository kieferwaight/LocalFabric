import pytest

from mcp_layer.tools.local_tools import _pick_ollama_model, local_research_scaffold, run_local_tests


def test_run_local_tests_success():
    result = run_local_tests("echo hello")
    assert result.startswith("SUCCESS")
    assert "hello" in result


def test_run_local_tests_failure_exit_code():
    result = run_local_tests("exit 1")
    assert "FAILURE" in result
    assert "Exit Code: 1" in result


def test_run_local_tests_timeout():
    result = run_local_tests("sleep 35")
    assert "timed out" in result.lower()


def test_research_scaffold_topic_fallback_no_error():
    # Topic (not URL) used to return an error; now it must fall back to DuckDuckGo lite.
    result = local_research_scaffold("not_a_url")
    assert not result.startswith("Error:")
    assert "Please provide a valid URL" not in result


def test_research_scaffold_url_fetch():
    url = "https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md"
    result = local_research_scaffold(url)
    assert "Local Scraper Failed" not in result
    assert len(result) > 100


@pytest.mark.xfail(
    _pick_ollama_model() is None,
    reason="Ollama not reachable or no models pulled",
    strict=False,
)
def test_ollama_summary_runs():
    url = "https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md"
    result = local_research_scaffold(url)
    assert result.startswith("[model:")
