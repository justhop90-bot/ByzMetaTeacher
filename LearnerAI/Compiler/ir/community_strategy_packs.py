"""Community-derived Byzantine strategy synthesis packs.

This module contains strategy policy only. It reuses the existing _StrategyProfile,
_StrategicDemandSpec, _StrategicNumberMode, and native lifecycle machinery. It does
not introduce a scheduler or a second .per language.
"""
from __future__ import annotations

from dataclasses import replace

from .civ_profile import EffectiveCivData
from .game_data import Age, BuildingId, Resource, UnitLineId
from .model import LifecycleState
from .strategy import (
    CapabilityIntent as _CapabilityIntent,
    CapabilityIntentKind as _CapabilityIntentKind,
    ExecutionDemandTemplate as _ExecutionDemandTemplate,
    OpportunityCostPolicy as _OpportunityCostPolicy,
    ProtectedResourceFloor as _ProtectedResourceFloor,
    StrategicDemandSpec as _StrategicDemandSpec,
    StrategicEvidence as _StrategicEvidence,
    StrategicEvidenceKind as _StrategicEvidenceKind,
    StrategicPriority as _StrategicPriority,
    StrategicTarget as _StrategicTarget,
    StrategicTargetKind as _StrategicTargetKind,
    StrategicNumberMode as _StrategicNumberMode,
    StrategyPosture as _StrategyPosture,
    StrategyProfile as _StrategyProfile,
    StrategicObservationSpec as _StrategicObservationSpec,
    CapabilityRecoveryContract as _CapabilityRecoveryContract,
    StrategicMilitaryComposition as _StrategicMilitaryComposition,
)
from .endgame import (
    EndgameMode as _EndgameMode,
    EndgamePolicyRule as _EndgamePolicyRule,
    EndgamePlan as _EndgamePlan,
    EndgameWinCondition as _EndgameWinCondition,
    EndgameFrontierState as _EndgameFrontierState,
    EndgamePushContract as _EndgamePushContract,
)
from .versioning import EvidenceKind, EvidenceRef
from .map_profile import default_byzantine_map_profiles
from .opening import default_byzantine_opening_selector
from .economic_control import default_byzantine_economy_controller
from .camp_control import CampResource, default_byzantine_camp_controller

_ENDGAME_CATAPHRACT_TARGET = 30
_ENDGAME_VARANGIAN_TARGET = 24
_ENDGAME_RAM_TARGET = 8
_ENDGAME_TREBUCHET_TARGET = 8


def _airef_provenance(effective: EffectiveCivData, locator: str) -> tuple[EvidenceRef, ...]:
    return (
        EvidenceRef(
            kind=EvidenceKind.AIREF,
            source="https://airef.github.io",
            revision="master",
            locator=locator,
            patch=effective.patch,
        ),
    )


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace("/", "-")


def _building(effective: EffectiveCivData, name: str):
    wanted = _slug(name)
    for item in effective.buildings:
        if _slug(item.name) == wanted:
            return item
    raise ValueError(f"strategy synthesis requires verified building '{name}'")


def _tech(effective: EffectiveCivData, name: str):
    wanted = _slug(name)
    for item in effective.technologies:
        if _slug(item.name) == wanted:
            return item
    raise ValueError(f"strategy synthesis requires verified technology '{name}'")


def _line(effective: EffectiveCivData, line: str):
    return effective.unit_line(UnitLineId(line))


def _provider_for_line(effective: EffectiveCivData, line: str) -> BuildingId:
    unit_line = _line(effective, line)
    if not unit_line.members:
        raise ValueError(f"strategy synthesis line '{line}' has no members")
    unit = effective.unit(int(unit_line.members[0]))
    if not unit.providers:
        raise ValueError(f"strategy synthesis line '{line}' has no verified provider")
    return unit.providers[0].building


def _observation(
    identity: str,
    expression: str,
    provenance: tuple[EvidenceRef, ...],
) -> _StrategicObservationSpec:
    return _StrategicObservationSpec(
        identity=identity,
        expression=expression,
        provenance=provenance,
    )


def _persistent(
    label: str,
    observation_ref: str,
) -> _StrategicEvidence:
    return _StrategicEvidence(
        _StrategicEvidenceKind.PERSISTENT,
        None,
        label,
        observation_ref=observation_ref,
    )


def _build_demand(
    *,
    identity: str,
    owner: str,
    posture: _StrategyPosture,
    priority: _StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building,
    requirements: tuple[str, ...],
    action_name: str | None = None,
    target_witness: str | None = None,
    release: str | None = None,
    opportunity_cost: _OpportunityCostPolicy | None = None,
    invalidate_ref: str | None = None,
    initial_state: LifecycleState = LifecycleState.ACTIVE,
) -> _StrategicDemandSpec:
    action_name = action_name or _slug(building.name)
    target_witness = target_witness or f"(building-type-count {action_name} > 0)"
    release = release or target_witness
    return _StrategicDemandSpec(
        identity=identity,
        owner=owner,
        posture=posture,
        priority=priority,
        reason=(_persistent(reason_label, reason_ref),),
        admissibility=(
            _persistent(f"{identity}:strategic-admission", reason_ref),
        ),
        invalidation=(
            _persistent(f"{identity}:policy-invalidation", invalidate_ref),
        ) if invalidate_ref else (),
        capability_intent=_CapabilityIntent(
            _CapabilityIntentKind.BUILD,
            "building",
            int(building.id),
        ),
        target=_StrategicTarget(
            _StrategicTargetKind.EXACT,
            "building",
            int(building.id),
        ),
        opportunity_cost=opportunity_cost,
        execution=_ExecutionDemandTemplate(
            requirements=requirements,
            action=f"(build {action_name})",
            witness=target_witness,
            release=release,
        ),
        recovery=_CapabilityRecoveryContract(),
        initial_state=initial_state,
    )


def _production_depth_demand(
    *,
    identity: str,
    building,
    floor: int,
    previous_floor: int,
    posture: _StrategyPosture,
    priority: _StrategicPriority,
    reason_ref: str,
    reason_label: str,
    age_guard: str,
    standing_demand: str,
    replacement_reason_ref: str | None = None,
    replacement_expression: str | None = None,
) -> _StrategicDemandSpec:
    building_token = _slug(building.name)
    requirements = [
        age_guard,
        standing_demand,
    ]
    if replacement_reason_ref is not None:
        if replacement_expression is None:
            raise ValueError("replacement_reason_ref requires replacement_expression")
        requirements[-1] = (
            "(or "
            f"{standing_demand} "
            f"{replacement_expression}"
            ")"
        )
    if previous_floor > 0:
        requirements.append(
            f"(building-type-count-total {building_token} >= {previous_floor})"
        )
    requirements.extend(
        (
            f"(building-type-count-total {building_token} < {floor})",
            f"(can-build {building_token})",
        )
    )
    demand = _build_demand(
        identity=identity,
        owner="production-depth",
        posture=posture,
        priority=priority,
        reason_ref=reason_ref,
        reason_label=reason_label,
        building=building,
        requirements=tuple(requirements),
        target_witness=f"(building-type-count {building_token} >= {floor})",
        release=f"(building-type-count {building_token} >= {floor})",
    )
    if replacement_reason_ref is not None:
        demand = replace(
            demand,
            reason=(
                *demand.reason,
                _persistent(
                    f"{identity}:attrition-replacement",
                    replacement_reason_ref,
                ),
            ),
        )
    return demand


