"""Professional Byzantine bot policy built on the existing compiler IR.

This module is bot policy, not compiler infrastructure. It composes the
community-derived stock Byzantine profile with explicit Dark -> Feudal ->
Castle production, infrastructure, age-up, economy, and conditional military
behavior needed by an actually deployable 1v1 land bot.
"""

from __future__ import annotations

from dataclasses import replace

from ..ir.civ_profile import EffectiveCivData
from ..ir.community_strategy_packs import _build_demand, _training_demand
from ..ir.game_data import Age, Resource
from ..ir.strategy import (
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
    StrategyPosture,
    build_byzantine_strategy,
)


def _persistent(label: str, observation_ref: str) -> StrategicEvidence:
    return StrategicEvidence(
        StrategicEvidenceKind.PERSISTENT,
        None,
        label,
        observation_ref=observation_ref,
    )


def _native_age(age: Age) -> str:
    return {
        Age.DARK: "dark-age",
        Age.FEUDAL: "feudal-age",
        Age.CASTLE: "castle-age",
        Age.IMPERIAL: "imperial-age",
    }[age]


def _age_observation(age: Age) -> str:
    return {
        Age.DARK: "current-dark-age",
        Age.FEUDAL: "current-feudal-age",
        Age.CASTLE: "strategy-castle-age",
        Age.IMPERIAL: "strategy-imperial-age",
    }[age]


def _aged_building_demand(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building_name: str,
    minimum_age: Age,
    lower_bound: int | None = None,
    upper_bound: int | None = None,
    invalidate_ref: str | None = None,
    extra_requirements: tuple[str, ...] = (),
    action_name: str | None = None,
) -> StrategicDemandSpec:
    building = next(
        item
        for item in effective.buildings
        if item.name.lower().replace(" ", "-") == building_name.lower().replace(" ", "-")
    )
    native_action = action_name or building_name
    guard_parts = [f"(current-age >= {_native_age(minimum_age)})"]
    if lower_bound is not None:
        guard_parts.append(
            f"(building-type-count-total {native_action} >= {lower_bound})"
        )
    if upper_bound is not None:
        guard_parts.append(
            f"(building-type-count-total {native_action} < {upper_bound})"
        )
    requirements = tuple(
        [*guard_parts, f"(can-build {native_action})", *extra_requirements]
    )
    return _build_demand(
        identity=identity,
        owner=owner,
        posture=posture,
        priority=priority,
        reason_ref=reason_ref,
        reason_label=reason_label,
        building=building,
        requirements=requirements,
        action_name=native_action,
        target_witness=f"(building-type-count {native_action} > 0)",
        invalidate_ref=invalidate_ref,
    )


def _staged_building(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building_name: str,
    minimum_age: Age,
    lower_bound: int,
    upper_bound: int,
) -> StrategicDemandSpec:
    return _aged_building_demand(
        effective=effective,
        identity=identity,
        owner=owner,
        posture=posture,
        priority=priority,
        reason_ref=reason_ref,
        reason_label=reason_label,
        building_name=building_name,
        minimum_age=minimum_age,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )


def _staged_training(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: StrategyPosture,
    priority: StrategicPriority,
    reason_ref: str,
    reason_label: str,
    line: str,
    action_symbol: str,
    witness_symbol: str,
    lower_bound: int,
    upper_bound: int,
    age_guard: str,
    extra_requirements: tuple[str, ...] = (),
) -> StrategicDemandSpec:
    base = _training_demand(
        effective=effective,
        identity=identity,
        owner=owner,
        posture=posture,
        priority=priority,
        reason_ref=reason_ref,
        reason_label=reason_label,
        line=line,
        minimum=upper_bound,
        age_guard=age_guard,
        action_symbol=action_symbol,
        witness_symbol=witness_symbol,
    )
    execution = replace(
        base.execution,
        requirements=(
            age_guard,
            f"(can-train-with-escrow {action_symbol})",
            f"(unit-type-count-total {action_symbol} >= {lower_bound})",
            f"(unit-type-count-total {action_symbol} < {upper_bound})",
            *extra_requirements,
        ),
    )
    return replace(base, execution=execution)



def _with_execution_guards(
    demand: StrategicDemandSpec,
    *guards: str,
) -> StrategicDemandSpec:
    """Add explicit native threat/world-state guards to a stock demand.

    Community evidence explains why a policy exists; these guards make the
    deployed .per executable conditionally. This keeps bot policy honest when
    the stock strategic reason is intentionally broad.
    """
    execution = replace(
        demand.execution,
        requirements=(*demand.execution.requirements, *guards),
    )
    return replace(demand, execution=execution)


