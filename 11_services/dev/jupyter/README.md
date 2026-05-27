# Jupyter Notebook

## Purpose

Notebook host for LocalFabric's research and development workflow. Notebooks
in [`20_notebooks/`](../../../20_notebooks/) run against this container with
the project installed editably, so cells like `from harnesses.markdown import MarkdownHarness` work without bootstrap ceremony.

## Container

- Base image: `jupyter/base-notebook`
- Compose file: [`docker-compose.yml`](docker-compose.yml)
- Dockerfile: [`Dockerfile`](Dockerfile) — layers `pip install -e ".[notebook]"`
  onto the base image so project imports and the `[notebook]` extras
  (`ipykernel`, `openai`) are available in the kernel.

## Mounts

| Host           | Container           | Purpose                                                                        |
| -------------- | ------------------- | ------------------------------------------------------------------------------ |
| repo root      | `/workspace`        | Live source — edits flow both ways. The editable install's `.pth` points here. |
| `${DATA_PATH}` | `/home/jovyan/work` | Per-instance scratch / output directory.                                       |

Bind `${DATA_PATH}` to `14_data/apps/jupyter/<name>/` per the data convention.

## Ports & Auth

| Host env var    |           Default | Use                                                    |
| --------------- | ----------------: | ------------------------------------------------------ |
| `JUPYTER_PORT`  |            `8888` | Jupyter UI port.                                       |
| `JUPYTER_TOKEN` | `localfabric-dev` | Fixed dev token. Override if you need a different one. |

Open: `http://localhost:8888/?token=localfabric-dev`

The token is a dev convenience, not real security — it gives a stable URL so
you don't have to scrape container logs every restart. Override
`JUPYTER_TOKEN` for any non-localhost use.

## Run

Via the service runtime (preferred):

```bash
python -m service_runtime.cmd up jupyter ./14_data/apps/jupyter/scratch
python -m service_runtime.cmd status jupyter ./14_data/apps/jupyter/scratch
python -m service_runtime.cmd down jupyter ./14_data/apps/jupyter/scratch
```

Or directly with compose (from this directory):

```bash
DATA_PATH=../../../14_data/apps/jupyter/scratch docker compose up -d
docker compose down
```

## Verifying

After `up`, in a new notebook under `/workspace/20_notebooks`:

```python
from harnesses.markdown import MarkdownHarness
MarkdownHarness()
```

Should succeed with no `ModuleNotFoundError`.

## Rebuilding

The Dockerfile installs project dependencies at build time. After changes to
[`pyproject.toml`](../../../pyproject.toml) (new deps, new optional extras),
rebuild the image:

```bash
DATA_PATH=./14_data/apps/jupyter/scratch \
  docker compose -f 11_services/dev/jupyter/docker-compose.yml build
```

`DATA_PATH` isn't used by the build itself, but compose parses every volume
mount during build and will reject an empty `${DATA_PATH}`. The service
runtime sets this automatically; manual builds need it set explicitly.

The next `up` will use the new image. Source-only edits (anything inside
`/workspace`) do not require a rebuild — they flow through the live mount.
