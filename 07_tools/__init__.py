"""Provider-neutral local tools.

Each subpackage is a separate domain (browser, classify, embeddings, image,
metadata, pdf, shell, vision, docx). Subpackages are loaded on demand rather
than eagerly imported here because several pull in optional dependencies
(``cv2``, ``lancedb``, the Ollama harness, etc.).
"""