def _castle_age_transition(effective: EffectiveCivData) -> StrategicDemandSpec:
    advance = effective.age_advance(Age.CASTLE)
    cost = effective.cost_of_age_advance(Age.CASTLE)
    return StrategicDemandSpec(
        identity="castle-age-transition",
        owner="age-transition",
        posture=StrategyPosture.BOOM,
        priority=StrategicPriority.CORE,
        reason=(
            _persistent(
                "Reach Castle Age as the core Byzantine land conversion point",
                "current-feudal-age",
            ),
        ),
        admissibility=(
            _persistent(
                "Castle Age remains the next admissible age from Feudal",
                "current-feudal-age",
            ),
        ),
        invalidation=(),
        capability_intent=CapabilityIntent(
            CapabilityIntentKind.AGE_ADVANCE,
            "age-advance",
            "castle-age",
            advance.provider_building,
        ),
        target=StrategicTarget(
            StrategicTargetKind.EXACT,
            "age-advance",
            "castle-age",
        ),
        opportunity_cost=OpportunityCostPolicy(
            owner="age-transition",
            protected_floors=(
                ProtectedResourceFloor(Resource.FOOD, cost.food),
                ProtectedResourceFloor(Resource.GOLD, cost.gold),
            ),
            emergency_override_postures=(
                StrategyPosture.FLUSH,
                StrategyPosture.RUSH,
            ),
        ),
        execution=ExecutionDemandTemplate(
            requirements=(
                "(current-age == feudal-age)",
                "(can-research-with-escrow castle-age)",
            ),
            action="(research castle-age)",
            witness="(current-age >= castle-age)",
            release="(current-age >= castle-age)",
            escrow_release_resources=(Resource.FOOD, Resource.GOLD),
        ),
    )


def _bot_demands(effective: EffectiveCivData) -> tuple[StrategicDemandSpec, ...]:
    demands: list[StrategicDemandSpec] = [_castle_age_transition(effective)]

    # Civilian production is deliberately staged. One permanent "make
    # villagers" demand is easy to write and excellent at starving everything
    # else, which is apparently how humanity discovered economic collapse.
    villager_stages = (
        ("villagers-dark-18", Age.DARK, 10, 18, "Dark Age villager production"),
        ("villagers-feudal-30", Age.FEUDAL, 18, 30, "Feudal economic growth"),
        ("villagers-castle-45", Age.CASTLE, 30, 45, "Castle expansion economy"),
        ("villagers-imperial-70", Age.IMPERIAL, 45, 70, "Imperial production backbone"),
    )
    for identity, age, lower, upper, label in villager_stages:
        demands.append(
            _staged_training(
                effective=effective,
                identity=identity,
                owner="economy",
                posture=StrategyPosture.BOOM,
                priority=StrategicPriority.CORE,
                reason_ref=_age_observation(age),
                reason_label=label,
                line="villager-line",
                action_symbol="villager",
                witness_symbol="villager",
                lower_bound=lower,
                upper_bound=upper,
                age_guard=f"(current-age >= {_native_age(age)})",
            )
        )

    # Minimal land infrastructure. Placement remains delegated to the native
    # build action and its existing lifecycle witnesses.
    for spec in (
        (
            "dark-lumber-camp",
            "Dark Age lumber camp",
            "lumber-camp",
            "562",
            Age.DARK,
            "current-dark-age",
        ),
        (
            "dark-mining-camp",
            "Dark Age mining camp",
            "mining-camp",
            "584",
            Age.DARK,
            "current-dark-age",
        ),
        (
            "dark-mill",
            "Dark Age mill",
            "mill",
            "68",
            Age.DARK,
            "current-dark-age",
        ),
        (
            "feudal-barracks",
            "Feudal barracks for stable military production",
            "barracks",
            Age.FEUDAL,
            "current-feudal-age",
        ),
        (
            "feudal-stable",
            "Feudal stable so Castle cavalry conversion has a ready provider",
            "stable",
            Age.FEUDAL,
            "current-feudal-age",
        ),
    ):
        identity, reason_label, building_name, native_action, age, reason_ref = spec
        demands.append(
            _aged_building_demand(
                effective=effective,
                identity=identity,
                owner="infrastructure",
                posture=StrategyPosture.BOOM,
                priority=StrategicPriority.CORE,
                reason_ref=reason_ref,
                reason_label=reason_label,
                building_name=building_name,
                minimum_age=age,
                action_name=native_action,
            )
        )

    # Houses are metered by current count. This avoids a standing burst of
    # house requests and keeps production alive without a universal scheduler.
    for index in range(14):
        demands.append(
            _staged_building(
                effective=effective,
                identity=f"house-stage-{index + 1}",
                owner="housing",
                posture=StrategyPosture.BOOM,
                priority=StrategicPriority.SUPPORT,
                reason_ref="current-dark-age",
                reason_label=f"Maintain housing headroom, stage {index + 1}",
                building_name="house",
                minimum_age=Age.DARK,
                lower_bound=index,
                upper_bound=index + 1,
            )
        )

    # Feudal response package guards are attached to the stock counter
    # demands below. Keeping one demand per counter avoids double production.
    demands.append(
        _aged_building_demand(
            effective=effective,
            identity="feudal-archery-range",
            owner="infrastructure",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.DEFENSE,
            reason_ref="enemy-ranged-pressure",
            reason_label="Provide the Feudal ranged-production counter under archer pressure",
            building_name="archery-range",
            minimum_age=Age.FEUDAL,
            extra_requirements=(
                "(players-unit-type-count any-enemy archer-line >= 3)",
            ),
        )
    )

    # Castle power is staged instead of asking for six of everything at once.
    demands.extend(
        (
            _staged_training(
                effective=effective,
                identity="castle-cataphracts-2-4",
                owner="military",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.CORE,
                reason_ref="strategy-castle-age",
                reason_label="Establish the first Byzantine Cataphract core",
                line="cataphract-line",
                action_symbol="cataphract",
                witness_symbol="cataphract",
                lower_bound=2,
                upper_bound=4,
                age_guard="(current-age >= castle-age)",
            ),
            _staged_training(
                effective=effective,
                identity="castle-knights-3-5",
                owner="military",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.SUPPORT,
                reason_ref="strategy-castle-age",
                reason_label="Maintain mobile Castle cavalry for pressure and reaction",
                line="knight-line",
                action_symbol="knight-line",
                witness_symbol="knight-line",
                lower_bound=3,
                upper_bound=5,
                age_guard="(current-age >= castle-age)",
            ),
            _staged_training(
                effective=effective,
                identity="castle-varangians-2-4",
                owner="castle-varangian",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-infantry-pressure",
                reason_label="Commit Varangian Guards only against sustained infantry pressure",
                line="varangian-guard-line",
                action_symbol="varangian-guard",
                witness_symbol="varangian-guard",
                lower_bound=2,
                upper_bound=4,
                age_guard="(current-age >= castle-age)",
                extra_requirements=(
                    "(players-unit-type-count any-enemy militia-line >= 5)",
                ),
            ),
            _staged_training(
                effective=effective,
                identity="castle-mangonels-1-2",
                owner="siege",
                posture=StrategyPosture.CASTLE_POWER,
                priority=StrategicPriority.DEFENSE,
                reason_ref="strategy-enemy-siege",
                reason_label="Maintain limited Castle siege under sustained enemy siege pressure",
                line="mangonel-line",
                action_symbol="mangonel-line",
                witness_symbol="mangonel-line",
                lower_bound=1,
                upper_bound=2,
                age_guard="(current-age >= castle-age)",
                extra_requirements=(
                    "(players-unit-type-count any-enemy mangonel-line >= 2)",
                ),
            ),
        )
    )

    return tuple(demands)


