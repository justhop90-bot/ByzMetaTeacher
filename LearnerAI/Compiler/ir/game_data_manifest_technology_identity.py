"""Explicit Byzantine technology identities whose fields are absent from the pinned snapshot.

These identities exist to make manifest-declared upgrade triggers usable without
inventing research-time data. Fixed costs are recorded only where current public
engine documentation provides them; unresolved research time remains None.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, ResourceCost, TechId


@dataclass(frozen=True)
class ByzantineManifestTechnologyIdentitySeed:
    id: TechId
    name: str
    available_age: Age
    provider_building: BuildingId
    base_cost: ResourceCost | None
    research_time_seconds: int | None
    provenance_label: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("technology identity name must not be empty")
        if not self.provenance_label.strip():
            raise ValueError("technology identity provenance label must not be empty")
        if self.research_time_seconds is not None and self.research_time_seconds < 0:
            raise ValueError("technology identity research time must be non-negative")


BYZANTINE_MANIFEST_TECHNOLOGY_IDENTITY_SEEDS = (
    ByzantineManifestTechnologyIdentitySeed(
        TechId(905),
        "Demolition Ship",
        Age.CASTLE,
        BuildingId(45),
        ResourceCost(wood=150, gold=100),
        None,
        "official 2026 naval update",
    ),
    ByzantineManifestTechnologyIdentitySeed(
        TechId(244),
        "Heavy Demolition Ship",
        Age.IMPERIAL,
        BuildingId(45),
        ResourceCost(wood=250, gold=350),
        None,
        "official 2026 naval update",
    ),
)


__all__ = [
    "BYZANTINE_MANIFEST_TECHNOLOGY_IDENTITY_SEEDS",
    "ByzantineManifestTechnologyIdentitySeed",
]
