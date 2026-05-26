"""Build the router's ROUTES list from the runtime catalog.

Replaces the legacy hardcoded ROUTES literal in scorer.py with a
catalog-driven walk: every definition with `has_route=True` (i.e. every
descendant of `route.base`) is exposed to the scorer as a RouteEntry.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.runtimes.yaml.src import Runtime


@dataclass(frozen=True)
class RouteEntry:
    """A route the scorer can rank."""

    id: str
    description: str
    intent_affinity: tuple[str, ...]
    tier: str
    cost: int
    deferred_model: str | None


def load_routes(runtime: Runtime) -> list[RouteEntry]:
    """Return one RouteEntry per `has_route` catalog definition.

    Routes are read from each definition's resolved variables block
    (intent_affinity, tier, cost, deferred_model). Routes with no
    intent_affinity are still returned — the scorer can decide how to
    handle them.
    """
    routes: list[RouteEntry] = []
    for entry in runtime.globals["catalog"]["definitions"]:
        if not entry.get("has_route"):
            continue
        # Pull the resolved values for the route's variables.
        assembled = runtime.assemble_definition_frame(entry["id"])
        variables = assembled.variables
        intent = tuple(variables.get("intent_affinity") or [])
        tier = str(variables.get("tier") or "LOCAL")
        cost = int(variables.get("cost") or 0)
        deferred = str(variables.get("deferred_model") or "") or None
        routes.append(
            RouteEntry(
                id=entry["id"],
                description=entry.get("description") or "",
                intent_affinity=intent,
                tier=tier,
                cost=cost,
                deferred_model=deferred,
            )
        )
    return routes
