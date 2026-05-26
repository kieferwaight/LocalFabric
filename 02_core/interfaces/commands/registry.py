"""CommandRegistry — discovers ``command.*`` YAML definitions at runtime.

Scans ``runtime.globals['catalog']['definitions']`` for entries where
``has_command=True`` (set by ``_update_catalog`` in the YAML runtime).
For each concrete command (i.e. not ``command.base`` itself) it assembles
the full resolved frame so that inherited inputs and variables are included,
then packages everything into a :class:`Command` dataclass for use by
:mod:`binder`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

try:
    from core.runtimes.yaml.src.definition import InputConstraint
except ModuleNotFoundError:
    from src.definition import InputConstraint  # type: ignore[no-redef]


@dataclass
class Command:
    """A concrete command definition ready to be bound to CLI / API / MCP."""

    id: str
    description: str
    inputs: dict[str, InputConstraint]
    argv_spec: dict
    http_spec: dict
    mcp_spec: dict

    @property
    def definition_id(self) -> str:
        """Alias for :attr:`id`; kept for clarity at call sites."""
        return self.id


class CommandRegistry:
    """Discovers and exposes ``command.*`` definitions from a loaded Runtime.

    Parameters
    ----------
    runtime:
        A fully-loaded :class:`~core.runtimes.yaml.src.Runtime` instance
        (i.e. ``stdlib.load-modules`` has already been executed so that
        ``command.yaml`` is registered).
    """

    def __init__(self, runtime: object) -> None:
        # Typed as ``object`` to avoid a hard circular import at module level;
        # callers supply a real Runtime instance.
        self._runtime = runtime

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def iter_commands(self) -> Iterator[Command]:
        """Yield one :class:`Command` per concrete ``command.*`` definition.

        ``command.base`` is excluded (it is abstract and carries no
        meaningful ``argv_spec`` / inputs of its own).
        """
        catalog: list[dict] = (
            self._runtime.globals.get("catalog", {}).get("definitions", [])
        )
        for entry in catalog:
            if not entry.get("has_command"):
                continue
            def_id: str = entry["id"]
            if def_id == "command.base":
                continue
            yield self._build_command(def_id, entry)

    def get(self, group: str, verb: str | None = None) -> Command | None:
        """Look up a command by its ``argv_spec.group`` / ``argv_spec.verb`` pair.

        Returns ``None`` if no matching command is found.
        """
        for cmd in self.iter_commands():
            if cmd.argv_spec.get("group") != group:
                continue
            if verb is None or cmd.argv_spec.get("verb") == verb:
                return cmd
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_command(self, def_id: str, _entry: dict) -> Command:
        """Assemble the full inherited frame and construct a :class:`Command`."""
        assembled = self._runtime.assemble_definition_frame(def_id)

        # Variables are already resolved as native Python objects (dicts / lists
        # / scalars) by the YAML compiler — no Jinja rendering needed here.
        argv_spec: dict = assembled.variables.get("argv_spec") or {}
        http_spec: dict = assembled.variables.get("http_spec") or {}
        mcp_spec: dict = assembled.variables.get("mcp_spec") or {}

        # Ensure they are plain dicts (defensive against unexpected string values).
        if not isinstance(argv_spec, dict):
            argv_spec = {}
        if not isinstance(http_spec, dict):
            http_spec = {}
        if not isinstance(mcp_spec, dict):
            mcp_spec = {}

        return Command(
            id=def_id,
            description=assembled.description or "",
            inputs=dict(assembled.inputs),
            argv_spec=argv_spec,
            http_spec=http_spec,
            mcp_spec=mcp_spec,
        )


# ---------------------------------------------------------------------------
# Smoke test — run directly to verify discovery
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Allow running from the repo root without an installed package.
    _repo_root = Path(__file__).resolve().parents[3]
    for _p in (str(_repo_root / "02_core"), str(_repo_root / "02_core/runtimes/yaml")):
        if _p not in sys.path:
            sys.path.insert(0, _p)

    from core.runtimes.yaml.src import Runtime  # noqa: E402 — deferred

    r = Runtime(workflow_dir=str(_repo_root / "02_core/runtimes/yaml"))
    r.import_yaml(str(_repo_root / "02_core/runtimes/yaml/definitions/stdlib.yaml"))
    r.execute("stdlib.load-modules", {})

    reg = CommandRegistry(r)
    for cmd in reg.iter_commands():
        print(cmd.id, "→", cmd.argv_spec.get("group"), cmd.argv_spec.get("verb"))