def _research_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: _StrategyPosture,
    priority: _StrategicPriority,
    age_guard: str,
    age_observation_ref: str,
    tech_name: str,
    reason_label: str,
    resources: tuple[Resource, ...],
    minimum_floors: tuple[tuple[Resource, int], ...] = (),
    additional_requirements: tuple[str, ...] = (),
) -> _StrategicDemandSpec:
    tech = _tech(effective, tech_name)
    token = _slug(tech.name)
    complete_ref = f"{identity}-complete"
    pending_ref = f"{identity}-pending"
    floors = tuple(_ProtectedResourceFloor(resource, amount) for resource, amount in minimum_floors)
    policy = None
    if floors:
        policy = _OpportunityCostPolicy(
            owner=owner,
            protected_floors=floors,
            emergency_override_postures=(_StrategyPosture.FLUSH, _StrategyPosture.RUSH),
        )
    demand = _StrategicDemandSpec(
        identity=identity,
        owner=owner,
        posture=posture,
        priority=priority,
        reason=(
            _persistent(reason_label, pending_ref),
            _persistent(f"{identity}:age-window", age_observation_ref),
        ),
        admissibility=(
            _persistent(f"{identity}:age-admissibility", age_observation_ref),
        ),
        invalidation=(
            _persistent(f"{identity}:completed", complete_ref),
        ),
        capability_intent=_CapabilityIntent(
            _CapabilityIntentKind.RESEARCH,
            "technology",
            int(tech.id),
        ),
        target=_StrategicTarget(
            _StrategicTargetKind.EXACT,
            "technology",
            int(tech.id),
        ),
        opportunity_cost=policy,
        execution=_ExecutionDemandTemplate(
            requirements=(
                age_guard,
                *additional_requirements,
                f"(can-research-with-escrow {token})",
            ),
            action=f"(research {token})",
            witness=f"(research-completed {int(tech.id)})",
            release=f"(research-completed {int(tech.id)})",
            escrow_release_resources=resources,
        ),
        recovery=_CapabilityRecoveryContract(),
    )
    return demand


def _training_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: _StrategyPosture,
    priority: _StrategicPriority,
    reason_ref: str,
    reason_label: str,
    line: str,
    minimum: int,
    age_guard: str,
    action_symbol: str | None = None,
    witness_symbol: str | None = None,
    invalidate_ref: str | None = None,
) -> _StrategicDemandSpec:
    provider = _provider_for_line(effective, line)
    action_symbol = action_symbol or line
    witness_symbol = witness_symbol or action_symbol
    train_target = action_symbol
    return _StrategicDemandSpec(
        identity=identity,
        owner=owner,
        production_arbitration_group="production",
        posture=posture,
        priority=priority,
        reason=(_persistent(reason_label, reason_ref),),
        admissibility=(
            _persistent(f"{identity}:age-admission", reason_ref),
        ),
        invalidation=(
            _persistent(f"{identity}:policy-invalidation", invalidate_ref),
        ) if invalidate_ref else (),
        capability_intent=_CapabilityIntent(
            _CapabilityIntentKind.TRAIN,
            "unit-line",
            line,
            provider,
        ),
        target=_StrategicTarget(
            _StrategicTargetKind.CURRENT_QUEUED,
            "unit-line",
            line,
            minimum=minimum,
        ),
        opportunity_cost=None,
        execution=_ExecutionDemandTemplate(
            requirements=(
                age_guard,
                f"(can-train-with-escrow {train_target})",
                f"(unit-type-count-total {train_target} < {minimum})",
            ),
            action=f"(train {action_symbol})",
            witness=f"(unit-type-count {witness_symbol} >= {minimum})",
            release=f"(unit-type-count {witness_symbol} >= {minimum})",
        ),
        recovery=_CapabilityRecoveryContract(),
    )



def _endgame_training_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    priority: _StrategicPriority,
    line: str,
    minimum: int,
    reason_refs: tuple[str, ...],
    reason_labels: tuple[str, ...],
    requirement_expressions: tuple[str, ...],
    action_symbol: str | None = None,
    witness_symbol: str | None = None,
) -> _StrategicDemandSpec:
    if len(reason_refs) != len(reason_labels):
        raise ValueError("endgame training reason refs/labels must have equal length")
    provider = _provider_for_line(effective, line)
    action_symbol = action_symbol or line
    witness_symbol = witness_symbol or action_symbol
    reasons = tuple(
        _persistent(label, reference)
        for reference, label in zip(reason_refs, reason_labels)
    )
    requirements = (
        "(current-age >= imperial-age)",
        *requirement_expressions,
        f"(can-train-with-escrow {action_symbol})",
        f"(unit-type-count-total {action_symbol} < {minimum})",
    )
    return _StrategicDemandSpec(
        identity=identity,
        owner=owner,
        production_arbitration_group="production",
        posture=_StrategyPosture.CASTLE_POWER,
        priority=priority,
        reason=reasons,
        admissibility=(
            _persistent(
                f"{identity}:imperial-admission",
                "strategy-imperial-age",
            ),
        ),
        invalidation=(),
        capability_intent=_CapabilityIntent(
            _CapabilityIntentKind.TRAIN,
            "unit-line",
            line,
            provider,
        ),
        target=_StrategicTarget(
            _StrategicTargetKind.CURRENT_QUEUED,
            "unit-line",
            line,
            minimum=minimum,
        ),
        opportunity_cost=None,
        execution=_ExecutionDemandTemplate(
            requirements=requirements,
            action=f"(train {action_symbol})",
            witness=f"(unit-type-count {witness_symbol} >= {minimum})",
            release=f"(unit-type-count {witness_symbol} >= {minimum})",
        ),
        recovery=_CapabilityRecoveryContract(),
    )


