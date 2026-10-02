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
from ..ir.economic_control import EconomyMode
from ..ir.game_data import Age, Resource
from ..ir import strategy as _strategy


def _persistent(label: str, observation_ref: str) -> _strategy.StrategicEvidence:
    return _strategy.StrategicEvidence(
        _strategy.StrategicEvidenceKind.PERSISTENT,
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
    posture: _strategy.StrategyPosture,
    priority: _strategy.StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building_name: str,
    minimum_age: Age,
    lower_bound: int | None = None,
    upper_bound: int | None = None,
    invalidate_ref: str | None = None,
    extra_requirements: tuple[str, ...] = (),
    action_name: str | None = None,
) -> _strategy.StrategicDemandSpec:
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
    target_witness = (
        f"(building-type-count {native_action} >= {upper_bound})"
        if upper_bound is not None
        else f"(building-type-count {native_action} > 0)"
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
        target_witness=target_witness,
        invalidate_ref=invalidate_ref,
    )


def _staged_building(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: _strategy.StrategyPosture,
    priority: _strategy.StrategicPriority,
    reason_ref: str,
    reason_label: str,
    building_name: str,
    minimum_age: Age,
    lower_bound: int,
    upper_bound: int,
    extra_requirements: tuple[str, ...] = (),
) -> _strategy.StrategicDemandSpec:
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
        extra_requirements=extra_requirements,
    )


def _staged_training(
    *,
    effective: EffectiveCivData,
    identity: str,
    owner: str,
    posture: _strategy.StrategyPosture,
    priority: _strategy.StrategicPriority,
    reason_ref: str,
    reason_label: str,
    line: str,
    action_symbol: str,
    witness_symbol: str,
    lower_bound: int,
    upper_bound: int,
    age_guard: str,
    extra_requirements: tuple[str, ...] = (),
) -> _strategy.StrategicDemandSpec:
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
    demand: _strategy.StrategicDemandSpec,
    *guards: str,
) -> _strategy.StrategicDemandSpec:
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



def _dark_loom_research(effective: EffectiveCivData) -> _strategy.StrategicDemandSpec:
    tech = effective.tech(22)
    cost = effective.cost_of("tech:22")
    return _strategy.StrategicDemandSpec(
        identity="dark-loom",
        owner="economy",
        posture=_strategy.StrategyPosture.BOOM,
        priority=_strategy.StrategicPriority.SUPPORT,
        reason=(
            _persistent(
                "Secure the Dark Age villager economy before the Feudal transition",
                "current-dark-age",
            ),
        ),
        admissibility=(
            _persistent(
                "Loom remains admissible while the Byzantine bot is in Dark Age",
                "current-dark-age",
            ),
        ),
        invalidation=(),
        capability_intent=_strategy.CapabilityIntent(
            _strategy.CapabilityIntentKind.RESEARCH,
            "technology",
            int(tech.id),
        ),
        target=_strategy.StrategicTarget(
            _strategy.StrategicTargetKind.EXACT,
            "technology",
            int(tech.id),
        ),
        opportunity_cost=_strategy.OpportunityCostPolicy(
            owner="economy",
            protected_floors=(
                _strategy.ProtectedResourceFloor(Resource.GOLD, cost.gold),
            ),
            emergency_override_postures=(
                _strategy.StrategyPosture.FLUSH,
                _strategy.StrategyPosture.RUSH,
            ),
        ),
        execution=_strategy.ExecutionDemandTemplate(
            requirements=(
                "(current-age == dark-age)",
                "(can-research-with-escrow loom)",
            ),
            action="(research loom)",
            witness="(research-completed 22)",
            release="(research-completed 22)",
            escrow_release_resources=(Resource.GOLD,),
        ),
    )


