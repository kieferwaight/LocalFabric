# ollama harness

Talks to a local Ollama server (default `http://localhost:11434`) over its REST
API. Unlike the hosted-API harnesses, this one *does* manage a process: when
`manage_server` is true (default), `start()` will spawn `ollama serve` if the
server is not already reachable, and `stop()` will SIGTERM the spawned process
group. `status` queries `/api/tags`, `health` pings `/`, and `invoke`/`stream`
use `/api/chat`.
