"""Pytest conftest — registers bucket-name aliases for the test run.

The numeric-prefixed directories (02_core, 04_harnesses, ...) are not valid
Python identifiers. `pip install -e .` (via pyproject.toml's package-dir
mapping) is the canonical way to make imports like `from harnesses.base
import Harness` resolve. This file does the same thing in-process so that
`pytest` works without an install step.

It must live at the test-collection root for pytest to auto-load it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

# bucket-dir → import name. Keep in sync with [tool.setuptools.package-dir]
# in pyproject.toml.
_BUCKETS: dict[str, str] = {
    "02_core/src/core": "core",
    "03_adapters": "adapters",
    "04_harnesses": "harnesses",
    "05_router": "router",
    "06_workflows": "workflows",
    "07_tools": "tools",
    "08_drivers": "drivers",
    "10_service_runtime": "service_runtime",
    "11_mcp": "mcp_servers",
}


def _register(alias: str, target: Path) -> None:
    if alias in sys.modules:
        return
    init_file = target / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        alias,
        str(init_file) if init_file.is_file() else None,
        submodule_search_locations=[str(target)],
    )
    if spec is None:
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    if spec.loader is not None and init_file.is_file():
        spec.loader.exec_module(module)


for rel, alias in _BUCKETS.items():
    _register(alias, _ROOT / rel)
