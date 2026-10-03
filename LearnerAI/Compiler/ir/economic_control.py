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
    FAST_IMPERIAL = 9


class CastleBankState(IntEnum):
    IDLE = 0
    HARD_RESERVED = 1
    BUFFER_RESERVED = 2


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
    pressure_observation: str = "strategy-arabia-early-pressure"
    castle_bank_state_name: str = "byzantine-castle-bank-state"
    castle_bank_hard_food: int = 800
    castle_bank_hard_gold: int = 200
    castle_bank_buffer_food: int = 950
    castle_bank_buffer_gold: int = 300
    policies: tuple[EconomyModePolicy, ...] = ()

    def __post_init__(self) -> None:
        if not self.controller_id.strip():
            raise ValueError("economy controller id must not be empty")
        modes = tuple(item.mode for item in self.policies)
        if len(modes) != len(set(modes)):
            raise ValueError("economy controller modes must be unique")
        if self.castle_bank_hard_food <= 0 or self.castle_bank_hard_gold <= 0:
            raise ValueError("Castle bank hard reserve must be positive")
        if self.castle_bank_buffer_food < self.castle_bank_hard_food:
            raise ValueError("Castle bank food buffer must cover the hard reserve")
        if self.castle_bank_buffer_gold < self.castle_bank_hard_gold:
            raise ValueError("Castle bank gold buffer must cover the hard reserve")


def default_byzantine_economy_controller() -> EconomyControllerPlan:
    return EconomyControllerPlan(
        controller_id="byzantine-economy-v1",
        policies=(
            EconomyModePolicy(EconomyMode.BASE, EconomyAllocation(55, 30, 15, 5)),
            EconomyModePolicy(EconomyMode.COUNTER_FEUDAL, EconomyAllocation(42, 38, 20, 8)),
            EconomyModePolicy(EconomyMode.FAST_CASTLE, EconomyAllocation(50, 25, 25, 3)),
            EconomyModePolicy(EconomyMode.WATER_ECONOMY, EconomyAllocation(40, 40, 20, 5)),
            EconomyModePolicy(EconomyMode.WATER_CONTROL, EconomyAllocation(38, 42, 20, 8)),
            EconomyModePolicy(EconomyMode.CASTLE_CONVERSION, EconomyAllocation(45, 25, 30, 7)),
            EconomyModePolicy(EconomyMode.IMPERIAL_CONVERSION, EconomyAllocation(40, 25, 35, 7)),
            EconomyModePolicy(EconomyMode.FAST_IMPERIAL, EconomyAllocation(42, 20, 38, 7)),
        ),
    )


_SN_TARGETS = (
    ("sn-food-gatherer-percentage", 117),
    ("sn-wood-gatherer-percentage", 120),
    ("sn-gold-gatherer-percentage", 118),
    ("sn-stone-gatherer-percentage", 119),
    ("sn-percent-civilian-builders", 1),
)


