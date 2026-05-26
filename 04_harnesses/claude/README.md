# claude harness

Wraps the Anthropic Claude API (`anthropic` Python SDK) as a lifecycle-controlled
harness. Because Claude is a hosted API, `start`/`stop`/`status` are lightweight —
they simply manage the SDK client object. `invoke` calls the Messages API once,
`stream` yields incremental Messages stream events, `health` issues a 1-token
ping, and `logs` returns the recent request IDs and state transitions
