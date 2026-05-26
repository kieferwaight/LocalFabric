"""AST-based introspection of Python packages, for barrel `__init__.py` generation.

The runtime calls this from `stdlib.python.barrel` to scan a package directory,
read each module's `__all__`, and feed the results into a Jinja template that
renders the package's `__init__.py`.

We use `ast.parse` rather than importing the modules: imports would execute
module-level code (including circular ones) and require the target package to
be installed, which a generator must not assume.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModuleExports:
    name: str               # `.compiler` or `.src` — sibling module name
    is_subpackage: bool     # True for subdirs containing __init__.py
    docstring: str          # First line of the module docstring (or "")
    exports: list[str]      # Names from the module's `__all__`


def discover_modules(package_dir: Path) -> list[Path]:
    """Direct children of `package_dir` that can contribute to a barrel.

    Returns sibling `.py` files (excluding `__init__.py` and names starting
    with `_`) plus subdirectories containing an `__init__.py`. The returned
    paths point at the `.py` file or subpackage `__init__.py`, so callers can
    AST-parse them uniformly.
    """
    if not package_dir.is_dir():
        raise ValueError(f"Not a directory: {package_dir}")
    items: list[Path] = []
    for child in sorted(package_dir.iterdir()):
        if child.name.startswith(".") or child.name.startswith("_"):
            continue
        if child.is_file() and child.suffix == ".py":
            items.append(child)
        elif child.is_dir() and (child / "__init__.py").exists():
            items.append(child / "__init__.py")
    return items


def _parse_all_assignment(tree: ast.Module) -> list[str] | None:
    """Return the literal names from `__all__ = [...]` at module top level.

    Returns `None` if no `__all__` is declared (so callers can fall back to
    public-name inference). Returns `[]` if `__all__` is declared but empty or
    not a static literal — a deliberate "export nothing" signal.
    """
    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                break
        else:
            continue
        if not isinstance(value, (ast.List, ast.Tuple)):
            return []
        names: list[str] = []
        for element in value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                names.append(element.value)
        return names
    return None


def _infer_public_names(tree: ast.Module) -> list[str]:
    """Fallback when `__all__` is absent: every top-level public name.

    Picks up `class Foo`, `def foo`, and `Foo = ...` at module scope, skipping
    underscore-prefixed names and dunders. Re-exported imports
    (`from x import y`) are excluded — a barrel of barrels should declare its
    surface explicitly via `__all__`.
    """
    names: list[str] = []
    seen: set[str] = set()
    for node in tree.body:
        candidates: list[str] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            candidates.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    candidates.append(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            candidates.append(node.target.id)
        for name in candidates:
            if name.startswith("_") or name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def read_module_exports(module_path: Path) -> ModuleExports:
    """Parse a `.py` file and extract its barrel-relevant metadata.

    `name` is the importable suffix used after the leading dot in
    `from .name import ...`. For a sibling `compiler.py` that's `compiler`;
    for a subpackage `src/__init__.py` that's `src`.
    """
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))
    raw_docstring = ast.get_docstring(tree) or ""
    docstring = raw_docstring.strip().splitlines()[0] if raw_docstring.strip() else ""
    declared = _parse_all_assignment(tree)
    exports = declared if declared is not None else _infer_public_names(tree)
    if module_path.name == "__init__.py":
        name = module_path.parent.name
        is_subpackage = True
    else:
        name = module_path.stem
        is_subpackage = False
    return ModuleExports(
        name=name,
        is_subpackage=is_subpackage,
        docstring=docstring,
        exports=exports,
    )


def scan_package(
    package_dir: Path, exclude: list[str] | None = None
) -> list[dict[str, object]]:
    """Return one entry per barrel-relevant child of `package_dir`.

    Entries with an empty `exports` list are dropped — re-exporting nothing is
    not useful, and a missing `__all__` is usually a signal the module isn't
    meant to participate in a barrel. Names listed in `exclude` are skipped
    explicitly; use this for CLI entry-point modules or test helpers that
    happen to live in the package directory but aren't part of its API.
    """
    skip = set(exclude or [])
    out: list[dict[str, object]] = []
    for path in discover_modules(package_dir):
        meta = read_module_exports(path)
        if meta.name in skip:
            continue
        # Subpackages are namespaces and worth exposing even when empty.
        # A `.py` module with no exports is usually implementation-internal —
        # re-exporting nothing from it is just noise, so skip.
        if not meta.is_subpackage and not meta.exports:
            continue
        out.append({
            "name": meta.name,
            "is_subpackage": meta.is_subpackage,
            "docstring": meta.docstring,
            "exports": list(meta.exports),
        })
    return out
