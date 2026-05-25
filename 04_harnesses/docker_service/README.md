# docker_service harness

Generic lifecycle harness for any Docker Compose-backed service from the
`09_services/` catalog. Wraps the `docker compose` CLI: `start` runs
`up -d`, `stop` runs `down`, `status` parses `ps --format json`, and `logs`
calls `compose logs --tail N`. Services are not directly invokable — `invoke`
and `stream` raise — they are consumed downstream via drivers and adapters.
`health` performs an HTTP GET against an optional `health_url` from the config.
