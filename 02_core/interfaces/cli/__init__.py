"""``localfabric`` CLI — pure Typer.

The root app is assembled in ``main.py`` by mounting each domain
sub-app (``db``, ``ingest``, ``image_intelligence``, ``markdown``). The
raw markdown-runtime entry (``localfabric-md``) lives in
``markdown_runtime.py`` because it does not register Typer commands —
its argv shape is inherited from the YAML runtime's
:class:`ShellEnvironment`.
"""
