# 21_datasets/image/

← [Up to 21_datasets](../README.md)

Image samples for vision, OCR, classification, and layout tasks. Each
image file has a sibling `*.dataset.yaml` manifest at the same path stem.

## Children (subclasses)

| Subclass         | Purpose                                                                          |
| ---------------- | -------------------------------------------------------------------------------- |
| [`photo/`](photo/)                   | Real-world photography. Source license must be CC0/permissive. |
| [`screenshot/`](screenshot/)         | Captured UI surfaces — terminals, web pages, native apps.       |
| [`diagram/`](diagram/)               | Diagrams, charts, architecture drawings.                        |
| [`document-page/`](document-page/)   | Single rasterized page from a document (PDF render, scan).      |

## Conventions

- **Extensions**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.tiff`, `.bmp`.
- **Color profile**: prefer sRGB; record any deviation in `media.color_profile`.
- **Dimensions**: include `media.width` and `media.height` (pixels) in every manifest.
- **Manifest** `class:` field MUST be `image`.

See [`../README.md`](../README.md) for the master manifest contract.
See [`photo/example-placeholder.001.dataset.yaml`](photo/example-placeholder.001.dataset.yaml)
for a fully-populated template.
