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


@dataclass(frozen=True)
class OpeningSelectorPlan:
    plan_id: str
    state_name: str = "opening-plan"
    water_observation: str = "strategy-water-islands"
    naval_pressure_observation: str = "strategy-enemy-naval-pressure"
    arena_observation: str = "strategy-arena-map"
    arabia_observation: str = "strategy-arabia-map"
    enemy_pressure_observation: str = "strategy-opening-pressure"

    def __post_init__(self) -> None:
        for name, value in (
            ("plan_id", self.plan_id),
            ("state_name", self.state_name),
            ("water_observation", self.water_observation),
            ("naval_pressure_observation", self.naval_pressure_observation),
            ("arena_observation", self.arena_observation),
            ("arabia_observation", self.arabia_observation),
            ("enemy_pressure_observation", self.enemy_pressure_observation),
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
    arabia = profile.observation(plan.arabia_observation).expression
    pressure = profile.observation(plan.enemy_pressure_observation).expression

    state = NativeControlState(
        plan.state_name,
        GoalSlotRequest(
            StorageRequestId(
                SemanticId(plan.plan_id, plan.state_name),
                "opening-selection",
            ),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )
    unselected = f"(goal {plan.state_name} -1)"
    guard = lambda body: f"(and {unselected} {body})"

    rules = (
        NativeControlRule(
            "opening-selector-water-control",
            facts=(parse_expression(guard(f"(and {water} {naval})"), SourceLocation(1)),),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.WATER_CONTROL})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-water-economy",
            facts=(parse_expression(guard(f"(and {water} (not {naval}))"), SourceLocation(1)),),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.WATER_ECONOMY})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-fast-castle",
            facts=(
                parse_expression(
                    guard(
                        f"(and (and {arena} (not {pressure})) (not {water}))"
                    ),
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {OpeningPlanValue.FAST_CASTLE})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "opening-selector-fast-castle-standard-land",
            facts=(
                parse_expression(
                    guard(
                        f"(and (and (not {water}) (and (not {arena}) (and (not {arabia}) (and (not (map-type hybrid)) (not {pressure})))))"
                    ),
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {OpeningPlanValue.FAST_CASTLE})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "opening-selector-counter-feudal",
            facts=(parse_expression(guard(f"(and (not {water}) (and (not {arena}) {pressure}))"), SourceLocation(1)),),
            actions=(parse_expression(f"(set-goal {plan.state_name} {OpeningPlanValue.COUNTER_FEUDAL})", SourceLocation(1)),),
        ),
        NativeControlRule(
            "opening-selector-defensive-standard-arabia",
            facts=(
                parse_expression(
                    guard(f"(and {arabia} (not {pressure}))"),
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {OpeningPlanValue.DEFENSIVE_STANDARD})",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "opening-selector-defensive-standard",
            facts=(
                parse_expression(
                    guard(f"(and (map-type hybrid) (not {pressure}))"),
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {plan.state_name} {OpeningPlanValue.DEFENSIVE_STANDARD})",
                    SourceLocation(1),
                ),
            ),
        ),
    )
    return NativeControlPlan(states=(state,), rules=rules)


__all__ = (
    "OpeningFamily",
    "OpeningPlanValue",
    "OpeningSelectorPlan",
    "default_byzantine_opening_selector",
    "lower_opening_selector",
)
