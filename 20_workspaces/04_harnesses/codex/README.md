# codex harness

Wraps the OpenAI Codex surface — either the hosted endpoint or a local Codex
CLI proxy — using the `openai` SDK. Identical shape to the OpenAI harness, but
with code-tuned defaults, a longer default timeout, and an extra fallback chain
for the API key (`CODEX_API_KEY` then `OPENAI_API_KEY`).