_RESEARCH_PACK = (
    # Feudal economic multipliers take precedence over generic support research,
    # but the execution guard still yields whenever Castle Age is natively feasible.
    ("research-double-bit-axe", "economy", "feudal-age", "double-bit-axe", _StrategicPriority.ECONOMIC_MULTIPLIER, (Resource.FOOD, Resource.WOOD)),
    ("research-horse-collar", "economy", "feudal-age", "horse-collar", _StrategicPriority.ECONOMIC_MULTIPLIER, (Resource.FOOD, Resource.WOOD)),
    ("research-wheelbarrow", "economy", "feudal-age", "wheelbarrow", _StrategicPriority.ECONOMIC_MULTIPLIER, (Resource.FOOD,)),
    ("research-hand-cart", "economy", "castle-age", "hand-cart", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-bow-saw", "economy", "castle-age", "bow-saw", _StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-two-man-saw", "economy", "imperial-age", "two-man-saw", _StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-bodkin-arrow", "military", "castle-age", "bodkin-arrow", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-conscription", "military", "imperial-age", "conscription", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-chemistry", "military", "imperial-age", "chemistry", _StrategicPriority.SUPPORT, (Resource.GOLD,)),
    ("research-gold-mining", "economy", "feudal-age", "gold-mining", _StrategicPriority.SUPPORT, (Resource.FOOD,)),
    ("research-gold-shaft-mining", "economy", "castle-age", "gold-shaft-mining", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-heavy-plow", "economy", "castle-age", "heavy-plow", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-fletching", "military", "feudal-age", "fletching", _StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
)


def community_strategy_observations(
    effective: EffectiveCivData,
) -> tuple[_StrategicObservationSpec, ...]:
    town_center = _building(effective, "town-center")
    house = _building(effective, "house")
    outpost = _building(effective, "outpost")
    monastery = _building(effective, "monastery")
    siege_workshop = _building(effective, "siege-workshop")
    stable = _building(effective, "stable")
    archery_range = _building(effective, "archery-range")
    dock = _building(effective, "dock")
    blacksmith = _building(effective, "blacksmith")
    barracks = _building(effective, "barracks")
    castle = _building(effective, "castle")
    university = _building(effective, "university")
    lumber_camp = _building(effective, "lumber-camp")
    mining_camp = _building(effective, "mining-camp")
    opening_pressure = (
        "(or (players-unit-type-count any-enemy knight >= 3) "
        "(or (players-unit-type-count any-enemy archer-line >= 4) "
        "(players-unit-type-count any-enemy militia-line >= 5)))"
    )
    production_depth_observations = (
        (
            "barracks",
            "(or (unit-type-count-total varangian-guard-line >= {threshold}) "
            "(unit-type-count-total 359 >= {threshold}))",
            "strategy-production-barracks-depth",
        ),
        (
            "stable",
            "(or (or (unit-type-count-total cataphract-line >= {threshold}) "
            "(unit-type-count-total knight-line >= {threshold})) "
            "(unit-type-count-total camel-rider-line >= {threshold}))",
            "strategy-production-stable-depth",
        ),
        (
            "archery-range",
            "(or (unit-type-count-total crossbowman >= {threshold}) "
            "(unit-type-count-total skirmisher-line >= {threshold}))",
            "strategy-production-range-depth",
        ),
        (
            "siege-workshop",
            "(unit-type-count-total mangonel-line >= {threshold})",
            "strategy-production-siege-depth",
        ),
    )

    observations = [
        _observation(
            "strategy-castle-age",
            "(current-age >= castle-age)",
            effective.age_advance(Age.CASTLE).provenance,
        ),
        _observation(
            "strategy-imperial-age",
            "(current-age >= imperial-age)",
            effective.age_advance(Age.IMPERIAL).provenance,
        ),
        _observation(
            "strategy-endgame-attack-package-live",
            "(attack-soldier-count > 0)",
            _airef_provenance(effective, "commands/commands-details.html#attack-soldier-count"),
        ),
        _observation(
            "strategy-endgame-attack-package-cleared",
            "(attack-soldier-count <= 0)",
            _airef_provenance(effective, "commands/commands-details.html#attack-soldier-count"),
        ),
        _observation(
            "strategy-imperial-spend-food",
            "(and (current-age >= imperial-age) (food-amount >= 2200))",
            _airef_provenance(effective, "commands/commands-details.html#food-amount"),
        ),
        _observation(
            "strategy-imperial-spend-wood",
            "(and (current-age >= imperial-age) (wood-amount >= 2200))",
            _airef_provenance(effective, "commands/commands-details.html#wood-amount"),
        ),
        _observation(
            "strategy-imperial-spend-gold",
            "(and (current-age >= imperial-age) (gold-amount >= 2500))",
            _airef_provenance(effective, "commands/commands-details.html#gold-amount"),
        ),
        _observation(
            "strategy-imperial-cataphract-replacement",
            "(and (current-age >= imperial-age) (unit-type-count cataphract < 12))",
            effective.unit_line("cataphract-line").provenance,
        ),
        _observation(
            "strategy-imperial-varangian-replacement",
            "(and (current-age >= imperial-age) (unit-type-count varangian-guard < 12))",
            effective.unit_line("varangian-guard-line").provenance,
        ),
        _observation(
            "strategy-imperial-ram-replacement",
            "(and (current-age >= imperial-age) ((or (unit-type-count 422 < 2) (or (unit-type-count 548 < 2) (unit-type-count 1258 < 2)))))",
            _airef_provenance(effective, "commands/commands-details.html#unit-type-count"),
        ),
        _observation(
            "strategy-imperial-trebuchet-replacement",
            "(and (current-age >= imperial-age) (unit-type-count trebuchet < 2))",
            _airef_provenance(effective, "commands/commands-details.html#unit-type-count"),
        ),
        _observation(
            "strategy-arena-map",
            "(map-type arena)",
            _airef_provenance(effective, "commands/commands-details.html#map-type"),
        ),
        _observation(
            "strategy-opening-resource-front-ready",
            "(and (building-type-count-total house >= 1) (and (building-type-count-total lumber-camp >= 1) (building-type-count-total mining-camp >= 1)))",
            tuple(
                dict.fromkeys(
                    (*house.provenance,
                     *lumber_camp.provenance,
                     *mining_camp.provenance)
                )
            ),
        ),
        _observation(
            "strategy-opening-pressure",
            opening_pressure,
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-enemy-pressure",
            opening_pressure,
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-enemy-infantry-pressure",
            "(players-unit-type-count any-enemy militia-line >= 5)",
            effective.unit_line("militia-line").provenance,
        ),
        _observation(
            "strategy-enemy-infantry-pressure-cleared",
            "(players-unit-type-count any-enemy militia-line < 5)",
            effective.unit_line("militia-line").provenance,
        ),
        _observation(
            "strategy-enemy-ranged",
            "(players-unit-type-count any-enemy archer-line >= 4)",
            effective.unit_line("archer-line").provenance,
        ),
        _observation(
            "strategy-enemy-siege",
            "(players-unit-type-count any-enemy mangonel-line >= 2)",
            effective.unit_line("mangonel-line").provenance,
        ),
        _observation(
            "strategy-enemy-castle",
            f"(players-building-type-count any-enemy {int(castle.id)} >= 1)",
            castle.provenance,
        ),
        _observation(
            "strategy-town-center-capability",
            f"(building-type-count-total {int(town_center.id)} < 2)",
            town_center.provenance,
        ),
        _observation(
            "strategy-town-center-complete",
            f"(building-type-count-total {int(town_center.id)} >= 2)",
            town_center.provenance,
        ),
        _observation(
            "strategy-outpost-capability",
            f"(building-type-count-total {int(outpost.id)} < 1)",
            outpost.provenance,
        ),
        _observation(
            "strategy-monastery-capability",
            f"(building-type-count-total {int(monastery.id)} < 1)",
            monastery.provenance,
        ),
        _observation(
            "strategy-monastery-exists",
            f"(building-type-count-total {int(monastery.id)} >= 1)",
            monastery.provenance,
        ),
        _observation(
            "strategy-siege-workshop-capability",
            f"(building-type-count-total {int(siege_workshop.id)} < 1)",
            siege_workshop.provenance,
        ),
        _observation(
            "strategy-stable-capability",
            f"(building-type-count-total {int(stable.id)} < 1)",
            stable.provenance,
        ),
        _observation(
            "strategy-archery-capability",
            f"(building-type-count-total {int(archery_range.id)} < 1)",
            archery_range.provenance,
        ),
        _observation(
            "strategy-dock-exists",
            f"(building-type-count-total {int(dock.id)} >= 1)",
            dock.provenance,
        ),
        _observation(
            "strategy-water-islands",
            "(map-type islands)",
            _airef_provenance(effective, "commands/commands-details.html#map-type"),
        ),
        _observation(
            "strategy-own-transport-capable",
            "(unit-type-count transport-ship >= 1)",
            effective.unit(545).provenance,
        ),
        _observation(
            "strategy-enemy-naval-pressure",
            "(or (players-unit-type-count any-enemy galley-line >= 2) "
            "(players-unit-type-count any-enemy fire-galley-line >= 2))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("galley-line").provenance,
                     *effective.unit_line("fire-galley-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-enemy-naval-pressure-cleared",
            "(and (players-unit-type-count any-enemy galley-line < 2) "
            "(players-unit-type-count any-enemy fire-galley-line < 2))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("galley-line").provenance,
                     *effective.unit_line("fire-galley-line").provenance)
                )
            ),
        ),
        _observation(
            "strategy-own-warboat-floor",
            "(warboat-count >= 2)",
            _airef_provenance(effective, "commands/commands-details.html#warboat-count"),
        ),
        _observation(
            "strategy-blacksmith-exists",
            f"(building-type-count-total {int(blacksmith.id)} >= 1)",
            blacksmith.provenance,
        ),
        _observation(
            "strategy-barracks-exists",
            f"(building-type-count-total {int(barracks.id)} >= 1)",
            barracks.provenance,
        ),
        _observation(
            "strategy-university-exists",
            f"(building-type-count-total {int(university.id)} >= 1)",
            university.provenance,
        ),
    ]

    # resource-found is the supported native resource-front fact. Its latch/live
    # behavior remains OPEN, so this layer treats it as an observation signal only;
    # actual camp service is witnessed independently through dropsite distance.
    for resource, gatherer_sn, distance_sn, label in (
        (CampResource.WOOD, "sn-wood-gatherer-percentage", "sn-lumber-camp-max-distance", "wood"),
        (CampResource.GOLD, "sn-gold-gatherer-percentage", "sn-mining-camp-max-distance", "gold"),
        (CampResource.STONE, "sn-stone-gatherer-percentage", "sn-mining-camp-max-distance", "stone"),
    ):
        observations.extend(
            (
                _observation(
                    f"camp-front-{label}-active",
                    (
                        f"(and (current-age >= feudal-age) (resource-found {resource.value}))"
                        if resource is CampResource.STONE
                        else f"(resource-found {resource.value})"
                    ),
                    _airef_provenance(effective, "commands/commands-details.html#resource-found"),
                ),
                _observation(
                    f"camp-front-{label}-remote",
                    f"(or (dropsite-min-distance {resource.value} <= -1) (dropsite-min-distance {resource.value} s:>= {distance_sn}))",
                    _airef_provenance(effective, "commands/commands-details.html#dropsite-min-distance"),
                ),
            )
        )


    observations.append(
        _observation(
            "strategy-villager-continuity",
            "(unit-type-count-total villager < 110)",
            _airef_provenance(
                effective,
                "commands/commands-details.html#unit-type-count-total",
            ),
        )
    )

    for identity, _owner, _age, tech_name, _priority, _resources in _RESEARCH_PACK:
        tech = _tech(effective, tech_name)
        observations.append(
            _observation(
                f"{identity}-complete",
                f"(research-completed {int(tech.id)})",
                tech.provenance,
            )
        )
        observations.append(
            _observation(
                f"{identity}-pending",
                f"(not (research-completed {int(tech.id)}))",
                tech.provenance,
            )
        )

    replacement_depth_observations = (
        (
            "strategy-production-barracks-replacement",
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count varangian-guard < 12) "
            "(unit-type-count 359 < 12)))",
        ),
        (
            "strategy-production-stable-replacement",
            "(and (current-age >= imperial-age) "
            "(unit-type-count cataphract < 12))",
        ),
        (
            "strategy-production-range-replacement",
            "(and (current-age >= imperial-age) "
            "(or (unit-type-count 492 < 12) "
            "(unit-type-count skirmisher-line < 12)))",
        ),
        (
            "strategy-production-siege-replacement",
            "(and (current-age >= imperial-age) "
            "(unit-type-count trebuchet < 4))",
        ),
    )
    for identity, expression in replacement_depth_observations:
        observations.append(
            _observation(
                identity,
                expression,
                _airef_provenance(
                    effective,
                    "commands/commands-details.html#unit-type-count",
                ),
            )
        )

    for provider, expression_template, base_identity in production_depth_observations:
        thresholds = (6, 12, 18) if provider != "siege-workshop" else (2, 4, 6)
        for threshold in thresholds:
            identity = f"{base_identity}-{threshold}"
            expression = expression_template.format(threshold=threshold)
            observations.append(
                _observation(
                    identity,
                    expression,
                    _airef_provenance(
                        effective,
                        "commands/commands-details.html#unit-type-count-total",
                    ),
                )
            )

    return tuple(observations)


