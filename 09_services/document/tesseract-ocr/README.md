# Tesseract OCR

## Purpose

OCR worker scaffold for extracting text from images and scanned documents.

## Container

- Image: `contentgraph-tesseract-ocr:local`
- Build context: `.`
- Compose file: `docker-compose.yml`

## Storage

- `${DATA_PATH}` -> `/work`: local input/output workspace
- Application code lives in `./app`

Bind to a data instance under `14_data/runs/workers/tesseract-ocr/<name>/`.

## Ports

| Host env var | Default | Container | Use |
| --- | ---: | ---: | --- |
| none | n/a | n/a | Worker has no exposed port |

## Run

```bash
DATA_PATH=./14_data/runs/workers/tesseract-ocr/main docker compose up -d --build
docker compose logs -f
docker compose down
```

## Notes

- Includes `tesseract-ocr` and `poppler-utils`.
- Usually better as a worker dependency than a network service.
