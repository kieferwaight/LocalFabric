"""
drivers — storage and persistence layer.

Owns all persistent file I/O and storage access. Workflows must delegate
writes here; they never touch the filesystem or databases directly.

Subpackages:
    cache    — JSON-file caches for tool state
    file     — artifact filesystem operations
    sql      — SQLite via SQLAlchemy Core (asset registry, workflow runs)
    vector   — embedded vector stores (NumPy in-memory, LanceDB persistent)
"""
