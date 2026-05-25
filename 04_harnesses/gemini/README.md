# gemini harness

Wraps Google Gemini via the `google-generativeai` Python SDK. Translates
OpenAI-style `messages` into Gemini's `contents` shape on the way in. `invoke`
calls `generate_content`, `stream` uses `generate_content(stream=True)`, and
`health` issues a tiny `generate_content("ping")`. The SDK does not expose
server-side request IDs, so the harness mints client-side UUIDs for `logs()`.
