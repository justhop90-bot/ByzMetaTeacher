"""Civilization-specific factual overlays and effective snapshot resolution."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .game_data import (
    Age,
    AgeAdvanceDef,
    AgeAdvanceId,
    BuildingDef,
    CoverageStatus,
    EngineUnitClass,
    FactualCoverage,
    BuildingId,
    CivId,
    EntitySelector,
    GameData,
    ModifierOperation,
    NumericModifier,
    Prerequisite,
    PrerequisiteKind,
    ProductionProvider,
    Rational,
    ResearchProvider,
    ResourceCost,
    RoundingMode,
    SelectorKind,
    TechEffect,
    TechEffectKind,
    TechId,
    TechnologyDef,
    UnitDef,
    UnitEffect,
    UnitEffectKind,
    UnitId,
    UnitLineDef,
    UnitLineId,
    UpgradeRelation,
    canonical_fingerprint,
    validate_game_data,
)
from .versioning import (
    EvidenceKind,
    EvidenceRef,
    PatchChange,
    PatchId,
    PatchOperationKind,
    Validity,
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
    age_scope: Age | None = None
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
    coverage: FactualCoverage

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

    def require_coverage(self, entity_type: str, entity_id: int | str) -> None:
        if not self.coverage.verifies(entity_type, entity_id):
            raise ValueError(
                f"factual coverage is not sufficient for {entity_type}:{entity_id}; "
                f"snapshot status is {self.coverage.status.value}"
            )

    def building_hp_bonus_for_age(self, age: Age) -> tuple[CivBonus, ...]:
        return tuple(
            bonus
            for bonus in self.bonuses
            if bonus.kind is CivBonusKind.BUILDING_HP
            and bonus.age_scope is age
        )

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
        controller = EvidenceRef(
            EvidenceKind.REPOSITORY_CONTROLLER,
            "Basilisk/Basilisk.per",
            "main",
            "defconst varangian-guard 2703; defconst elite-varangian-guard 2704; defconst ri-elite-varangian-guard 1454",
            patch,
            verification="cross-check",
        )
        return CivProfile(
            civ_id=cls.CIV_ID,
            name="Byzantines",
            tech_tree_id=cls.TECH_TREE_ID,
            patch=patch,
            base_data=_byzantine_game_data(patch, manifest, community, controller),
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
                    "byz-counter-skirmisher-discount",
                    CivBonusKind.COST,
                    EntitySelector.unit_line(UnitLineId("skirmisher-line")),
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
                    EntitySelector.all_buildings(),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(110, 100),
                    ),
                    attribute="hp",
                    age_scope=Age.DARK,
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-feudal",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.all_buildings(),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(120, 100),
                    ),
                    attribute="hp",
                    age_scope=Age.FEUDAL,
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-castle",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.all_buildings(),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(130, 100),
                    ),
                    attribute="hp",
                    age_scope=Age.CASTLE,
                    provenance=(community, official),
                ),
                CivBonus(
                    "byz-building-hp-imperial",
                    CivBonusKind.BUILDING_HP,
                    EntitySelector.all_buildings(),
                    NumericModifier(
                        ModifierOperation.MULTIPLY,
                        Rational(140, 100),
                    ),
                    attribute="hp",
                    age_scope=Age.IMPERIAL,
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
                    "logistica-trample-current-units",
                    EntitySelector.tech(TechId(61)),
                    EntitySelector.units(
                        UnitId(40),
                        UnitId(553),
                        UnitId(2703),
                        UnitId(2704),
                    ),
                    CivInteractionKind.TRAMPLE_DAMAGE,
                    provenance=(official, controller),
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
                        ("varangian-guard", "enabled;numeric-id=2703"),
                        ("elite-varangian-guard", "enabled;numeric-id=2704"),
                        ("elite-varangian-guard-tech", "tech-id=1454"),
                        ("cataphract-infantry-bonus", "13"),
                        ("elite-cataphract-infantry-bonus", "18"),
                        ("logistica-target", "cataphract,varangian-guard"),
                    ),
                    (official,),
                ),
            ),
            provenance=(manifest, community, official, controller),
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
    upgrades_to: int | None = None,
    validity: Validity | None = None,
    engine_classes: tuple[EngineUnitClass, ...] = (),
    effects: tuple[UnitEffect, ...] = (),
    provenance: tuple[EvidenceRef, ...] = (),
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
        upgrades_to=UnitId(upgrades_to) if upgrades_to is not None else None,
        classes=classes,
        validity=validity,
        provenance=provenance,
        engine_classes=engine_classes,
        effects=effects,
    )

def _byzantine_game_data(
    patch: PatchId,
    evidence: EvidenceRef,
    community: EvidenceRef,
    controller: EvidenceRef,
) -> GameData:
    buildings = (
        BuildingDef(
            BuildingId(12),
            "Barracks",
            Age.DARK,
            ResourceCost(wood=175),
            trainable_lines=(
                UnitLineId("militia-line"),
                UnitLineId("spearman-line"),
                UnitLineId("varangian-guard-line"),
            ),
            researchable_technologies=(
                TechId(222), TechId(207), TechId(217), TechId(264),
                TechId(197), TechId(429), TechId(602), TechId(875),
                TechId(215), TechId(1454),
            ),
        ),
        BuildingDef(
            BuildingId(49),
            "Siege Workshop",
            Age.CASTLE,
            ResourceCost(wood=200),
            trainable_lines=(
                UnitLineId("ram-line"),
                UnitLineId("mangonel-line"),
                UnitLineId("scorpion-line"),
                UnitLineId("siege-tower-line"),
                UnitLineId("bombard-cannon-line"),
            ),
            researchable_technologies=(TechId(96), TechId(255), TechId(257), TechId(239)),
        ),
        BuildingDef(
            BuildingId(45),
            "Dock",
            Age.DARK,
            ResourceCost(wood=150),
            trainable_lines=(
                UnitLineId("fire-galley-line"),
                UnitLineId("fire-ship-line"),
                UnitLineId("dromon-line"),
            ),
            researchable_technologies=(TechId(906), TechId(65), TechId(34), TechId(35), TechId(246)),
        ),
        BuildingDef(BuildingId(50), "Farm", Age.DARK, ResourceCost(wood=60)),
        BuildingDef(BuildingId(68), "Mill", Age.DARK, ResourceCost(wood=50)),
        BuildingDef(BuildingId(70), "House", Age.DARK, ResourceCost(wood=25)),
        BuildingDef(BuildingId(72), "Palisade Wall", Age.DARK, None),
        BuildingDef(BuildingId(79), "Watch Tower", Age.FEUDAL, None),
        BuildingDef(
            BuildingId(82),
            "Castle",
            Age.CASTLE,
            ResourceCost(stone=650),
            trainable_lines=(
                UnitLineId("cataphract-line"),
                UnitLineId("petard-line"),
                UnitLineId("trebuchet-line"),
            ),
            researchable_technologies=(TechId(361), TechId(61), TechId(464)),
        ),
        BuildingDef(BuildingId(84), "Market", Age.FEUDAL, ResourceCost(wood=175)),
        BuildingDef(
            BuildingId(87),
            "Archery Range",
            Age.FEUDAL,
            ResourceCost(wood=175),
            trainable_lines=(
                UnitLineId("archer-line"),
                UnitLineId("crossbow-line"),
                UnitLineId("skirmisher-line"),
                UnitLineId("hand-cannoneer-line"),
                UnitLineId("cavalry-archer-line"),
            ),
            researchable_technologies=(
                TechId(100), TechId(237), TechId(98), TechId(218), TechId(437), TechId(436),
            ),
        ),
        BuildingDef(
            BuildingId(101),
            "Stable",
            Age.FEUDAL,
            ResourceCost(wood=175),
            trainable_lines=(
                UnitLineId("scout-cavalry-line"),
                UnitLineId("knight-line"),
                UnitLineId("camel-rider-line"),
            ),
            researchable_technologies=(
                TechId(254), TechId(428), TechId(209), TechId(265),
                TechId(236), TechId(435), TechId(39),
            ),
        ),
        BuildingDef(BuildingId(103), "Blacksmith", Age.FEUDAL, ResourceCost(wood=150)),
        BuildingDef(
            BuildingId(104),
            "Monastery",
            Age.CASTLE,
            ResourceCost(wood=175),
            trainable_lines=(UnitLineId("monk-line"),),
        ),
        BuildingDef(
            BuildingId(109),
            "Town Center",
            Age.DARK,
            ResourceCost(wood=275, stone=100),
            researchable_technologies=(TechId(8), TechId(280)),
        ),
        BuildingDef(BuildingId(117), "Stone Wall", Age.FEUDAL, None),
        BuildingDef(BuildingId(155), "Fortified Wall", Age.CASTLE, None),
        BuildingDef(
            BuildingId(209),
            "University",
            Age.CASTLE,
            ResourceCost(wood=200),
            researchable_technologies=(TechId(47), TechId(93), TechId(374), TechId(375), TechId(373)),
        ),
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
        UnitLineDef(UnitLineId("militia-line"), "Militia line", (UnitId(74), UnitId(75), UnitId(77), UnitId(473), UnitId(567)), (evidence,)),
        UnitLineDef(UnitLineId("spearman-line"), "Spearman line", (UnitId(93), UnitId(358), UnitId(359)), (evidence,)),
        UnitLineDef(UnitLineId("skirmisher-line"), "Skirmisher line", (UnitId(7), UnitId(6)), (evidence,)),
        UnitLineDef(UnitLineId("camel-rider-line"), "Camel Rider line", (UnitId(329), UnitId(330)), (evidence,)),
        UnitLineDef(UnitLineId("scout-cavalry-line"), "Scout Cavalry line", (UnitId(448), UnitId(546), UnitId(441)), (evidence,)),
        UnitLineDef(UnitLineId("knight-line"), "Knight line", (UnitId(38), UnitId(283), UnitId(569)), (evidence,)),
        UnitLineDef(UnitLineId("archer-line"), "Archer line", (UnitId(4),), (evidence,)),
        UnitLineDef(UnitLineId("crossbow-line"), "Crossbow line", (UnitId(24), UnitId(492)), (evidence,)),
        UnitLineDef(UnitLineId("cavalry-archer-line"), "Cavalry Archer line", (UnitId(39), UnitId(474)), (evidence,)),
        UnitLineDef(UnitLineId("hand-cannoneer-line"), "Hand Cannoneer line", (UnitId(5),), (evidence,)),
        UnitLineDef(UnitLineId("cataphract-line"), "Cataphract line", (UnitId(40), UnitId(553)), (evidence,)),
        UnitLineDef(UnitLineId("petard-line"), "Petard line", (UnitId(440),), (evidence,)),
        UnitLineDef(UnitLineId("varangian-guard-line"), "Varangian Guard line", (UnitId(2703), UnitId(2704)), (controller,)),
        UnitLineDef(UnitLineId("monk-line"), "Monk line", (UnitId(125),), (evidence,)),
        UnitLineDef(UnitLineId("ram-line"), "Ram line", (UnitId(1258), UnitId(422), UnitId(548)), (evidence,)),
        UnitLineDef(UnitLineId("mangonel-line"), "Mangonel line", (UnitId(280),), (evidence,)),
        UnitLineDef(UnitLineId("scorpion-line"), "Scorpion line", (UnitId(279),), (evidence,)),
        UnitLineDef(UnitLineId("siege-tower-line"), "Siege Tower line", (UnitId(1105),), (evidence,)),
        UnitLineDef(UnitLineId("trebuchet-line"), "Trebuchet line", (UnitId(331),), (evidence,)),
        UnitLineDef(UnitLineId("bombard-cannon-line"), "Bombard Cannon line", (UnitId(36),), (evidence,)),
        UnitLineDef(UnitLineId("fire-galley-line"), "Fire Galley line", (UnitId(1103),), (evidence,)),
        UnitLineDef(UnitLineId("fire-ship-line"), "Fire Ship line", (UnitId(529), UnitId(532)), (evidence,)),
        UnitLineDef(UnitLineId("dromon-line"), "Dromon line", (UnitId(1795),), (evidence,)),
    )
    units = (
        _unit(4, "Archer", "archer-line", Age.FEUDAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_to=24),
        _unit(5, "Hand Cannoneer", "hand-cannoneer-line", Age.IMPERIAL, 87, ResourceCost(food=45, gold=50), classes=("RANGED",)),
        _unit(6, "Elite Skirmisher", "skirmisher-line", Age.CASTLE, 87, ResourceCost(food=25, wood=35), classes=("RANGED",), upgrades_from=7, upgrades_to=None),
        _unit(7, "Skirmisher", "skirmisher-line", Age.FEUDAL, 87, ResourceCost(food=25, wood=35), classes=("RANGED",), upgrades_to=6),
        _unit(24, "Crossbowman", "crossbow-line", Age.CASTLE, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=4, upgrades_to=492),
        _unit(36, "Bombard Cannon", "bombard-cannon-line", Age.IMPERIAL, 49, ResourceCost(wood=225, gold=225), classes=("SIEGE",)),
        _unit(38, "Knight", "knight-line", Age.CASTLE, 101, ResourceCost(food=60, gold=75), classes=("CAVALRY",), upgrades_to=283),
        _unit(39, "Cavalry Archer", "cavalry-archer-line", Age.CASTLE, 87, ResourceCost(wood=40, gold=60), classes=("RANGED", "CAVALRY"), upgrades_to=474),
        _unit(40, "Cataphract", "cataphract-line", Age.CASTLE, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE"), upgrades_to=553),
        _unit(74, "Militia", "militia-line", Age.DARK, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",), upgrades_to=75),
        _unit(75, "Man-at-Arms", "militia-line", Age.FEUDAL, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",), upgrades_from=74, upgrades_to=77),
        _unit(77, "Long Swordsman", "militia-line", Age.CASTLE, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",), upgrades_from=75, upgrades_to=473),
        _unit(93, "Spearman", "spearman-line", Age.FEUDAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_to=358),
        _unit(125, "Monk", "monk-line", Age.CASTLE, 104, ResourceCost(gold=100), classes=("MONK",)),
        _unit(279, "Scorpion", "scorpion-line", Age.CASTLE, 49, ResourceCost(wood=75, gold=75), classes=("SIEGE",)),
        _unit(280, "Mangonel", "mangonel-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=135), classes=("SIEGE",), upgrades_to=None),
        _unit(283, "Cavalier", "knight-line", Age.IMPERIAL, 101, ResourceCost(food=60, gold=75), classes=("CAVALRY",), upgrades_from=38, upgrades_to=569),
        _unit(329, "Camel Rider", "camel-rider-line", Age.CASTLE, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",), upgrades_to=330),
        _unit(330, "Heavy Camel Rider", "camel-rider-line", Age.IMPERIAL, 101, ResourceCost(food=55, gold=60), classes=("CAVALRY",), upgrades_from=329),
        _unit(331, "Trebuchet", "trebuchet-line", Age.IMPERIAL, 82, ResourceCost(wood=200, gold=200), classes=("SIEGE",)),
        _unit(358, "Pikeman", "spearman-line", Age.CASTLE, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=93, upgrades_to=359),
        _unit(359, "Halberdier", "spearman-line", Age.IMPERIAL, 12, ResourceCost(food=35, wood=25), classes=("INFANTRY",), upgrades_from=358),
        _unit(422, "Capped Ram", "ram-line", Age.IMPERIAL, 49, ResourceCost(wood=160, gold=75), classes=("SIEGE",), upgrades_from=1258, upgrades_to=548),
        _unit(548, "Siege Ram", "ram-line", Age.IMPERIAL, 49, ResourceCost(wood=160, gold=75), classes=("SIEGE",), upgrades_from=422),
        _unit(440, "Petard", "petard-line", Age.CASTLE, 82, ResourceCost(food=65, gold=20), classes=("SIEGE", "UNIQUE")),
        _unit(441, "Hussar", "scout-cavalry-line", Age.IMPERIAL, 101, ResourceCost(food=80), classes=("CAVALRY",), upgrades_from=546),
        _unit(448, "Scout Cavalry", "scout-cavalry-line", Age.FEUDAL, 101, ResourceCost(food=80), classes=("CAVALRY",), upgrades_to=546),
        _unit(474, "Heavy Cavalry Archer", "cavalry-archer-line", Age.IMPERIAL, 87, ResourceCost(wood=40, gold=60), classes=("CAVALRY", "RANGED"), upgrades_from=39),
        _unit(473, "Two-Handed Swordsman", "militia-line", Age.IMPERIAL, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",), upgrades_from=77, upgrades_to=567),
        _unit(492, "Arbalester", "crossbow-line", Age.IMPERIAL, 87, ResourceCost(wood=25, gold=45), classes=("RANGED",), upgrades_from=24),
        _unit(529, "Fire Ship", "fire-ship-line", Age.CASTLE, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",), upgrades_to=532),
        _unit(532, "Fast Fire Ship", "fire-ship-line", Age.IMPERIAL, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",), upgrades_from=529),
        _unit(546, "Light Cavalry", "scout-cavalry-line", Age.CASTLE, 101, ResourceCost(food=80), classes=("CAVALRY",), upgrades_from=448, upgrades_to=441),
        _unit(553, "Elite Cataphract", "cataphract-line", Age.IMPERIAL, 82, ResourceCost(food=70, gold=75), classes=("CAVALRY", "UNIQUE"), upgrades_from=40),
        _unit(567, "Champion", "militia-line", Age.IMPERIAL, 12, ResourceCost(food=50, gold=20), classes=("INFANTRY",), upgrades_from=473),
        _unit(569, "Paladin", "knight-line", Age.IMPERIAL, 101, ResourceCost(food=60, gold=75), classes=("CAVALRY",), upgrades_from=283),
        _unit(1103, "Fire Galley", "fire-galley-line", Age.FEUDAL, 45, ResourceCost(wood=75, gold=45), classes=("NAVAL",)),
        _unit(1105, "Siege Tower", "siege-tower-line", Age.CASTLE, 49, ResourceCost(wood=100, gold=120), classes=("SIEGE",)),
        _unit(1258, "Battering Ram", "ram-line", Age.CASTLE, 49, ResourceCost(wood=160, gold=75), classes=("SIEGE",), upgrades_to=422),
        _unit(1795, "Dromon", "dromon-line", Age.IMPERIAL, 45, ResourceCost(wood=175, gold=150), classes=("NAVAL",)),
        _unit(
            2703,
            "Varangian Guard",
            "varangian-guard-line",
            Age.CASTLE,
            12,
            ResourceCost(food=65, gold=45),
            classes=("INFANTRY", "UNIQUE"),
            validity=Validity(patch, None),
            upgrades_to=2704,
            engine_classes=(EngineUnitClass.INFANTRY, EngineUnitClass.SHOCK_INFANTRY),
            effects=(
                UnitEffect(
                    UnitEffectKind.PASSIVE_RESOURCE_GENERATION,
                    "gold-when-fighting-other-units",
                    value="combat-triggered",
                    resource=Resource.GOLD,
                    provenance=(controller,),
                ),
                UnitEffect(
                    UnitEffectKind.TECHNOLOGY_INTERACTION,
                    "affected-by-gambesons",
                    target=EntitySelector.technology(TechId(875)),
                    provenance=(controller,),
                ),
            ),
            provenance=(evidence, controller),
        ),
        _unit(
            2704,
            "Elite Varangian Guard",
            "varangian-guard-line",
            Age.IMPERIAL,
            12,
            ResourceCost(food=65, gold=45),
            classes=("INFANTRY", "UNIQUE"),
            validity=Validity(patch, None),
            upgrades_from=2703,
            engine_classes=(EngineUnitClass.INFANTRY, EngineUnitClass.SHOCK_INFANTRY),
            effects=(
                UnitEffect(
                    UnitEffectKind.PASSIVE_RESOURCE_GENERATION,
                    "gold-when-fighting-other-units",
                    value="combat-triggered",
                    resource=Resource.GOLD,
                    provenance=(controller,),
                ),
                UnitEffect(
                    UnitEffectKind.TECHNOLOGY_INTERACTION,
                    "affected-by-gambesons",
                    target=EntitySelector.technology(TechId(875)),
                    provenance=(controller,),
                ),
            ),
            provenance=(evidence, controller),
        ),
    )
    techs = (
        TechnologyDef(TechId(47), "Chemistry", Age.IMPERIAL, (ResearchProvider(BuildingId(209)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(93), "Ballistics", Age.CASTLE, (ResearchProvider(BuildingId(209)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(374), "Careening", Age.CASTLE, (ResearchProvider(BuildingId(209)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(375), "Dry Dock", Age.IMPERIAL, (ResearchProvider(BuildingId(209)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(373), "Shipwright", Age.IMPERIAL, (ResearchProvider(BuildingId(209)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(222), "Man-at-Arms", Age.FEUDAL, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(75),), provenance=(evidence,)),
        TechnologyDef(TechId(207), "Long Swordsman", Age.CASTLE, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(77),), provenance=(evidence,)),
        TechnologyDef(TechId(217), "Two-Handed Swordsman", Age.IMPERIAL, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(473),), provenance=(evidence,)),
        TechnologyDef(TechId(264), "Champion", Age.IMPERIAL, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(567),), provenance=(evidence,)),
        TechnologyDef(TechId(197), "Pikeman", Age.CASTLE, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(358),), provenance=(evidence,)),
        TechnologyDef(TechId(429), "Halberdier", Age.IMPERIAL, (ResearchProvider(BuildingId(12)),), None, None, upgrades=(UnitId(359),), provenance=(evidence,)),
        TechnologyDef(TechId(602), "Arson", Age.FEUDAL, (ResearchProvider(BuildingId(12)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(875), "Gambesons", Age.CASTLE, (ResearchProvider(BuildingId(12)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(215), "Squires", Age.CASTLE, (ResearchProvider(BuildingId(12)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(100), "Crossbowman", Age.CASTLE, (ResearchProvider(BuildingId(87)),), None, None, upgrades=(UnitId(24),), provenance=(evidence,)),
        TechnologyDef(TechId(237), "Arbalester", Age.IMPERIAL, (ResearchProvider(BuildingId(87)),), None, None, upgrades=(UnitId(492),), provenance=(evidence,)),
        TechnologyDef(TechId(98), "Elite Skirmisher", Age.CASTLE, (ResearchProvider(BuildingId(87)),), None, None, upgrades=(UnitId(6),), provenance=(evidence,)),
        TechnologyDef(TechId(218), "Heavy Cavalry Archer", Age.IMPERIAL, (ResearchProvider(BuildingId(87)),), None, None, upgrades=(UnitId(474),), provenance=(evidence,)),
        TechnologyDef(TechId(437), "Thumb Ring", Age.CASTLE, (ResearchProvider(BuildingId(87)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(436), "Parthian Tactics", Age.IMPERIAL, (ResearchProvider(BuildingId(87)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(254), "Light Cavalry", Age.CASTLE, (ResearchProvider(BuildingId(101)),), None, None, upgrades=(UnitId(546),), provenance=(evidence,)),
        TechnologyDef(TechId(428), "Hussar", Age.IMPERIAL, (ResearchProvider(BuildingId(101)),), None, None, upgrades=(UnitId(441),), provenance=(evidence,)),
        TechnologyDef(TechId(209), "Cavalier", Age.IMPERIAL, (ResearchProvider(BuildingId(101)),), None, None, upgrades=(UnitId(283),), provenance=(evidence,)),
        TechnologyDef(TechId(265), "Paladin", Age.IMPERIAL, (ResearchProvider(BuildingId(101)),), None, None, upgrades=(UnitId(569),), provenance=(evidence,)),
        TechnologyDef(TechId(236), "Heavy Camel Rider", Age.IMPERIAL, (ResearchProvider(BuildingId(101)),), None, None, upgrades=(UnitId(330),), provenance=(evidence,)),
        TechnologyDef(TechId(435), "Bloodlines", Age.FEUDAL, (ResearchProvider(BuildingId(101)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(39), "Husbandry", Age.CASTLE, (ResearchProvider(BuildingId(101)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(96), "Capped Ram", Age.IMPERIAL, (ResearchProvider(BuildingId(49)),), None, None, upgrades=(UnitId(422),), provenance=(evidence,)),
        TechnologyDef(TechId(255), "Siege Ram", Age.IMPERIAL, (ResearchProvider(BuildingId(49)),), None, None, upgrades=(UnitId(548),), provenance=(evidence,)),
        TechnologyDef(TechId(257), "Onager", Age.IMPERIAL, (ResearchProvider(BuildingId(49)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(239), "Heavy Scorpion", Age.IMPERIAL, (ResearchProvider(BuildingId(49)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(34), "Warships", Age.CASTLE, (ResearchProvider(BuildingId(45)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(35), "Heavy Warships", Age.IMPERIAL, (ResearchProvider(BuildingId(45)),), None, None, provenance=(evidence,)),
        TechnologyDef(TechId(246), "Fast Fire Ship", Age.IMPERIAL, (ResearchProvider(BuildingId(45)),), None, None, provenance=(evidence,)),
        TechnologyDef(
            TechId(8), "Town Watch", Age.FEUDAL, (ResearchProvider(BuildingId(109)),),
            ResourceCost(food=75), 25,
        ),
        TechnologyDef(
            TechId(61), "Logistica", Age.IMPERIAL, (ResearchProvider(BuildingId(82)),),
            ResourceCost(food=800, gold=600), 50,
        ),
        TechnologyDef(
            TechId(1454), "Elite Varangian Guard", Age.IMPERIAL, (ResearchProvider(BuildingId(12)),),
            None, None, validity=Validity(patch, None), provenance=(controller,),
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
                    attribute="range",
                    modifier=NumericModifier(ModifierOperation.ADD, 1),
                ),
                TechEffect(
                    kind="STAT_MODIFIER",
                    target=EntitySelector.unit_line(UnitLineId("dromon-line")),
                    attribute="blast-radius",
                    modifier=NumericModifier(ModifierOperation.ADD, Rational(1, 5)),
                ),
                TechEffect(
                    kind="STAT_MODIFIER",
                    target=EntitySelector.building(BuildingId(236)),
                    attribute="blast-radius",
                    modifier=NumericModifier(ModifierOperation.ADD, Rational(1, 2)),
                ),
            ),
        ),
        TechnologyDef(
            TechId(906), "Fishing Lines", Age.FEUDAL, (ResearchProvider(BuildingId(45)),),
            None, None,
        ),
    )
    upgrade_relations = (
        UpgradeRelation(UnitId(74), UnitId(75), TechId(222), (evidence,)),
        UpgradeRelation(UnitId(75), UnitId(77), TechId(207), (evidence,)),
        UpgradeRelation(UnitId(77), UnitId(473), TechId(217), (evidence,)),
        UpgradeRelation(UnitId(473), UnitId(567), TechId(264), (evidence,)),
        UpgradeRelation(UnitId(93), UnitId(358), TechId(197), (evidence,)),
        UpgradeRelation(UnitId(358), UnitId(359), TechId(429), (evidence,)),
        UpgradeRelation(UnitId(4), UnitId(24), TechId(100), (evidence,)),
        UpgradeRelation(UnitId(24), UnitId(492), TechId(237), (evidence,)),
        UpgradeRelation(UnitId(7), UnitId(6), TechId(98), (evidence,)),
        UpgradeRelation(UnitId(39), UnitId(474), TechId(218), (evidence,)),
        UpgradeRelation(UnitId(448), UnitId(546), TechId(254), (evidence,)),
        UpgradeRelation(UnitId(546), UnitId(441), TechId(428), (evidence,)),
        UpgradeRelation(UnitId(38), UnitId(283), TechId(209), (evidence,)),
        UpgradeRelation(UnitId(283), UnitId(569), TechId(265), (evidence,)),
        UpgradeRelation(UnitId(329), UnitId(330), TechId(236), (evidence,)),
        UpgradeRelation(UnitId(1258), UnitId(422), TechId(96), (evidence,)),
        UpgradeRelation(UnitId(422), UnitId(548), TechId(255), (evidence,)),
        UpgradeRelation(UnitId(529), UnitId(532), TechId(246), (evidence,)),
        UpgradeRelation(UnitId(40), UnitId(553), TechId(361), (evidence,)),
        UpgradeRelation(UnitId(2703), UnitId(2704), TechId(1454), (evidence, controller)),
    )
    advances = (
        AgeAdvanceDef(
            AgeAdvanceId("feudal-age"),
            Age.FEUDAL,
            BuildingId(109),
            ResourceCost(food=500),
            None,
            from_age=Age.DARK,
            native_tech_id=TechId(101),
            prerequisites=(),
            provenance=(evidence,),
        ),
        AgeAdvanceDef(
            AgeAdvanceId("castle-age"),
            Age.CASTLE,
            BuildingId(109),
            ResourceCost(food=800, gold=200),
            None,
            from_age=Age.FEUDAL,
            native_tech_id=TechId(102),
            prerequisites=(),
            provenance=(evidence,),
        ),
        AgeAdvanceDef(
            AgeAdvanceId("imperial-age"),
            Age.IMPERIAL,
            BuildingId(109),
            ResourceCost(food=1000, gold=800),
            None,
            from_age=Age.CASTLE,
            native_tech_id=TechId(103),
            prerequisites=(),
            provenance=(evidence,),
        ),
    )
    buildings = tuple(
        replace(item, provenance=item.provenance or (evidence,))
        for item in buildings
    )
    units = tuple(
        replace(item, provenance=item.provenance or (evidence,))
        for item in units
    )
    techs = tuple(
        replace(item, provenance=item.provenance or (evidence,))
        for item in techs
    )
    advances = tuple(
        replace(item, provenance=item.provenance or (evidence,))
        for item in advances
    )
    resolved_buildings = tuple(sorted(buildings, key=lambda item: int(item.id)))
    resolved_units = tuple(sorted(units, key=lambda item: int(item.id)))
    resolved_lines = tuple(sorted(lines, key=lambda item: str(item.id)))
    resolved_techs = tuple(sorted(techs, key=lambda item: int(item.id)))
    resolved_advances = tuple(sorted(advances, key=lambda item: item.age.value))
    coverage = FactualCoverage(
        CoverageStatus.FACTUAL_SUBSET,
        verified_buildings=frozenset(item.id for item in resolved_buildings),
        verified_units=frozenset(item.id for item in resolved_units),
        verified_unit_lines=frozenset(item.id for item in resolved_lines),
        verified_technologies=frozenset(item.id for item in resolved_techs),
        verified_age_advances=frozenset(item.id for item in resolved_advances),
        verified_upgrade_relations=frozenset(
            (item.previous, item.current, item.research)
            for item in upgrade_relations
        ),
    )
    return GameData(
        patch=patch,
        buildings=resolved_buildings,
        units=resolved_units,
        unit_lines=resolved_lines,
        technologies=resolved_techs,
        age_advances=resolved_advances,
        upgrade_relations=upgrade_relations,
        provenance=(evidence, community),
        coverage=coverage,
    )