def community_strategy_demands(
    effective: EffectiveCivData,
) -> tuple[_StrategicDemandSpec, ...]:
    town_center = _building(effective, "town-center")
    outpost = _building(effective, "outpost")
    monastery = _building(effective, "monastery")
    siege_workshop = _building(effective, "siege-workshop")
    stable = _building(effective, "stable")
    archery_range = _building(effective, "archery-range")
    university = _building(effective, "university")
    lumber_camp = _building(effective, "lumber-camp")
    mining_camp = _building(effective, "mining-camp")
    observations = community_strategy_observations(effective)
    opening_pressure = (
        "(or (players-unit-type-count any-enemy knight >= 3) "
        "(or (players-unit-type-count any-enemy archer-line >= 4) "
        "(players-unit-type-count any-enemy militia-line >= 5)))"
    )
    demands: list[_StrategicDemandSpec] = []

    provider = _provider_for_line(effective, "villager-line")
    villager_demand = _StrategicDemandSpec(
        identity="civilian-villager-continuity",
        owner="economy",
        production_arbitration_group="production",
        posture=_StrategyPosture.BOOM,
        priority=_StrategicPriority.CORE,
        reason=(
            _persistent(
                "Villager production remains the P0 economic continuity floor",
                "strategy-villager-continuity",
            ),
        ),
        admissibility=(
            _persistent(
                "Villager production remains admissible until the age bank is issuable",
                "strategy-villager-continuity",
            ),
        ),
        invalidation=(),
        capability_intent=_CapabilityIntent(
            _CapabilityIntentKind.TRAIN,
            "unit-line",
            "villager-line",
            provider,
        ),
        target=_StrategicTarget(
            _StrategicTargetKind.CURRENT_QUEUED,
            "unit-line",
            "villager-line",
            minimum=110,
        ),
        opportunity_cost=None,
        execution=_ExecutionDemandTemplate(
            requirements=(
                "(current-age >= dark-age)",
                "(can-train villager)",
                "(not (and (current-age == dark-age) "
                "(unit-type-count-total villager >= 21)))",
                "(not (and (current-age == feudal-age) "
                "(and (unit-type-count-total villager >= 28) "
                "(and (building-type-count-total blacksmith >= 1) "
                "(and (building-type-count-total market >= 1) "
                "(can-research-with-escrow castle-age))))))",
            ),
            action="(train villager)",
            witness="(unit-type-count villager >= 110)",
            release="(unit-type-count villager >= 110)",
        ),
        recovery=_CapabilityRecoveryContract(),
    )
    demands.append(villager_demand)

    camp_specs = (
        (CampResource.WOOD, lumber_camp, 6, "sn-lumber-camp-max-distance"),
        (CampResource.GOLD, mining_camp, 5, "sn-mining-camp-max-distance"),
        (CampResource.STONE, mining_camp, 5, "sn-mining-camp-max-distance"),
    )
    stone_camp_policy = _OpportunityCostPolicy(
        owner="castle-trajectory",
        protected_floors=(
            _ProtectedResourceFloor(Resource.STONE, 650),
        ),
        emergency_override_postures=(
            _StrategyPosture.FLUSH,
            _StrategyPosture.RUSH,
        ),
    )
    for resource, building, max_count, distance_sn in camp_specs:
        label = resource.value
        active_ref = f"camp-front-{label}-active"
        remote_ref = f"camp-front-{label}-remote"
        active_expression = next(
            item.expression for item in observations if item.identity == active_ref
        )
        remote_expression = next(
            item.expression for item in observations if item.identity == remote_ref
        )
        for floor in range(1, max_count + 1):
            count_guard = f"(building-type-count-total {int(building.id)} < {floor})"
            requirements = [
                active_expression,
                count_guard,
                f"(can-build {_slug(building.name)})",
            ]
            if floor >= 2:
                requirements = [
                    active_expression,
                    remote_expression,
                    count_guard,
                    f"(can-build {_slug(building.name)})",
                ]
            building_token = _slug(building.name)
            action = f"(build {building_token})"
            witness = f"(building-type-count {_slug(building.name)} >= {floor})"
            demands.append(
                _StrategicDemandSpec(
                    identity=f"economy-{label}-camp-floor-{floor}",
                    owner=(
                        "castle-trajectory"
                        if resource is CampResource.STONE
                        else "economy-camps"
                    ),
                    posture=_StrategyPosture.BOOM,
                    priority=(
                        _StrategicPriority.SUPPORT
                        if floor <= 2
                        else _StrategicPriority.OPTIONAL
                    ),
                    reason=(
                        _persistent(
                            f"Active {label} resource front requires a functional "
                            f"{label} dropsite floor {floor}",
                            active_ref,
                        ),
                    ),
                    admissibility=(
                        _persistent(
                            f"The {label} camp floor remains strategically admissible "
                            "while the resource front is active",
                            active_ref,
                        ),
                    ),
                    invalidation=(),
                    capability_intent=_CapabilityIntent(
                        _CapabilityIntentKind.BUILD,
                        "building",
                        int(building.id),
                    ),
                    target=_StrategicTarget(
                        _StrategicTargetKind.EXACT,
                        "building",
                        int(building.id),
                    ),
                    opportunity_cost=(
                        stone_camp_policy
                        if resource is CampResource.STONE
                        else None
                    ),
                    execution=_ExecutionDemandTemplate(
                        requirements=tuple(requirements),
                        action=action,
                        witness=witness,
                        release=witness,
                    ),
                    initial_state=(
                        LifecycleState.ACTIVE
                        if floor == 1 and resource is not CampResource.STONE
                        else LifecycleState.RELEASED
                    ),
                    provenance=_airef_provenance(
                        effective,
                        "commands/commands-details.html#build",
                    ),
                )
            )


    imperial = effective.age_advance(Age.IMPERIAL)
    imperial_cost = effective.cost_of_age_advance(Age.IMPERIAL)
    demands.append(
        _StrategicDemandSpec(
            identity="imperial-conversion",
            owner="age-transition",
            posture=_StrategyPosture.CASTLE_POWER,
            priority=_StrategicPriority.CORE,
            reason=(
                _persistent("Imperial remains the next durable strategic conversion", "strategy-castle-age"),
            ),
            admissibility=(
                _persistent("Imperial remains admissible in Castle Age", "strategy-castle-age"),
            ),
            invalidation=(
                _persistent("Imperial conversion complete", "strategy-imperial-age"),
            ),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.AGE_ADVANCE,
                "age-advance",
                "imperial-age",
                imperial.provider_building,
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.EXACT,
                "age-advance",
                "imperial-age",
            ),
            opportunity_cost=_OpportunityCostPolicy(
                owner="age-transition",
                protected_floors=(
                    _ProtectedResourceFloor(Resource.FOOD, imperial_cost.food),
                    _ProtectedResourceFloor(Resource.GOLD, imperial_cost.gold),
                ),
                emergency_override_postures=(_StrategyPosture.FLUSH, _StrategyPosture.RUSH),
            ),
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(can-research-with-escrow imperial-age)",
                ),
                action="(research imperial-age)",
                witness="(current-age >= imperial-age)",
                release="(current-age >= imperial-age)",
                escrow_release_resources=(Resource.FOOD, Resource.GOLD),
            ),
        )
    )

    # Castle economic expansion. Native can-build remains the authoritative
    # affordability/provider admission; the strategic policy decides when the
    # expansion is wanted.
    tc_policy = _OpportunityCostPolicy(
        owner="castle-economy",
        protected_floors=(
            _ProtectedResourceFloor(Resource.WOOD, effective.cost_of(f"building:{int(town_center.id)}").wood),
        ),
        emergency_override_postures=(_StrategyPosture.FLUSH, _StrategyPosture.RUSH),
    )
    demands.append(
        _StrategicDemandSpec(
            identity="castle-second-town-center",
            owner="castle-economy",
            posture=_StrategyPosture.CASTLE_POWER,
            priority=_StrategicPriority.CORE,
            reason=(
                _persistent(
                    "Castle Age creates an economic expansion opportunity",
                    "strategy-castle-age",
                ),
            ),
            admissibility=(
                _persistent(
                    "Second Town Center opportunity remains strategically admissible",
                    "strategy-town-center-capability",
                ),
            ),
            invalidation=(
                _persistent(
                    "Second Town Center objective is already satisfied",
                    "strategy-town-center-complete",
                ),
            ),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.BUILD,
                "building",
                int(town_center.id),
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.EXACT,
                "building",
                int(town_center.id),
            ),
            opportunity_cost=tc_policy,
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(building-type-count-total town-center < 2)",
                    "(can-build town-center)",
                ),
                action="(build town-center)",
                witness="(building-type-count town-center >= 2)",
                release="(building-type-count town-center >= 2)",
            ),
        )
    )

    demands.extend(
        (
            _build_demand(
                identity="castle-stable-capability",
                owner="production",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.SUPPORT,
                reason_ref="strategy-castle-age",
                reason_label="Castle cavalry production requires a stable provider",
                building=stable,
                requirements=(" (can-build stable)".strip(),),
            ),
            _build_demand(
                identity="castle-archery-capability",
                owner="production",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.SUPPORT,
                reason_ref="strategy-enemy-ranged",
                reason_label="Sustained ranged pressure creates a real ranged-production capability demand",
                building=archery_range,
                requirements=(" (can-build archery-range)".strip(),),
                invalidate_ref="strategy-imperial-age",
            ),
            _build_demand(
                identity="castle-siege-capability",
                owner="production",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-siege",
                reason_label="Enemy siege creates an explicit siege-capability demand",
                building=siege_workshop,
                requirements=(" (can-build siege-workshop)".strip(),),
            ),
            _build_demand(
                identity="castle-monastery-capability",
                owner="support",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.OPTIONAL,
                reason_ref="strategy-castle-age",
                reason_label="Castle support includes a Monk/relic capability",
                building=monastery,
                requirements=(" (can-build monastery)".strip(),),
            ),
            _build_demand(
                identity="imperial-university-capability",
                owner="research",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.SUPPORT,
                reason_ref="strategy-castle-age",
                reason_label="Imperial conversion requires a verified university provider",
                building=university,
                requirements=("(current-age >= castle-age)", "(can-build university)"),
            ),
            _build_demand(
                identity="adaptive-outpost",
                owner="defense",
                posture=_StrategyPosture.FLUSH,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-pressure",
                reason_label="Sustained enemy pressure justifies one defensive observation point",
                building=outpost,
                requirements=(
                    "(current-age >= feudal-age)",
                    opening_pressure,
                    "(or (dropsite-min-distance gold >= 7) "
                    "(or (dropsite-min-distance stone >= 7) "
                    "(dropsite-min-distance wood >= 7)))",
                    "(can-build outpost)",
                ),
                initial_state=LifecycleState.RELEASED,
            ),
        )
    )

    for identity, owner, age, tech_name, priority, resources in _RESEARCH_PACK:
        demand = _research_demand(
            effective=effective,
            identity=identity,
            owner=owner,
            posture=(
                _StrategyPosture.CASTLE_POWER
                if age in {"castle-age", "imperial-age"}
                else _StrategyPosture.BOOM
            ),
            priority=priority,
            age_guard=f"(current-age >= {age})",
            age_observation_ref={
                "feudal-age": "current-feudal-age",
                "castle-age": "strategy-castle-age",
                "imperial-age": "strategy-imperial-age",
            }[age],
            tech_name=tech_name,
            reason_label=f"Community research package: {tech_name}",
            resources=resources,
            additional_requirements=(
                ("(not (can-research-with-escrow castle-age))",)
                if tech_name in {"double-bit-axe", "horse-collar", "wheelbarrow"}
                and age == "feudal-age"
                else ()
            ),
        )
        demands.append(demand)

    # Standing military floors.
    demands.extend(
        (
            _training_demand(
                effective=effective,
                identity="castle-knight-floor",
                owner="military",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.CORE,
                reason_ref="strategy-castle-age",
                reason_label="Maintain a Castle mobility floor for pressure/reaction",
                line="knight-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="castle-cataphract-floor",
                owner="military",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.CORE,
                reason_ref="strategy-castle-age",
                reason_label="Maintain the Byzantine premium Castle power floor",
                line="cataphract-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="castle-varangian-guard-floor",
                owner="castle-varangian",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-infantry-pressure",
                reason_label="Maintain a conditional Byzantine Varangian Guard floor against sustained infantry pressure",
                line="varangian-guard-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
                action_symbol="varangian-guard",
                witness_symbol="varangian-guard",
                invalidate_ref="strategy-enemy-infantry-pressure-cleared",
            ),
            _training_demand(
                effective=effective,
                identity="castle-siege-floor",
                owner="military",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-siege",
                reason_label="Maintain a mobile anti-siege response when enemy siege is observed",
                line="knight-line",
                minimum=3,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="castle-mangonel-floor",
                owner="military",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-ranged",
                reason_label="Sustained ranged pressure justifies a Castle siege-support floor",
                line="mangonel-line",
                minimum=1,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="imperial-bombard-floor",
                owner="military",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-castle",
                reason_label="Enemy fortification creates an Imperial Bombard Cannon conversion demand",
                line="bombard-cannon-line",
                minimum=1,
                age_guard="(current-age >= imperial-age)",
                action_symbol="bombard-cannon",
                witness_symbol="bombard-cannon",
            ),
            _training_demand(
                effective=effective,
                identity="castle-monk-floor",
                owner="support",
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.OPTIONAL,
                reason_ref="strategy-monastery-exists",
                reason_label="Use a bounded Monk support floor once the monastery capability exists",
                line="monk-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
                action_symbol="monk",
                witness_symbol="monk",
            ),
        )
    )

    # Provider depth follows standing military demand. Queue depth remains OPEN:
    # these demands expand the physical production network only after witnessed
    # standing units reach the next threshold.
    standing_depth_observations = {
        item.identity: item.expression
        for item in observations
    }
    provider_depth_specs = (
        ("barracks", "castle-barracks-depth-2", 2, 0, "strategy-production-barracks-depth-6", "(current-age >= castle-age)", None),
        ("barracks", "imperial-barracks-depth-3", 3, 2, "strategy-production-barracks-depth-12", "(current-age >= imperial-age)", "strategy-production-barracks-replacement"),
        ("barracks", "imperial-barracks-depth-4", 4, 3, "strategy-production-barracks-depth-18", "(current-age >= imperial-age)", "strategy-production-barracks-replacement"),
        ("stable", "castle-stable-depth-2", 2, 0, "strategy-production-stable-depth-6", "(current-age >= castle-age)", None),
        ("stable", "imperial-stable-depth-3", 3, 2, "strategy-production-stable-depth-12", "(current-age >= imperial-age)", "strategy-production-stable-replacement"),
        ("stable", "imperial-stable-depth-4", 4, 3, "strategy-production-stable-depth-18", "(current-age >= imperial-age)", "strategy-production-stable-replacement"),
        ("archery-range", "castle-range-depth-2", 2, 0, "strategy-production-range-depth-6", "(current-age >= castle-age)", None),
        ("archery-range", "imperial-range-depth-3", 3, 2, "strategy-production-range-depth-12", "(current-age >= imperial-age)", "strategy-production-range-replacement"),
        ("archery-range", "imperial-range-depth-4", 4, 3, "strategy-production-range-depth-18", "(current-age >= imperial-age)", "strategy-production-range-replacement"),
        ("siege-workshop", "castle-siege-depth-2", 2, 0, "strategy-production-siege-depth-2", "(current-age >= castle-age)", None),
        ("siege-workshop", "imperial-siege-depth-3", 3, 2, "strategy-production-siege-depth-4", "(current-age >= imperial-age)", "strategy-production-siege-replacement"),
        ("siege-workshop", "imperial-siege-depth-4", 4, 3, "strategy-production-siege-depth-6", "(current-age >= imperial-age)", "strategy-production-siege-replacement"),
    )
    for (
        building_name,
        identity,
        floor,
        previous_floor,
        standing_observation_ref,
        age_guard,
        replacement_reason_ref,
    ) in provider_depth_specs:
        building = _building(effective, building_name)
        standing_demand = standing_depth_observations[standing_observation_ref]
        demands.append(
            _production_depth_demand(
                identity=identity,
                building=building,
                floor=floor,
                previous_floor=previous_floor,
                posture=_StrategyPosture.CASTLE_POWER,
                priority=_StrategicPriority.DEFENSE,
                reason_ref=standing_observation_ref,
                reason_label=(
                    f"Standing military demand warrants {floor} {building_name} "
                    "production providers"
                ),
                age_guard=age_guard,
                standing_demand=standing_demand,
                replacement_reason_ref=replacement_reason_ref,
                replacement_expression=(
                    next(
                        item.expression
                        for item in observations
                        if item.identity == replacement_reason_ref
                    )
                    if replacement_reason_ref is not None
                    else None
                ),
            )
        )

    # Imperial spending envelope: admit continuous replacement/sustain demands only
    # while the protected food/wood/gold bank is present. The execution target remains
    # the full standing package; replacement pressure is a world-state floor loss,
    # never a synthetic "combat-loss" counter.
    demands.extend(
        (
            _endgame_training_demand(
                effective=effective,
                identity="imperial-cataphract-sustain",
                owner="endgame-replacement",
                priority=_StrategicPriority.DEFENSE,
                line="cataphract-line",
                minimum=_ENDGAME_CATAPHRACT_TARGET,
                reason_refs=(
                    "strategy-imperial-spend-food",
                    "strategy-imperial-spend-gold",
                    "strategy-imperial-cataphract-replacement",
                ),
                reason_labels=(
                    "Imperial food bank is above the protected spending envelope",
                    "Imperial gold bank is above the protected spending envelope",
                    "Cataphract standing floor has fallen below the replacement threshold",
                ),
                requirement_expressions=(
                    "(and (food-amount >= 2200) (gold-amount >= 2500))",
                ),
            ),
            _endgame_training_demand(
                effective=effective,
                identity="imperial-varangian-sustain",
                owner="endgame-replacement",
                priority=_StrategicPriority.DEFENSE,
                line="varangian-guard-line",
                minimum=_ENDGAME_VARANGIAN_TARGET,
                reason_refs=(
                    "strategy-imperial-spend-food",
                    "strategy-imperial-spend-gold",
                    "strategy-enemy-infantry-pressure",
                    "strategy-imperial-varangian-replacement",
                ),
                reason_labels=(
                    "Imperial food bank is above the protected spending envelope",
                    "Imperial gold bank is above the protected spending envelope",
                    "Enemy infantry pressure keeps the Varangian package strategically active",
                    "Varangian standing floor has fallen below the replacement threshold",
                ),
                requirement_expressions=(
                    "(and (food-amount >= 2200) (gold-amount >= 2500))",
                    "(players-unit-type-count any-enemy militia-line >= 5)",
                ),
                action_symbol="varangian-guard",
                witness_symbol="varangian-guard",
            ),
            _endgame_training_demand(
                effective=effective,
                identity="imperial-ram-sustain",
                owner="endgame-siege-replacement",
                priority=_StrategicPriority.DEFENSE,
                line="ram-line",
                minimum=_ENDGAME_RAM_TARGET,
                reason_refs=(
                    "strategy-imperial-spend-wood",
                    "strategy-imperial-ram-replacement",
                ),
                reason_labels=(
                    "Imperial wood bank is above the protected spending envelope",
                    "Ram standing floor has fallen below the replacement threshold",
                ),
                requirement_expressions=(
                    "(wood-amount >= 2200)",
                    "(building-type-count-total siege-workshop >= 1)",
                ),
                action_symbol="battering-ram-line",
                witness_symbol="battering-ram-line",
            ),
            _endgame_training_demand(
                effective=effective,
                identity="imperial-trebuchet-sustain",
                owner="endgame-siege-replacement",
                priority=_StrategicPriority.DEFENSE,
                line="trebuchet-line",
                minimum=_ENDGAME_TREBUCHET_TARGET,
                reason_refs=(
                    "strategy-imperial-spend-wood",
                    "strategy-imperial-spend-gold",
                    "strategy-enemy-castle",
                    "strategy-imperial-trebuchet-replacement",
                ),
                reason_labels=(
                    "Imperial wood bank is above the protected spending envelope",
                    "Imperial gold bank is above the protected spending envelope",
                    "Enemy fortification creates a valid trebuchet conversion channel",
                    "Trebuchet standing floor has fallen below the replacement threshold",
                ),
                requirement_expressions=(
                    "(and (wood-amount >= 2200) (gold-amount >= 2500))",
                    "(players-building-type-count any-enemy castle >= 1)",
                    "(building-type-count-total siege-workshop >= 1)",
                ),
                action_symbol="trebuchet",
                witness_symbol="trebuchet",
            ),
        )
    )

    # Water continuity starts only after a real dock is observed. This is
    # deliberately narrower than automatic water discovery: the latter still
    # requires a proven environmental predicate and remains OPEN.
    fishing_provider = _provider_for_line(effective, "fishing-ship-line")
    demands.append(
        _StrategicDemandSpec(
            identity="water-fishing-continuity",
            owner="water-economy",
            production_arbitration_group="production",
            posture=_StrategyPosture.BOOM,
            priority=_StrategicPriority.SUPPORT,
            reason=(
                _persistent(
                    "Existing dock establishes an active water-economic opportunity",
                    "strategy-dock-exists",
                ),
            ),
            admissibility=(
                _persistent(
                    "Existing dock is a verified strategic water provider",
                    "strategy-dock-exists",
                ),
            ),
            invalidation=(),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.TRAIN,
                "unit-line",
                "fishing-ship-line",
                fishing_provider,
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "fishing-ship-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(building-type-count-total dock >= 1)",
                    "(can-train-with-escrow fishing-ship)",
                    "(unit-type-count-total fishing-ship < 2)",
                ),
                action="(train fishing-ship)",
                witness="(unit-type-count fishing-ship >= 2)",
                release="(unit-type-count fishing-ship >= 2)",
            ),
        )
    )
    demands.append(
        _StrategicDemandSpec(
            identity="water-transport-capability",
            owner="water-transport",
            production_arbitration_group="production",
            posture=_StrategyPosture.BOOM,
            priority=_StrategicPriority.DEFENSE,
            reason=(
                _persistent(
                    "Islands map requires protected transport capability",
                    "strategy-water-islands",
                ),
            ),
            admissibility=(
                _persistent(
                    "Transport is admissible on a disconnected water map",
                    "strategy-water-islands",
                ),
            ),
            invalidation=(),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.TRAIN,
                "unit-line",
                "transport-ship-line",
                _provider_for_line(effective, "transport-ship-line"),
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "transport-ship-line",
                minimum=1,
            ),
            opportunity_cost=None,
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= dark-age)",
                    "(map-type islands)",
                    "(building-type-count-total dock >= 1)",
                    "(can-train-with-escrow transport-ship)",
                    "(unit-type-count-total transport-ship < 1)",
                ),
                action="(train transport-ship)",
                witness="(unit-type-count transport-ship >= 1)",
                release="(unit-type-count transport-ship >= 1)",
            ),
        )
    )
    demands.append(
        _StrategicDemandSpec(
            identity="water-naval-defense",
            owner="water-naval",
            production_arbitration_group="production",
            posture=_StrategyPosture.BOOM,
            priority=_StrategicPriority.DEFENSE,
            reason=(
                _persistent(
                    "Enemy naval pressure requires a bounded defensive ship floor",
                    "strategy-enemy-naval-pressure",
                ),
            ),
            admissibility=(
                _persistent(
                    "Island water makes defensive naval production strategically admissible",
                    "strategy-water-islands",
                ),
                _persistent(
                    "Enemy naval pressure justifies the defensive floor",
                    "strategy-enemy-naval-pressure",
                ),
            ),
            invalidation=(
                _persistent(
                    "Enemy naval pressure has cleared",
                    "strategy-enemy-naval-pressure-cleared",
                ),
            ),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.TRAIN,
                "unit-line",
                "fire-galley-line",
                _provider_for_line(effective, "fire-galley-line"),
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "fire-galley-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(map-type islands)",
                    "(building-type-count-total dock >= 1)",
                    "(players-unit-type-count any-enemy galley-line >= 2)",
                    "(can-train-with-escrow fire-galley)",
                    "(unit-type-count-total fire-galley < 2)",
                ),
                action="(train fire-galley)",
                witness="(unit-type-count fire-galley >= 2)",
                release="(or (unit-type-count fire-galley >= 2) "
                "(and (players-unit-type-count any-enemy galley-line < 2) "
                "(players-unit-type-count any-enemy fire-galley-line < 2)))",
            ),
        )
    )
    demands.append(
        _StrategicDemandSpec(
            identity="water-naval-control",
            owner="water-naval",
            production_arbitration_group="production",
            posture=_StrategyPosture.CASTLE_POWER,
            priority=_StrategicPriority.SUPPORT,
            reason=(
                _persistent(
                    "Sustained enemy naval pressure requires water control capacity",
                    "strategy-enemy-naval-pressure",
                ),
            ),
            admissibility=(
                _persistent("Water control is admissible on Islands", "strategy-water-islands"),
                _persistent("Enemy naval pressure is active", "strategy-enemy-naval-pressure"),
            ),
            invalidation=(
                _persistent(
                    "Enemy naval pressure has cleared",
                    "strategy-enemy-naval-pressure-cleared",
                ),
            ),
            capability_intent=_CapabilityIntent(
                _CapabilityIntentKind.TRAIN,
                "unit-line",
                "galley-line",
                _provider_for_line(effective, "galley-line"),
            ),
            target=_StrategicTarget(
                _StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "galley-line",
                minimum=3,
            ),
            opportunity_cost=None,
            execution=_ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(map-type islands)",
                    "(building-type-count-total dock >= 1)",
                    "(players-unit-type-count any-enemy galley-line >= 2)",
                    "(can-train-with-escrow galley)",
                    "(unit-type-count-total galley < 3)",
                ),
                action="(train galley)",
                witness="(unit-type-count galley >= 3)",
                release="(or (unit-type-count galley >= 3) "
                "(and (players-unit-type-count any-enemy galley-line < 2) "
                "(players-unit-type-count any-enemy fire-galley-line < 2)))",
            ),
        )
    )

    return tuple(demands)


