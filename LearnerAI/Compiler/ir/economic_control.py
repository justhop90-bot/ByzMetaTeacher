"""Deterministic economic posture controller for the Byzantine compiler."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..ast import SourceLocation
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
    pressure_observation: str = "strategy-opening-pressure"
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
            EconomyModePolicy(EconomyMode.BASE, EconomyAllocation(55, 30, 15, 5)),
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
    ("sn-stone-gatherer-percentage", 119),
    ("sn-percent-civilian-builders", 1),
)


def lower_economy_controller(
    plan: EconomyControllerPlan,
    profile,
) -> NativeControlPlan:
    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from ..semantic.analyzer import parse_expression

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

    allocation_by_mode = {item.mode: item.allocation for item in plan.policies}
    pressure = profile.observation(plan.pressure_observation).expression
    feudal_window = "(and (current-age >= feudal-age) (current-age < castle-age))"
    no_knight_pressure = "(not (players-unit-type-count any-enemy knight >= 3))"
    no_ranged_pressure = "(not (players-unit-type-count any-enemy archer-line >= 4))"
    no_infantry_pressure = "(not (players-unit-type-count any-enemy militia-line >= 5))"
    no_pressure = (
        no_knight_pressure,
        no_ranged_pressure,
        no_infantry_pressure,
    )
    opening = lambda value: f"(goal {plan.opening_state} {value})"
    not_emergency_recovery = f"(not {opening(6)})"
    castle_bank_maturity = (
        "(and (unit-type-count-total villager >= 28) "
        "(and (building-type-count-total blacksmith >= 1) "
        "(building-type-count-total market >= 1)))"
    )
    water_pre_castle = f"(not {castle_bank_maturity})"
    water_castle_opening = (
        f"(or {opening(3)} "
        f"(and (or {opening(4)} {opening(5)}) {castle_bank_maturity}))"
    )

    def select_rule(
        identity: str,
        mode: EconomyMode,
        guard: str | tuple[str, ...],
    ) -> NativeControlRule:
        guard_terms = (guard,) if isinstance(guard, str) else guard
        return NativeControlRule(
            identity,
            facts=tuple(
                parse_expression(term, SourceLocation(1))
                for term in guard_terms
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {int(mode)})",
                    SourceLocation(1),
                ),
            ),
        )

    def write_rule(
        identity: str,
        mode: EconomyMode,
        symbol: str,
        value: int,
    ) -> NativeControlRule:
        return NativeControlRule(
            identity,
            facts=(
                parse_expression(
                    f"(goal {plan.state_name} {int(mode)})",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(up-compare-sn {symbol} != {value})",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-strategic-number {symbol} {value})",
                    SourceLocation(1),
                ),
            ),
        )

    selection_rules = (
        select_rule(
            "economy-controller-select-counter-pressure",
            EconomyMode.COUNTER_FEUDAL,
            (
                f"(and {feudal_window} {pressure})",
                "(not (map-type arena))",
                not_emergency_recovery,
            ),
        ),
        select_rule(
            "economy-controller-select-fast-castle",
            EconomyMode.FAST_CASTLE,
            (feudal_window, *no_pressure, water_castle_opening, not_emergency_recovery),
        ),
        select_rule(
            "economy-controller-select-counter-feudal",
            EconomyMode.COUNTER_FEUDAL,
            (feudal_window, *no_pressure, opening(2), not_emergency_recovery),
        ),
        select_rule(
            "economy-controller-select-water-economy",
            EconomyMode.WATER_ECONOMY,
            (feudal_window, *no_pressure, opening(4), water_pre_castle, not_emergency_recovery),
        ),
        select_rule(
            "economy-controller-select-water-control",
            EconomyMode.WATER_CONTROL,
            (feudal_window, *no_pressure, opening(5), water_pre_castle, not_emergency_recovery),
        ),
        select_rule(
            "economy-controller-select-base",
            EconomyMode.BASE,
            (
                "(current-age < castle-age)",
                f"(or {opening(1)} {opening(6)})",
            ),
        ),
        select_rule(
            "economy-controller-select-castle-conversion",
            EconomyMode.CASTLE_CONVERSION,
            "(and (current-age >= castle-age) (current-age < imperial-age))",
        ),
        select_rule(
            "economy-controller-select-imperial-conversion",
            EconomyMode.IMPERIAL_CONVERSION,
            "(current-age >= imperial-age)",
        ),
    )

    writer_rules = []
    for mode in EconomyMode:
        allocation = allocation_by_mode[mode]
        for symbol, value in (
            ("sn-food-gatherer-percentage", allocation.food),
            ("sn-wood-gatherer-percentage", allocation.wood),
            ("sn-gold-gatherer-percentage", allocation.gold),
            ("sn-percent-civilian-builders", allocation.builders),
        ):
            writer_rules.append(
                write_rule(
                    f"economy-controller-write-{mode.name.lower()}-{symbol}",
                    mode,
                    symbol,
                    value,
                )
            )

    # Stone is deliberately outside the generic economy allocation tuple.
    # The Byzantine Dark Age contract is nevertheless explicit: BASE owns a
    # fail-safe zero-stone write instead of inheriting an engine/default split.
    writer_rules.append(
        NativeControlRule(
            "economy-controller-write-base-sn-stone-gatherer-percentage",
            facts=(
                parse_expression("(goal economy-posture 1)", SourceLocation(1)),
                parse_expression(
                    "(up-compare-sn sn-stone-gatherer-percentage != 0)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    "(set-strategic-number sn-stone-gatherer-percentage 0)",
                    SourceLocation(1),
                ),
            ),
        )
    )

    return NativeControlPlan(
        states=tuple(states),
        rules=selection_rules + tuple(writer_rules),
    )


__all__ = (
    "EconomyAllocation",
    "EconomyControllerPlan",
    "EconomyMode",
    "EconomyModePolicy",
    "default_byzantine_economy_controller",
    "lower_economy_controller",
)
