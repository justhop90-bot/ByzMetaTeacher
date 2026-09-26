"""Typed factual GameData for the Basilisk compiler."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import NewType

from .versioning import EvidenceRef, PatchChange, PatchId, Validity

BuildingId = NewType("BuildingId", int)
UnitId = NewType("UnitId", int)
TechId = NewType("TechId", int)
CivId = NewType("CivId", int)
AgeAdvanceId = NewType("AgeAdvanceId", str)
UnitLineId = NewType("UnitLineId", str)


class Age(str, Enum):
    DARK = "DARK"
    FEUDAL = "FEUDAL"
    CASTLE = "CASTLE"
    IMPERIAL = "IMPERIAL"


class Resource(str, Enum):
    FOOD = "FOOD"
    WOOD = "WOOD"
    GOLD = "GOLD"
    STONE = "STONE"


class ModifierOperation(str, Enum):
    MULTIPLY = "MULTIPLY"
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"


class RoundingMode(str, Enum):
    NONE = "NONE"
    ENGINE_NEAREST = "ENGINE_NEAREST"


@dataclass(frozen=True, order=True)
class Rational:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator <= 0:
            raise ValueError("Rational denominator must be positive")


@dataclass(frozen=True)
class ResourceCost:
    food: int = 0
    wood: int = 0
    gold: int = 0
    stone: int = 0

    def __post_init__(self) -> None:
        if min(self.food, self.wood, self.gold, self.stone) < 0:
            raise ValueError("Resource costs cannot be negative")

    def scaled(self, factor: Rational, rounding: RoundingMode) -> "ResourceCost":
        def apply(value: int) -> int:
            raw_num = value * factor.numerator
            den = factor.denominator
            if rounding is RoundingMode.NONE:
                if raw_num % den:
                    raise ValueError("fractional resource cost requires explicit rounding")
                return raw_num // den
            if rounding is RoundingMode.ENGINE_NEAREST:
                return (raw_num + den // 2) // den
            raise ValueError(f"unsupported rounding mode: {rounding}")

        return ResourceCost(
            food=apply(self.food),
            wood=apply(self.wood),
            gold=apply(self.gold),
            stone=apply(self.stone),
        )


@dataclass(frozen=True)
class NumericModifier:
    operation: ModifierOperation
    value: Rational | int
    rounding: RoundingMode = RoundingMode.NONE


class SelectorKind(str, Enum):
    BUILDING = "BUILDING"
    UNIT = "UNIT"
    UNIT_LINE = "UNIT_LINE"
    TECHNOLOGY = "TECHNOLOGY"
    AGE_ADVANCE = "AGE_ADVANCE"
    BUILDING_CLASS = "BUILDING_CLASS"
    UNIT_CLASS = "UNIT_CLASS"
    AGE = "AGE"


@dataclass(frozen=True)
class EntitySelector:
    kind: SelectorKind
    ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    ages: tuple[Age, ...] = ()

    @staticmethod
    def unit(unit_id: UnitId) -> "EntitySelector":
        return EntitySelector(SelectorKind.UNIT, ids=(str(int(unit_id)),))

    @staticmethod
    def unit_line(line: UnitLineId) -> "EntitySelector":
        return EntitySelector(SelectorKind.UNIT_LINE, ids=(str(line),))

    @staticmethod
    def building(building_id: BuildingId) -> "EntitySelector":
        return EntitySelector(SelectorKind.BUILDING, ids=(str(int(building_id)),))

    @staticmethod
    def tech(tech_id: TechId) -> "EntitySelector":
        return EntitySelector(SelectorKind.TECHNOLOGY, ids=(str(int(tech_id)),))

    @staticmethod
    def unit_class(tag: str) -> "EntitySelector":
        return EntitySelector(SelectorKind.UNIT_CLASS, tags=(tag,))

    @staticmethod
    def age(age: Age) -> "EntitySelector":
        return EntitySelector(SelectorKind.AGE, ages=(age,))

    @staticmethod
    def buildings_at_age(age: Age) -> "EntitySelector":
        return EntitySelector(SelectorKind.BUILDING_CLASS, ages=(age,))

    @staticmethod
    def age_advance(age: Age) -> "EntitySelector":
        return EntitySelector(SelectorKind.AGE_ADVANCE, ids=(age.value,))


@dataclass(frozen=True)
class Prerequisite:
    kind: str
    age: Age | None = None
    building: BuildingId | None = None
    technology: TechId | None = None
    entity: str | None = None
    count: int | None = None
    children: tuple["Prerequisite", ...] = ()


@dataclass(frozen=True)
class ProductionProvider:
    building: BuildingId


@dataclass(frozen=True)
class ResearchProvider:
    building: BuildingId


@dataclass(frozen=True)
class TechEffect:
    kind: str
    target: EntitySelector
    attribute: str | None = None
    modifier: NumericModifier | None = None
    interaction_id: str | None = None


@dataclass(frozen=True)
class UnitLineDef:
    id: UnitLineId
    name: str
    members: tuple[UnitId, ...]
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class BuildingDef:
    id: BuildingId
    name: str
    available_age: Age
    base_cost: ResourceCost | None
    prerequisites: tuple[Prerequisite, ...] = ()
    trainable_lines: tuple[UnitLineId, ...] = ()
    researchable_technologies: tuple[TechId, ...] = ()
    classes: tuple[str, ...] = ()
    validity: Validity | None = None
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class UnitDef:
    id: UnitId
    name: str
    line: UnitLineId
    available_age: Age
    providers: tuple[ProductionProvider, ...]
    base_cost: ResourceCost | None
    train_time_seconds: int | None
    prerequisites: tuple[Prerequisite, ...] = ()
    upgrades_from: UnitId | None = None
    upgrades_to: UnitId | None = None
    classes: tuple[str, ...] = ()
    validity: Validity | None = None
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class AgeAdvanceDef:
    id: AgeAdvanceId
    age: Age
    provider_building: BuildingId
    base_cost: ResourceCost | None
    research_time_seconds: int | None
    prerequisites: tuple[Prerequisite, ...] = ()
    validity: Validity | None = None
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class TechnologyDef:
    id: TechId
    name: str
    available_age: Age
    providers: tuple[ResearchProvider, ...]
    base_cost: ResourceCost | None
    research_time_seconds: int | None
    prerequisites: tuple[Prerequisite, ...] = ()
    unlocks_units: tuple[UnitId, ...] = ()
    unlocks_buildings: tuple[BuildingId, ...] = ()
    effects: tuple[TechEffect, ...] = ()
    upgrades: tuple[UnitId, ...] = ()
    validity: Validity | None = None
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class GameData:
    patch: PatchId
    buildings: tuple[BuildingDef, ...]
    units: tuple[UnitDef, ...]
    unit_lines: tuple[UnitLineDef, ...]
    technologies: tuple[TechnologyDef, ...]
    age_advances: tuple[AgeAdvanceDef, ...]
    patch_changes: tuple[PatchChange, ...] = ()
    provenance: tuple[EvidenceRef, ...] = ()

    def building(self, building_id: int) -> BuildingDef:
        return _lookup(self.buildings, BuildingId(building_id), "building")

    def unit(self, unit_id: int) -> UnitDef:
        return _lookup(self.units, UnitId(unit_id), "unit")

    def tech(self, tech_id: int) -> TechnologyDef:
        return _lookup(self.technologies, TechId(tech_id), "technology")

    def age_advance(self, age: Age) -> AgeAdvanceDef:
        for item in self.age_advances:
            if item.age is age:
                return item
        raise KeyError(f"unknown age advance {age.value}")

    def unit_line(self, line_id: UnitLineId | str) -> UnitLineDef:
        return _lookup(self.unit_lines, UnitLineId(line_id), "unit line")


def validate_game_data(data: GameData) -> None:
    _unique(data.buildings, "building")
    _unique(data.units, "unit")
    _unique(data.technologies, "technology")
    _unique(data.age_advances, "age-advance")
    _unique(data.unit_lines, "unit-line")

    building_ids = {item.id for item in data.buildings}
    unit_ids = {item.id for item in data.units}
    tech_ids = {item.id for item in data.technologies}
    line_ids = {item.id for item in data.unit_lines}
    age_advance_ids = {item.id for item in data.age_advances}

    for building in data.buildings:
        for line in building.trainable_lines:
            if line not in line_ids:
                raise ValueError(f"building {building.id} references unknown unit line {line}")
        for tech in building.researchable_technologies:
            if tech not in tech_ids:
                raise ValueError(f"building {building.id} references unknown technology {tech}")

    for unit in data.units:
        if unit.line not in line_ids:
            raise ValueError(f"unit {unit.id} references unknown unit line {unit.line}")
        for provider in unit.providers:
            if provider.building not in building_ids:
                raise ValueError(
                    f"unit {unit.id} references unknown provider building {provider.building}"
                )
        if unit.upgrades_from is not None and unit.upgrades_from not in unit_ids:
            raise ValueError(f"unit {unit.id} references unknown upgrade predecessor")
        if unit.upgrades_to is not None and unit.upgrades_to not in unit_ids:
            raise ValueError(f"unit {unit.id} references unknown upgrade successor")

    for age_advance in data.age_advances:
        if age_advance.provider_building not in building_ids:
            raise ValueError(
                f"age advance {age_advance.id} references unknown provider building {age_advance.provider_building}"
            )
        for prereq in age_advance.prerequisites:
            if prereq.technology is not None and prereq.technology not in tech_ids:
                raise ValueError(
                    f"age advance {age_advance.id} references unknown prerequisite technology {prereq.technology}"
                )

    for tech in data.technologies:
        for provider in tech.providers:
            if provider.building not in building_ids:
                raise ValueError(
                    f"technology {tech.id} references unknown provider building {provider.building}"
                )
        for unit_id in tech.unlocks_units:
            if unit_id not in unit_ids:
                raise ValueError(f"technology {tech.id} references unknown unit {unit_id}")
        for building_id in tech.unlocks_buildings:
            if building_id not in building_ids:
                raise ValueError(f"technology {tech.id} references unknown building {building_id}")


def canonical_fingerprint(value: object) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _canonical(val) for key, val in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {
            field: _canonical(getattr(value, field))
            for field in value.__dataclass_fields__
        }
    return str(value)


def _unique(items: tuple[object, ...], kind: str) -> None:
    seen: set[object] = set()
    for item in items:
        item_id = getattr(item, "id")
        if item_id in seen:
            raise ValueError(f"duplicate {kind} id {item_id}")
        seen.add(item_id)


def _lookup(items: tuple[object, ...], item_id: object, label: str):
    for item in items:
        if getattr(item, "id") == item_id:
            return item
    raise KeyError(f"unknown {label} id {item_id}")
