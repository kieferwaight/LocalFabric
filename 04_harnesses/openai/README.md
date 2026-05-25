# openai harness

Wraps the OpenAI Chat Completions API (`openai` Python SDK) as a lifecycle
controller. `start`/`stop` manage the SDK client; `invoke` calls
`chat.completions.create`; `stream` yields incremental chunks; `health` runs
`models.list` as a cheap reachability check. `logs` returns recent request IDs
and state transitions.
