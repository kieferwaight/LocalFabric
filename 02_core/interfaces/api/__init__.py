"""FastAPI HTTP mirror of the CLI/MCP command surface.

Every ``command.*`` YAML definition that declares a non-empty ``http_spec``
is automatically exposed as a route on the app returned by :func:`app.build_app`.
Adding a new HTTP endpoint requires only a YAML edit — no Python changes here.
"""
