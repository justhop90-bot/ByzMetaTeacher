"""Machine-checked Byzantine unit materialization seeds for Update 185872.

The seeds are restricted to manifest units whose identity, cost, and train time are
available in the pinned aoe2techtree data.json source. Upgrade chains stop before
trigger technologies that are not yet represented in GameData.
"""

from dataclasses import dataclass

from .game_data import Age, BuildingId, ResourceCost, UnitId, UnitLineId


@dataclass(frozen=True)
class ByzantineManifestUnitSeed:
    id: UnitId
    name: str
    available_age: Age
    provider_building: BuildingId
    line: UnitLineId
    base_cost: ResourceCost
    train_time_seconds: int
    snapshot_name: str
    internal_name: str
    upgrades_from: UnitId | None = None
    upgrades_to: UnitId | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.snapshot_name.strip():
            raise ValueError("unit seed names must not be empty")
        normalize = lambda value: "".join(
            char for char in value.lower() if char.isalnum()
        )
        if normalize(self.name) != normalize(self.snapshot_name):
            raise ValueError(
                f"unit seed '{int(self.id)}' has conflicting manifest/snapshot names"
            )
        if self.train_time_seconds < 0:
            raise ValueError("unit seed train time must be non-negative")
        if not self.internal_name.strip():
            raise ValueError("unit seed internal name must not be empty")


BYZANTINE_MANIFEST_UNIT_SEEDS = (
    ByzantineManifestUnitSeed(
        UnitId(550),
        "Onager",
        Age.IMPERIAL,
        BuildingId(49),
        UnitLineId("mangonel-line"),
        ResourceCost(food=0, wood=160, stone=0, gold=135),
        46,
        undefined,
        "ONAGR",
        UnitId(280),
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(13),
        "Heavy Plow",
        Age.CASTLE,
        BuildingId(68),
        UnitLineId("fishing-ship-line"),
        ResourceCost(food=0, wood=75, stone=0, gold=0),
        40,
        undefined,
        "FSHSP",
        None,
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(545),
        "Transport Ship",
        Age.DARK,
        BuildingId(45),
        UnitLineId("transport-ship-line"),
        ResourceCost(food=0, wood=125, stone=0, gold=0),
        46,
        undefined,
        "XPORT",
        None,
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(539),
        "Galley",
        Age.FEUDAL,
        BuildingId(45),
        UnitLineId("galley-line"),
        ResourceCost(food=0, wood=90, stone=0, gold=30),
        45,
        undefined,
        "SGALY",
        None,
        UnitId(21),
    ),
    ByzantineManifestUnitSeed(
        UnitId(21),
        "War Galley",
        Age.CASTLE,
        BuildingId(45),
        UnitLineId("galley-line"),
        ResourceCost(food=0, wood=90, stone=0, gold=30),
        27,
        undefined,
        "GALLY",
        UnitId(539),
        UnitId(442),
    ),
    ByzantineManifestUnitSeed(
        UnitId(442),
        "Galleon",
        Age.IMPERIAL,
        BuildingId(45),
        UnitLineId("galley-line"),
        ResourceCost(food=0, wood=90, stone=0, gold=30),
        27,
        undefined,
        "WARGA",
        UnitId(21),
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(2626),
        "Hulk",
        Age.FEUDAL,
        BuildingId(45),
        UnitLineId("hulk-line"),
        ResourceCost(food=0, wood=75, stone=0, gold=35),
        42,
        undefined,
        "Hulk",
        None,
        UnitId(2627),
    ),
    ByzantineManifestUnitSeed(
        UnitId(2627),
        "War Hulk",
        Age.CASTLE,
        BuildingId(45),
        UnitLineId("hulk-line"),
        ResourceCost(food=0, wood=75, stone=0, gold=35),
        27,
        undefined,
        "War hulk",
        UnitId(2626),
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(1104),
        "Demolition Raft",
        Age.FEUDAL,
        BuildingId(45),
        UnitLineId("demolition-raft-line"),
        ResourceCost(food=0, wood=45, stone=0, gold=80),
        45,
        undefined,
        "SDGAL",
        None,
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(17),
        "Banking",
        Age.IMPERIAL,
        BuildingId(84),
        UnitLineId("trade-cog-line"),
        ResourceCost(food=0, wood=100, stone=0, gold=50),
        36,
        undefined,
        "COGXX",
        None,
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(83),
        "Villager",
        Age.DARK,
        BuildingId(109),
        UnitLineId("villager-line"),
        ResourceCost(food=50, wood=0, stone=0, gold=0),
        25,
        undefined,
        "VMBAS",
        None,
        None,
    ),
    ByzantineManifestUnitSeed(
        UnitId(128),
        "Trade Cart",
        Age.FEUDAL,
        BuildingId(84),
        UnitLineId("trade-cart-line"),
        ResourceCost(food=0, wood=100, stone=0, gold=50),
        51,
        undefined,
        "TCART",
        None,
        None,
    ),
)\n\n__all__ = ["BYZANTINE_MANIFEST_UNIT_SEEDS", "ByzantineManifestUnitSeed"]\n