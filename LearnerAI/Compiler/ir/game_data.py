"""Typed factual GameData for the Basilisk compiler."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from math import gcd
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


class GameDataScope(str, Enum):
    UNIVERSAL = "UNIVERSAL"
    CIVILIZATION = "CIVILIZATION"


class CoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    FACTUAL_SUBSET = "FACTUAL_SUBSET"
    UNKNOWN = "UNKNOWN"


class PrerequisiteKind(str, Enum):
    AGE = "AGE"
    BUILDING = "BUILDING"
    BUILDING_COUNT = "BUILDING_COUNT"
    TECHNOLOGY_RESEARCHED = "TECHNOLOGY_RESEARCHED"
    UNIT = "UNIT"
    UNIT_COUNT = "UNIT_COUNT"
    ENTITY_COUNT = "ENTITY_COUNT"
    ALL = "ALL"
    ANY = "ANY"
    N_OF = "N_OF"


class TechEffectKind(str, Enum):
    STAT_MODIFIER = "STAT_MODIFIER"
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    INTERACTION = "INTERACTION"


class UnitEffectKind(str, Enum):
    PASSIVE_RESOURCE_GENERATION = "PASSIVE_RESOURCE_GENERATION"
    ENGINE_CLASS = "ENGINE_CLASS"
    TECHNOLOGY_INTERACTION = "TECHNOLOGY_INTERACTION"


class EngineUnitClass(str, Enum):
    INFANTRY = "INFANTRY"
    SHOCK_INFANTRY = "SHOCK_INFANTRY"
    CAVALRY = "CAVALRY"
    RANGED = "RANGED"
    SIEGE = "SIEGE"
    NAVAL = "NAVAL"
    MONK = "MONK"


@dataclass(frozen=True, order=True)
class Rational:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if self.denominator <= 0:
            raise ValueError("Rational denominator must be positive")
        divisor = gcd(abs(self.numerator), self.denominator)
        object.__setattr__(self, "numerator", self.numerator // divisor)
        object.__setattr__(self, "denominator", self.denominator // divisor)


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
    def units(*unit_ids: UnitId) -> "EntitySelector":
        return EntitySelector(
            SelectorKind.UNIT,
            ids=tuple(str(int(unit_id)) for unit_id in unit_ids),
        )

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
    def all_buildings() -> "EntitySelector":
        return EntitySelector(SelectorKind.BUILDING_CLASS)

    @staticmethod
    def age_advance(age: Age) -> "EntitySelector":
        return EntitySelector(SelectorKind.AGE_ADVANCE, ids=(age.value,))


@dataclass(frozen=True)
class Prerequisite:
    kind: PrerequisiteKind
    age: Age | None = None
    building: BuildingId | None = None
    technology: TechId | None = None
    entity: str | None = None
    count: int | None = None
    children: tuple["Prerequisite", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", PrerequisiteKind(self.kind))
        if self.kind is PrerequisiteKind.N_OF:
            if self.count is None or self.count < 1:
                raise ValueError("N_OF prerequisites require a positive count")
            if not self.children:
                raise ValueError("N_OF prerequisites require child predicates")
            if self.count > len(self.children):
                raise ValueError("N_OF prerequisite count cannot exceed child predicate count")


@dataclass(frozen=True)
class ProductionProvider:
    building: BuildingId


@dataclass(frozen=True)
class ResearchProvider:
    building: BuildingId


@dataclass(frozen=True)
class TechEffect:
    kind: TechEffectKind
    target: EntitySelector
    attribute: str | None = None
    modifier: NumericModifier | None = None
    interaction_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", TechEffectKind(self.kind))


@dataclass(frozen=True)
class UnitEffect:
    kind: UnitEffectKind
    attribute: str
    value: Rational | int | str | None = None
    target: EntitySelector | None = None
    resource: Resource | None = None
    provenance: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", UnitEffectKind(self.kind))


@dataclass(frozen=True)
class UpgradeRelation:
    previous: UnitId
    current: UnitId
    research: TechId
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class FactualCoverage:
    status: CoverageStatus
    verified_buildings: frozenset[BuildingId] = frozenset()
    verified_units: frozenset[UnitId] = frozenset()
    verified_unit_lines: frozenset[UnitLineId] = frozenset()
    verified_technologies: frozenset[TechId] = frozenset()
    verified_age_advances: frozenset[AgeAdvanceId] = frozenset()
    verified_upgrade_relations: frozenset[tuple[UnitId, UnitId, TechId]] = frozenset()

    def verifies(self, entity_type: str, entity_id: int | str) -> bool:
        if self.status is CoverageStatus.UNKNOWN:
            return False
        if entity_type == "building":
            return BuildingId(int(entity_id)) in self.verified_buildings
        if entity_type == "unit":
            return UnitId(int(entity_id)) in self.verified_units
        if entity_type == "unit-line":
            return UnitLineId(str(entity_id)) in self.verified_unit_lines
        if entity_type == "technology":
            return TechId(int(entity_id)) in self.verified_technologies
        if entity_type == "age-advance":
            return AgeAdvanceId(str(entity_id)) in self.verified_age_advances
        raise ValueError(f"unknown coverage entity type {entity_type}")


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
    engine_classes: tuple[EngineUnitClass, ...] = ()
    effects: tuple[UnitEffect, ...] = ()


@dataclass(frozen=True)
class AgeAdvanceDef:
    id: AgeAdvanceId
    age: Age
    provider_building: BuildingId
    base_cost: ResourceCost | None
    research_time_seconds: int | None
    from_age: Age | None = None
    native_tech_id: TechId | None = None
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
    upgrade_relations: tuple[UpgradeRelation, ...] = ()
    patch_changes: tuple[PatchChange, ...] = ()
    provenance: tuple[EvidenceRef, ...] = ()
    coverage: FactualCoverage = FactualCoverage(CoverageStatus.UNKNOWN)
    scope: GameDataScope = GameDataScope.UNIVERSAL
    scope_civ_id: CivId | None = None

    def __post_init__(self) -> None:
        if self.scope is GameDataScope.CIVILIZATION and self.scope_civ_id is None:
            raise ValueError("civilization-scoped GameData requires scope_civ_id")
        if self.scope is GameDataScope.UNIVERSAL and self.scope_civ_id is not None:
            raise ValueError("universal GameData cannot carry scope_civ_id")

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

    for line in data.unit_lines:
        for member in line.members:
            if member not in unit_ids:
                raise ValueError(
                    f"unit line {line.id} references unknown unit {member}"
                )

    for building in data.buildings:
        for line in building.trainable_lines:
            if line not in line_ids:
                raise ValueError(f"building {building.id} references unknown unit line {line}")
            members = [item for item in data.units if item.line == line]
            if not members:
                raise ValueError(f"building {building.id} references empty unit line {line}")
            for member in members:
                if not any(provider.building == building.id for provider in member.providers):
                    raise ValueError(
                        f"building {building.id} claims trainable line {line}, "
                        f"but unit {member.id} does not list the building as a provider"
                    )
        for tech in building.researchable_technologies:
            if tech not in tech_ids:
                raise ValueError(f"building {building.id} references unknown technology {tech}")
            technology = next(item for item in data.technologies if item.id == tech)
            if not any(provider.building == building.id for provider in technology.providers):
                raise ValueError(
                    f"building {building.id} claims research capability for {tech}, "
                    "but the technology does not point back to the building"
                )

    for unit in data.units:
        if unit.line not in line_ids:
            raise ValueError(f"unit {unit.id} references unknown unit line {unit.line}")
        for provider in unit.providers:
            if provider.building not in building_ids:
                raise ValueError(
                    f"unit {unit.id} references unknown provider building {provider.building}"
                )
            provider_building = next(item for item in data.buildings if item.id == provider.building)
            if unit.line not in provider_building.trainable_lines:
                raise ValueError(
                    f"unit {unit.id} names provider building {provider.building}, "
                    f"but the building does not expose line {unit.line}"
                )
        if unit.upgrades_from is not None:
            if unit.upgrades_from not in unit_ids:
                raise ValueError(f"unit {unit.id} references unknown upgrade predecessor")
            predecessor = next(item for item in data.units if item.id == unit.upgrades_from)
            if predecessor.upgrades_to != unit.id:
                raise ValueError(
                    f"unit {unit.id} upgrade predecessor {unit.upgrades_from} "
                    "does not point back to this unit"
                )
        if unit.upgrades_to is not None:
            if unit.upgrades_to not in unit_ids:
                raise ValueError(f"unit {unit.id} references unknown upgrade successor")
            successor = next(item for item in data.units if item.id == unit.upgrades_to)
            if successor.upgrades_from != unit.id:
                raise ValueError(
                    f"unit {unit.id} upgrade successor {unit.upgrades_to} "
                    "does not point back to this unit"
                )

    relation_keys = {
        (item.previous, item.current, item.research)
        for item in data.upgrade_relations
    }
    if len(relation_keys) != len(data.upgrade_relations):
        raise ValueError("duplicate upgrade relation")
    for relation in data.upgrade_relations:
        if relation.previous not in unit_ids or relation.current not in unit_ids:
            raise ValueError(
                f"upgrade relation {relation.previous}->{relation.current} references unknown unit"
            )
        if relation.research not in tech_ids:
            raise ValueError(
                f"upgrade relation {relation.previous}->{relation.current} references unknown research technology {relation.research}"
            )
        previous = next(item for item in data.units if item.id == relation.previous)
        current = next(item for item in data.units if item.id == relation.current)
        if current.upgrades_from != previous.id or previous.upgrades_to != current.id:
            raise ValueError(
                f"upgrade relation {relation.previous}->{relation.current} disagrees with unit upgrade links"
            )
        research = next(item for item in data.technologies if item.id == relation.research)
        if current.id not in research.upgrades:
            raise ValueError(
                f"upgrade relation {relation.previous}->{relation.current} is not exposed by technology {research.id}"
            )

    for unit in data.units:
        if unit.upgrades_from is not None and not any(
            relation.previous == unit.upgrades_from and relation.current == unit.id
            for relation in data.upgrade_relations
        ):
            raise ValueError(
                f"unit {unit.id} has an upgrade predecessor but no explicit research relation"
            )

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
