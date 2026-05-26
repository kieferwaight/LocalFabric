"""Workspace-layout sanity checks.

Catches drift between the on-disk numeric-bucket structure and the
pyproject manifest: every bucket must be either packaged or explicitly
excluded; the manifest must not reference buckets that no longer exist;
the MCP sdk override must resolve to a real package.
"""
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_pyproject() -> dict:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def _numeric_buckets() -> list[str]:
    return sorted(
        p.name
        for p in PROJECT_ROOT.iterdir()
        if p.is_dir() and p.name[:2].isdigit() and "_" in p.name
    )


def test_every_numeric_bucket_is_packaged_or_excluded():
    cfg = _load_pyproject()
    package_dir = cfg["tool"]["setuptools"]["package-dir"]
    excluded = set(cfg["tool"]["localfabric"]["workspace_manifest"]["excluded_buckets"])
    packaged = {path.split("/", 1)[0] for path in package_dir.values()}

    for bucket in _numeric_buckets():
        is_packaged = bucket in packaged
        is_excluded = bucket in excluded

        assert is_packaged or is_excluded, (
            f"DIVERGENCE: physical folder '{bucket}' is on disk but appears in "
            f"neither [tool.setuptools].package-dir nor "
            f"[tool.localfabric.workspace_manifest].excluded_buckets."
        )
        assert not (is_packaged and is_excluded), (
            f"CONFLICT: '{bucket}' is listed as both packaged and excluded."
        )


def test_no_phantom_excluded_or_packaged_entries():
    """Every bucket named in the manifest must exist on disk."""
    cfg = _load_pyproject()
    package_dir = cfg["tool"]["setuptools"]["package-dir"]
    excluded = set(cfg["tool"]["localfabric"]["workspace_manifest"]["excluded_buckets"])
    packaged = {path.split("/", 1)[0] for path in package_dir.values()}
    on_disk = set(_numeric_buckets())

    phantom_packaged = packaged - on_disk
    phantom_excluded = excluded - on_disk

    assert not phantom_packaged, (
        f"package-dir points at non-existent buckets: {sorted(phantom_packaged)}"
    )
    assert not phantom_excluded, (
        f"excluded_buckets lists non-existent buckets: {sorted(phantom_excluded)}"
    )


def test_mcp_sdk_override_resolves_to_a_real_package():
    """system_sdk_override must name an enumerated package in pyproject."""
    cfg = _load_pyproject()
    override = cfg["tool"]["localfabric"]["mcp_mapping"]["system_sdk_override"]
    packages = set(cfg["tool"]["setuptools"]["packages"])

    assert override in packages, (
        f"system_sdk_override = '{override}' is not enumerated in "
        f"[tool.setuptools].packages — the override would be silently inert."
    )
    assert override != "mcp", (
        "system_sdk_override must NOT be 'mcp' — that would shadow the PyPI "
        "mcp package, which the MCP server imports from."
    )
