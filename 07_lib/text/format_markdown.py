from pathlib import Path
from harnesses.lmstudio import harness as lmstudio
from core.runtimes.markdown.frontmatter import parse as parse_frontmatter

PROMPT_PATH = Path(__file__).resolve().parents[2] / "12_prompts" / "tasks.format-markdown.md"


def load_prompt() -> str:
    return parse_frontmatter(
        PROMPT_PATH.read_text(encoding="utf-8"), source_path=str(PROMPT_PATH)
    ).body


def format_markdown_with_lmstudio(file_path: str, model: str = "qwen/qwen3.6-27b") -> str:
    # Read file content
    content = Path(file_path).read_text(encoding="utf-8")
    prompt_template = load_prompt()
    prompt = prompt_template.replace("{{markdown_content}}", content)

    harness = lmstudio.LMStudioHarness({
        "base_url": "http://localhost:1234/v1",
        "model": model,
        "api_key": "lm-studio"
    })
    response = harness.invoke({
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    })
    return response["choices"][0]["message"]["content"]