def _castle_age_transition(effective: EffectiveCivData) -> _strategy.StrategicDemandSpec:
    advance = effective.age_advance(Age.CASTLE)
    cost = effective.cost_of_age_advance(Age.CASTLE)
    return _strategy.StrategicDemandSpec(
        identity="castle-age-transition",
        owner="age-transition",
        posture=_strategy.StrategyPosture.BOOM,
        priority=_strategy.StrategicPriority.CORE,
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
        capability_intent=_strategy.CapabilityIntent(
            _strategy.CapabilityIntentKind.AGE_ADVANCE,
            "age-advance",
            "castle-age",
            advance.provider_building,
        ),
        target=_strategy.StrategicTarget(
            _strategy.StrategicTargetKind.EXACT,
            "age-advance",
            "castle-age",
        ),
        opportunity_cost=_strategy.OpportunityCostPolicy(
            owner="age-transition",
            protected_floors=(
                _strategy.ProtectedResourceFloor(Resource.FOOD, cost.food),
                _strategy.ProtectedResourceFloor(Resource.GOLD, cost.gold),
            ),
            emergency_override_postures=(
                _strategy.StrategyPosture.FLUSH,
                _strategy.StrategyPosture.RUSH,
            ),
        ),
        execution=_strategy.ExecutionDemandTemplate(
            requirements=(
                "(current-age == feudal-age)",
                "(unit-type-count-total villager >= 24)",
                "(not (players-unit-type-count any-enemy militia-line >= 5))",
                "(can-research-with-escrow castle-age)",
            ),
            action="(research castle-age)",
            witness="(current-age >= castle-age)",
            release="(current-age >= castle-age)",
            escrow_release_resources=(Resource.FOOD, Resource.GOLD),
        ),
    )


def _bot_demands(effective: EffectiveCivData) -> tuple[_strategy.StrategicDemandSpec, ...]:
    demands: list[_strategy.StrategicDemandSpec] = [_castle_age_transition(effective)]

    # Civilian production is deliberately staged. One permanent "make
    # villagers" demand is easy to write and excellent at starving everything
    # else, which is apparently how humanity discovered economic collapse.
    demands.append(_dark_loom_research(effective))

    villager_stages = (
        ("villagers-dark-22", Age.DARK, 10, 22, "Dark Age villager production", ()),
        (
            "villagers-dark-counter-24",
            Age.DARK,
            22,
            24,
            "Dark Age counter-opening economic growth",
            ("(goal opening-plan 2)",),
        ),
        (
            "villagers-dark-fast-castle-26",
            Age.DARK,
            22,
            26,
            "Dark Age Fast Castle economic growth",
            ("(goal opening-plan 3)",),
        ),
        (
            "villagers-dark-water-24",
            Age.DARK,
            22,
            24,
            "Dark Age water-opening economic growth",
            ("(or (goal opening-plan 4) (goal opening-plan 5))",),
        ),
        ("villagers-feudal-30", Age.FEUDAL, 18, 30, "Feudal economic growth", ()),
        ("villagers-castle-45", Age.CASTLE, 30, 45, "Castle expansion economy", ()),
        ("villagers-imperial-70", Age.IMPERIAL, 45, 70, "Imperial production backbone", ()),
    )
    for identity, age, lower, upper, label, extra_requirements in villager_stages:
        demands.append(
            _staged_training(
                effective=effective,
                identity=identity,
                owner="economy",
                posture=_strategy.StrategyPosture.BOOM,
                priority=_strategy.StrategicPriority.CORE,
                reason_ref=_age_observation(age),
                reason_label=label,
                line="villager-line",
                action_symbol="villager",
                witness_symbol="villager",
                lower_bound=lower,
                upper_bound=upper,
                age_guard=f"(current-age >= {_native_age(age)})",
                extra_requirements=extra_requirements,
            )
        )


    demands.append(
        _aged_building_demand(
            effective=effective,
            identity="feudal-barracks",
            owner="infrastructure",
            posture=_strategy.StrategyPosture.BOOM,
            priority=_strategy.StrategicPriority.CORE,
            reason_ref="current-feudal-age",
            reason_label="Maintain the Barracks provider for Byzantine Feudal counter continuity",
            building_name="barracks",
            minimum_age=Age.FEUDAL,
            lower_bound=0,
            upper_bound=1,
        )
    )

    # The stock strategy owns Castle providers (Stable, Siege Workshop,
    # Monastery, University, etc.). The bot adds only the Feudal ranged
    # provider here because the threat-conditioned Skirmisher package needs it
    # before Castle.

    demands.append(
        _aged_building_demand(
            effective=effective,
            identity="feudal-archery-range",
            owner="infrastructure",
            posture=_strategy.StrategyPosture.FLUSH,
            priority=_strategy.StrategicPriority.DEFENSE,
            reason_ref="enemy-ranged-pressure",
            reason_label="Provide the Feudal ranged-production counter under archer pressure",
            building_name="archery-range",
            minimum_age=Age.FEUDAL,
            action_name="87",
            extra_requirements=(
                "(players-unit-type-count any-enemy archer-line >= 3)",
            ),
        )
    )

    # Houses are metered by current count. This avoids a standing burst of
    # house requests and keeps production alive without a universal scheduler.
    house_villager_thresholds = (
        10, 16, 22, 28, 34, 40, 46, 52, 58, 64, 70, 76,
    )
    for index, villager_threshold in enumerate(house_villager_thresholds):
        demands.append(
            _staged_building(
                effective=effective,
                identity=f"house-stage-{index + 1}",
                owner="housing",
                posture=_strategy.StrategyPosture.BOOM,
                priority=_strategy.StrategicPriority.SUPPORT,
                reason_ref="current-dark-age",
                reason_label=f"Maintain housing headroom, stage {index + 1}",
                building_name="house",
                minimum_age=Age.DARK,
                lower_bound=index,
                upper_bound=index + 1,
                extra_requirements=(
                    f"(unit-type-count villager >= {villager_threshold})",
                ),
            )
        )

    # Stock counter demands already own the Feudal response lifecycle.
    # Castle military floors are already owned by the stock Byzantine
    # strategy. Bot policy only strengthens their executable threat guards.
    return tuple(demands)



