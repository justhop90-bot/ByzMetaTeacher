"""Typed water, naval, and transport execution policy.

This module owns only the compiler-facing water execution state machine and
its native persistent-control lowering. It deliberately does not claim that
a Transport Ship reaching a target point proves a successful landing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from ..ast import SourceLocation

if TYPE_CHECKING:
    from ..runtime_binding import GoalSlotRequest
from .model import GoalRole, SemanticId, StorageRequestId
from .native_control import NativeControlPlan, NativeControlRule, NativeControlState


class WaterPosture(IntEnum):
    UNKNOWN = -1
    NONE = 0
    FISHING = 1
    NAVAL_DEFENSE = 2
    NAVAL_CONTROL = 3
    TRANSPORT_SUPPORT = 4


class TransportExecutionPhase(IntEnum):
    UNKNOWN = -1
    INACTIVE = 0
    PREPARE = 1
    READY = 2
    RECOVER = 3


@dataclass(frozen=True)
class WaterExecutionState:
    """Current compiler/runtime interpretation of the water execution envelope."""

    posture: WaterPosture = WaterPosture.NONE
    transport_phase: TransportExecutionPhase = TransportExecutionPhase.INACTIVE
    transport_required: bool | None = False
    transport_capable: bool | None = False
    dock_exists: bool | None = False
    naval_pressure: bool | None = False
    warboat_floor_met: bool | None = False


@dataclass(frozen=True)
class WaterExecutionPlan:
    """Typed strategy references for water/naval/transport execution."""

    plan_id: str
    water_posture_state: str
    transport_phase_state: str
    transport_required_observation: str
    transport_capable_observation: str
    dock_observation: str
    naval_pressure_observation: str
    naval_pressure_cleared_observation: str
    warboat_floor_observation: str

    def __post_init__(self) -> None:
        for name, value in (
            ("plan_id", self.plan_id),
            ("water_posture_state", self.water_posture_state),
            ("transport_phase_state", self.transport_phase_state),
            ("transport_required_observation", self.transport_required_observation),
            ("transport_capable_observation", self.transport_capable_observation),
            ("dock_observation", self.dock_observation),
            ("naval_pressure_observation", self.naval_pressure_observation),
            ("naval_pressure_cleared_observation", self.naval_pressure_cleared_observation),
            ("warboat_floor_observation", self.warboat_floor_observation),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


def transition_transport_execution(
    current: WaterExecutionState,
    *,
    transport_required: bool,
    transport_capable: bool,
) -> WaterExecutionState:
    """Advance transport execution without treating dispatch as landing proof."""

    if transport_required is None or transport_capable is None:
        phase = current.transport_phase if current.transport_phase is not TransportExecutionPhase.INACTIVE else TransportExecutionPhase.UNKNOWN
    elif not transport_required:
        phase = TransportExecutionPhase.INACTIVE
    elif transport_capable:
        phase = TransportExecutionPhase.READY
    elif current.transport_phase is TransportExecutionPhase.READY:
        phase = TransportExecutionPhase.RECOVER
    else:
        phase = TransportExecutionPhase.PREPARE

    return WaterExecutionState(
        posture=current.posture,
        transport_phase=phase,
        transport_required=transport_required,
        transport_capable=transport_capable,
        dock_exists=current.dock_exists,
        naval_pressure=current.naval_pressure,
        warboat_floor_met=current.warboat_floor_met,
    )


def derive_water_posture(
    *,
    transport_required: bool,
    dock_exists: bool,
    naval_pressure: bool,
    warboat_floor_met: bool,
) -> WaterPosture:
    """Derive deterministic water posture from typed strategic observations."""
    if transport_required is True:
        return WaterPosture.TRANSPORT_SUPPORT
    if transport_required is None:
        return WaterPosture.UNKNOWN
    if naval_pressure is True:
        if warboat_floor_met is None:
            return WaterPosture.UNKNOWN
        return (
            WaterPosture.NAVAL_CONTROL
            if warboat_floor_met
            else WaterPosture.NAVAL_DEFENSE
        )
    if naval_pressure is None:
        return WaterPosture.UNKNOWN
    if dock_exists is True:
        return WaterPosture.FISHING
    if dock_exists is None:
        return WaterPosture.UNKNOWN
    return WaterPosture.NONE


def lower_water_execution_plan(
    plan: WaterExecutionPlan,
    profile,
) -> NativeControlPlan:
    """Lower water posture and transport recovery into the shared control plane."""
    from ..runtime_binding import GoalSlotRequest
    from ..semantic.analyzer import parse_expression

    required = profile.observation(plan.transport_required_observation).expression
    capable = profile.observation(plan.transport_capable_observation).expression
    dock = profile.observation(plan.dock_observation).expression
    naval = profile.observation(plan.naval_pressure_observation).expression
    warboats = profile.observation(plan.warboat_floor_observation).expression

    posture_state = plan.water_posture_state
    phase_state = plan.transport_phase_state
    posture_owner = SemanticId(plan.plan_id, posture_state)
    phase_owner = SemanticId(plan.plan_id, phase_state)

    states = (
        NativeControlState(
            posture_state,
            GoalSlotRequest(
                StorageRequestId(posture_owner, "water-posture"),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            phase_state,
            GoalSlotRequest(
                StorageRequestId(phase_owner, "transport-phase"),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
    )

    def goal(name: str, value: int):
        return parse_expression(f"(goal {name} {value})", SourceLocation(1))

    def set_goal(name: str, value: int):
        return parse_expression(f"(set-goal {name} {value})", SourceLocation(1))

    rules = [
        NativeControlRule(
            "water-execution-initialize",
            facts=(goal(phase_state, 0), goal(posture_state, 0)),
            actions=(
                set_goal(phase_state, 0),
                set_goal(posture_state, 0),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "transport-phase-no-longer-required",
            facts=(
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                parse_expression(
                    f"(or {goal(phase_state, 1).source} "
                    f"(or {goal(phase_state, 2).source} {goal(phase_state, 3).source}))",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(phase_state, 0),),
        ),
        NativeControlRule(
            "transport-phase-recover-on-capability-loss",
            facts=(
                required,
                goal(phase_state, int(TransportExecutionPhase.READY)),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
            ),
            actions=(set_goal(phase_state, int(TransportExecutionPhase.RECOVER)),),
        ),
        NativeControlRule(
            "transport-phase-prepare",
            facts=(
                required,
                parse_expression(
                    f"(or {goal(phase_state, 0).source} {goal(phase_state, 3).source})",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
            ),
            actions=(set_goal(phase_state, int(TransportExecutionPhase.PREPARE)),),
        ),
        NativeControlRule(
            "transport-phase-ready",
            facts=(
                required,
                capable,
                parse_expression(
                    f"(not {goal(phase_state, int(TransportExecutionPhase.READY)).source})",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(phase_state, int(TransportExecutionPhase.READY)),),
        ),
        NativeControlRule(
            "water-posture-transport",
            facts=(required,),
            actions=(set_goal(posture_state, int(WaterPosture.TRANSPORT_SUPPORT)),),
        ),
        NativeControlRule(
            "water-posture-naval-defense",
            facts=(
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                naval,
                parse_expression(f"(not {warboats.source})", SourceLocation(1)),
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NAVAL_DEFENSE)),),
        ),
        NativeControlRule(
            "water-posture-naval-control",
            facts=(
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                naval,
                warboats,
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NAVAL_CONTROL)),),
        ),
        NativeControlRule(
            "water-posture-fishing",
            facts=(
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                dock,
            ),
            actions=(set_goal(posture_state, int(WaterPosture.FISHING)),),
        ),
        NativeControlRule(
            "water-posture-none",
            facts=(
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                parse_expression(f"(not {dock.source})", SourceLocation(1)),
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NONE)),),
        ),
    ]

    return NativeControlPlan(states=states, rules=tuple(rules))


__all__ = [
    "TransportExecutionPhase",
    "WaterExecutionPlan",
    "WaterExecutionState",
    "WaterPosture",
    "derive_water_posture",
    "lower_water_execution_plan",
    "transition_transport_execution",
]
