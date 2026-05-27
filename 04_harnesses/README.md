# 04_harnesses

The **Harness Layer** controls execution lifecycle for every external thing the
system talks to: hosted LLM providers (Claude, OpenAI, Gemini, Codex), local
model servers (Ollama, LM Studio), and Docker Compose services from the
`11_services/` catalog.

Per `ARCHITECTURE.md`, harnesses handle process or API invocation, streaming,
retries, timeouts, auth, and telemetry. They sit *below* the router and
workflows, and *above* the adapter layer — workflows never call providers
directly; they go through a harness.

## Contract

Every harness inherits from `harnesses.base.Harness` and implements:

| Method     | Responsibility                                       |
| ---------- | ---------------------------------------------------- |
| `start()`  | Bring the harness into a running state. Idempotent.  |
| `stop()`   | Tear it down cleanly. Idempotent.                    |
| `status()` | Return current lifecycle state without side effects. |
| `invoke()` | Single request/response.                             |
| `stream()` | Request returning an iterator of incremental events. |
| `logs()`   | Recent log/request-id buffer (default last 50).      |
| `health()` | Active reachability probe.                           |

`start`/`stop`/`status` return a `HarnessStatus` dataclass; `invoke` returns a
dict; `stream` yields dicts; `logs` returns a list of strings.

For hosted APIs (Claude, OpenAI, Gemini, Codex, LM Studio), `start`/`stop` only
manage the SDK client object — the remote service is not actually launched.
For Ollama, `start` will spawn `ollama serve` if not already running. For
`docker_service`, `start`/`stop` shell out to `docker compose up -d`/`down`.

## Layout

```
04_harnesses/
├── base.py               # abstract Harness + HarnessStatus + HarnessError
├── claude/harness.py     # Anthropic SDK
├── codex/harness.py      # openai SDK pointed at Codex CLI / API
├── gemini/harness.py     # google-generativeai SDK
├── openai/harness.py     # openai SDK against OpenAI proper
├── lmstudio/harness.py   # openai SDK -> http://localhost:1234/v1
├── ollama/harness.py     # REST against http://localhost:11434, manages process
└── docker_service/harness.py  # generic docker compose service
```

## Adding a new harness

1. Create `04_harnesses/<provider>/` with `__init__.py`, `harness.py`, `README.md`.
1. Subclass `harnesses.base.Harness` and implement the seven methods.
1. Accept a `config: Mapping[str, Any]` in `__init__`.
1. Re-export the class from the package `__init__.py`.
1. Register the harness with the router (`05_router/`).
