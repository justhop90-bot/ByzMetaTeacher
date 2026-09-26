"""Civilization-specific factual overlays and effective snapshot resolution."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .game_data import (
    Age,
    AgeAdvanceDef,
    AgeAdvanceId,
    BuildingDef,
    BuildingId,
    CivId,
    EntitySelector,
    GameData,
    ModifierOperation,
    NumericModifier,
    Prerequisite,
    ProductionProvider,
    Rational,
    ResearchProvider,
    ResourceCost,
    RoundingMode,
    SelectorKind,
    TechEffect,
    TechId,
    TechnologyDef,
    UnitDef,
    UnitId,
    UnitLineDef,
    UnitLineId,
    canonical_fingerprint,
    validate_game_data,
)
from .versioning import (
    EvidenceKind,
    EvidenceRef,
    PatchChange,
    PatchId,
    PatchOperationKind,
)


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
    COST_OVERRIDE = "COST_OVERRIDE"
    FREE = "FREE"
    BUILDING_HP = "BUILDING_HP"
    STAT = "STAT"
    TRAIN_TIME = "TRAIN_TIME"
    RESEARCH_TIME = "RESEARCH_TIME"
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    INTERACTION = "INTERACTION"


class CivInteractionKind(str, Enum):
    TRAMPLE_DAMAGE = "TRAMPLE_DAMAGE"
    BONUS_DAMAGE = "BONUS_DAMAGE"
    TARGET_SCOPE = "TARGET_SCOPE"


@dataclass(frozen=True)
class CivBonus:
    id: str
    kind: CivBonusKind
    selector: EntitySelector
    modifier: NumericModifier | None = None
    fixed_cost: ResourceCost | None = None
    attribute: str | None = None
    scope: str = "SELF"
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class CivInteraction:
    id: str
    source: EntitySelector
    target: EntitySelector
    kind: CivInteractionKind
    attribute: str | None = None
    value: int | None = None
    scope: str = "SELF"
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class CivProfile:
    civ_id: CivId
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
    civ_id: CivId
    civ_name: str
    buildings: tuple[BuildingDef, ...]
    units: tuple[UnitDef, ...]
    unit_lines: tuple[UnitLineDef, ...]
    technologies: tuple[TechnologyDef, ...]
    age_advances: tuple[AgeAdvanceDef, ...]
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

    def unit_line(self, line_id: UnitLineId | str) -> UnitLineDef:
        return next(item for item in self.unit_lines if item.id == UnitLineId(line_id))

    def tech(self, tech_id: int) -> TechnologyDef:
        return next(item for item in self.technologies if item.id == TechId(tech_id))

    def age_advance(self, age: Age) -> AgeAdvanceDef:
        return next(item for item in self.age_advances if item.age is age)

    def matches_bonus_selector(self, selector: EntitySelector, entity: object) -> bool:
        return _selector_matches(selector, entity)

    def is_free_for_civ(self, key: str) -> bool:
        kind, raw_id = key.split(":", 1)
        if kind != "tech":
            return False
        entity = self.tech(int(raw_id))
        return any(
            bonus.kind is CivBonusKind.FREE
            and _selector_matches(bonus.selector, entity)
            for bonus in self.bonuses
        )

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
        base_cost = entity.base_cost
        if base_cost is None:
            raise ValueError(f"base cost is unresolved for {key}")
        if self.is_free_for_civ(key):
            return ResourceCost()
        override = _cost_override(entity, self.bonuses)
        if override is not None:
            return override
        return _apply_cost_modifiers(base_cost, entity, self.bonuses)

    def cost_of_age_advance(self, age: Age) -> ResourceCost:
        advance = self.age_advance(age)
        if advance.base_cost is None:
            raise ValueError(f"base cost is unresolved for age advance {age.value}")
        override = _cost_override(advance, self.bonuses)
        if override is not None:
            return override
        return _apply_cost_modifiers(advance.base_cost, advance, self.bonuses)


class ByzantineProfile:
    CIV_ID = CivId(7)
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
            extraction_version="compiler-game-data-v2",
        )
        official = EvidenceRef(
            EvidenceKind.OFFICIAL_PATCH,
            "https://www.ageofempires.com/news/age-of-empires-ii-definitive-edition-update-185872/",
            "Update 185872",
            "Byzantines",
            patch,
        )
        community = EvidenceRef(
            EvidenceKind.COMMUNITY_REFERENCE,
            "https://liquipedia.net/ageofempires/Byzantines/Age_of_Empires_II",
            "current",
            "Byzantine civilization bonuses and technology costs",
            patch,
        )
        return CivProfile(
            civ_id=cls.CIV_ID,
            name="Byzantines",
            tech_tree_id=cls.TECH_TREE_ID,
            patch=patch,
            base_data=_byzantine_game_data(patch, manifest, community),
            availability=(),
            bonuses=(
                CivBonus(
                    "byz-counter-unit-discount",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("spearman-line")),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(3, 4),
                        RoundingMode.ENGINE_NEAREST,
                    ),
                    attribute="cost",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-counter-camel-discount",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("camel-rider-line")),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(3, 4),
                        RoundingMode.ENGINE_NEAREST,
                    ),
                    attribute="cost",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-imperial-age-cost-override",
                    CivBonusKind.COST_OVERRIDE,
                    EntitySelector.age_advance(Age.IMPERIAL),
                    fixed_cost=ResourceCost(food=667, gold=536),
                    attribute="cost",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-dark",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.buildings_at_age(Age.DARK),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(110, 100),
                    ),
                    attribute="hp",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-feudal",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.buildings_at_age(Age.FEUDAL),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(120, 100),
                    ),
                    attribute="hp",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-castle",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.buildings_at_age(Age.CASTLE),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(130, 100),
                    ),
                    attribute="hp",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-imperial",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.buildings_at_age(Age.IMPERIAL),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(140, 100),
                    ),
                    attribute="hp",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-fire-ship-speed",
                    CivBonusKind.STAT,
                    EntitySelector.unit_line(UnitLineId("fire-ship-line")),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(4, 5),
                    ),
                    attribute="attack-interval",
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-free-town-watch",
                    CivBonusKind.FREE,
                    EntitySelector.tech(TechId(8)),
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-free-town-patrol",
                    CivBonusKind.FREE,
                    EntitySelector.tech(TechId(280)),
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-team-monk-heal",
                    CivBonusKind.STAT,
                    EntitySelector.unit_class("MONK"),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(2, 1),
                    ),
                    attribute="heal-rate",
                    scope="TEAM",
                    provenance=(community, official),
                ),
            ),
            interactions=(
                CivInteraction(
                    "logistica-trample-expansion",
                    EntitySelector.tech(TechId(61)),
                    EntitySelector.unit_class("VARANGIAN_OR_CATAPHRACT"),
                    CivInteractionKind.TRAMPLE_DAMAGE,
                    provenance=(official,),
                ),
                CivInteraction(
                    "cataphract-anti-infantry-185872",
                    EntitySelector.unit(UnitId(40)),
                    EntitySelector.unit_class("INFANTRY"),
                    CivInteractionKind.BONUS_DAMAGE,
                    attribute="bonus-damage",
                    value=13,
                    provenance=(official,),
                ),
                CivInteraction(
                    "elite-cataphract-anti-infantry-185872",
                    EntitySelector.unit(UnitId(553)),
                    EntitySelector.unit_class("INFANTRY"),
                    CivInteractionKind.BONUS_DAMAGE,
                    attribute="bonus-damage",
                    value=18,
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
                        ("varangian-guard", "enabled;numeric-id-unverified"),
                        ("elite-varangian-guard", "enabled;numeric-id-unverified"),
                        ("cataphract-infantry-bonus", "13"),
                        ("elite-cataphract-infantry-bonus", "18"),
                        ("logistica-target", "cataphract,varangian-guard"),
                    ),
                    (official,),
                ),
            ),
            provenance=(manifest, community, official),
        )


def resolve_effective_civ(profile: CivProfile) -> EffectiveCivData:
    if profile.patch != profile.base_data.patch:
        raise ValueError(
            "CivProfile patch must match the GameData snapshot patch; "
            "patch overlays are not silently inferred"
        )
    validate_game_data(profile.base_data)

    buildings = {
        item.id
        for item in profile.base_data.buildings
        if item.validity is None or item.validity.contains(profile.patch)
    }
    units = {
        item.id
        for item in profile.base_data.units
        if item.validity is None or item.validity.contains(profile.patch)
    }
    techs = {
        item.id
        for item in profile.base_data.technologies
        if item.validity is None or item.validity.contains(profile.patch)
    }

    for rule in profile.availability:
        _apply_availability(rule, buildings, units, techs)

    fingerprint = canonical_fingerprint(
        {
            "patch": profile.patch,
            "civ": profile.civ_id,
            "name": profile.name,
            "buildings": profile.base_data.buildings,
            "units": profile.base_data.units,
            "unit_lines": profile.base_data.unit_lines,
            "technologies": profile.base_data.technologies,
            "age_advances": profile.base_data.age_advances,
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
        unit_lines=profile.base_data.unit_lines,
        technologies=profile.base_data.technologies,
        age_advances=profile.base_data.age_advances,
        available_buildings=frozenset(buildings),
        available_units=frozenset(units),
        available_technologies=frozenset(techs),
        bonuses=profile.bonuses,
        interactions=profile.interactions,
        patch_changes=profile.patch_changes,
        fingerprint=fingerprint,
    )


def _cost_override(
    entity: object,
    bonuses: tuple[CivBonus, ...],
) -> ResourceCost | None:
    matches = [
        bonus.fixed_cost
        for bonus in bonuses
        if bonus.kind is CivBonusKind.COST_OVERRIDE
        and bonus.fixed_cost is not None
        and _selector_matches(bonus.selector, entity)
    ]
    if len(matches) > 1:
        raise ValueError("multiple civilization cost overrides match one entity")
    return matches[0] if matches else None


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
        if modifier.operation is not ModifierOperation.MULTIPLY:
            raise NotImplementedError(
                f"unsupported civilization cost modifier: {modifier.operation.value}"
            )
        if not isinstance(modifier.value, Rational):
            raise TypeError("MULTIPLY modifiers require Rational values")
        result = result.scaled(modifier.value, modifier.rounding)
    return result


def _selector_matches(selector: EntitySelector, entity: object) -> bool:
    if selector.kind is SelectorKind.UNIT_LINE:
        return getattr(entity, "line", None) in {
            UnitLineId(value) for value in selector.ids
        }
    if selector.kind is SelectorKind.UNIT_CLASS:
        return isinstance(entity, UnitDef) and any(
            tag in getattr(entity, "classes", ()) for tag in selector.tags
        )
    if selector.kind is SelectorKind.BUILDING_CLASS:
        return isinstance(entity, BuildingDef) and (
            not selector.ages or getattr(entity, "available_age", None) in selector.ages
        )
    if selector.kind is SelectorKind.UNIT:
        return isinstance(entity, UnitDef) and str(getattr(entity, "id", "")) in selector.ids
    if selector.kind is SelectorKind.BUILDING:
        return isinstance(entity, BuildingDef) and str(getattr(entity, "id", "")) in selector.ids
    if selector.kind is SelectorKind.TECHNOLOGY:
        return isinstance(entity, TechnologyDef) and str(getattr(entity, "id", "")) in selector.ids
    if selector.kind is SelectorKind.AGE_ADVANCE:
        return isinstance(entity, AgeAdvanceDef) and entity.age.value in selector.ids
    if selector.kind is SelectorKind.AGE:
        return getattr(entity, "available_age", None) in selector.ages
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


def _byzantine_game_data(
    patch: PatchId,
    evidence: EvidenceRef,
    community: EvidenceRef,
) -> GameData:
    buildings = (
        BuildingDef(BuildingId(12), "Barracks", Age.DARK, ResourceCost(wood=175),
                    trainable_lines=(UnitLineId("militia-line"), UnitLineId("spearman-line"))),
        BuildingDef(BuildingId(49), "Siege Workshop", Age.CASTLE, ResourceCost(wood=200)),
        BuildingDef(BuildingId(45), "Dock", Age.DARK, ResourceCost(wood=150)),
        BuildingDef(BuildingId(50), "Farm", Age.DARK, ResourceCost(wood=60)),
        BuildingDef(BuildingId(68), "Mill", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(70), "House", Age.DARK, ResourceCost(wood=25)),
        BuildingDef(BuildingId(72), "Palisade Wall", Age.DARK, None),
        BuildingDef(BuildingId(79), "Watch Tower", Age.FEUDAL, None),
        BuildingDef(BuildingId(82), "Castle", Age.CASTLE, ResourceCost(stone=650),
                    researchable_technologies=(TechId(61), TechId(464))),
        BuildingDef(BuildingId(84), "Market", Age.FEUDAL, ResourceCost(wood=175)),
        BuildingDef(BuildingId(87), "Archery Range", Age.FEUDAL, ResourceCost(wood=175)),
        BuildingDef(BuildingId(101), "Stable", Age.FEUDAL, ResourceCost(wood=175)),
        BuildingDef(BuildingId(103), "Blacksmith", Age.FEUDAL, ResourceCost(wood=150)),
        BuildingDef(BuildingId(104), "Monastery", Age.CASTLE, ResourceCost(wood=175)),
        BuildingDef(BuildingId(109), "Town Center", Age.DARK, ResourceCost(wood=275, stone=100)),
        BuildingDef(BuildingId(117), "Stone Wall", Age.FEUDAL, None),
        BuildingDef(BuildingId(155), "Fortified Wall", Age.CASTLE, None),
        BuildingDef(BuildingId(209), "University", Age.CASTLE, ResourceCost(wood=200)),
        BuildingDef(BuildingId(234), "Guard Tower", Age.CASTLE, None),
        BuildingDef(BuildingId(235), "Keep", Age.IMPERIAL, None),
        BuildingDef(BuildingId(236), "Bombard Tower", Age.IMPERIAL, None),
        BuildingDef(BuildingId(276), "Wonder", Age.IMPERIAL, None),
        BuildingDef(BuildingId(487), "Gate", Age.FEUDAL, None),
        BuildingDef(BuildingId(562), "Lumber Camp", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(584), "Mining Camp", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(598), "Outpost", Age.DARK, ResourceCost(wood=25, stone=5)),
        BuildingDef(BuildingId(621), "Town Center", Age.CASTLE, ResourceCost(wood=275, stone=100)),
        BuildingDef(BuildingId(792), "Palisade Gate", Age.DARK, None),
    )
    lines = (
        UnitLineDef(UnitLineId("militia-line"), "Militia line", (UnitId(74),), (evidence,)),
        UnitLineDef(UnitLineId("spearman-line"), "Spearman line", (UnitId(93), UnitId(358), UnitId(359)), (evidence,)),
        UnitLineDef(UnitLineId("skirmisher-line"), "Skirmisher line", (UnitId(7), UnitId(6)), (evidence,)),
        UnitLineDef(UnitLineId("camel-rider-line"), "Camel Rider line", (UnitId(329), UnitId(330)), (evidence,)),
        UnitLineDef(UnitLineId("knight-line"), "Knight line", (UnitId(38),), (evidence,)),
        UnitLineDef(UnitLineId("scout-cavalry-line"), "Scout Cavalry line", (UnitId(448),), (evidence,)),
        UnitLineDef(UnitLineId("archer-line"), "Archer line", (UnitId(4),), (evidence,)),
        UnitLineDef(UnitLineId("crossbow-line"), "Crossbow line", (UnitId(24), UnitId(492)), (evidence,)),
        UnitLineDef(UnitLineId("cataphract-line"), "Cataphract line", (UnitId(40), UnitId(553)), (evidence,)),
        UnitLineDef(UnitLineId("monk-line"), "Monk line", (UnitId(125),), (evidence,)),
        UnitLineDef(UnitLineId("ram-line"), "Ram line", (UnitId(1258),), (evidence,)),
        UnitLineDef(UnitLineId("mangonel-line"), "Mangonel line", (UnitId(280),), (evidence,)),
        UnitLineDef(UnitLineId("scorpion-line"), "Scorpion line", (UnitId(279),), (evidence,)),
        UnitLineDef(UnitLineId("trebuchet-line"), "Trebuchet line", (UnitId(331),), (evidence,)),
        UnitLineDef(UnitLineId("bombard-cannon-line"), "Bombard Cannon line", (UnitId(36),), (evidence,)),
        UnitLineDef(UnitLineId("cavalry-archer-line"), "Cavalry Archer line", (UnitId(474),), (evidence,)),
        UnitLineDef(UnitLineId("fire-galley-line"), "Fire Galley line", (UnitId(1103),), (evidence,)),
        UnitLineDef(UnitLineId("fire-ship-line"), "Fire Ship line", (UnitId(529), UnitId(532)), (evidence,)),
    )
    units = (
        _unit(4, "Archer", "archer-line", Age.FEUDAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",)),
        _unit(6, "Elite Skirmisher", "skirmisher-line", Age.CASTLE, 87, ResourceCost(food=25, wood=35), classes=("RANGED",), upgrades_from=7),
        _unit(7, "Skirmisher", "skirmisher-line", Age.FEUDAL, 87, ResourceCost(food=25, wood=35), classes=("RANGED",)),
        _unit(24, "Crossbowman", "crossbow-line", Age.CASTLE, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=4),
        _unit(36, "Bombard Cannon", "bombard-cannon-line", Age.IMPERIAL, 209, ResourceCost(wood=225, gold=225), classes=("SIEGE",)),
        _unit(38, "Knight", "knight-line", Age.CASTLE, 101, ResourceCost(food=60, gold=75), classes=("CAVALRY",)),
        _unit(40, "Cataphract", "cataphract-line", Age.CASTLE, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE"),),
        _unit(74, "Militia", "militia-line", Age.DARK, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",)),
        _unit(93, "Spearman", "spearman-line", Age.FEUDAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",)),
        _unit(125, "Monk", "monk-line", Age.CASTLE, 104, ResourceCost(gold=100), classes=("MONK",)),
        _unit(279, "Scorpion", "scorpion-line", Age.CASTLE, 49, ResourceCost(wood=75, gold=75), classes=("SIEGE",)),
        _unit(280, "Mangonel", "mangonel-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=135), classes=("SIEGE",)),
        _unit(329, "Camel Rider", "camel-rider-line", Age.CASTLE, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",)),
        _unit(330, "Heavy Camel Rider", "camel-rider-line", Age.IMPERIAL, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",), upgrades_from=329),
        _unit(331, "Trebuchet", "trebuchet-line", Age.IMPERIAL, 82, ResourceCost(wood=200, gold=200), classes=("SIEGE",)),
        _unit(358, "Pikeman", "spearman-line", Age.CASTLE, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=93),
        _unit(359, "Halberdier", "spearman-line", Age.IMPERIAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=358),
        _unit(448, "Scout Cavalry", "scout-cavalry-line", Age.FEUDAL, 101, ResourceCost(food=80), classes=("CAVALRY",)),
        _unit(474, "Heavy Cavalry Archer", "cavalry-archer-line", Age.IMPERIAL, 87, ResourceCost(wood=40, gold=60), classes=("CAVALRY", "RANGED")),
        _unit(492, "Arbalester", "crossbow-line", Age.IMPERIAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=24),
        _unit(529, "Fire Ship", "fire-ship-line", Age.CASTLE, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",)),
        _unit(532, "Fast Fire Ship", "fire-ship-line", Age.IMPERIAL, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",), upgrades_from=529),
        _unit(553, "Elite Cataphract", "cataphract-line", Age.IMPERIAL, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE"), upgrades_from=40),
        _unit(1103, "Fire Galley", "fire-galley-line", Age.FEUDAL, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",)),
        _unit(1258, "Battering Ram", "ram-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=75), classes=("SIEGE",)),
    )
    techs = (
        TechnologyDef(
            TechId(8), "Town Watch", Age.FEUDAL, (ResearchProvider(BuildingId(109)),),
            ResourceCost(food=75), 25,
        ),
        TechnologyDef(
            TechId(61), "Logistica", Age.IMPERIAL, (ResearchProvider(BuildingId(82)),),
            ResourceCost(food=800, gold=600), 50,
        ),
        TechnologyDef(
            TechId(65), "Gillnets", Age.CASTLE, (ResearchProvider(BuildingId(45)),),
            None, None,
        ),
        TechnologyDef(
            TechId(280), "Town Patrol", Age.CASTLE, (ResearchProvider(BuildingId(109)),),
            ResourceCost(food=300, gold=100), 40,
            prerequisites=(Prerequisite("TECHNOLOGY_RESEARCHED", technology=TechId(8)),),
        ),
        TechnologyDef(
            TechId(464), "Greek Fire", Age.CASTLE, (ResearchProvider(BuildingId(82)),),
            ResourceCost(food=250, gold=300), 40,
            effects=(
                TechEffect(
                    kind="STAT_MODIFIER",
                    target=EntitySelector.unit_line(UnitLineId("fire-ship-line")),
                    attribute="fire-ship-technology",
                ),
            ),
        ),
        TechnologyDef(
            TechId(906), "Fishing Lines", Age.FEUDAL, (ResearchProvider(BuildingId(45)),),
            None, None,
        ),
    )
    advances = (
        AgeAdvanceDef(
            AgeAdvanceId("feudal-age"),
            Age.FEUDAL,
            BuildingId(109),
            ResourceCost(food=500),
            130,
            prerequisites=(
                Prerequisite("BUILDING_COUNT", building=BuildingId(12), count=1),
                Prerequisite("AGE_ADVANCE_BUILDING_COUNT", count=2),
            ),
            provenance=(evidence,),
        ),
        AgeAdvanceDef(
            AgeAdvanceId("castle-age"),
            Age.CASTLE,
            BuildingId(109),
            ResourceCost(food=800, gold=200),
            160,
            prerequisites=(
                Prerequisite("BUILDING_COUNT", building=BuildingId(87), count=1),
                Prerequisite("BUILDING_COUNT", building=BuildingId(103), count=1),
            ),
            provenance=(evidence,),
        ),
        AgeAdvanceDef(
            AgeAdvanceId("imperial-age"),
            Age.IMPERIAL,
            BuildingId(109),
            ResourceCost(food=1000, gold=800),
            190,
            prerequisites=(
                Prerequisite("CASTLE_OR_ALTERNATE", building=BuildingId(82), count=1),
            ),
            provenance=(evidence,),
        ),
    )
    return GameData(
        patch=patch,
        buildings=tuple(sorted(buildings, key=lambda item: int(item.id))),
        units=tuple(sorted(units, key=lambda item: int(item.id))),
        unit_lines=tuple(sorted(lines, key=lambda item: str(item.id))),
        technologies=tuple(sorted(techs, key=lambda item: int(item.id))),
        age_advances=tuple(sorted(advances, key=lambda item: item.age.value)),
        provenance=(evidence, community),
    )