def default_byzantine_endgame_plan() -> _EndgamePlan:
    return _EndgamePlan(
        identity="byzantine-endgame-v1",
        rules=(
            _EndgamePolicyRule(
                identity="breakthrough",
                mode=_EndgameMode.BREAKTHROUGH,
                win_condition=_EndgameWinCondition.CAPABILITY_COLLAPSE,
                observation_refs=(
                    "strategy-imperial-spend-gold",
                    "strategy-enemy-castle",
                ),
                priority=100,
            ),
            _EndgamePolicyRule(
                identity="attrition",
                mode=_EndgameMode.ATTRITION,
                win_condition=_EndgameWinCondition.ATTRITION,
                observation_refs=("strategy-imperial-spend-gold",),
                priority=90,
            ),
            _EndgamePolicyRule(
                identity="resource-denial",
                mode=_EndgameMode.RESOURCE_DENIAL,
                win_condition=_EndgameWinCondition.RESOURCE_CONTROL,
                observation_refs=(
                    "strategy-imperial-spend-gold",
                    "strategy-enemy-pressure",
                ),
                priority=80,
            ),
        ),
        objective_priority=("siege", "defense", "production", "town-center"),
        push_contract=_EndgamePushContract(
            identity="byzantine-endgame-push-v1",
            attack_group_count=1,
            attack_soldier_percent=100,
            minimum_group_size=6,
            maximum_group_size=40,
            live_witness_ref="strategy-endgame-attack-package-live",
            cleared_witness_ref="strategy-endgame-attack-package-cleared",
            frontier=(
                _EndgameFrontierState.SIEGE,
                _EndgameFrontierState.DEFENSE,
                _EndgameFrontierState.PRODUCTION,
                _EndgameFrontierState.TOWN_CENTER,
            ),
        ),
    )


