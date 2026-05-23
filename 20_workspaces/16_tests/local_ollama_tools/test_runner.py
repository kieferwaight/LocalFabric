from mcp_layer.tools.local_tools import local_research_scaffold, run_local_tests

# Test 1: Local Ollama Research Scaffold
url = "https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md"
research_result = local_research_scaffold(url)
print("\n=== OLLAMA RESEARCH RESULT ===")
print(research_result)

# Test 2: Local Test Suite and Log Scrubber
print("\n=== TEST EXECUTOR RESULT ===")
test_result = run_local_tests("pytest")
print(test_result)
