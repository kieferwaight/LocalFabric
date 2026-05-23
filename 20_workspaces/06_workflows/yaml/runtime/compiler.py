"""YAML parser → Definition registry with structural validation and cycle detection."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set

import yaml

from .definition import Definition


class Compiler:
    def __init__(self, registry: Dict[str, Definition]):
        self.registry = registry

    def import_file(self, path: str) -> List[Definition]:
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        return self.import_raw(raw)

    def import_raw(self, raw: object) -> List[Definition]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError("YAML root must be a list of definitions.")
        loaded: List[Definition] = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise ValueError(f"Definition entries must be mappings, got {type(entry).__name__}.")
            definition = Definition.from_dict(entry)
            if definition.id in self.registry:
                # later imports override earlier ones — the spec keeps this lenient
                pass
            self.registry[definition.id] = definition
            loaded.append(definition)
        self.validate_all()
        return loaded

    def validate_all(self) -> None:
        for def_id in list(self.registry.keys()):
            self._validate_references(def_id)
        visited: Set[str] = set()
        for def_id in list(self.registry.keys()):
            self.detect_cycle(def_id, visited, set())

    def _validate_references(self, def_id: str) -> None:
        target = self.registry[def_id]
        if target.extends and target.extends not in self.registry:
            raise ValueError(
                f"Definition {def_id!r} extends unknown definition {target.extends!r}."
            )
        for mixin in target.mixins:
            if mixin not in self.registry:
                raise ValueError(
                    f"Definition {def_id!r} uses unknown mixin {mixin!r}."
                )

    def detect_cycle(self, def_id: str, visited: Set[str], processing: Set[str]) -> None:
        if def_id in processing:
            raise ValueError(f"Cyclic inheritance detected: {def_id} forms a loop.")
        if def_id in visited:
            return
        if def_id not in self.registry:
            raise ValueError(f"Unknown definition referenced: {def_id!r}.")
        processing.add(def_id)
        target = self.registry[def_id]
        if target.extends:
            self.detect_cycle(target.extends, visited, processing)
        for mixin in target.mixins:
            self.detect_cycle(mixin, visited, processing)
        processing.remove(def_id)
        visited.add(def_id)
