"""Typed map-policy metadata for the Byzantine strategy compiler."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MapKind(str, Enum):
    ARABIA = "ARABIA"
    ARENA = "ARENA"
    STANDARD_LAND = "STANDARD_LAND"
    HYBRID = "HYBRID"
    ISLANDS = "ISLANDS"


@dataclass(frozen=True)
class MapProfile:
    """Policy metadata for one supported map family.

    Native detection remains an observation concern. This type records the
    compiler's strategy envelope and the default policy associated with it.
    """

    identity: MapKind
    default_opening: str
    native_map_expression: str | None = None
    water_expected: bool = False

    def __post_init__(self) -> None:
        if not self.default_opening.strip():
            raise ValueError("map profile default opening must not be empty")
        if self.native_map_expression is not None and not self.native_map_expression.strip():
            raise ValueError("map profile native expression must not be empty")


def default_byzantine_map_profiles() -> tuple[MapProfile, ...]:
    return (
        MapProfile(MapKind.ARABIA, "DEFENSIVE_STANDARD", "(map-type arabia)"),
        MapProfile(MapKind.ARENA, "FAST_CASTLE", "(map-type arena)"),
        MapProfile(MapKind.STANDARD_LAND, "DEFENSIVE_STANDARD"),
        MapProfile(MapKind.HYBRID, "DEFENSIVE_STANDARD"),
        MapProfile(
            MapKind.ISLANDS,
            "WATER_ECONOMY",
            "(or (map-type islands) (map-type pacific-islands))",
            True,
        ),
    )


__all__ = ("MapKind", "MapProfile", "default_byzantine_map_profiles")