def lower_economy_controller(plan: EconomyControllerPlan) -> NativeControlPlan:
    from ..semantic.analyzer import parse_expression

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
    states.append(
        NativeControlState(
            plan.castle_bank_state_name,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.controller_id, "castle-bank-state"),
                    "castle-bank-selection",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        )
    )
    for symbol, native_id in _SN_TARGETS:
        states.append(
            NativeControlState(
                symbol,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(plan.controller_id, symbol),
                        "strategic-number-writer",
                    ),
                    role=GoalRole.NATIVE_OUTPUT,
                ),
            )
        )

    def select_rule(identity: str, mode: EconomyMode, guard: str) -> NativeControlRule:
        return NativeControlRule(
            identity,
            facts=(parse_expression(guard, SourceLocation(1)),),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {int(mode)})",
                    SourceLocation(1),
                ),
            ),
        )

    selection_rules = (
        select_rule(
            "economy-controller-select-counter-pressure",
            EconomyMode.COUNTER_FEUDAL,
            f"(and (and (current-age >= feudal-age) (current-age < castle-age)) "
            f"({plan.pressure_observation}))",
        ),
        select_rule(
            "economy-controller-select-fast-castle",
            EconomyMode.FAST_CASTLE,
            f"(and (and (current-age >= feudal-age) (current-age < castle-age)) "
            f"(and (not ({plan.pressure_observation})) (goal {plan.opening_state} 3)))",
        ),
        select_rule(
            "economy-controller-select-counter-feudal",
            EconomyMode.COUNTER_FEUDAL,
            f"(and (and (current-age >= feudal-age) (current-age < castle-age)) "
            f"(and (not ({plan.pressure_observation})) (goal {plan.opening_state} 2)))",
        ),
        select_rule(
            "economy-controller-select-water-economy",
            EconomyMode.WATER_ECONOMY,
            f"(and (and (current-age >= feudal-age) (current-age < castle-age)) "
            f"(and (not ({plan.pressure_observation})) (goal {plan.opening_state} 4)))",
        ),
        select_rule(
            "economy-controller-select-water-control",
            EconomyMode.WATER_CONTROL,
            f"(and (and (current-age >= feudal-age) (current-age < castle-age)) "
            f"(and (not ({plan.pressure_observation})) (goal {plan.opening_state} 5)))",
        ),
        select_rule(
            "economy-controller-select-base",
            EconomyMode.BASE,
            f"(and (current-age < castle-age) "
            f"(and (not ({plan.pressure_observation})) "
            f"(goal {plan.opening_state} 1)))",
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
        select_rule(
            "economy-controller-select-food-recovery",
            EconomyMode.COUNTER_FEUDAL,
            "(food-amount < 350)",
        ),
    )

    policy_map = {policy.mode: policy for policy in plan.policies}

    def write_rule(identity: str, goal_value: str, command: str, value: int) -> NativeControlRule:
        return NativeControlRule(
            identity,
            facts=(
                parse_expression(
                    f"(goal {plan.state_name} {goal_value})",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(up-compare-sn {command} != {value})",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-strategic-number {command} {value})",
                    SourceLocation(1),
                ),
            ),
        )

    writer_rules = []
    mode_names = {
        EconomyMode.BASE: "base",
        EconomyMode.COUNTER_FEUDAL: "counter_feudal",
        EconomyMode.FAST_CASTLE: "fast_castle",
        EconomyMode.WATER_ECONOMY: "water_economy",
        EconomyMode.WATER_CONTROL: "water_control",
        EconomyMode.CASTLE_CONVERSION: "castle_conversion",
        EconomyMode.IMPERIAL_CONVERSION: "imperial_conversion",
        EconomyMode.FAST_IMPERIAL: "fast_imperial",
    }
    for mode in EconomyMode:
        policy = policy_map.get(mode)
        if policy is None:
            continue
        mode_name = mode_names[mode]
        for symbol, attr, value in (
            ("sn-food-gatherer-percentage", "food", policy.allocation.food),
            ("sn-wood-gatherer-percentage", "wood", policy.allocation.wood),
            ("sn-gold-gatherer-percentage", "gold", policy.allocation.gold),
            ("sn-percent-civilian-builders", "builders", policy.allocation.builders),
        ):
            writer_rules.append(
                write_rule(
                    f"economy-controller-write-{mode_name}-{symbol}",
                    str(int(mode)),
                    symbol,
                    value,
                )
            )

    bank_state = plan.castle_bank_state_name
    bank_rules = (
        NativeControlRule(
            "economy-controller-castle-bank-initialize",
            facts=(parse_expression(f"(goal {bank_state} -1)", SourceLocation(1)),),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.IDLE)})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "economy-controller-castle-bank-release-on-castle",
            facts=(parse_expression("(current-age >= castle-age)", SourceLocation(1)),),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.IDLE)})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "economy-controller-castle-bank-break-hard-reserve",
            facts=(
                parse_expression("(current-age == feudal-age)", SourceLocation(1)),
                parse_expression("(map-type arabia)", SourceLocation(1)),
                parse_expression(
                    f"(or (food-amount < {plan.castle_bank_hard_food}) "
                    f"(gold-amount < {plan.castle_bank_hard_gold}))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.IDLE)})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "economy-controller-castle-bank-protect-hard",
            facts=(
                parse_expression("(current-age == feudal-age)", SourceLocation(1)),
                parse_expression("(map-type arabia)", SourceLocation(1)),
                parse_expression(
                    f"(or (goal {plan.opening_state} 1) (goal {plan.opening_state} 2))",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(food-amount >= {plan.castle_bank_hard_food})",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(gold-amount >= {plan.castle_bank_hard_gold})",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(goal {bank_state} {int(CastleBankState.IDLE)})",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.HARD_RESERVED)})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "economy-controller-castle-bank-protect-buffer",
            facts=(
                parse_expression("(current-age == feudal-age)", SourceLocation(1)),
                parse_expression("(map-type arabia)", SourceLocation(1)),
                parse_expression(
                    f"(or (goal {plan.opening_state} 1) (goal {plan.opening_state} 2))",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(food-amount >= {plan.castle_bank_buffer_food})",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(gold-amount >= {plan.castle_bank_buffer_gold})",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.BUFFER_RESERVED)})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "economy-controller-castle-bank-relax-buffer",
            facts=(
                parse_expression(
                    f"(goal {bank_state} {int(CastleBankState.BUFFER_RESERVED)})",
                    SourceLocation(1),
                ),
                parse_expression("(current-age == feudal-age)", SourceLocation(1)),
                parse_expression("(map-type arabia)", SourceLocation(1)),
                parse_expression(
                    f"(and (food-amount >= {plan.castle_bank_hard_food}) "
                    f"(and (gold-amount >= {plan.castle_bank_hard_gold}) "
                    f"(or (food-amount < {plan.castle_bank_buffer_food}) "
                    f"(gold-amount < {plan.castle_bank_buffer_gold})))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {bank_state} {int(CastleBankState.HARD_RESERVED)})",
                    SourceLocation(1),
                ),
            ),
        ),
    )

    return NativeControlPlan(
        states=tuple(states),
        rules=bank_rules + selection_rules + tuple(writer_rules),
    )


__all__ = (
    "EconomyAllocation",
    "EconomyControllerPlan",
    "EconomyMode",
    "EconomyModePolicy",
    "CastleBankState",
    "default_byzantine_economy_controller",
    "lower_economy_controller",
)
