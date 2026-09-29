"""Explicit Byzantine unit identities whose authoritative costs/train times are unresolved.

These records establish the identity, provider, age, line, and upgrade links needed
for the compiler graph. Unknown fixed fields remain None and are never synthesized.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, UnitId, UnitLineId


@dataclass(frozen=True)
class ByzantineManifestUnitIdentitySeed:
    id: UnitId
    name: str
    available_age: Age
    provider_building: BuildingId
    line: UnitLineId
    base_cost: None = None
    train_time_seconds: None = None
    upgrades_from: UnitId | None = None
    upgrades_to: UnitId | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("unit identity name must not be empty")


BYZANTINE_MANIFEST_UNIT_IDENTITY_SEEDS = (
    ByzantineManifestUnitIdentitySeed(
        UnitId(527),
        "Demolition Ship",
        Age.CASTLE,
        BuildingId(45),
        UnitLineId("demolition-raft-line"),
        upgrades_from=UnitId(1104),
        upgrades_to=UnitId(528),
    ),
    ByzantineManifestUnitIdentitySeed(
        UnitId(528),
        "Heavy Demolition Ship",
        Age.IMPERIAL,
        BuildingId(45),
        UnitLineId("demolition-raft-line"),
        upgrades_from=UnitId(527),
    ),
)


__all__ = [
    "BYZANTINE_MANIFEST_UNIT_IDENTITY_SEEDS",
    "ByzantineManifestUnitIdentitySeed",
]
