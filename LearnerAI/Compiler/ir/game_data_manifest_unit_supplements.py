"""Explicit Byzantine unit supplements whose factual fields are not present in the pinned 185872 subset.

Carrack is separated from the snapshot-backed seeds because the pinned unit snapshot
does not contain the new Hulk-line end state. Its upgrade trigger is the existing
public Heavy Warships technology rather than an invented hidden TechId.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, ResourceCost, UnitId, UnitLineId


@dataclass(frozen=True)
class ByzantineManifestUnitSupplementSeed:
    id: UnitId
    name: str
    available_age: Age
    provider_building: BuildingId
    line: UnitLineId
    base_cost: ResourceCost
    train_time_seconds: int
    upgrades_from: UnitId | None = None
    upgrades_to: UnitId | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("unit supplement name must not be empty")
        if self.train_time_seconds < 0:
            raise ValueError("unit supplement train time must be non-negative")


BYZANTINE_MANIFEST_UNIT_SUPPLEMENT_SEEDS = (
    ByzantineManifestUnitSupplementSeed(
        UnitId(2628),
        "Carrack",
        Age.IMPERIAL,
        BuildingId(45),
        UnitLineId("hulk-line"),
        ResourceCost(wood=75, gold=35),
        27,
        upgrades_from=UnitId(2627),
    ),
)


__all__ = [
    "BYZANTINE_MANIFEST_UNIT_SUPPLEMENT_SEEDS",
    "ByzantineManifestUnitSupplementSeed",
]
