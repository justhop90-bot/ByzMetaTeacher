"""Durable, deterministic opening interpretation lowered to native Goal state."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, Enum

from ..ast import SourceLocation
from .model import GoalRole, SemanticId, StorageRequestId
from .native_control import NativeControlPlan, NativeControlRule, NativeControlState


class OpeningFamily(str, Enum):
    DEFENSIVE_STANDARD = "DEFENSIVE_STANDARD"
    COUNTER_FEUDAL = "COUNTER_FEUDAL"
    FAST_CASTLE = "FAST_CASTLE"
    WATER_ECONOMY = "WATER_ECONOMY"
    WATER_CONTROL = "WATER_CONTROL"
    EMERGENCY_RECOVERY = "EMERGENCY_RECOVERY"


class OpeningPlanValue(IntEnum):
    UNKNOWN = 0
    DEFENSIVE_STANDARD = 1
    COUNTER_FEUDAL = 2
    FAST_CASTLE = 3
    WATER_ECONOMY = 4
    WATER_CONTROL = 5
    EMERGENCY_RECOVERY = 6


@dataclass(frozen=True)
class OpeningSelectorPlan:
    plan_id: str
    state_name: str = "opening-plan"
    recovery_state_name: str = "opening-recovery"
    recovery_origin_state_name: str = "opening-recovery-origin"
    recovery_gold_proven_state_name: str = "opening-recovery-gold-proven"
    recovery_water_proven_state_name: str = "opening-recovery-water-proven"
    water_observation: str = "strategy-water-islands"
    naval_pressure_observation: str = "strategy-enemy-naval-pressure"
    arena_observation: str = "strategy-arena-map"
    enemy_pressure_observation: str = "strategy-opening-pressure"
    base_defense_observation: str = "strategy-opening-base-defense-collapse"
    transport_capable_observation: str = "strategy-own-transport-capable"

    def __post_init__(self) -> None:
        for name, value in (
            ("plan_id", self.plan_id),
            ("state_name", self.state_name),
            ("recovery_state_name", self.recovery_state_name),
            ("recovery_origin_state_name", self.recovery_origin_state_name),
            ("recovery_gold_proven_state_name", self.recovery_gold_proven_state_name),
            ("recovery_water_proven_state_name", self.recovery_water_proven_state_name),
            ("water_observation", self.water_observation),
            ("naval_pressure_observation", self.naval_pressure_observation),
            ("arena_observation", self.arena_observation),
            ("enemy_pressure_observation", self.enemy_pressure_observation),
            ("base_defense_observation", self.base_defense_observation),
            ("transport_capable_observation", self.transport_capable_observation),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


def default_byzantine_opening_selector() -> OpeningSelectorPlan:
    return OpeningSelectorPlan(plan_id="byzantine-opening-v1")


def lower_opening_selector(
    plan: OpeningSelectorPlan,
    profile,
) -> NativeControlPlan:
    from ..runtime_binding import GoalSlotRequest
    from ..semantic.analyzer import parse_expression
    water = profile.observation(plan.water_observation).expression
    naval = profile.observation(plan.naval_pressure_observation).expression
    arena = profile.observation(plan.arena_observation).expression
    pressure = profile.observation(plan.enemy_pressure_observation).expression
    base_defense = profile.observation(plan.base_defense_observation).expression
    transport_capable = profile.observation(plan.transport_capable_observation).expression
    dock_exists = profile.observation("strategy-dock-exists").expression
    gold_remote = profile.observation("camp-front-gold-remote").expression

    def goal_state(name: str, role: str) -> NativeControlState:
        return NativeControlState(
            name,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, name),
                    role,
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        )

    states = (
        goal_state(plan.state_name, "opening-selection"),
        goal_state(plan.recovery_state_name, "opening-recovery"),
        goal_state(plan.recovery_origin_state_name, "opening-recovery-origin"),
        goal_state(plan.recovery_gold_proven_state_name, "opening-recovery-proof"),
        goal_state(plan.recovery_water_proven_state_name, "opening-recovery-proof"),
    )
    unselected = f"(goal {plan.state_name} -1)"
    recovery_idle = f"(goal {plan.recovery_state_name} 0)"
    recovery_active = f"(goal {plan.recovery_state_name} 1)"
    recovery_origin_unset = f"(goal {plan.recovery_origin_state_name} -1)"
    gold_proven = f"(goal {plan.recovery_gold_proven_state_name} 1)"
    water_proven = f"(goal {plan.recovery_water_proven_state_name} 1)"

    opening_plan_selected = (
        f"(or {f'(goal {plan.state_name} {OpeningPlanValue.DEFENSIVE_STANDARD})'} "
        f"{f'(or (goal {plan.state_name} {OpeningPlanValue.COUNTER_FEUDAL})'} "
        f"{f'(or (goal {plan.state_name} {OpeningPlanValue.FAST_CASTLE})'} "
        f"{f'(or (goal {plan.state_name} {OpeningPlanValue.WATER_ECONOMY})'} "
        f"(goal {plan.state_name} {OpeningPlanValue.WATER_CONTROL}))))"
    )
    water_plan_selected = (
        f"(or (goal {plan.state_name} {OpeningPlanValue.WATER_ECONOMY}) "
        f"(goal {plan.state_name} {OpeningPlanValue.WATER_CONTROL}))"
    )
    gold_front_viable = f"(not {gold_remote})"
    gold_front_lost = (
        f"(and {gold_proven} (current-age < castle-age) "
        "(and (resource-found gold) (dropsite-min-distance gold <= -1)))"
    )
    water_path_lost = (
        f"(and {water_proven} {water}) "
        f"(not {transport_capable})"
    )
    recovery_disaster = (
        f"(or {gold_front_lost} "
        f"(or {water_path_lost} {base_defense}))"
    )
    recovery_clear = (
        f"(and (not {gold_front_lost}) "
        f"(and (not {water_path_lost}) (not {base_defense}))"
    )

    rules = [
    def native_facts(*expressions: str):
        return tuple(
            parse_expression(expression, SourceLocation(1))
            for expression in expressions
        )

    rules = (
        NativeControlRule(
            "opening-selector-water-control",
            facts=native_facts(unselected, water, naval),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.WATER_CONTROL})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-water-economy",
            facts=native_facts(unselected, water, f"(not {naval})"),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.WATER_ECONOMY})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-fast-castle",
            facts=native_facts(unselected, arena, f"(not {pressure})"),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.FAST_CASTLE})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-counter-feudal",
            facts=native_facts(unselected, f"(not {water})", f"(not {arena})", pressure),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.COUNTER_FEUDAL})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-defensive-standard",
            facts=native_facts(unselected, f"(not {water})", f"(not {arena})", f"(not {pressure})"),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.DEFENSIVE_STANDARD})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-recovery-prove-gold",
            facts=native_facts(
                opening_plan_selected,
                "(current-age >= feudal-age)",
                gold_front_viable,
                f"(goal {plan.recovery_gold_proven_state_name} -1)",
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.recovery_gold_proven_state_name} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "opening-recovery-prove-water",
            facts=native_facts(
                water_plan_selected,
                water,
                dock_exists,
                transport_capable,
                f"(goal {plan.recovery_water_proven_state_name} -1)",
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.recovery_water_proven_state_name} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
    ]

    recovery_plans = (
        ("defensive-standard", OpeningPlanValue.DEFENSIVE_STANDARD),
        ("counter-feudal", OpeningPlanValue.COUNTER_FEUDAL),
        ("fast-castle", OpeningPlanValue.FAST_CASTLE),
        ("water-economy", OpeningPlanValue.WATER_ECONOMY),
        ("water-control", OpeningPlanValue.WATER_CONTROL),
    )
    for label, value in recovery_plans:
        rules.append(
            NativeControlRule(
                f"opening-recovery-enter-{label}",
                facts=native_facts(
                    f"(goal {plan.state_name} {value})",
                    recovery_idle,
                    recovery_origin_unset,
                    recovery_disaster,
                ),
                actions=(
                    parse_expression(
                        f"(set-goal {plan.recovery_origin_state_name} {value})",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-goal {plan.state_name} {OpeningPlanValue.EMERGENCY_RECOVERY})",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-goal {plan.recovery_state_name} 1)",
                        SourceLocation(1),
                    ),
                ),
            )
        )
        rules.append(
            NativeControlRule(
                f"opening-recovery-exit-{label}",
                facts=native_facts(
                    f"(goal {plan.state_name} {OpeningPlanValue.EMERGENCY_RECOVERY})",
                    recovery_active,
                    f"(goal {plan.recovery_origin_state_name} {value})",
                    recovery_clear,
                ),
                actions=(
                    parse_expression(
                        f"(set-goal {plan.state_name} {value})",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-goal {plan.recovery_origin_state_name} -1)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-goal {plan.recovery_state_name} 0)",
                        SourceLocation(1),
                    ),
                ),
            )
        )

    return NativeControlPlan(states=states, rules=tuple(rules))


__all__ = (
    "OpeningFamily",
    "OpeningPlanValue",
    "OpeningSelectorPlan",
    "default_byzantine_opening_selector",
    "lower_opening_selector",
)