def _feudal_economy_controller(controller):
    policies = tuple(
        replace(
            policy,
            allocation=replace(
                policy.allocation,
                food=42,
                wood=40,
                gold=18,
                builders=8,
            ),
        )
        if policy.mode is EconomyMode.COUNTER_FEUDAL
        else policy
        for policy in controller.policies
    )
    return replace(controller, policies=policies)

def build_byzantine_bot_profile(effective: EffectiveCivData):
    """Build the deployable Byzantine Core v1 profile.

    The stock strategy remains the base policy package. This function adds
    explicit bot-level production and opening continuity without changing the
    compiler's generic semantics.
    """
    base = _strategy.build_byzantine_strategy(effective)

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

    wheelbarrow_id = int(base.demand("research-wheelbarrow").target.entity_id)
    research_guard_by_identity = {
        "research-wheelbarrow": (
            "(unit-type-count-total villager >= 20)",
        ),
        "research-double-bit-axe": (
            f"(research-completed {wheelbarrow_id})",
        ),
        "research-horse-collar": (
            f"(research-completed {wheelbarrow_id})",
        ),
        "research-fletching": (
            "(building-type-count-total 87 >= 1)",
            "(players-unit-type-count any-enemy archer-line >= 3)",
        ),
    }
    guarded_demands = tuple(
        _with_execution_guards(
            demand,
            *guard_by_identity.get(demand.identity, ()),
            *research_guard_by_identity.get(demand.identity, ()),
            *(
                (
                    "(current-age == feudal-age)",
                    "(building-type-count-total barracks >= 1)",
                )
                if demand.identity == "counter-mounted-spears"
                else ()
            ),
            *(
                (
                    "(current-age == feudal-age)",
                    "(building-type-count-total 87 >= 1)",
                )
                if demand.identity == "counter-ranged-skirmishers"
                else ()
            ),
        )
        if (
            demand.identity in guard_by_identity
            or demand.identity in research_guard_by_identity
            or demand.identity in {"counter-mounted-spears", "counter-ranged-skirmishers"}
        )
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
        economy_controller=_feudal_economy_controller(base.economy_controller),
    )


__all__ = ("build_byzantine_bot_profile",)
