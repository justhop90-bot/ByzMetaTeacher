"""Semantic adapters backed by the checked-in AIRef native command schema."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .native_schema import NativeCommandRegistry, load_default_native_schema


@dataclass(frozen=True)
class Primitive:
    name: str
    kind: str
    role: str
    min_args: int
    max_args: int
    version: str = "DE"
    completion_witness: bool = True
    conflict_class: str | None = None

class PrimitiveRegistry:
    def __init__(
        self,
        primitives: tuple[Primitive, ...],
        native_registry: NativeCommandRegistry | None = None,
    ):
        self._items = {p.name: p for p in primitives}
        self._native = native_registry

    def get(self, name: str) -> Primitive | None:
        return self._items.get(name)

    def require(self, name: str) -> Primitive:
        item = self.get(name)
        if item is None:
            raise KeyError(name)
        return item

    def native(self, name: str):
        return self._native.get(name) if self._native is not None else None

    def require_native(self, name: str):
        item = self.native(name)
        if item is None:
            raise KeyError(name)
        return item

    def validate_native_signature(self, name: str, arg_count: int) -> None:
        native = self.require_native(name)
        if arg_count != native.parameter_count:
            raise ValueError(
                f"native command '{name}' expects exactly "
                f"{native.parameter_count} argument(s), got {arg_count}"
            )

    def validate_adapter_contract(self, primitive: Primitive) -> None:
        native = self.require_native(primitive.name)
        expected = "Action" if primitive.kind == "ACTION" else "Fact"
        if native.command_type != expected:
            raise ValueError(
                f"semantic adapter kind mismatch for '{primitive.name}': "
                f"adapter={primitive.kind}, native={native.command_type}"
            )
        if not (primitive.min_args <= native.parameter_count <= primitive.max_args):
            raise ValueError(
                f"semantic adapter arity mismatch for '{primitive.name}': "
                f"native={native.parameter_count}, "
                f"semantic={primitive.min_args}..{primitive.max_args}"
            )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

def default_de_registry(schema_path: Path | None = None) -> PrimitiveRegistry:
    facts = [
        Primitive("current-age", "FACT", "OBSERVATION", 2, 2),
        Primitive("food-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("wood-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("gold-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("stone-amount", "FACT", "OBSERVATION", 2, 2),
        Primitive("players-unit-type-count", "FACT", "OBSERVATION", 4, 4),
        Primitive("players-building-type-count", "FACT", "OBSERVATION", 4, 4),
        Primitive("game-time", "FACT", "TIMING", 2, 2, completion_witness=False),
        Primitive("dropsite-min-distance", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("building-available", "FACT", "ADMISSIBILITY", 1, 1),
        Primitive("can-afford-building", "FACT", "RESOURCE_ARBITRATION", 1, 1),
        Primitive("can-build", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-build-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("building-type-count", "FACT", "OBSERVATION", 3, 3),
        Primitive("building-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("unit-type-count", "FACT", "OBSERVATION", 3, 3),
        Primitive("unit-type-count-total", "FACT", "OBSERVATION", 3, 3, completion_witness=False),
        Primitive("can-train", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-train-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("up-pending-objects", "FACT", "OBSERVATION", 4, 4, completion_witness=False),
        Primitive("research-available", "FACT", "ADMISSIBILITY", 1, 1),
        Primitive("can-afford-research", "FACT", "RESOURCE_ARBITRATION", 1, 1),
        Primitive("can-research", "FACT", "FEASIBILITY", 1, 1),
        Primitive("can-research-with-escrow", "FACT", "FEASIBILITY", 1, 1),
        Primitive("research-completed", "FACT", "WITNESS", 1, 1, completion_witness=True),
    ]
    actions = [
        Primitive(
            "build",
            "ACTION",
            "ACTION",
            1,
            1,
            completion_witness=False,
            conflict_class="BUILD_PASS_SINGLETON",
        ),
        Primitive("train", "ACTION", "ACTION", 1, 1, completion_witness=False),
        Primitive("research", "ACTION", "ACTION", 1, 1, completion_witness=False),
    ]
    native_registry = (
        load_default_native_schema()
        if schema_path is None
        else NativeCommandRegistry.from_path(schema_path)
    )
    registry = PrimitiveRegistry(tuple(facts + actions), native_registry)
    for primitive in facts + actions:
        registry.validate_adapter_contract(primitive)
    return registry
