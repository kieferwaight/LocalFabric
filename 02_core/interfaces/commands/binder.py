"""Command binder — turns a :class:`~registry.Command` into a Typer / FastAPI / FastMCP handler.

Phase C1 implements :func:`bind_typer` only.
:func:`bind_fastapi` and :func:`bind_fastmcp` are stubs that Phase C3/C4 will fill in.
"""

from __future__ import annotations

import inspect
import json
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console

try:
    from core.interfaces.commands.registry import Command
except ModuleNotFoundError:
    from interfaces.commands.registry import Command  # type: ignore[no-redef]

if TYPE_CHECKING:
    # Runtime is not imported at module level to avoid circular dependencies
    # and to keep CLI startup fast.
    from core.runtimes.yaml.src import Runtime

# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

_PYTYPE_MAP: dict[str, type] = {
    "string": str,
    "number": float,
    "boolean": bool,
    # array and object are passed as JSON strings and parsed at invocation time.
    "array": str,
    "object": str,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def bind_typer(
    parent: typer.Typer,
    command: Command,
    runtime: Runtime,
    group_cache: dict[str, typer.Typer] | None = None,
) -> None:
    """Register *command* as a Typer subcommand under *parent*.

    The command's ``argv_spec["group"]`` determines the sub-Typer name (e.g.
    ``"task"``). The ``argv_spec["verb"]`` is the command name within that
    group (e.g. ``"run"``). Sub-Typers are created on first use and cached via
    *group_cache* so that commands sharing a group share one sub-app.

    Parameters
    ----------
    parent:
        Root :class:`typer.Typer` to mount the group sub-app onto.
    command:
        A :class:`~registry.Command` sourced from :class:`~registry.CommandRegistry`.
    runtime:
        A loaded :class:`~core.runtimes.yaml.src.Runtime` used to execute
        the command when its handler is invoked.
    group_cache:
        Optional dict mapping group name → sub-Typer; pass the same dict for
        all :func:`bind_typer` calls that share a *parent* so groups are
        reused rather than duplicated.
    """
    if group_cache is None:
        group_cache = {}

    group: str = command.argv_spec.get("group") or command.id.split(".")[1]
    verb: str = command.argv_spec.get("verb") or command.id.split(".")[-1]

    if group not in group_cache:
        sub_app = typer.Typer(name=group, help=f"{group.title()} commands.", no_args_is_help=True)
        parent.add_typer(sub_app, name=group)
        group_cache[group] = sub_app

    sub_app = group_cache[group]
    handler = _make_handler(command, runtime)
    sub_app.command(name=verb, help=command.description or f"{group} {verb}")(handler)


def bind_fastapi(api: Any, command: Command, runtime: Any) -> None:
    """Register *command* as a FastAPI route on *api*.

    Route method: ``command.http_spec["method"]`` (default ``"POST"``).
    Route path:   ``command.http_spec["path"]`` (required; skip if missing).
    Request body: pydantic ``BaseModel`` built from ``command.inputs``:
        ``string`` → ``str``, ``number`` → ``float``, ``boolean`` → ``bool``,
        ``array`` → ``list``, ``object`` → ``dict``.
    Handler: calls ``runtime.execute(command.definition_id, arguments=body.model_dump())``
        and returns ``{"status": "ok", "command_id": ..., "result": <scope dict>}``.
    All routes require the ``require_token`` dependency (loopback is always allowed).

    fastapi and pydantic are imported lazily here to keep CLI-only environments
    from pulling in the full FastAPI dependency tree.
    """
    from fastapi import Depends, HTTPException
    from pydantic import Field, create_model

    try:
        from core.interfaces.api.auth import require_token
    except ModuleNotFoundError:
        from interfaces.api.auth import require_token  # type: ignore[no-redef]

    path: str = command.http_spec.get("path", "")
    if not path:
        return

    method: str = (command.http_spec.get("method") or "POST").upper()

    # Build pydantic request model from command.inputs.
    _API_TYPE_MAP: dict[str, type] = {
        "string": str,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    fields: dict[str, Any] = {}
    for name, c in command.inputs.items():
        pytype = _API_TYPE_MAP.get(c.type, str)
        if c.required:
            default = ...  # Ellipsis sentinel — pydantic v2 required field
        else:
            default = c.default if c.default is not None else None
        fields[name] = (pytype, Field(default, description=c.description or ""))

    RequestModel = create_model(  # noqa: N806
        f"{command.id.replace('.', '_')}_Request", **fields
    )

    # Capture loop variables in the closure.
    _cmd_id = command.definition_id

    async def handler(
        body: RequestModel,  # type: ignore[valid-type]
        _: None = Depends(require_token),
    ) -> dict:
        try:
            result = runtime.execute(_cmd_id, arguments=body.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
        return {"status": "ok", "command_id": _cmd_id, "result": result}

    # Give the handler a unique name so FastAPI's OpenAPI schema doesn't collide.
    handler.__name__ = f"{command.id.replace('.', '_')}_handler"
    handler.__qualname__ = handler.__name__

    # `from __future__ import annotations` at the top of this module causes all
    # annotations to be stored as strings (PEP 563). FastAPI resolves them via
    # get_type_hints(), which uses the handler's __globals__. Since RequestModel is
    # a local variable (not in __globals__), FastAPI can't find it and falls back
    # to treating `body` as a query parameter. Fix: overwrite __annotations__ with
    # the actual resolved types.
    handler.__annotations__ = {
        "body": RequestModel,
        "_": type(None),
        "return": dict,
    }

    # Register against the appropriate HTTP method.
    route_registrar = getattr(api, method.lower(), None)
    if route_registrar is None:
        raise ValueError(f"FastAPI app has no method '{method.lower()}' for command {command.id!r}.")
    route_registrar(path, summary=command.description or command.id)(handler)


def bind_fastmcp(mcp: Any, command: Command, runtime: Any) -> None:
    """Register *command* as a FastMCP tool on *mcp*.

    Tool name:
        ``command.id`` with dots replaced by underscores (FastMCP tool
        names must be Python identifiers).
    Tool description:
        ``command.description``.
    Input schema:
        Built from ``command.inputs`` — each :class:`~registry.InputConstraint`
        maps ``type`` to a Python annotation (``string``→``str``,
        ``number``→``float``, ``boolean``→``bool``, ``array``→``list``,
        ``object``→``dict``) and ``required``/``default`` to parameter
        defaults.  FastMCP introspects the handler's ``__signature__`` so
        no manual JSON schema authoring is needed.

    Parameters
    ----------
    mcp:
        A :class:`mcp.server.fastmcp.FastMCP` instance.
    command:
        A :class:`~registry.Command` sourced from :class:`~registry.CommandRegistry`.
    runtime:
        A loaded :class:`~core.runtimes.yaml.src.Runtime` used to execute
        the command when the tool is invoked.
    """
    tool_name = command.id.replace(".", "_")

    # FastMCP natively accepts list / dict annotations for array / object.
    _MCP_TYPE_MAP: dict[str, type] = {
        "string": str,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    params: list[inspect.Parameter] = []
    for name, constraint in command.inputs.items():
        pytype = _MCP_TYPE_MAP.get(constraint.type, str)

        if not constraint.required and constraint.default is not None:
            default = constraint.default
        elif not constraint.required:
            # Optional with no stated default — use the zero value for the type.
            default = [] if constraint.type == "array" else ({} if constraint.type == "object" else None)
        else:
            default = inspect.Parameter.empty

        params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=pytype,
                default=default,
            )
        )

    def handler(**kwargs: Any) -> Any:
        return runtime.execute(command.definition_id, arguments=kwargs)

    handler.__signature__ = inspect.Signature(parameters=params)
    handler.__name__ = tool_name
    handler.__qualname__ = tool_name
    handler.__doc__ = command.description or f"Invoke {command.id}."

    mcp.tool(name=tool_name, description=command.description or f"Invoke {command.id}.")(handler)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_handler(command: Command, runtime: Runtime):
    """Build a dynamic function whose ``__signature__`` matches the command inputs.

    Typer introspects ``__signature__`` to generate CLI argument/option
    definitions, so we must construct it explicitly for dynamic commands.

    Positional inputs (listed in ``argv_spec.positional``) become
    ``typer.Argument``; all others become ``typer.Option``.
    """
    positional_names: list[str] = list(command.argv_spec.get("positional") or [])
    params: list[inspect.Parameter] = []

    for name, constraint in command.inputs.items():
        pytype = _PYTYPE_MAP.get(constraint.type, str)
        is_positional = name in positional_names

        if is_positional:
            typer_marker = typer.Argument(help=constraint.description or "")
        else:
            typer_marker = typer.Option(help=constraint.description or "")

        annotation = Annotated[pytype, typer_marker]

        # Determine the default value for this parameter.
        if constraint.required and constraint.default is None:
            default = inspect.Parameter.empty
        else:
            # For object/array types, the CLI receives a JSON string;
            # use an empty string as the default rather than {} / [].
            if constraint.type in ("object", "array"):
                default = "" if constraint.default is None else json.dumps(constraint.default)
            else:
                default = constraint.default

        params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=annotation,
                default=default,
            )
        )

    def handler(**kwargs: Any) -> None:
        coerced: dict[str, Any] = {}
        for k, v in kwargs.items():
            c = command.inputs[k]
            if c.type in ("object", "array") and isinstance(v, str):
                if v:
                    v = json.loads(v)
                elif c.default is not None:
                    v = c.default
                else:
                    v = {} if c.type == "object" else []
            coerced[k] = v

        result = runtime.execute(command.definition_id, arguments=coerced)
        Console().print(result if result is not None else "[dim]ok[/dim]")

    handler.__signature__ = inspect.Signature(parameters=params)
    handler.__name__ = verb_name = command.argv_spec.get("verb") or command.id.split(".")[-1]
    handler.__qualname__ = f"{command.id.replace('.', '_')}_{verb_name}"
    return handler
