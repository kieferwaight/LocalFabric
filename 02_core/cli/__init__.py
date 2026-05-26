"""Adapter layer — interface translation, one class per domain.

Every adapter inherits from :class:`adapters.base.Adapter` and declares a
single ``interface`` (``"cli"``, ``"rest"``, ``"mcp"`` …) and a single
``domain`` (``"db"``, ``"ingest"``, ``"image_intelligence"`` …). Concrete
adapters live in interface-named sub-buckets (currently just ``cli/``);
each domain gets its own ``<domain>_adapter.py`` file with one class.

See [03_adapters/base.py](base.py) for the base contract and
[03_adapters/cli/base.py](cli/base.py) for the CLI-specific extension
that adds ``CliCommand`` sub-classes for individual sub-commands.
"""

from adapters.base import Adapter, AdapterError

__all__ = ["Adapter", "AdapterError"]
