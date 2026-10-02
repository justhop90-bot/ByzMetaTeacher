"""Community-derived Byzantine strategy synthesis packs.

This module contains strategy policy only. It reuses the existing StrategyProfile,
StrategicDemandSpec, StrategicNumberMode, and native lifecycle machinery. It does
not introduce a scheduler or a second .per language.
"""
from __future__ import annotations

from dataclasses import replace

from .civ_profile import EffectiveCivData
from .game_data import Age, BuildingId, Resource, TechId, UnitLineId
from .strategy import (
    CapabilityIntent,
    CapabilityIntentKind,
    ExecutionDemandTemplate,
    OpportunityCostPolicy,
    ProtectedResourceFloor,
    StrategicDemandSpec,
    StrategicEvidence,
    StrategicEvidenceKind,
    StrategicPriority,
    StrategicTarget,
    StrategicTargetKind,
    StrategicNumberMode,
    StrategyPosture,
    StrategyProfile,
    StrategicObservationSpec,
    CapabilityRecoveryContract,
    StrategicMilitaryComposition,
)
from .versioning import EvidenceRef


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
) -> StrategicObservationSpec:
    return StrategicObservationSpec(
        identity=identity,
        expression=expression,
        provenance=provenance,
    )


def _persistent(
    label: str,
    observation_ref: str,
) -> StrategicEvidence:
    return StrategicEvidence(
        StrategicEvidenceKind.PERSISTENT,
        None,
        label,
        observation_ref=observation_ref,
    )


def _execution(
    label: str,
    expression: str,
) -> StrategicEvidence:
    return StrategicEvidence(
        StrategicEvidenceKind.EXECUTION,
        expression,
        label,
    )


def _build_demand(
    *,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building,
    requirements: tuple[str, ...],
    action_name: str | None = None,
    target_witness: str | None = None,
    release: str | None = None,
    opportunity_cost: OpportunityCostPolicy | None = None,
    invalidate_ref: str | None = None,
) -> StrategicDemandSpec:
    action_name = action_name or _slug(building.name)
    target_witness = target_witness or f"(building-type-count {action_name} > 0)"
    release = release or target_witness
    return StrategicDemandSpec(
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
        capability_intent=CapabilityIntent(
            CapabilityIntentKind.BUILD,
            "building",
            int(building.id),
        ),
        target=StrategicTarget(
            StrategicTargetKind.EXACT,
            "building",
            int(building.id),
        ),
        opportunity_cost=opportunity_cost,
        execution=ExecutionDemandTemplate(
            requirements=requirements,
            action=f"(build {action_name})",
            witness=target_witness,
            release=release,
        ),
        recovery=CapabilityRecoveryContract(),
    )


def _research_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    age_guard: str,
    age_observation_ref: str,
    tech_name: str,
    reason_label: str,
    resources: tuple[Resource, ...],
    minimum_floors: tuple[tuple[Resource, int], ...] = (),
) -> StrategicDemandSpec:
    tech = _tech(effective, tech_name)
    token = _slug(tech.name)
    complete_ref = f"{identity}-complete"
    floors = tuple(ProtectedResourceFloor(resource, amount) for resource, amount in minimum_floors)
    policy = None
    if floors:
        policy = OpportunityCostPolicy(
            owner=owner,
            protected_floors=floors,
            emergency_override_postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH),
        )
    demand = StrategicDemandSpec(
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
        capability_intent=CapabilityIntent(
            CapabilityIntentKind.RESEARCH,
            "technology",
            int(tech.id),
        ),
        target=StrategicTarget(
            StrategicTargetKind.EXACT,
            "technology",
            int(tech.id),
        ),
        opportunity_cost=policy,
        execution=ExecutionDemandTemplate(
            requirements=(
                age_guard,
                f"(can-research-with-escrow {token})",
                f"(not (research-completed {int(tech.id)}))",
            ),
            action=f"(research {token})",
            witness=f"(research-completed {int(tech.id)})",
            release=f"(research-completed {int(tech.id)})",
            escrow_release_resources=resources,
        ),
    )
    return demand


