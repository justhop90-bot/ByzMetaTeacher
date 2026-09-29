"""Explicit Byzantine technology identity-conflict overrides for Update 185872.

These seeds are intentionally separate from the pinned aoe2techtree snapshot seeds:
the snapshot uses the same numeric IDs for different technology identities.  These
records therefore require independent source evidence and must never be merged by ID
through the normal snapshot identity-safe materializer.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, ResourceCost, TechId


@dataclass(frozen=True)
class ByzantineManifestTechnologyConflictSeed:
    id: TechId
    name: str
    available_age: Age
    provider_building: BuildingId
    base_cost: ResourceCost
    research_time_seconds: int
    conflicting_snapshot_name: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.conflicting_snapshot_name.strip():
            raise ValueError("technology conflict seed names must not be empty")
        normalize = lambda value: "".join(
            char for char in value.lower() if char.isalnum()
        )
        if normalize(self.name) == normalize(self.conflicting_snapshot_name):
            raise ValueError(
                f"technology conflict seed '{int(self.id)}' must represent a name identity conflict"
            )
        if self.research_time_seconds < 0:
            raise ValueError("technology conflict research time must be non-negative")


BYZANTINE_MANIFEST_TECHNOLOGY_CONFLICT_SEEDS = (
    ByzantineManifestTechnologyConflictSeed(
        TechId(54),
        "Treadmill Crane",
        Age.CASTLE,
        BuildingId(209),
        ResourceCost(wood=200, stone=50),
        20,
        "Stone cutting",
    ),
    ByzantineManifestTechnologyConflictSeed(
        TechId(909),
        "Siphons",
        Age.CASTLE,
        BuildingId(209),
        ResourceCost(food=100, gold=175),
        45,
        "Carvel Hull",
    ),
)


__all__ = [
    "BYZANTINE_MANIFEST_TECHNOLOGY_CONFLICT_SEEDS",
    "ByzantineManifestTechnologyConflictSeed",
]
