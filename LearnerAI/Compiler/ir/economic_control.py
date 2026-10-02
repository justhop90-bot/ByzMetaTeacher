"""Deterministic economic posture controller for the Byzantine compiler."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..ast import SourceLocation
from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
from ..semantic.analyzer import parse_expression
from .model import GoalRole, SemanticId, StorageRequestId
from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
from .strategic_number import StrategicNumberOrigin


class EconomyMode(IntEnum):
    BASE = 1
    COUNTER_FEUDAL = 2
    FAST_CASTLE = 3
    WATER_ECONOMY = 4
    WATER_CONTROL = 5
    CASTLE_CONVERSION = 6
    IMPERIAL_CONVERSION = 7


@dataclass(frozen=True)
class EconomyAllocation:
    food: int
    wood: int
    gold: int
    builders: int

    def __post_init__(self) -> None:
        for name, value in (
            ("food", self.food),
            ("wood", self.wood),
            ("gold", self.gold),
            ("builders", self.builders),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"economy allocation {name} must be an integer")
            if not 0 <= value <= 100:
                raise ValueError(f"economy allocation {name} must be in 0..100")


@dataclass(frozen=True)
class EconomyModePolicy:
    mode: EconomyMode
    allocation: EconomyAllocation

    def __post_init__(self) -> None:
        if self.allocation.food + self.allocation.wood + self.allocation.gold > 100:
            raise ValueError("economy allocation percentages must sum to at most 100")


@dataclass(frozen=True)
class EconomyControllerPlan:
    controller_id: str
    state_name: str = "economy-posture"
    opening_state: str = "opening-plan"
    pressure_observation: str = "strategy-enemy-pressure"
    policies: tuple[EconomyModePolicy, ...] = ()

    def __post_init__(self) -> None:
        if not self.controller_id.strip():
            raise ValueError("economy controller id must not be empty")
        modes = tuple(item.mode for item in self.policies)
        if len(modes) != len(set(modes)):
            raise ValueError("economy controller modes must be unique")


def default_byzantine_economy_controller() -> EconomyControllerPlan:
    return EconomyControllerPlan(
        controller_id="byzantine-economy-v1",
        policies=(
            EconomyModePolicy(EconomyMode.BASE, EconomyAllocation(50, 30, 20, 5)),
            EconomyModePolicy(EconomyMode.COUNTER_FEUDAL, EconomyAllocation(42, 38, 20, 8)),
            EconomyModePolicy(EconomyMode.FAST_CASTLE, EconomyAllocation(55, 15, 30, 3)),
            EconomyModePolicy(EconomyMode.WATER_ECONOMY, EconomyAllocation(40, 40, 20, 5)),
            EconomyModePolicy(EconomyMode.WATER_CONTROL, EconomyAllocation(38, 42, 20, 8)),
            EconomyModePolicy(EconomyMode.CASTLE_CONVERSION, EconomyAllocation(45, 25, 30, 7)),
            EconomyModePolicy(EconomyMode.IMPERIAL_CONVERSION, EconomyAllocation(40, 25, 35, 7)),
        ),
    )


_SN_TARGETS = (
    ("sn-food-gatherer-percentage", 117),
    ("sn-wood-gatherer-percentage", 120),
    ("sn-gold-gatherer-percentage", 118),
    ("sn-percent-civilian-builders", 1),
)


def lower_economy_controller(
    plan: EconomyControllerPlan,
    profile,
) -> NativeControlPlan:
    existing_ids = {
        mode.native_strategic_number_id
        for mode in profile.strategic_number_modes
    }
    overlap = existing_ids.intersection({item[1] for item in _SN_TARGETS})
    if overlap:
        raise ValueError(
            f"economy controller Strategic Number writers overlap strategy-owned ids: {sorted(overlap)}"
        )

    profile_ids = {item.mode for item in plan.policies}
    required_modes = set(EconomyMode)
    if profile_ids != required_modes:
        missing = sorted(required_modes - profile_ids, key=int)
        extra = sorted(profile_ids - required_modes, key=int)
        raise ValueError(
            f"economy controller policy coverage mismatch; missing={missing}, extra={extra}"
        )

    states = [
        NativeControlState(
            plan.state_name,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.controller_id, plan.state_name),
                    "economy-selection",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        )
    ]
    for symbol, native_id in _SN_TARGETS:
        states.append(
            NativeControlState(
                symbol,
                StrategicNumberRequest(
                    StorageRequestId(
                        SemanticId(plan.controller_id, symbol),
                        "economy-strategic-number",
                    ),
                    why_not_goal=(
                        "Native civilian-allocation Strategic Number; the controller "
                        "does not infer a deeper villager scheduler contract."
                    ),
                    stability_key=f"{plan.controller_id}:{native_id}",
                    origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                    native_strategic_number_id=native_id,
                ),
            )
        )

    allocation_by_mode = {
        item.mode: item.allocation
        for item in plan.policies
    }

    def drift_guard(allocation: EconomyAllocation) -> str:
        names_and_values = (
            ("sn-food-gatherer-percentage", allocation.food),
            ("sn-wood-gatherer-percentage", allocation.wood),
            ("sn-gold-gatherer-percentage", allocation.gold),
            ("sn-percent-civilian-builders", allocation.builders),
        )
        terms = tuple(
            f"(up-compare-sn {name} != {value})"
            for name, value in names_and_values
        )
        combined = terms[0]
        for term in terms[1:]:
            combined = f"(or {combined} {term})"
        return combined

    def rule(identity: str, mode: EconomyMode, guard: str) -> NativeControlRule:
        allocation = allocation_by_mode[mode]
        actions = (
            parse_expression(f"(set-goal {plan.state_name} {int(mode)})", SourceLocation(1)),
            parse_expression(f"(set-strategic-number sn-food-gatherer-percentage {allocation.food})", SourceLocation(1)),
            parse_expression(f"(set-strategic-number sn-wood-gatherer-percentage {allocation.wood})", SourceLocation(1)),
            parse_expression(f"(set-strategic-number sn-gold-gatherer-percentage {allocation.gold})", SourceLocation(1)),
            parse_expression(f"(set-strategic-number sn-percent-civilian-builders {allocation.builders})", SourceLocation(1)),
        )
        return NativeControlRule(
            identity,
            facts=(parse_expression(guard, SourceLocation(1)),),
            actions=actions,
        )

    drift_by_mode = {
        mode: drift_guard(allocation_by_mode[mode])
        for mode in EconomyMode
    }

    feudal_window = "(and (current-age >= feudal-age) (current-age < castle-age))"
    pre_castle_no_pressure = f"(and {feudal_window} (not {profile.observation(plan.pressure_observation).expression}))"
    pressure = profile.observation(plan.pressure_observation).expression
    opening = lambda value: f"(goal {plan.opening_state} {value})"

    rules = (
        rule(
            "economy-controller-counter-pressure",
            EconomyMode.COUNTER_FEUDAL,
            f"(and {feudal_window} (and {pressure} {drift_by_mode[EconomyMode.COUNTER_FEUDAL]}))",
        ),
        rule(
            "economy-controller-fast-castle",
            EconomyMode.FAST_CASTLE,
            f"(and {pre_castle_no_pressure} (and {opening(3)} {drift_by_mode[EconomyMode.FAST_CASTLE]}))",
        ),
        rule(
            "economy-controller-counter-feudal",
            EconomyMode.COUNTER_FEUDAL,
            f"(and {pre_castle_no_pressure} (and {opening(2)} {drift_by_mode[EconomyMode.COUNTER_FEUDAL]}))",
        ),
        rule(
            "economy-controller-water-economy",
            EconomyMode.WATER_ECONOMY,
            f"(and {pre_castle_no_pressure} (and {opening(4)} {drift_by_mode[EconomyMode.WATER_ECONOMY]}))",
        ),
        rule(
            "economy-controller-water-control",
            EconomyMode.WATER_CONTROL,
            f"(and {pre_castle_no_pressure} (and {opening(5)} {drift_by_mode[EconomyMode.WATER_CONTROL]}))",
        ),
        rule(
            "economy-controller-base",
            EconomyMode.BASE,
            f"(and (current-age < castle-age) (and (not {pressure}) (and {opening(1)} {drift_by_mode[EconomyMode.BASE]})))",
        ),
        rule(
            "economy-controller-castle-conversion",
            EconomyMode.CASTLE_CONVERSION,
            f"(and (current-age >= castle-age) (and (current-age < imperial-age) {drift_by_mode[EconomyMode.CASTLE_CONVERSION]}))",
        ),
        rule(
            "economy-controller-imperial-conversion",
            EconomyMode.IMPERIAL_CONVERSION,
            f"(and (current-age >= imperial-age) {drift_by_mode[EconomyMode.IMPERIAL_CONVERSION]})",
        ),
    )

    return NativeControlPlan(states=tuple(states), rules=rules)


__all__ = (
    "EconomyAllocation",
    "EconomyControllerPlan",
    "EconomyMode",
    "EconomyModePolicy",
    "default_byzantine_economy_controller",
    "lower_economy_controller",
)
