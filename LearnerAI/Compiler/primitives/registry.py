"""Small authoritative primitive profile for the first Basilisk compiler slice.

This registry is intentionally explicit. Unknown commands are errors rather than
being silently passed through as if the compiler understood them.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Primitive:
    name: str
    kind: str
    role: str
    min_args: int
    max_args: int
    version: str = "DE"
    completion_witness: bool = True

class PrimitiveRegistry:
    def __init__(self, primitives: tuple[Primitive, ...]):
        self._items = {p.name: p for p in primitives}

    def get(self, name: str) -> Primitive | None:
        return self._items.get(name)

    def require(self, name: str) -> Primitive:
        item = self.get(name)
        if item is None:
            raise KeyError(name)
        return item

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

def default_de_registry() -> PrimitiveRegistry:
    facts = [
        Primitive("current-age", "FACT", "OBSERVATION", 2, 2),
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
        Primitive("build", "ACTION", "ACTION", 1, 1),
        Primitive("train", "ACTION", "ACTION", 1, 1),
        Primitive("research", "ACTION", "ACTION", 1, 1),
    ]
    return PrimitiveRegistry(tuple(facts + actions))