def build_byzantine_bot_profile(effective: EffectiveCivData):
    """Build the deployable Byzantine Core v1 profile.

    The stock strategy remains the base policy package. This function adds
    explicit bot-level production and opening continuity without changing the
    compiler's generic semantics.
    """
    base = build_byzantine_strategy(effective)

    guard_by_identity = {
        "counter-mounted-spears": (
            "(players-unit-type-count any-enemy scout-cavalry-line >= 3)",
        ),
        "counter-ranged-skirmishers": (
            "(players-unit-type-count any-enemy archer-line >= 3)",
        ),
        "counter-castle-camels": (
            "(players-unit-type-count any-enemy knight >= 3)",
        ),
        "counter-castle-cataphracts": (
            "(players-unit-type-count any-enemy militia-line >= 5)",
        ),
        "counter-castle-siege-response": (
            "(players-unit-type-count any-enemy mangonel-line >= 2)",
        ),
        "castle-varangian-guard-floor": (
            "(players-unit-type-count any-enemy militia-line >= 5)",
        ),
        "castle-siege-floor": (
            "(players-unit-type-count any-enemy mangonel-line >= 2)",
        ),
        "castle-mangonel-floor": (
            "(players-unit-type-count any-enemy archer-line >= 4)",
        ),
        "imperial-bombard-floor": (
            "(players-building-type-count any-enemy castle >= 1)",
        ),
        "castle-archery-capability": (
            "(players-unit-type-count any-enemy archer-line >= 4)",
        ),
        "castle-siege-capability": (
            "(players-unit-type-count any-enemy mangonel-line >= 2)",
        ),
        "adaptive-outpost": (
            "(or (players-unit-type-count any-enemy knight >= 3) "
            "(or (players-unit-type-count any-enemy archer-line >= 4) "
            "(players-unit-type-count any-enemy militia-line >= 5)))",
        ),
    }

    guarded_demands = tuple(
        _with_execution_guards(demand, *guard_by_identity[demand.identity])
        if demand.identity in guard_by_identity
        else demand
        for demand in base.demands
    )
    base = replace(base, demands=guarded_demands)

    existing = {item.identity for item in base.demands}
    additions = tuple(
        demand for demand in _bot_demands(effective)
        if demand.identity not in existing
    )
    return replace(
        base,
        demands=(*base.demands, *additions),
        profile_id=base.profile_id,
    )


__all__ = ("build_byzantine_bot_profile",)