def _training_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    reason_ref: str,
    reason_label: str,
    line: str,
    minimum: int,
    age_guard: str,
) -> StrategicDemandSpec:
    provider = _provider_for_line(effective, line)
    return StrategicDemandSpec(
        identity=identity,
        owner=owner,
        production_arbitration_group=owner,
        posture=posture,
        priority=priority,
        reason=(_persistent(reason_label, reason_ref),),
        admissibility=(
            _persistent(f"{identity}:age-admission", reason_ref),
        ),
        invalidation=(),
        capability_intent=CapabilityIntent(
            CapabilityIntentKind.TRAIN,
            "unit-line",
            line,
            provider,
        ),
        target=StrategicTarget(
            StrategicTargetKind.CURRENT_QUEUED,
            "unit-line",
            line,
            minimum=minimum,
        ),
        opportunity_cost=None,
        execution=ExecutionDemandTemplate(
            requirements=(
                age_guard,
                f"(can-train-with-escrow {line})",
                f"(unit-type-count-total {line} < {minimum})",
            ),
            action=f"(train {line})",
            witness=f"(unit-type-count {line} >= {minimum})",
            release=f"(unit-type-count {line} >= {minimum})",
        ),
    )


_RESEARCH_PACK = (
    ("research-wheelbarrow", "economy", "feudal-age", "wheelbarrow", StrategicPriority.SUPPORT, (Resource.FOOD,)),
    ("research-double-bit-axe", "economy", "feudal-age", "double-bit-axe", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-horse-collar", "economy", "feudal-age", "horse-collar", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-hand-cart", "economy", "castle-age", "hand-cart", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.WOOD)),
    ("research-bow-saw", "economy", "castle-age", "bow-saw", StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-two-man-saw", "economy", "castle-age", "two-man-saw", StrategicPriority.SUPPORT, (Resource.WOOD, Resource.GOLD)),
    ("research-bodkin-arrow", "military", "feudal-age", "bodkin-arrow", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-bloodlines", "military", "feudal-age", "bloodlines", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-conscription", "military", "imperial-age", "conscription", StrategicPriority.SUPPORT, (Resource.FOOD, Resource.GOLD)),
    ("research-chemistry", "military", "imperial-age", "chemistry", StrategicPriority.SUPPORT, (Resource.GOLD,)),
)


def community_strategy_observations(
    effective: EffectiveCivData,
) -> tuple[StrategicObservationSpec, ...]:
    town_center = _building(effective, "town-center")
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
            "strategy-enemy-pressure",
            "(or (players-unit-type-count any-enemy knight >= 3) "
            "(players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5))",
            tuple(
                dict.fromkeys(
                    (*effective.unit_line("knight-line").provenance,
                     *effective.unit_line("archer-line").provenance,
                     *effective.unit_line("militia-line").provenance)
                )
            ),
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

    return tuple(observations)


