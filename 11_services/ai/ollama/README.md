# Ollama

## Purpose

Local embeddings and local LLM classification/runtime service.

## Container

- Image: `ollama/ollama`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/root/.ollama`: Ollama model cache and runtime data

Bind to a data instance under `14_data/apps/ollama/<name>/`.

## Ports

| Host env var  | Default | Container | Use        |
| ------------- | ------: | --------: | ---------- |
| `OLLAMA_PORT` | `11434` |   `11434` | Ollama API |

## Run

```bash
cmd ollama ./14_data/apps/ollama/main
```

Or directly:

```bash
DATA_PATH=./14_data/apps/ollama/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Model files can consume significant disk space.
- Pull models after startup with `docker exec contentgraph-ollama ollama pull <model>`.