def community_strategy_sn_modes() -> tuple[_StrategicNumberMode, ...]:
    return (
        _StrategicNumberMode(
            "explore-groups-dark",
            42,
            1,
            minimum_age=Age.DARK,
            maximum_age=Age.DARK,
            priority=10,
        ),
        _StrategicNumberMode(
            "explore-groups-feudal",
            42,
            2,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            priority=10,
        ),
        _StrategicNumberMode(
            "explore-groups-castle",
            42,
            2,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
            priority=10,
        ),
        _StrategicNumberMode(
            "explore-groups-imperial",
            42,
            3,
            minimum_age=Age.IMPERIAL,
            maximum_age=Age.IMPERIAL,
            priority=10,
        ),
        _StrategicNumberMode(
            "total-explorers-dark",
            18,
            2,
            minimum_age=Age.DARK,
            maximum_age=Age.DARK,
            priority=5,
        ),
        _StrategicNumberMode(
            "total-explorers-feudal",
            18,
            3,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            priority=5,
        ),
        _StrategicNumberMode(
            "total-explorers-castle",
            18,
            4,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
            priority=5,
        ),
        _StrategicNumberMode(
            "total-explorers-imperial",
            18,
            4,
            minimum_age=Age.IMPERIAL,
            maximum_age=Age.IMPERIAL,
            priority=5,
        ),
        _StrategicNumberMode(
            "attack-groups-feudal",
            36,
            1,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            postures=(_StrategyPosture.FLUSH, _StrategyPosture.RUSH, _StrategyPosture.BOOM),
            priority=5,
        ),
        _StrategicNumberMode(
            "attack-groups-castle",
            36,
            2,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
            postures=(_StrategyPosture.CASTLE_POWER,),
            priority=5,
        ),
    )