def community_strategy_demands(
    effective: EffectiveCivData,
) -> tuple[StrategicDemandSpec, ...]:
    town_center = _building(effective, "town-center")
    outpost = _building(effective, "outpost")
    monastery = _building(effective, "monastery")
    siege_workshop = _building(effective, "siege-workshop")
    stable = _building(effective, "stable")
    archery_range = _building(effective, "archery-range")
    university = _building(effective, "university")

    demands: list[StrategicDemandSpec] = []

    imperial = effective.age_advance(Age.IMPERIAL)
    imperial_cost = effective.cost_of_age_advance(Age.IMPERIAL)
    demands.append(
        StrategicDemandSpec(
            identity="imperial-conversion",
            owner="age-transition",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.CORE,
            reason=(
                _persistent("Imperial remains the next durable strategic conversion", "strategy-castle-age"),
            ),
            admissibility=(
                _persistent("Imperial remains admissible in Castle Age", "strategy-castle-age"),
            ),
            invalidation=(
                _persistent("Imperial conversion complete", "strategy-imperial-age"),
            ),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.AGE_ADVANCE,
                "age-advance",
                "imperial-age",
                imperial.provider_building,
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "age-advance",
                "imperial-age",
            ),
            opportunity_cost=OpportunityCostPolicy(
                owner="age-transition",
                protected_floors=(
                    ProtectedResourceFloor(Resource.FOOD, imperial_cost.food),
                    ProtectedResourceFloor(Resource.GOLD, imperial_cost.gold),
                ),
                emergency_override_postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH),
            ),
            execution=ExecutionDemandTemplate(
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
    tc_policy = OpportunityCostPolicy(
        owner="castle-economy",
        protected_floors=(
            ProtectedResourceFloor(Resource.WOOD, effective.cost_of(f"building:{int(town_center.id)}").wood),
        ),
        emergency_override_postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH),
    )
    demands.append(
        StrategicDemandSpec(
            identity="castle-second-town-center",
            owner="castle-economy",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.CORE,
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
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.BUILD,
                "building",
                int(town_center.id),
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "building",
                int(town_center.id),
            ),
            opportunity_cost=tc_policy,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(building-type-count-total town-center < 2)",
                    "(can-build town-center)",
                ),
                action="(build town-center)",
                witness="(building-type-count-total town-center >= 2)",
                release="(building-type-count-total town-center >= 2)",
            ),
        )
    )

    demands.extend(
        (
            _build_demand(
                identity="castle-stable-capability",
                owner="production",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.SUPPORT,
                reason_ref="strategy-castle-age",
                reason_label="Castle cavalry production requires a stable provider",
                building=stable,
                requirements=(" (can-build stable)".strip(),),
            ),
            _build_demand(
                identity="castle-archery-capability",
                owner="production",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.SUPPORT,
                reason_ref="strategy-enemy-pressure",
                reason_label="Ranged pressure creates a real ranged-production capability demand",
                building=archery_range,
                requirements=(" (can-build archery-range)".strip(),),
                invalidate_ref="strategy-imperial-age",
            ),
            _build_demand(
                identity="castle-siege-capability",
                owner="production",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-siege",
                reason_label="Enemy siege creates an explicit siege-capability demand",
                building=siege_workshop,
                requirements=(" (can-build siege-workshop)".strip(),),
            ),
            _build_demand(
                identity="castle-monastery-capability",
                owner="support",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.OPTIONAL,
                reason_ref="strategy-castle-age",
                reason_label="Castle support includes a Monk/relic capability",
                building=monastery,
                requirements=(" (can-build monastery)".strip(),),
            ),
            _build_demand(
                identity="imperial-university-capability",
                owner="research",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.SUPPORT,
                reason_ref="strategy-castle-age",
                reason_label="Imperial conversion requires a verified university provider",
                building=university,
                requirements=(" (current-age >= castle-age)", "(can-build university)"),
            ),
            _build_demand(
                identity="adaptive-outpost",
                owner="defense",
                posture=StrategyPosture.FLUSH,
                priority=StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-pressure",
                reason_label="Sustained enemy pressure justifies one defensive observation point",
                building=outpost,
                requirements=(" (can-build outpost)".strip(),),
            ),
        )
    )

    for identity, owner, age, tech_name, priority, resources in _RESEARCH_PACK:
        demand = _research_demand(
            effective=effective,
            identity=identity,
            owner=owner,
            posture=(
                StrategyPosture.CASTLE_POWER
                if age in {"castle-age", "imperial-age"}
                else StrategyPosture.BOOM
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
        )
        demands.append(demand)

    # Standing military floors.
    demands.extend(
        (
            _training_demand(
                effective=effective,
                identity="castle-knight-floor",
                owner="military",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.CORE,
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
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.CORE,
                reason_ref="strategy-castle-age",
                reason_label="Maintain the Byzantine premium Castle power floor",
                line="cataphract-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="castle-siege-floor",
                owner="military",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-siege",
                reason_label="Maintain a mobile anti-siege response when enemy siege is observed",
                line="knight-line",
                minimum=3,
                age_guard="(current-age >= castle-age)",
            ),
            _training_demand(
                effective=effective,
                identity="castle-monk-floor",
                owner="support",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.OPTIONAL,
                reason_ref="strategy-monastery-capability",
                reason_label="Use a bounded Monk support floor once the monastery capability exists",
                line="monk-line",
                minimum=2,
                age_guard="(current-age >= castle-age)",
            ),
        )
    )

    # Water continuity starts only after a real dock is observed. This is
    # deliberately narrower than automatic water discovery: the latter still
    # requires a proven environmental predicate and remains OPEN.
    fishing = _line(effective, "fishing-ship-line")
    fishing_provider = _provider_for_line(effective, "fishing-ship-line")
    demands.append(
        StrategicDemandSpec(
            identity="water-fishing-continuity",
            owner="water-economy",
            posture=StrategyPosture.BOOM,
            priority=StrategicPriority.SUPPORT,
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
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "fishing-ship-line",
                fishing_provider,
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "fishing-ship-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(building-type-count-total dock >= 1)",
                    "(can-train-with-escrow fishing-ship-line)",
                    "(unit-type-count-total fishing-ship-line < 2)",
                ),
                action="(train fishing-ship-line)",
                witness="(unit-type-count fishing-ship-line >= 2)",
                release="(unit-type-count fishing-ship-line >= 2)",
            ),
        )
    )

    return tuple(demands)


