"""Machine-checked Byzantine building materialization seeds for Update 185872.

Fish Trap's manifest provider building is retained as source metadata because the
current BuildingDef IR has no provider field; no synthetic provider semantics are added.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, ResourceCost


@dataclass(frozen=True)
class ByzantineManifestBuildingSeed:
    id: BuildingId
    name: str
    available_age: Age
    base_cost: ResourceCost
    provider_building: BuildingId
    snapshot_name: str
    internal_name: str
    hp: int
    train_time_seconds: int
    link: int | None = None
    trigger: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.snapshot_name.strip():
            raise ValueError("building seed names must not be empty")
        normalize = lambda value: "".join(
            char for char in value.lower() if char.isalnum()
        )
        if normalize(self.name) != normalize(self.snapshot_name):
            raise ValueError(
                f"building seed '{int(self.id)}' has conflicting manifest/snapshot names"
            )
        if self.hp < 0 or self.train_time_seconds < 0:
            raise ValueError("building seed HP/train time must be non-negative")


BYZANTINE_MANIFEST_BUILDING_SEEDS = (
    ByzantineManifestBuildingSeed(
        BuildingId(199),
        "Fish Trap",
        Age.FEUDAL,
        ResourceCost(wood=100),
        BuildingId(45),
        "Fish Trap",
        "FTRAP",
        250,
        40,
        None,
        None,
    ),
)


__all__ = ["BYZANTINE_MANIFEST_BUILDING_SEEDS", "ByzantineManifestBuildingSeed"]
