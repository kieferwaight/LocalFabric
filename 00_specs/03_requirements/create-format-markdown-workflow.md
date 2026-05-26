---
model: qwen/qwen3.6-27b
provider: lmstudio
endpoint: http://localhost:1234/v1
prompt_path: 12_prompts/tasks.spec-promotion.requirements.md
prompt_sha256: 29953859f29d53befb6e5e0e2e446563cdc00e7e597945f8be16b10280772175
promoted_at: '2026-05-23T21:40:17Z'
---

# Requirements — notebook-format-markdown-test

## Functional requirements

**F1: Prompt Artifact Loading**  
The notebook must load `12_prompts/tasks.format-markdown.md` using the standardized prompt registry/loader from `02_core`, treating it as an immutable input artifact without inline templating or fallback logic. Resolves research Q1.

**F2: LM Studio API Communication**  
All model requests must route through the existing OpenAI-compatible driver in `08_drivers` (or `03_adapters`), initialized via core configuration patterns rather than direct HTTP calls or raw `requests` usage. Resolves research Q2.

**F3: Context Window Validation**  
A pre-flight token counter must estimate input length, emit a warning if it exceeds 10k tokens, and hard-fail or truncate requests exceeding the 18k model limit before dispatch. Resolves research Q3.

**F4: Input Handling**  
The notebook must provide a dedicated cell for pasting raw "dirty" markdown strings, with an optional secondary cell to load from a local file path, ensuring both inputs normalize to a single string payload. Resolves research Q4.

**F5: Output Evaluation & Logging**  
The notebook must include a comparison cell showing a diff between input and output, plus heuristic checks for heading hierarchy, list indentation, and code block syntax to log formatting quality. Resolves research Q5.

**F6: Pipeline-Ready Abstraction**  
The core logic must be encapsulated in a reusable `run_format_markdown(input_text: str) -> str` function with a stable signature, enabling future import by workflows, slash commands, or MCP dispatchers without notebook UI dependencies. Resolves research Q6.

**F7: Model Availability Verification**  
At notebook startup, the system must explicitly verify that `qwen/qwen3.6-27b` is loaded and responsive on `http://localhost:1234/v1`, failing fast with a clear error message if unavailable rather than attempting silent fallback. Resolves research Q7.

**F8: Deterministic Generation Parameters**  
Generation parameters (temperature, top_p, max_tokens) must be fixed to reproducible defaults for testing, with an optional toggle cell to override them for experimentation without breaking the core pipeline. Resolves research Q8.

## Non-functional requirements

**N1: Performance**  
Token estimation and API round-trips must complete within 15 seconds for inputs under 10k tokens under normal local network conditions, with timeout handling to prevent hanging cells.

**N2: Security**  
API keys, base URLs, and model identifiers must be sourced exclusively from environment variables or `02_core` config; no credentials may be hardcoded, committed, or logged in plaintext.

**N3: Observability**  
All driver calls, token counts, heuristic evaluation results, and execution timestamps must be logged to a structured JSON log file in `04_harnesses/logs/` with unique request IDs for traceability.

**N4: Classification-Audit Compliance**  
Every formatted output must be tagged with a classification label (e.g., `clean`, `needs_review`, `failed`) and recorded in the audit trail to satisfy automated scanning by `17_scripts/audit_classifications.py`.

**N5: Path Discipline**  
All file references must use relative paths anchored to the repository root, and the notebook must validate that `12_prompts/tasks.format-markdown.md` exists and is readable before execution begins.

## Acceptance criteria

**A1:** Executing the notebook startup cell raises a clear exception if `http://localhost:1234/v1` does not return a valid model list containing `qwen/qwen3.6-27b`.

**A2:** Pasting a malformed markdown string into the input cell and running the pipeline produces a valid markdown output with corrected heading levels, list indentation, and code block syntax.

**A3:** The pre-flight token counter blocks execution and displays a warning when input exceeds 10k tokens, and hard-fails at 18k tokens without sending a request to the server.

**A4:** Running `python3 17_scripts/audit_classifications.py` against the notebook's output log directory returns zero classification violations and confirms all outputs are properly tagged.

**A5:** The `run_format_markdown()` function can be imported in a separate Python script without executing notebook-specific UI cells, returning a string within the expected schema.

**A6:** Generation parameters default to `temperature=0.1` and `top_p=0.9`, and overriding them via the toggle cell changes the output without breaking the pipeline or audit logging.

## Out of scope

- MCP server dispatch logic and tool registration (deferred until workflow orchestration layer is stabilized and driver abstraction supports dynamic routing)
- Pre-commit hook integration and repository-wide scanning (deferred until core formatting function is validated and performance benchmarks are met)
- Slash command UI integration and chat client routing (deferred until prompt layer supports dynamic templating and context injection)
- Automatic prompt versioning and fallback chains (deferred until `02_core` prompt registry supports semantic versioning and health-check polling)
- Cross-model compatibility testing beyond Qwen 3.6 27B (deferred until adapter abstraction supports dynamic model routing and token limit negotiation)