def community_water_execution_plan():
    from .water import WaterExecutionPlan

    return WaterExecutionPlan(
        plan_id="byzantine-water-v1",
        water_posture_state="water-posture",
        transport_phase_state="transport-phase",
        transport_required_observation="strategy-water-islands",
        transport_capable_observation="strategy-own-transport-capable",
        dock_observation="strategy-dock-exists",
        naval_pressure_observation="strategy-enemy-naval-pressure",
        naval_pressure_cleared_observation="strategy-enemy-naval-pressure-cleared",
        warboat_floor_observation="strategy-own-warboat-floor",
    )


def build_byzantine_stock_strategy(
    effective: EffectiveCivData,
    *,
    include_water_continuity: bool = True,
) -> _StrategyProfile:
    """Build the broader stock-style Byzantine strategy from the existing base.

    The existing Castle profile remains the compatibility baseline. This builder
    composes the new community-derived strategic packs on top of that profile.
    """
    from .strategy import (
        _default_byzantine_attack_plan,
        _default_byzantine_duc_plan,
        build_byzantine_castle_strategy,
    )
    from .role_separation import default_byzantine_role_separation_plan

    base = build_byzantine_castle_strategy(effective)
    stock_profile_id = "byzantine-stock-v1"
    endgame_plan = default_byzantine_endgame_plan()
    observations = list(base.observations)
    observed = {item.identity for item in observations}
    for observation in community_strategy_observations(effective):
        if observation.identity not in observed:
            observations.append(observation)

    demands = []
    for base_demand in base.demands:
        if base_demand.identity == "feudal-transition":
            execution = replace(
                base_demand.execution,
                requirements=(
                    "(current-age == dark-age)",
                    "(unit-type-count-total villager >= 21)",
                    "(can-research-with-escrow feudal-age)",
                ),
            )
            base_demand = replace(
                base_demand,
                execution=execution,
            )
        if (
            base_demand.execution is not None
            and base_demand.execution.action.startswith("(train ")
        ):
            base_demand = replace(
                base_demand,
                production_arbitration_group="production",
            )
        demands.append(base_demand)
    existing_demands = {item.identity for item in demands}
    for demand in community_strategy_demands(effective):
        if demand.identity == "water-fishing-continuity" and not include_water_continuity:
            continue
        if demand.identity in existing_demands:
            raise ValueError(f"duplicate community strategy demand '{demand.identity}'")
        demands.append(demand)

    compositions = list(base.military_compositions)
    composition_ids = {item.identity for item in compositions}
    for composition in (
        _StrategicMilitaryComposition(
            identity="castle-standard-package",
            production_demands=("castle-knight-floor", "castle-cataphract-floor"),
            attack_objective="castle-commitment",
        ),
        _StrategicMilitaryComposition(
            identity="castle-defense-package",
            production_demands=(
                "counter-mounted-spears",
                "counter-ranged-skirmishers",
                "counter-castle-cataphracts",
            ),
            attack_objective="byzantine-castle-pressure",
        ),
        _StrategicMilitaryComposition(
            identity="castle-infantry-package",
            production_demands=(
                "castle-varangian-guard-floor",
                "counter-castle-cataphracts",
            ),
            attack_objective="byzantine-castle-pressure",
        ),
    ):
        if composition.identity not in composition_ids:
            compositions.append(composition)

    return replace(
        base,
        profile_id=stock_profile_id,
        demands=tuple(demands),
        observations=tuple(observations),
        military_compositions=tuple(compositions),
        strategic_number_modes=tuple(
            (*base.strategic_number_modes, *community_strategy_sn_modes())
        ),
        attack_plan=_default_byzantine_attack_plan(stock_profile_id),
        duc_plan=_default_byzantine_duc_plan(stock_profile_id),
        water_execution_plan=community_water_execution_plan(),
        map_profile=default_byzantine_map_profiles(),
        opening_selector=default_byzantine_opening_selector(),
        economy_controller=default_byzantine_economy_controller(),
        camp_controller=default_byzantine_camp_controller(),
        role_separation_plan=default_byzantine_role_separation_plan(stock_profile_id),
        endgame_plan=endgame_plan,
        envelope=replace(
            base.envelope,
            maps=("ARABIA", "ARENA", "STANDARD_LAND", "HYBRID", "ISLANDS"),
        ),
    )


__all__ = [
    "build_byzantine_stock_strategy",
    "community_strategy_demands",
    "community_strategy_observations",
    "community_strategy_sn_modes",
    "default_byzantine_endgame_plan",
    "community_water_execution_plan",
]
