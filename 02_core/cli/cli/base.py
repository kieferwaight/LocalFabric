"""CLI-specific adapter and command base classes.

A :class:`CliAdapter` represents a single-domain slice of the CLI surface
(``localfabric db …``, ``localfabric ingest …``, …). It owns one Typer
sub-app and a list of :class:`CliCommand` subclasses — one class per
sub-command verb (``init``, ``run``, ``single``, …). The convention is
strict: no free-standing ``@app.command`` functions, no multi-domain
adapters.

Composing the top-level ``localfabric`` CLI is the job of
[adapters.cli.main](main.py), which iterates the registered adapter
classes and mounts each ``build_typer()`` under the parent app.

Adapters that aren't backed by Typer (e.g. the raw markdown runtime
runner in [markdown_runtime_adapter.py](markdown_runtime_adapter.py))
inherit from :class:`CliAdapter` for the interface tag but provide
their own ``main(argv)`` entry instead of overriding ``commands``.
"""

from __future__ import annotations

import abc
from typing import Any, ClassVar

import typer

from adapters.base import Adapter


class CliCommand(abc.ABC):
    """A single CLI sub-command, expressed as a class.

    Each ``CliAdapter`` lists its commands in the order they should appear
    under its Typer sub-app. The class-level ``name`` is the verb the
    user types; ``help`` becomes the Typer help string. ``run`` is the
    Typer callback — declare it as a ``@staticmethod`` with
    ``Annotated[...]`` arguments so Typer can introspect the signature.
    """

    name: ClassVar[str]
    help: ClassVar[str] = ""

    @classmethod
    def register(cls, app: typer.Typer) -> None:
        """Attach this command's ``run`` callback to the given Typer app."""
        if not getattr(cls, "name", None):
            raise TypeError(f"{cls.__name__} must declare a class-level `name`")
        app.command(name=cls.name, help=cls.help or None)(cls.run)

    @staticmethod
    @abc.abstractmethod
    def run(*args: Any, **kwargs: Any) -> Any:
        """Typer callback. Override as ``@staticmethod`` with annotated args."""


class CliAdapter(Adapter):
    """Single-domain CLI adapter that exposes one Typer sub-app.

    Subclasses set:

    * ``domain`` — the slice covered (``"db"``, ``"ingest"``, …).
    * ``typer_name`` — the verb the sub-app mounts under
      (``localfabric <typer_name> ...``); defaults to ``domain``.
    * ``typer_help`` — help string shown by Typer.
    * ``commands`` — ordered list of :class:`CliCommand` subclasses.
    """

    interface: ClassVar[str] = "cli"
    typer_name: ClassVar[str] = ""
    typer_help: ClassVar[str] = ""
    commands: ClassVar[list[type[CliCommand]]] = []

    @classmethod
    def mount_name(cls) -> str:
        """Verb used when mounting under the parent Typer app."""
        return cls.typer_name or cls.domain

    @classmethod
    def build_typer(cls) -> typer.Typer:
        """Build a Typer sub-app populated with this adapter's commands."""
        app = typer.Typer(help=cls.typer_help or None, no_args_is_help=True)
        for command_cls in cls.commands:
            command_cls.register(app)
        return app


__all__ = ["CliAdapter", "CliCommand"]
