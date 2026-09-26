"""Civilization-specific factual overlays and effective snapshot resolution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .game_data import (
    Age,
    BuildingDef,
    BuildingId,
    EntitySelector,
    GameData,
    ModifierOperation,
    NumericModifier,
    ProductionProvider,
    Rational,
    ResearchProvider,
    ResourceCost,
    RoundingMode,
    SelectorKind,
    TechId,
    TechnologyDef,
    UnitDef,
    UnitId,
    UnitLineDef,
    UnitLineId,
    canonical_fingerprint,
    validate_game_data,
)
from .versioning import EvidenceKind, EvidenceRef, PatchChange, PatchId, PatchOperationKind


class AvailabilityOperation(str, Enum):
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"


@dataclass(frozen=True)
class CivAvailabilityRule:
    operation: AvailabilityOperation
    selector: EntitySelector
    provenance: tuple[EvidenceRef, ...] = ()


class CivBonusKind(str, Enum):
    COST = "COST"
    BUILDING_HP = "BUILDING_HP"
    STAT = "STAT"
    TRAIN_TIME = "TRAIN_TIME"
    RESEARCH_TIME = "RESEARCH_TIME"
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    INTERACTION = "INTERACTION"


@dataclass(frozen=True)
class CivBonus:
    id: str
    kind: CivBonusKind
    selector: EntitySelector
    modifier: NumericModifier | None = None
    attribute: str | None = None
    scope: str = "SELF"
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class CivInteraction:
    id: str
    source: EntitySelector
    target: EntitySelector
    effect: str
    scope: str = "SELF"
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class CivProfile:
    civ_id: int
    name: str
    tech_tree_id: int
    patch: PatchId
    base_data: GameData
    availability: tuple[CivAvailabilityRule, ...]
    bonuses: tuple[CivBonus, ...]
    interactions: tuple[CivInteraction, ...]
    patch_changes: tuple[PatchChange, ...]
    provenance: tuple[EvidenceRef, ...]


@dataclass(frozen=True)
class EffectiveCivData:
    patch: PatchId
    civ_id: int
    civ_name: str
    buildings: tuple[BuildingDef, ...]
    units: tuple[UnitDef, ...]
    technologies: tuple[TechnologyDef, ...]
    available_buildings: frozenset[BuildingId]
    available_units: frozenset[UnitId]
    available_technologies: frozenset[TechId]
    bonuses: tuple[CivBonus, ...]
    interactions: tuple[CivInteraction, ...]
    patch_changes: tuple[PatchChange, ...]
    fingerprint: str

    def building(self, building_id: int) -> BuildingDef:
        return next(item for item in self.buildings if item.id == BuildingId(building_id))

    def unit(self, unit_id: int) -> UnitDef:
        return next(item for item in self.units if item.id == UnitId(unit_id))

    def tech(self, tech_id: int) -> TechnologyDef:
        return next(item for item in self.technologies if item.id == TechId(tech_id))

    def cost_of(self, key: str) -> ResourceCost:
        kind, raw_id = key.split(":", 1)
        if kind == "unit":
            entity = self.unit(int(raw_id))
        elif kind == "building":
            entity = self.building(int(raw_id))
        elif kind == "tech":
            entity = self.tech(int(raw_id))
        else:
            raise KeyError(f"unknown cost key kind: {kind}")
        cost = entity.base_cost
        if cost is None:
            raise ValueError(f"base cost is unresolved for {key}")
        return _apply_cost_modifiers(cost, entity, self.bonuses)


class ByzantineProfile:
    CIV_ID = 7
    TECH_TREE_ID = 256

    @classmethod
    def for_update_185872(cls) -> CivProfile:
        patch = PatchId("AOE2DE", "185872", None, "2026-09-22")
        manifest = EvidenceRef(
            EvidenceKind.REPOSITORY_MANIFEST,
            "docs/reference/BYZANTINES_manifest.txt",
            "main",
            "CivTechTrees=BYZANTINES;tech_tree_id=256",
            patch,
            extraction_version="compiler-game-data-v1",
        )
        official = EvidenceRef(
            EvidenceKind.OFFICIAL_PATCH,
            "https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/",
            "Update 185872",
            "Byzantines",
            patch,
        )
        return CivProfile(
            civ_id=cls.CIV_ID,
            name="Byzantines",
            tech_tree_id=cls.TECH_TREE_ID,
            patch=patch,
            base_data=_byzantine_game_data(patch, manifest),
            availability=(),
            bonuses=(
                CivBonus(
                    "byz-counter-unit-discount-skirmisher",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("skirmisher-line")),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(3, 4), RoundingMode.ENGINE_NEAREST),
                    attribute="cost",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-counter-unit-discount-pike",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("pikeman-line")),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(3, 4), RoundingMode.ENGINE_NEAREST),
                    attribute="cost",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-counter-unit-discount-halberdier",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("halberdier-line")),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(3, 4), RoundingMode.ENGINE_NEAREST),
                    attribute="cost",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-counter-unit-discount-camel",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("camel-rider-line")),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(3, 4), RoundingMode.ENGINE_NEAREST),
                    attribute="cost",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-imperial-discount",
                    CivBonusKind.COST,
                    EntitySelector.age(Age.IMPERIAL),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(67, 100), RoundingMode.ENGINE_NEAREST),
                    attribute="cost",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-building-hp-dark",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.age(Age.DARK),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(110, 100)),
                    attribute="hp",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-building-hp-feudal",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.age(Age.FEUDAL),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(120, 100)),
                    attribute="hp",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-building-hp-castle",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.age(Age.CASTLE),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(130, 100)),
                    attribute="hp",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-building-hp-imperial",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.age(Age.IMPERIAL),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(140, 100)),
                    attribute="hp",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-fire-ship-speed",
                    CivBonusKind.STAT,
                    EntitySelector.unit_line(UnitLineId("fire-ship-line")),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(5, 6)),
                    attribute="attack-interval",
                    provenance=(official,),
                ),
                CivBonus(
                    "byz-team-monk-heal",
                    CivBonusKind.STAT,
                    EntitySelector.unit_class("MONK"),
                    NumericModifier(ModifierOperation.MULTIPLY, Rational(3, 2)),
                    attribute="heal-rate",
                    scope="TEAM",
                    provenance=(official,),
                ),
            ),
            interactions=(
                CivInteraction(
                    "logistica-trample-expansion",
                    EntitySelector.tech(TechId(61)),
                    EntitySelector.unit_class("VARANGIAN_OR_CATAPHRACT"),
                    "TRAMPLE_DAMAGE",
                    provenance=(official,),
                ),
            ),
            patch_changes=(
                PatchChange(
                    "civilization",
                    "byzantines",
                    PatchOperationKind.REPLACE,
                    None,
                    None,
                    (
                        ("varangian-guard", "enabled"),
                        ("elite-varangian-guard", "enabled"),
                        ("cataphract-infantry-bonus", "13"),
                        ("elite-cataphract-infantry-bonus", "18"),
                        ("logistica-target", "cataphract,varangian-guard"),
                    ),
                    (official,),
                ),
            ),
            provenance=(manifest, official),
        )


def resolve_effective_civ(profile: CivProfile) -> EffectiveCivData:
    validate_game_data(profile.base_data)
    buildings = set(item.id for item in profile.base_data.buildings)
    units = set(item.id for item in profile.base_data.units)
    techs = set(item.id for item in profile.base_data.technologies)

    for rule in profile.availability:
        _apply_availability(rule, buildings, units, techs)

    fingerprint = canonical_fingerprint(
        {
            "patch": profile.patch,
            "civ": profile.civ_id,
            "name": profile.name,
            "buildings": profile.base_data.buildings,
            "units": profile.base_data.units,
            "technologies": profile.base_data.technologies,
            "available_buildings": sorted(int(item) for item in buildings),
            "available_units": sorted(int(item) for item in units),
            "available_technologies": sorted(int(item) for item in techs),
            "bonuses": profile.bonuses,
            "interactions": profile.interactions,
            "patch_changes": profile.patch_changes,
        }
    )

    return EffectiveCivData(
        patch=profile.patch,
        civ_id=profile.civ_id,
        civ_name=profile.name,
        buildings=profile.base_data.buildings,
        units=profile.base_data.units,
        technologies=profile.base_data.technologies,
        available_buildings=frozenset(buildings),
        available_units=frozenset(units),
        available_technologies=frozenset(techs),
        bonuses=profile.bonuses,
        interactions=profile.interactions,
        patch_changes=profile.patch_changes,
        fingerprint=fingerprint,
    )


def _apply_cost_modifiers(
    base: ResourceCost,
    entity: object,
    bonuses: tuple[CivBonus, ...],
) -> ResourceCost:
    result = base
    for bonus in bonuses:
        if bonus.kind is not CivBonusKind.COST or bonus.modifier is None:
            continue
        if not _selector_matches(bonus.selector, entity):
            continue
        modifier = bonus.modifier
        if modifier.operation is ModifierOperation.MULTIPLY:
            if not isinstance(modifier.value, Rational):
                raise TypeError("MULTIPLY modifiers require Rational values")
            result = result.scaled(modifier.value, modifier.rounding)
        elif modifier.operation is ModifierOperation.ADD:
            raise NotImplementedError("additive cost modifiers are not implemented yet")
        else:
            raise NotImplementedError("subtractive cost modifiers are not implemented yet")
    return result


def _selector_matches(selector: EntitySelector, entity: object) -> bool:
    if selector.kind is SelectorKind.UNIT_LINE:
        return getattr(entity, "line", None) in {UnitLineId(value) for value in selector.ids}
    if selector.kind is SelectorKind.AGE:
        return getattr(entity, "available_age", None) in selector.ages
    if selector.kind is SelectorKind.UNIT_CLASS:
        return any(tag in getattr(entity, "classes", ()) for tag in selector.tags)
    if selector.kind is SelectorKind.UNIT:
        return str(getattr(entity, "id", "")) in selector.ids
    if selector.kind is SelectorKind.BUILDING:
        return str(getattr(entity, "id", "")) in selector.ids
    if selector.kind is SelectorKind.TECHNOLOGY:
        return str(getattr(entity, "id", "")) in selector.ids
    return False


def _apply_availability(
    rule: CivAvailabilityRule,
    buildings: set[BuildingId],
    units: set[UnitId],
    techs: set[TechId],
) -> None:
    if rule.selector.kind is SelectorKind.BUILDING:
        target = buildings
        ids = {BuildingId(int(value)) for value in rule.selector.ids}
    elif rule.selector.kind is SelectorKind.UNIT:
        target = units
        ids = {UnitId(int(value)) for value in rule.selector.ids}
    elif rule.selector.kind is SelectorKind.TECHNOLOGY:
        target = techs
        ids = {TechId(int(value)) for value in rule.selector.ids}
    else:
        raise ValueError("availability rules require direct entity selectors")
    if rule.operation is AvailabilityOperation.ENABLE:
        target.update(ids)
    else:
        target.difference_update(ids)


def _unit(
    unit_id: int,
    name: str,
    line: str,
    age: Age,
    provider: int,
    cost: ResourceCost | None,
    *,
    classes: tuple[str, ...],
    upgrades_from: int | None = None,
) -> UnitDef:
    return UnitDef(
        id=UnitId(unit_id),
        name=name,
        line=UnitLineId(line),
        available_age=age,
        providers=(ProductionProvider(BuildingId(provider)),),
        base_cost=cost,
        train_time_seconds=None,
        upgrades_from=UnitId(upgrades_from) if upgrades_from is not None else None,
        classes=classes,
    )


def _byzantine_game_data(patch: PatchId, evidence: EvidenceRef) -> GameData:
    buildings = (
        BuildingDef(BuildingId(12), "Barracks", Age.DARK, ResourceCost(wood=175), trainable_lines=(UnitLineId("militia-line"), UnitLineId("spearman-line"), UnitLineId("pikeman-line"), UnitLineId("halberdier-line"))),
        BuildingDef(BuildingId(49), "Siege Workshop", Age.CASTLE, ResourceCost(wood=200)),
        BuildingDef(BuildingId(68), "Mill", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(70), "House", Age.DARK, ResourceCost(wood=25)),
        BuildingDef(BuildingId(82), "Castle", Age.CASTLE, ResourceCost(stone=650), researchable_technologies=(TechId(61),)),
        BuildingDef(BuildingId(84), "Market", Age.FEUDAL, ResourceCost(wood=175)),
        BuildingDef(BuildingId(87), "Archery Range", Age.FEUDAL, ResourceCost(wood=175), trainable_lines=(UnitLineId("archer-line"), UnitLineId("crossbow-line"), UnitLineId("arbalester-line"), UnitLineId("skirmisher-line"))),
        BuildingDef(BuildingId(101), "Stable", Age.FEUDAL, ResourceCost(wood=175), trainable_lines=(UnitLineId("camel-rider-line"), UnitLineId("knight-line"), UnitLineId("scout-cavalry-line"))),
        BuildingDef(BuildingId(103), "Blacksmith", Age.FEUDAL, ResourceCost(wood=150)),
        BuildingDef(BuildingId(104), "Monastery", Age.CASTLE, ResourceCost(wood=175), trainable_lines=(UnitLineId("monk-line"),)),
        BuildingDef(BuildingId(109), "Town Center", Age.DARK, ResourceCost(wood=275, stone=100)),
        BuildingDef(BuildingId(209), "University", Age.CASTLE, ResourceCost(wood=200)),
        BuildingDef(BuildingId(276), "Wonder", Age.IMPERIAL, None),
        BuildingDef(BuildingId(562), "Lumber Camp", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(584), "Mining Camp", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(598), "Outpost", Age.DARK, None),
        BuildingDef(BuildingId(487), "Gate", Age.FEUDAL, None),
        BuildingDef(BuildingId(117), "Stone Wall", Age.FEUDAL, None),
        BuildingDef(BuildingId(155), "Fortified Wall", Age.CASTLE, None),
        BuildingDef(BuildingId(234), "Guard Tower", Age.CASTLE, None),
        BuildingDef(BuildingId(235), "Keep", Age.IMPERIAL, None),
        BuildingDef(BuildingId(236), "Bombard Tower", Age.IMPERIAL, None),
        BuildingDef(BuildingId(45), "Dock", Age.DARK, None),
        BuildingDef(BuildingId(50), "Farm", Age.DARK, ResourceCost(wood=60)),
        BuildingDef(BuildingId(72), "Palisade Wall", Age.DARK, None),
        BuildingDef(BuildingId(79), "Watch Tower", Age.FEUDAL, None),
        BuildingDef(BuildingId(621), "Town Center", Age.CASTLE, None),
        BuildingDef(BuildingId(792), "Palisade Gate", Age.DARK, None),
    )
    lines = (
        UnitLineDef(UnitLineId("militia-line"), "Militia line", (UnitId(74),), (evidence,)),
        UnitLineDef(UnitLineId("spearman-line"), "Spearman line", (UnitId(93),), (evidence,)),
        UnitLineDef(UnitLineId("pikeman-line"), "Pikeman line", (UnitId(358),), (evidence,)),
        UnitLineDef(UnitLineId("halberdier-line"), "Halberdier line", (UnitId(359),), (evidence,)),
        UnitLineDef(UnitLineId("skirmisher-line"), "Skirmisher line", (UnitId(7), UnitId(6)), (evidence,)),
        UnitLineDef(UnitLineId("camel-rider-line"), "Camel Rider line", (UnitId(329), UnitId(330)), (evidence,)),
        UnitLineDef(UnitLineId("knight-line"), "Knight line", (UnitId(38),), (evidence,)),
        UnitLineDef(UnitLineId("scout-cavalry-line"), "Scout Cavalry line", (UnitId(448),), (evidence,)),
        UnitLineDef(UnitLineId("archer-line"), "Archer line", (UnitId(4),), (evidence,)),
        UnitLineDef(UnitLineId("crossbow-line"), "Crossbow line", (UnitId(24),), (evidence,)),
        UnitLineDef(UnitLineId("arbalester-line"), "Arbalester line", (UnitId(492),), (evidence,)),
        UnitLineDef(UnitLineId("cataphract-line"), "Cataphract line", (UnitId(40), UnitId(553)), (evidence,)),
        UnitLineDef(UnitLineId("monk-line"), "Monk line", (UnitId(125),), (evidence,)),
        UnitLineDef(UnitLineId("ram-line"), "Ram line", (UnitId(1258),), (evidence,)),
        UnitLineDef(UnitLineId("mangonel-line"), "Mangonel line", (UnitId(280),), (evidence,)),
        UnitLineDef(UnitLineId("scorpion-line"), "Scorpion line", (UnitId(279),), (evidence,)),
        UnitLineDef(UnitLineId("trebuchet-line"), "Trebuchet line", (UnitId(331),), (evidence,)),
        UnitLineDef(UnitLineId("bombard-cannon-line"), "Bombard Cannon line", (UnitId(36),), (evidence,)),
        UnitLineDef(UnitLineId("cavalry-archer-line"), "Cavalry Archer line", (UnitId(474),), (evidence,)),
    )
    units = (
        _unit(4, "Archer", "archer-line", Age.FEUDAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",)),
        _unit(6, "Elite Skirmisher", "skirmisher-line", Age.CASTLE, 87, ResourceCost(food=25, wood=35), classes=("RANGED",), upgrades_from=7),
        _unit(7, "Skirmisher", "skirmisher-line", Age.FEUDAL, 87, ResourceCost(food=25, wood=35), classes=("RANGED",)),
        _unit(24, "Crossbowman", "crossbow-line", Age.CASTLE, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=4),
        _unit(36, "Bombard Cannon", "bombard-cannon-line", Age.IMPERIAL, 209, ResourceCost(wood=225, gold=225), classes=("SIEGE",)),
        _unit(38, "Knight", "knight-line", Age.CASTLE, 101, ResourceCost(food=60, gold=75), classes=("CAVALRY",)),
        _unit(40, "Cataphract", "cataphract-line", Age.CASTLE, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE")),
        _unit(74, "Militia", "militia-line", Age.DARK, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",)),
        _unit(93, "Spearman", "spearman-line", Age.FEUDAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",)),
        _unit(125, "Monk", "monk-line", Age.CASTLE, 104, ResourceCost(gold=100), classes=("MONK",)),
        _unit(279, "Scorpion", "scorpion-line", Age.CASTLE, 49, ResourceCost(wood=75, gold=75), classes=("SIEGE",)),
        _unit(280, "Mangonel", "mangonel-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=135), classes=("SIEGE",)),
        _unit(329, "Camel Rider", "camel-rider-line", Age.CASTLE, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",)),
        _unit(330, "Heavy Camel Rider", "camel-rider-line", Age.IMPERIAL, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",), upgrades_from=329),
        _unit(331, "Trebuchet", "trebuchet-line", Age.IMPERIAL, 82, ResourceCost(wood=200, gold=200), classes=("SIEGE",)),
        _unit(358, "Pikeman", "pikeman-line", Age.CASTLE, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=93),
        _unit(359, "Halberdier", "halberdier-line", Age.IMPERIAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=358),
        _unit(448, "Scout Cavalry", "scout-cavalry-line", Age.FEUDAL, 101, ResourceCost(food=80), classes=("CAVALRY",)),
        _unit(474, "Heavy Cavalry Archer", "cavalry-archer-line", Age.IMPERIAL, 87, ResourceCost(wood=40, gold=60), classes=("CAVALRY", "RANGED")),
        _unit(492, "Arbalester", "arbalester-line", Age.IMPERIAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=24),
        _unit(553, "Elite Cataphract", "cataphract-line", Age.IMPERIAL, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE"), upgrades_from=40),
        _unit(1258, "Battering Ram", "ram-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=75), classes=("SIEGE",)),
    )
    techs = (
        TechnologyDef(
            id=TechId(61),
            name="Logistica",
            available_age=Age.IMPERIAL,
            providers=(ResearchProvider(BuildingId(82)),),
            base_cost=None,
            research_time_seconds=None,
        ),
    )
    return GameData(
        patch=patch,
        buildings=tuple(sorted(buildings, key=lambda item: int(item.id))),
        units=tuple(sorted(units, key=lambda item: int(item.id))),
        unit_lines=tuple(sorted(lines, key=lambda item: str(item.id))),
        technologies=techs,
        provenance=(evidence,),
    )