def community_strategy_sn_modes() -> tuple[StrategicNumberMode, ...]:
    return (
        StrategicNumberMode(
            "explore-groups-dark",
            42,
            1,
            minimum_age=Age.DARK,
            maximum_age=Age.DARK,
            priority=10,
        ),
        StrategicNumberMode(
            "explore-groups-feudal",
            42,
            2,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            priority=10,
        ),
        StrategicNumberMode(
            "explore-groups-castle",
            42,
            2,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
            priority=10,
        ),
        StrategicNumberMode(
            "explore-groups-imperial",
            42,
            3,
            minimum_age=Age.IMPERIAL,
            maximum_age=Age.IMPERIAL,
            priority=10,
        ),
        StrategicNumberMode(
            "total-explorers-dark",
            18,
            2,
            minimum_age=Age.DARK,
            maximum_age=Age.DARK,
            priority=5,
        ),
        StrategicNumberMode(
            "total-explorers-feudal",
            18,
            3,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            priority=5,
        ),
        StrategicNumberMode(
            "total-explorers-castle",
            18,
            4,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
            priority=5,
        ),
        StrategicNumberMode(
            "total-explorers-imperial",
            18,
            4,
            minimum_age=Age.IMPERIAL,
            maximum_age=Age.IMPERIAL,
            priority=5,
        ),
        StrategicNumberMode(
            "attack-groups-feudal",
            36,
            1,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
            postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH, StrategyPosture.BOOM),
            priority=5,
        ),
        StrategicNumberMode(
            "attack-groups-castle",
            36,
            2,
            minimum_age=Age.CASTLE,
            maximum_age=Age.IMPERIAL,
            postures=(StrategyPosture.CASTLE_POWER,),
            priority=5,
        ),
    )


def build_byzantine_stock_strategy(
    effective: EffectiveCivData,
    *,
    include_water_continuity: bool = True,
) -> StrategyProfile:
    """Build the broader stock-style Byzantine strategy from the existing base.

    The existing Castle profile remains the compatibility baseline. This builder
    composes the new community-derived strategic packs on top of that profile.
    """
    from .strategy import build_byzantine_castle_strategy

    base = build_byzantine_castle_strategy(effective)
    observations = list(base.observations)
    observed = {item.identity for item in observations}
    for observation in community_strategy_observations(effective):
        if observation.identity not in observed:
            observations.append(observation)

    demands = list(base.demands)
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
        StrategicMilitaryComposition(
            identity="castle-standard-package",
            production_demands=("castle-knight-floor", "castle-cataphract-floor"),
            attack_objective="byzantine-castle-pressure",
        ),
        StrategicMilitaryComposition(
            identity="castle-defense-package",
            production_demands=(
                "counter-mounted-spears",
                "counter-ranged-skirmishers",
                "counter-castle-cataphracts",
            ),
            attack_objective="byzantine-castle-pressure",
        ),
    ):
        if composition.identity not in composition_ids:
            compositions.append(composition)

    return replace(
        base,
        profile_id="byzantine-stock-v1",
        demands=tuple(demands),
        observations=tuple(observations),
        military_compositions=tuple(compositions),
        strategic_number_modes=tuple(
            (*base.strategic_number_modes, *community_strategy_sn_modes())
        ),
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
]
