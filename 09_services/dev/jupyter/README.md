# Jupyter Notebook

## Purpose

Optional analysis sandbox for notebooks and exploratory data work.

## Container

- Image: `jupyter/base-notebook`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/home/jovyan/work`: notebook workspace

Bind to a data instance under `14_data/apps/jupyter/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| `JUPYTER_PORT` | `8888` | `8888` | Jupyter UI |

## Run

```bash
DATA_PATH=./14_data/apps/jupyter/main docker compose up -d
docker compose logs -f
docker compose down
```

## Notes

- Check logs for the tokenized notebook URL on first startup.
