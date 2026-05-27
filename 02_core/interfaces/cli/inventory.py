"""Live-inventory Typer apps for `lfc` / `localfabric`.

Each group (`task`, `prompt`, `workflow`, `service`) supports:

- ``list``     — scan the on-disk inventory and print one row per definition
- ``describe`` — show the definition's title, description, and inputs
- ``run``      — execute, accepting ``--<input>=<value>`` flags discovered live
                 from the definition itself (printed as help when args are missing)

A top-level ``run`` command dispatches a ``.yaml`` or ``.md`` file through the
appropriate runtime.

The inventory side reads directly from the filesystem so it stays in sync with
edits without waiting for any reload step. Execution defers to the YAML
Runtime / MarkdownHarness — the same paths used by the wider platform.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CLI_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CLI_DIR.parents[2]
_TASKS_DIR = _REPO_ROOT / "05_tasks"
_WORKFLOWS_DIR = _REPO_ROOT / "06_workflows"
_PROMPTS_DIR = _REPO_ROOT / "12_prompts"
_YAML_RUNTIME_DIR = _REPO_ROOT / "02_core" / "runtimes" / "yaml"
_YAML_STDLIB = _YAML_RUNTIME_DIR / "definitions" / "stdlib.yaml"

_LIFECYCLE_ACTIONS = (
    "start",
    "stop",
    "enable",
    "disable",
    "install",
    "uninstall",
    "status",
)

_console = Console()


# ---------------------------------------------------------------------------
# Inventory record
# ---------------------------------------------------------------------------


@dataclass
class Definition:
    """A discovered definition on disk."""

    id: str
    title: str
    description: str
    inputs: dict[str, dict[str, Any]]
    path: Path
    kind: str  # "task" | "workflow" | "prompt"
    examples: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Filesystem scanners
# ---------------------------------------------------------------------------


def _parse_yaml_definition(path: Path, kind: str) -> Definition | None:
    try:
        docs = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(docs, list) or not docs:
        return None
    entry = docs[0]
    if not isinstance(entry, dict) or "id" not in entry:
        return None
    examples_raw = entry.get("examples") or []
    examples = [e for e in examples_raw if isinstance(e, dict) and "id" in e]
    return Definition(
        id=str(entry["id"]),
        title=str(entry.get("title") or ""),
        description=str(entry.get("description") or "").strip(),
        inputs=dict(entry.get("inputs") or {}),
        path=path,
        kind=kind,
        examples=examples,
    )


def _parse_md_prompt(path: Path) -> Definition | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    _, _, rest = text.partition("---\n")
    fm_text, sep, _body = rest.partition("\n---")
    if not sep:
        return None
    try:
        meta = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict) or "id" not in meta:
        return None
    return Definition(
        id=str(meta["id"]),
        title=str(meta.get("title") or ""),
        description=str(meta.get("description") or "").strip(),
        inputs=dict(meta.get("inputs") or {}),
        path=path,
        kind="prompt",
    )


def scan_tasks() -> list[Definition]:
    out: list[Definition] = []
    if _TASKS_DIR.exists():
        for p in sorted(_TASKS_DIR.glob("*.task.yaml")):
            d = _parse_yaml_definition(p, "task")
            if d is not None:
                out.append(d)
    return out


def scan_workflows() -> list[Definition]:
    out: list[Definition] = []
    if _WORKFLOWS_DIR.exists():
        for p in sorted(_WORKFLOWS_DIR.glob("*.workflow.yaml")):
            d = _parse_yaml_definition(p, "workflow")
            if d is not None:
                out.append(d)
    return out


def scan_prompts() -> list[Definition]:
    out: list[Definition] = []
    if _PROMPTS_DIR.exists():
        for p in sorted(_PROMPTS_DIR.glob("*.md")):
            d = _parse_md_prompt(p)
            if d is not None:
                out.append(d)
    return out


# ---------------------------------------------------------------------------
# Pretty printers
# ---------------------------------------------------------------------------


def _short_desc(description: str, width: int = 70) -> str:
    first = description.splitlines()[0].strip() if description else ""
    return first if len(first) <= width else first[: width - 1] + "…"


def _print_inventory(kind: str, defs: list[Definition]) -> None:
    if not defs:
        _console.print(f"[yellow]No {kind}s found.[/yellow]")
        return
    table = Table(title=f"Available {kind}s ({len(defs)})", show_lines=False)
    table.add_column("id", style="bold cyan", no_wrap=True)
    table.add_column("description")
    for d in defs:
        table.add_row(d.id, _short_desc(d.description or d.title))
    _console.print(table)


def _print_inputs(d: Definition) -> None:
    _console.print(f"[bold cyan]{d.id}[/bold cyan]  [dim]({d.kind})[/dim]")
    if d.title:
        _console.print(f"  {d.title}")
    if d.description:
        _console.print(f"\n{d.description}\n")
    if not d.inputs:
        _console.print("[dim]No declared inputs.[/dim]")
        return
    table = Table(title="inputs", show_lines=False)
    table.add_column("name", style="bold")
    table.add_column("type")
    table.add_column("required")
    table.add_column("default")
    table.add_column("description")
    for name, spec in d.inputs.items():
        if not isinstance(spec, dict):
            spec = {}
        default = spec.get("default")
        default_str = "" if default is None else json.dumps(default, default=str)
        table.add_row(
            name,
            str(spec.get("type") or "string"),
            "yes" if spec.get("required") else "no",
            default_str,
            _short_desc(str(spec.get("description") or "")),
        )
    _console.print(table)


def _print_examples(d: Definition) -> None:
    if not d.examples:
        return
    table = Table(title="examples", show_lines=False)
    table.add_column("id", style="bold cyan", no_wrap=True)
    table.add_column("description")
    for ex in d.examples:
        table.add_row(
            str(ex.get("id") or ""),
            _short_desc(str(ex.get("description") or "")),
        )
    _console.print(table)


def _print_run_help(d: Definition, *, group: str | None = None) -> None:
    """Render contextual `--help` output for a specific definition's run command.

    Group is the Typer parent group name (e.g. ``"task"``, ``"prompt"``) when
    invoked through ``lfc <group> run``; left as ``None`` for the top-level
    ``lfc run <file>`` form.
    """
    if group is None:
        usage = f"lfc run {d.path} [--example=<id>] [--<name>=<value> ...]"
    else:
        usage = f"lfc {group} run {d.id} [--example=<id>] [--<name>=<value> ...]"
    _console.print(f"Usage: [bold]{usage}[/bold]\n")
    _print_inputs(d)
    if d.inputs:
        required = [
            n for n, s in d.inputs.items()
            if isinstance(s, dict) and s.get("required")
        ]
        optional = [n for n in d.inputs if n not in required]
        if required:
            _console.print(f"\n[bold]Required:[/bold] {', '.join(required)}")
        if optional:
            _console.print(f"[dim]Optional:[/dim] {', '.join(optional)}")
    if d.examples:
        _console.print("")
        _print_examples(d)


def _missing_args_help(d: Definition, supplied: dict[str, Any]) -> None:
    _console.print(
        f"[yellow]Provide inputs for[/yellow] [bold cyan]{d.id}[/bold cyan] "
        "as --<name>=<value> flags:"
    )
    _print_inputs(d)
    required_missing = [
        n for n, s in d.inputs.items()
        if isinstance(s, dict) and s.get("required") and n not in supplied
    ]
    if required_missing:
        _console.print(
            f"\n[red]Missing required inputs:[/red] {', '.join(required_missing)}"
        )


def _parse_kv_args(extra: list[str]) -> dict[str, Any]:
    """Parse ``--key=value`` / ``--key value`` / ``--flag`` tokens into a dict."""
    args: dict[str, Any] = {}
    i = 0
    while i < len(extra):
        tok = extra[i]
        if tok.startswith("--"):
            key_part = tok[2:]
            if "=" in key_part:
                k, _, v = key_part.partition("=")
                args[k] = _coerce(v)
            else:
                # Boolean flag or `--key value`
                if i + 1 < len(extra) and not extra[i + 1].startswith("--"):
                    args[key_part] = _coerce(extra[i + 1])
                    i += 1
                else:
                    args[key_part] = True
        i += 1
    return args


def _coerce(raw: str) -> Any:
    """Best-effort scalar coercion for free-form CLI values."""
    if raw == "":
        return ""
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass
    if raw.startswith(("[", "{")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


# ---------------------------------------------------------------------------
# Runtime helpers (lazy)
# ---------------------------------------------------------------------------


def _example_inputs_or_exit(d: Definition, example_id: str) -> dict[str, Any]:
    """Look up an example by id on a freshly-scanned Definition.

    Returns its `inputs:` mapping (an empty dict for an empty / unset id), or
    exits non-zero with the list of available IDs when the id is unknown.
    """
    if not example_id:
        return {}
    for ex in d.examples:
        if str(ex.get("id") or "") == example_id:
            inputs = ex.get("inputs") or {}
            return dict(inputs) if isinstance(inputs, dict) else {}
    available = [str(ex.get("id") or "") for ex in d.examples if ex.get("id")]
    listing = ", ".join(repr(eid) for eid in available) or "(none declared)"
    _console.print(
        f"[red]No example[/red] [bold]{example_id}[/bold] on "
        f"[cyan]{d.id}[/cyan]. Available: {listing}"
    )
    raise typer.Exit(code=2)


def _complete_example_ids(ctx: typer.Context, incomplete: str) -> list[str]:
    """Best-effort autocompletion for `--example`: read the target YAML live.

    Resolves the target definition by inspecting already-parsed context params
    (a `path` for the top-level `lfc run` or a `definition_id` for
    `lfc <group> run`). Returns example IDs prefix-matched by `incomplete`.
    Falls back to an empty list if the target cannot be resolved — completion
    should never raise.
    """
    try:
        params = getattr(ctx, "params", {}) or {}
        candidate = params.get("path") or params.get("definition_id") or ""
        ids: list[str] = []
        if candidate:
            cand_path = Path(str(candidate))
            if cand_path.suffix.lower() in (".yaml", ".yml") and cand_path.exists():
                d = _parse_yaml_definition(cand_path, kind="task")
                if d is not None:
                    ids = [str(ex.get("id") or "") for ex in d.examples]
            else:
                for scan in (scan_tasks, scan_workflows):
                    for d in scan():
                        if d.id == str(candidate):
                            ids = [str(ex.get("id") or "") for ex in d.examples]
                            break
                    if ids:
                        break
        return [eid for eid in ids if eid and eid.startswith(incomplete)]
    except Exception:
        return []


def _build_yaml_runtime(extra_yaml: Path | None = None):
    """Boot a YAML Runtime with stdlib and optionally a single extra file imported."""
    from core.runtimes.yaml.src import Runtime

    r = Runtime(workflow_dir=str(_YAML_RUNTIME_DIR))
    r.import_yaml(str(_YAML_STDLIB))
    r.execute("stdlib.load-modules.workflow", {})
    if extra_yaml is not None:
        r.import_yaml(str(extra_yaml))
    return r


def _run_yaml_definition(
    d: Definition, arguments: dict[str, Any], *, example: str | None = None
) -> None:
    runtime = _build_yaml_runtime(extra_yaml=d.path)
    result = runtime.execute(d.id, arguments=arguments, example=example)
    _console.print(result if result is not None else "[dim]ok[/dim]")


def _run_prompt(
    d: Definition, arguments: dict[str, Any], *, example: str | None = None
) -> None:
    if example:
        _console.print(
            "[yellow]warning:[/yellow] --example is not supported for prompts; ignoring."
        )
    from core.runtimes.markdown import (
        MarkdownCompileError,
        MarkdownHarness,
        ProviderError,
        ProviderResult,
    )
    from core.runtimes.yaml.src import Runtime

    runtime = Runtime()
    if _YAML_STDLIB.exists():
        runtime.import_yaml(str(_YAML_STDLIB))
    harness = MarkdownHarness(runtime=runtime)
    try:
        result = harness.execute(str(d.path), arguments)
    except MarkdownCompileError as exc:
        _console.print(f"[red]compile error:[/red] {exc}")
        raise typer.Exit(code=2) from None
    except ProviderError as exc:
        _console.print(f"[red]provider error:[/red] {exc}")
        raise typer.Exit(code=3) from None

    if isinstance(result, ProviderResult):
        _console.print(result.text)
    elif isinstance(result, dict):
        _console.print(result)
    else:
        try:
            for _ in result:
                pass
        except ProviderError as exc:
            _console.print(f"\n[red]provider error during stream:[/red] {exc}")
            raise typer.Exit(code=3) from None


# ---------------------------------------------------------------------------
# Generic group builder
# ---------------------------------------------------------------------------


def _build_definition_group(
    name: str,
    *,
    kind: str,
    scan,
    runner,
    help_text: str,
) -> typer.Typer:
    app = typer.Typer(name=name, help=help_text, no_args_is_help=True)

    @app.command("list")
    def list_cmd() -> None:
        """List every available {kind} discovered on disk."""
        _print_inventory(kind, scan())

    @app.command("describe")
    def describe_cmd(definition_id: str = typer.Argument(..., help=f"{kind} id")) -> None:
        """Show the title, description, and declared inputs of a {kind}."""
        for d in scan():
            if d.id == definition_id:
                _print_inputs(d)
                return
        _console.print(
            f"[red]No {kind} with id[/red] [bold]{definition_id}[/bold]. "
            f"Use `lfc {name} list` to see what's available."
        )
        raise typer.Exit(code=2)

    @app.command(
        "run",
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
            "help_option_names": [],   # disable Click's built-in --help; we render our own
        },
    )
    def run_cmd(
        ctx: typer.Context,
        definition_id: str = typer.Argument("", help=f"{kind} id to invoke"),
        example: str = typer.Option(
            "",
            "--example",
            help="Name of a declared example whose inputs are merged before "
            "explicit --<name>=<value> flags.",
            autocompletion=_complete_example_ids,
        ),
    ) -> None:
        """Run a {kind}. Pass each declared input as ``--<name>=<value>``."""
        extras = list(ctx.args)
        # Treat `lfc <group> run --help` (where --help slid into the positional
        # because definition_id is optional) the same as no-id-with-help.
        if definition_id in ("--help", "-h"):
            extras.insert(0, definition_id)
            definition_id = ""
        wants_help = "--help" in extras or "-h" in extras
        if not definition_id:
            # No id supplied — print the static command help (lists subcommands of this group).
            _console.print(
                f"Usage: [bold]lfc {name} run <{kind}-id> "
                f"[--example=<id>] [--<name>=<value> ...][/bold]\n"
            )
            _console.print(
                f"Run [cyan]lfc {name} list[/cyan] to see every available {kind}, "
                f"or [cyan]lfc {name} run <id> --help[/cyan] for inputs of a specific {kind}."
            )
            raise typer.Exit(code=0 if wants_help else 2)
        for d in scan():
            if d.id == definition_id:
                if wants_help:
                    _print_run_help(d, group=name)
                    return
                args = _parse_kv_args(extras)
                example_inputs = _example_inputs_or_exit(d, example)
                effective = dict(example_inputs)
                effective.update(args)
                missing = [
                    n for n, s in d.inputs.items()
                    if isinstance(s, dict) and s.get("required") and n not in effective
                ]
                if missing or (not effective and d.inputs):
                    _missing_args_help(d, effective)
                    if missing:
                        raise typer.Exit(code=2)
                    return
                runner(d, args, example=example or None)
                return
        _console.print(
            f"[red]No {kind} with id[/red] [bold]{definition_id}[/bold]."
        )
        raise typer.Exit(code=2)

    # Rewrite docstrings so Typer's help text shows the right noun.
    list_cmd.__doc__ = (list_cmd.__doc__ or "").replace("{kind}", kind)
    describe_cmd.__doc__ = (describe_cmd.__doc__ or "").replace("{kind}", kind)
    run_cmd.__doc__ = (run_cmd.__doc__ or "").replace("{kind}", kind)
    return app


# ---------------------------------------------------------------------------
# Service group (special — uses the runtime catalog, not a directory scan)
# ---------------------------------------------------------------------------


def _scan_services() -> list[dict[str, Any]]:
    runtime = _build_yaml_runtime()
    cat: list[dict[str, Any]] = runtime.globals.get("catalog", {}).get("definitions", [])
    out: list[dict[str, Any]] = []
    for entry in cat:
        if not entry.get("has_service"):
            continue
        if entry["id"] == "service.base":
            continue
        out.append(entry)
    return out


def _build_service_group() -> typer.Typer:
    app = typer.Typer(
        name="service",
        help="Manage local services (start, stop, enable, disable, install, uninstall, status).",
        no_args_is_help=True,
    )

    @app.command("list")
    def list_cmd() -> None:
        """List every registered service definition."""
        services = _scan_services()
        if not services:
            _console.print("[yellow]No services found.[/yellow]")
            return
        table = Table(title=f"Available services ({len(services)})")
        table.add_column("id", style="bold cyan", no_wrap=True)
        table.add_column("title")
        for s in services:
            table.add_row(s["id"], _short_desc(s.get("title") or ""))
        _console.print(table)
        _console.print(
            f"\nActions: [bold]{', '.join(_LIFECYCLE_ACTIONS)}[/bold]\n"
            "Run with [cyan]lfc service <action> <service-id>[/cyan] or "
            "[cyan]lfc service action <service-id> <action>[/cyan]."
        )

    @app.command("describe")
    def describe_cmd(service_id: str = typer.Argument(..., help="service id")) -> None:
        """Show metadata for a service definition."""
        for s in _scan_services():
            if s["id"] == service_id:
                _console.print(f"[bold cyan]{s['id']}[/bold cyan]")
                if s.get("title"):
                    _console.print(f"  {s['title']}")
                if s.get("description"):
                    _console.print(f"\n{s['description'].strip()}\n")
                _console.print(
                    f"Available actions: [bold]{', '.join(_LIFECYCLE_ACTIONS)}[/bold]"
                )
                return
        _console.print(f"[red]No service with id[/red] [bold]{service_id}[/bold].")
        raise typer.Exit(code=2)

    def _do_action(service_id: str, action: str) -> None:
        if action not in _LIFECYCLE_ACTIONS:
            _console.print(
                f"[red]Unknown action[/red] [bold]{action}[/bold]. "
                f"Choose one of: {', '.join(_LIFECYCLE_ACTIONS)}."
            )
            raise typer.Exit(code=2)
        if not any(s["id"] == service_id for s in _scan_services()):
            _console.print(
                f"[red]No service with id[/red] [bold]{service_id}[/bold]. "
                "Use `lfc service list` to see what's available."
            )
            raise typer.Exit(code=2)
        runtime = _build_yaml_runtime()
        result = runtime.execute(service_id, arguments={"action": action})
        _console.print(result if result is not None else "[dim]ok[/dim]")

    @app.command("action")
    def action_cmd(
        service_id: str = typer.Argument(..., help="service id"),
        action: str = typer.Argument(
            ...,
            help=f"One of {', '.join(_LIFECYCLE_ACTIONS)}.",
        ),
    ) -> None:
        """Dispatch a lifecycle verb at a service."""
        _do_action(service_id, action)

    # Lifecycle shortcuts: `lfc service start <id>`, etc.
    for verb in _LIFECYCLE_ACTIONS:
        def _make(verb_: str):
            def _cmd(service_id: str = typer.Argument(..., help="service id")) -> None:
                _do_action(service_id, verb_)

            _cmd.__doc__ = f"`{verb_}` the given service."
            _cmd.__name__ = verb_
            return _cmd

        app.command(verb)(_make(verb))

    return app


# ---------------------------------------------------------------------------
# Generic file dispatch (`lfc run <file>`)
# ---------------------------------------------------------------------------


def _build_run_command(parent: typer.Typer) -> None:
    @parent.command(
        "run",
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
            "help_option_names": [],
        },
        help=(
            "Dispatch a .yaml task/workflow or a .md prompt through its runtime. "
            "Pass inputs as --<name>=<value>."
        ),
    )
    def run_file(
        ctx: typer.Context,
        path: Path = typer.Argument(..., exists=True, readable=True),
        definition_id: str = typer.Option(
            "",
            "--id",
            help="Explicit definition id (required when a YAML file declares multiple).",
        ),
        example: str = typer.Option(
            "",
            "--example",
            help="Name of a declared example whose inputs are merged before "
            "explicit --<name>=<value> flags.",
            autocompletion=_complete_example_ids,
        ),
    ) -> None:
        suffix = path.suffix.lower()
        extras = list(ctx.args)
        want_help = "--help" in extras or "-h" in extras
        args = _parse_kv_args(extras)

        if suffix in (".yaml", ".yml"):
            try:
                docs = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                _console.print(f"[red]Invalid YAML:[/red] {exc}")
                raise typer.Exit(code=2) from exc
            if not isinstance(docs, list) or not docs:
                _console.print("[red]YAML file did not contain a list of definitions.[/red]")
                raise typer.Exit(code=2)
            chosen = None
            if definition_id:
                chosen = next(
                    (d for d in docs if isinstance(d, dict) and d.get("id") == definition_id),
                    None,
                )
                if chosen is None:
                    _console.print(
                        f"[red]No definition with id[/red] [bold]{definition_id}[/bold] in {path}."
                    )
                    raise typer.Exit(code=2)
            else:
                chosen = docs[0]
                if len(docs) > 1:
                    ids = [d.get("id") for d in docs if isinstance(d, dict)]
                    available = ", ".join(map(str, ids))
                    _console.print(
                        f"[yellow]File declares multiple definitions; running first[/yellow] "
                        f"({chosen.get('id')}). Pick another with --id from: {available}"
                    )
            if not isinstance(chosen, dict) or "id" not in chosen:
                _console.print("[red]Top-level definition missing an 'id'.[/red]")
                raise typer.Exit(code=2)
            kind = "workflow" if str(chosen["id"]).endswith(".workflow") else "task"
            chosen_examples_raw = chosen.get("examples") or []
            chosen_examples = [
                e for e in chosen_examples_raw if isinstance(e, dict) and "id" in e
            ]
            d = Definition(
                id=chosen["id"],
                title=chosen.get("title") or "",
                description=str(chosen.get("description") or "").strip(),
                inputs=dict(chosen.get("inputs") or {}),
                path=path,
                kind=kind,
                examples=chosen_examples,
            )
            if want_help:
                _print_run_help(d)
                return
            example_inputs = _example_inputs_or_exit(d, example)
            effective = dict(example_inputs)
            effective.update(args)
            missing = [
                n for n, s in d.inputs.items()
                if isinstance(s, dict) and s.get("required") and n not in effective
            ]
            if missing or (not effective and d.inputs):
                _missing_args_help(d, effective)
                if missing:
                    raise typer.Exit(code=2)
                return
            _run_yaml_definition(d, args, example=example or None)
            return

        if suffix == ".md":
            d = _parse_md_prompt(path)
            if d is None:
                _console.print(
                    f"[red]Could not parse a prompt frontmatter from[/red] {path}."
                )
                raise typer.Exit(code=2)
            if want_help:
                _print_run_help(d)
                return
            missing = [
                n for n, s in d.inputs.items()
                if isinstance(s, dict) and s.get("required") and n not in args
            ]
            if missing or (not args and d.inputs):
                _missing_args_help(d, args)
                if missing:
                    raise typer.Exit(code=2)
                return
            _run_prompt(d, args, example=example or None)
            return

        _console.print(
            f"[red]Unsupported file extension[/red] [bold]{suffix}[/bold]. "
            "Expected .yaml, .yml, or .md."
        )
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# Public mounter
# ---------------------------------------------------------------------------


def mount_inventory(root: typer.Typer) -> None:
    """Attach inventory groups + `run` to *root*."""
    root.add_typer(
        _build_definition_group(
            "task",
            kind="task",
            scan=scan_tasks,
            runner=_run_yaml_definition,
            help_text="List, describe, and run YAML tasks from 05_tasks/.",
        ),
        name="task",
    )
    root.add_typer(
        _build_definition_group(
            "workflow",
            kind="workflow",
            scan=scan_workflows,
            runner=_run_yaml_definition,
            help_text="List, describe, and run YAML workflows from 06_workflows/.",
        ),
        name="workflow",
    )
    root.add_typer(
        _build_definition_group(
            "prompt",
            kind="prompt",
            scan=scan_prompts,
            runner=_run_prompt,
            help_text="List, describe, and run markdown prompts from 12_prompts/.",
        ),
        name="prompt",
    )
    root.add_typer(_build_service_group(), name="service")
    _build_run_command(root)
