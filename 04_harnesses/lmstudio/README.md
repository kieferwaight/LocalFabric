# lmstudio harness

Talks to a locally-running LM Studio server (OpenAI-compatible HTTP at
`http://localhost:1234/v1` by default) using the `openai` SDK. The harness does
not manage the LM Studio app itself — the user launches that — but it does
treat `models.list` as a reachability probe for both `status` (passive) and
`health` (active). `invoke` and `stream` use the standard chat completions
shape.
