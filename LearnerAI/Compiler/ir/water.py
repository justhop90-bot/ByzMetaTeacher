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
    water_map: bool | None = False
    transport_required: bool | None = False
    transport_capable: bool | None = False
    transport_rebuild_open: bool | None = False
    dock_exists: bool | None = False
    naval_pressure: bool | None = False
    warboat_floor_met: bool | None = False


class PacificTransportLifecyclePhase(IntEnum):
    UNKNOWN = -1
    IDLE = 0
    LOAD = 1
    TRANSIT = 2
    UNLOAD = 3
    LANDED = 4
    RECOVERY = 5


class PacificFishingControllerPhase(IntEnum):
    UNKNOWN = -1
    IDLE = 0
    ACTIVE = 1
    NAVAL_DEFENSE = 2


class PacificHarborDefensePhase(IntEnum):
    UNKNOWN = -1
    IDLE = 0
    ACTIVE = 1


class PacificTransportEscortPhase(IntEnum):
    UNKNOWN = -1
    IDLE = 0
    REQUIRED = 1
    READY = 2


@dataclass(frozen=True)
class WaterExecutionPlan:
    """Typed strategy references for water/naval/transport execution."""

    plan_id: str
    water_posture_state: str
    transport_phase_state: str
    transport_objective_state: str
    transport_rebuild_state: str
    pacific_opening_transport_state: str
    pacific_transport_lifecycle_state: str
    pacific_fishing_controller_state: str
    pacific_harbor_defense_state: str
    pacific_transport_escort_state: str
    pacific_transport_recovery_state: str
    feudal_resource_island_transport_state: str
    water_map_observation: str
    transport_required_observation: str
    transport_capable_observation: str
    transport_rebuild_open_observation: str
    dock_observation: str
    naval_pressure_observation: str
    naval_pressure_cleared_observation: str
    warboat_floor_observation: str

    def __post_init__(self) -> None:
        for name, value in (
            ("plan_id", self.plan_id),
            ("water_posture_state", self.water_posture_state),
            ("transport_phase_state", self.transport_phase_state),
            ("transport_objective_state", self.transport_objective_state),
            ("transport_rebuild_state", self.transport_rebuild_state),
            ("pacific_opening_transport_state", self.pacific_opening_transport_state),
            ("pacific_transport_lifecycle_state", self.pacific_transport_lifecycle_state),
            ("pacific_fishing_controller_state", self.pacific_fishing_controller_state),
            ("pacific_harbor_defense_state", self.pacific_harbor_defense_state),
            ("pacific_transport_escort_state", self.pacific_transport_escort_state),
            ("pacific_transport_recovery_state", self.pacific_transport_recovery_state),
            ("feudal_resource_island_transport_state", self.feudal_resource_island_transport_state),
            ("water_map_observation", self.water_map_observation),
            ("transport_required_observation", self.transport_required_observation),
            ("transport_capable_observation", self.transport_capable_observation),
            ("transport_rebuild_open_observation", self.transport_rebuild_open_observation),
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
    water_map: bool | None,
    transport_required: bool | None,
    transport_capable: bool | None,
    transport_rebuild_open: bool | None = False,
) -> WaterExecutionState:
    """Advance transport execution with explicit objective and recovery reopening."""

    if water_map is None or transport_required is None or transport_capable is None:
        phase = (
            current.transport_phase
            if current.transport_phase is not TransportExecutionPhase.INACTIVE
            else TransportExecutionPhase.UNKNOWN
        )
    elif not water_map or not transport_required:
        phase = TransportExecutionPhase.INACTIVE
    elif transport_capable:
        phase = TransportExecutionPhase.READY
    elif current.transport_phase is TransportExecutionPhase.READY:
        phase = TransportExecutionPhase.RECOVER
    elif (
        current.transport_phase is TransportExecutionPhase.RECOVER
        and transport_rebuild_open is True
    ):
        phase = TransportExecutionPhase.PREPARE
    elif current.transport_phase is TransportExecutionPhase.RECOVER:
        phase = TransportExecutionPhase.RECOVER
    else:
        phase = TransportExecutionPhase.PREPARE

    return WaterExecutionState(
        posture=current.posture,
        transport_phase=phase,
        water_map=water_map,
        transport_required=transport_required,
        transport_capable=transport_capable,
        transport_rebuild_open=transport_rebuild_open,
        dock_exists=current.dock_exists,
        naval_pressure=current.naval_pressure,
        warboat_floor_met=current.warboat_floor_met,
    )


def derive_water_posture(
    *,
    water_map: bool | None,
    transport_required: bool | None,
    dock_exists: bool | None,
    naval_pressure: bool | None,
    warboat_floor_met: bool | None,
) -> WaterPosture:
    """Derive deterministic water posture with environment/objective precedence."""

    if water_map is None:
        return WaterPosture.UNKNOWN
    if not water_map:
        return WaterPosture.NONE
    if transport_required is None:
        return WaterPosture.UNKNOWN
    if transport_required:
        return WaterPosture.TRANSPORT_SUPPORT
    if naval_pressure is None:
        return WaterPosture.UNKNOWN
    if naval_pressure:
        if warboat_floor_met is None:
            return WaterPosture.UNKNOWN
        return (
            WaterPosture.NAVAL_CONTROL
            if warboat_floor_met
            else WaterPosture.NAVAL_DEFENSE
        )
    if dock_exists is None:
        return WaterPosture.UNKNOWN
    return WaterPosture.FISHING if dock_exists else WaterPosture.NONE


def lower_water_execution_plan(
    plan: WaterExecutionPlan,
    profile,
) -> NativeControlPlan:
    """Lower water posture and transport recovery into the shared control plane."""
    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from ..semantic.analyzer import parse_expression
    from .strategic_number import StrategicNumberOrigin

    water_map = parse_expression(
        profile.observation(plan.water_map_observation).expression,
        SourceLocation(1),
    )
    required = parse_expression(
        profile.observation(plan.transport_required_observation).expression,
        SourceLocation(1),
    )
    rebuild_open = parse_expression(
        profile.observation(plan.transport_rebuild_open_observation).expression,
        SourceLocation(1),
    )
    capable = parse_expression(
        profile.observation(plan.transport_capable_observation).expression,
        SourceLocation(1),
    )
    dock = parse_expression(
        profile.observation(plan.dock_observation).expression,
        SourceLocation(1),
    )
    pacific = parse_expression(
        profile.observation("strategy-pacific-islands").expression,
        SourceLocation(1),
    )
    naval = parse_expression(
        profile.observation(plan.naval_pressure_observation).expression,
        SourceLocation(1),
    )
    naval_cleared = parse_expression(
        profile.observation(plan.naval_pressure_cleared_observation).expression,
        SourceLocation(1),
    )
    warboats = parse_expression(
        profile.observation(plan.warboat_floor_observation).expression,
        SourceLocation(1),
    )

    posture_state = plan.water_posture_state
    phase_state = plan.transport_phase_state
    boat_exploration_state = "sn-number-boat-explore-groups"
    posture_owner = SemanticId(plan.plan_id, posture_state)
    phase_owner = SemanticId(plan.plan_id, phase_state)
    boat_exploration_owner = SemanticId(plan.plan_id, boat_exploration_state)

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
        NativeControlState(
            boat_exploration_state,
            StrategicNumberRequest(
                StorageRequestId(
                    boat_exploration_owner,
                    "water-strategic-number",
                ),
                why_not_goal=(
                    "This state directly controls the DE-documented boat exploration "
                    "Strategic Number for the Byzantine water policy."
                ),
                stability_key=f"{plan.plan_id}:strategic-number:61",
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=61,
            ),
        ),
        NativeControlState(
            plan.transport_objective_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.transport_objective_state),
                    "transport-objective",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.transport_rebuild_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.transport_rebuild_state),
                    "transport-rebuild",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_opening_transport_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_opening_transport_state),
                    "pacific-opening-transport",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_transport_lifecycle_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_transport_lifecycle_state),
                    "pacific-transport-lifecycle",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_fishing_controller_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_fishing_controller_state),
                    "pacific-fishing-controller",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_harbor_defense_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_harbor_defense_state),
                    "pacific-harbor-defense",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_transport_escort_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_transport_escort_state),
                    "pacific-transport-escort",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            plan.pacific_transport_recovery_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.pacific_transport_recovery_state),
                    "pacific-transport-recovery",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            "sn-maximum-fish-boat-drop-distance",
            StrategicNumberRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, "sn-maximum-fish-boat-drop-distance"),
                    "water-strategic-number",
                ),
                why_not_goal=(
                    "This state directly controls the DE Strategic Number that bounds "
                    "fishing-boat resource distance on Pacific water."
                ),
                stability_key=f"{plan.plan_id}:strategic-number:236",
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=236,
            ),
        ),
        NativeControlState(
            "sn-fishing-boat-whaling-percentage",
            StrategicNumberRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, "sn-fishing-boat-whaling-percentage"),
                    "water-strategic-number",
                ),
                why_not_goal=(
                    "This state directly controls the DE Strategic Number selecting "
                    "the share of fishing ships that may target whales."
                ),
                stability_key=f"{plan.plan_id}:strategic-number:316",
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=316,
            ),
        ),
        NativeControlState(
            "pacific-transport-transit-witness",
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, "pacific-transport-transit-witness"),
                    "pacific-transport-transit-witness",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        NativeControlState(
            "pacific-transport-unload-witness",
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, "pacific-transport-unload-witness"),
                    "pacific-transport-unload-witness",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        ),
        *tuple(
            NativeControlState(
                name,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(profile.profile_id, name),
                        command,
                    ),
                    role=GoalRole.NATIVE_OUTPUT,
                ),
            )
            for name, command in (
                ("pacific-opening-transport-point", "up-get-point"),
                ("pacific-opening-transport-id", "up-get-object-data"),
                ("pacific-opening-transport-load-count", "up-get-object-data"),
                ("pacific-opening-transport-transit-action", "up-get-object-data"),
                ("pacific-opening-transport-distance", "up-get-object-data"),
                ("pacific-opening-transport-unload-action", "up-get-object-data"),
                ("pacific-opening-transport-unload-count", "up-get-object-data"),
            )
        ),
        NativeControlState(
            plan.feudal_resource_island_transport_state,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId(plan.plan_id, plan.feudal_resource_island_transport_state),
                    "feudal-resource-island-transport",
                ),
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
            facts=(
                goal(phase_state, 0),
                goal(posture_state, 0),
                goal(plan.transport_objective_state, 0),
                goal(plan.transport_rebuild_state, 0),
                goal(plan.pacific_opening_transport_state, 0),
                goal(plan.pacific_transport_lifecycle_state, int(PacificTransportLifecyclePhase.IDLE)),
                goal(plan.pacific_fishing_controller_state, int(PacificFishingControllerPhase.IDLE)),
                goal(plan.pacific_harbor_defense_state, int(PacificHarborDefensePhase.IDLE)),
                goal(plan.pacific_transport_escort_state, int(PacificTransportEscortPhase.IDLE)),
                goal(plan.pacific_transport_recovery_state, 0),
                goal("pacific-transport-transit-witness", 0),
                goal("pacific-transport-unload-witness", 0),
                goal(plan.feudal_resource_island_transport_state, 0),
            ),
            actions=(
                set_goal(phase_state, 0),
                set_goal(posture_state, 0),
                set_goal(plan.transport_objective_state, 0),
                set_goal(plan.transport_rebuild_state, 0),
                set_goal(plan.pacific_opening_transport_state, 0),
                set_goal(plan.feudal_resource_island_transport_state, 0),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "pacific-opening-transport-open",
            facts=(
                pacific,
                parse_expression("(current-age == dark-age)", SourceLocation(1)),
                parse_expression("(unit-type-count-total transport-ship >= 1)", SourceLocation(1)),
                goal(plan.pacific_opening_transport_state, 0),
            ),
            actions=(set_goal(plan.pacific_opening_transport_state, 1),),
        ),
        NativeControlRule(
            "pacific-opening-transport-close-at-feudal",
            facts=(
                goal(plan.pacific_opening_transport_state, 1),
                parse_expression("(current-age >= feudal-age)", SourceLocation(1)),
            ),
            actions=(set_goal(plan.pacific_opening_transport_state, 0),),
        ),
        NativeControlRule(
            "pacific-opening-transport-close-on-loss",
            facts=(
                goal(plan.pacific_opening_transport_state, 1),
                parse_expression("(unit-type-count-total transport-ship < 1)", SourceLocation(1)),
            ),
            actions=(set_goal(plan.pacific_opening_transport_state, 0),),
        ),
        NativeControlRule(
            "pacific-fishing-controller-open",
            facts=(
                pacific,
                dock,
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                parse_expression("(building-type-count-total dock >= 1)", SourceLocation(1)),
                parse_expression(
                    f"(goal {plan.pacific_fishing_controller_state} {int(PacificFishingControllerPhase.IDLE)})",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-enter-naval-defense",
            facts=(
                pacific,
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
                naval,
            ),
            actions=(
                set_goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.NAVAL_DEFENSE),
                ),
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance -2)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(set-strategic-number {boat_exploration_state} 0)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-recover-from-naval-defense",
            facts=(
                pacific,
                dock,
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.NAVAL_DEFENSE),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-close-nonwater",
            facts=(
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
                parse_expression(f"(not {pacific.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.IDLE),
                ),
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance -2)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-close-no-dock",
            facts=(
                parse_expression(
                    f"(not (goal {plan.pacific_fishing_controller_state} {int(PacificFishingControllerPhase.IDLE)}))",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {dock.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.IDLE),
                ),
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance -2)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-dark",
            facts=(
                pacific,
                dock,
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
                parse_expression("(current-age == dark-age)", SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance 30)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(set-strategic-number {boat_exploration_state} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-feudal",
            facts=(
                pacific,
                dock,
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
                parse_expression("(current-age >= feudal-age)", SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance 48)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(set-strategic-number {boat_exploration_state} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-escort-open",
            facts=(
                pacific,
                parse_expression("(current-age >= feudal-age)", SourceLocation(1)),
                dock,
                parse_expression(
                    "(or (unit-type-count-total transport-ship >= 1) "
                    "(goal pacific-transport-recovery 1))",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.IDLE),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.REQUIRED),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-escort-ready",
            facts=(
                goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.REQUIRED),
                ),
                parse_expression(
                    "(unit-type-count-total fire-galley >= 1)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.READY),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-escort-rearm-on-loss",
            facts=(
                goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.READY),
                ),
                parse_expression(
                    "(unit-type-count-total fire-galley < 1)",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.REQUIRED),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-escort-close-on-pressure",
            facts=(
                parse_expression(
                    f"(or {goal(plan.pacific_transport_escort_state, int(PacificTransportEscortPhase.REQUIRED)).source} "
                    f"{goal(plan.pacific_transport_escort_state, int(PacificTransportEscortPhase.READY)).source})",
                    SourceLocation(1),
                ),
                naval,
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.IDLE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-escort-close-nonwater",
            facts=(
                parse_expression(
                    f"(or {goal(plan.pacific_transport_escort_state, int(PacificTransportEscortPhase.REQUIRED)).source} "
                    f"{goal(plan.pacific_transport_escort_state, int(PacificTransportEscortPhase.READY)).source})",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {pacific.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_escort_state,
                    int(PacificTransportEscortPhase.IDLE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-harbor-defense-open",
            facts=(
                pacific,
                dock,
                naval,
                goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.IDLE),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.ACTIVE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-harbor-defense-close",
            facts=(
                goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.ACTIVE),
                ),
                naval_cleared,
            ),
            actions=(
                set_goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.IDLE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-harbor-defense-close-no-dock",
            facts=(
                goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.ACTIVE),
                ),
                parse_expression(f"(not {dock.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.IDLE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-recovery-close-nonwater",
            facts=(
                goal(plan.pacific_transport_recovery_state, 1),
                parse_expression(f"(not {pacific.source})", SourceLocation(1)),
            ),
            actions=(set_goal(plan.pacific_transport_recovery_state, 0),),
        ),
        NativeControlRule(
            "pacific-harbor-defense-close-nonwater",
            facts=(
                goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.ACTIVE),
                ),
                parse_expression(f"(not {pacific.source})", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_harbor_defense_state,
                    int(PacificHarborDefensePhase.IDLE),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-fishing-controller-castle",
            facts=(
                pacific,
                dock,
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                goal(
                    plan.pacific_fishing_controller_state,
                    int(PacificFishingControllerPhase.ACTIVE),
                ),
                parse_expression("(current-age >= castle-age)", SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    "(set-strategic-number sn-maximum-fish-boat-drop-distance 96)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(set-strategic-number sn-fishing-boat-whaling-percentage 0)",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(set-strategic-number {boat_exploration_state} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-open",
            facts=(
                pacific,
                parse_expression("(current-age == dark-age)", SourceLocation(1)),
                parse_expression("(unit-type-count-total transport-ship >= 1)", SourceLocation(1)),
                goal(plan.pacific_opening_transport_state, 1),
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.IDLE),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LOAD),
                ),
                set_goal("pacific-transport-transit-witness", 0),
                set_goal("pacific-transport-unload-witness", 0),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-load-witness",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LOAD),
                ),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-load-count >= 4)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.TRANSIT),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-transit-witness",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.TRANSIT),
                ),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-transit-action == 614)",
                    SourceLocation(1),
                ),
                goal("pacific-transport-transit-witness", 0),
            ),
            actions=(set_goal("pacific-transport-transit-witness", 1),),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-enter-unload",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.TRANSIT),
                ),
                goal("pacific-transport-transit-witness", 1),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-distance <= 64)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.UNLOAD),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-unload-witness",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.UNLOAD),
                ),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-unload-action == 621)",
                    SourceLocation(1),
                ),
                goal("pacific-transport-unload-witness", 0),
            ),
            actions=(set_goal("pacific-transport-unload-witness", 1),),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-landed",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.UNLOAD),
                ),
                goal("pacific-transport-unload-witness", 1),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-unload-count <= 0)",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(up-compare-goal pacific-opening-transport-unload-action != 621)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LANDED),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-recovery-open-on-landed",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LANDED),
                ),
                goal(plan.pacific_transport_recovery_state, 0),
            ),
            actions=(
                set_goal(plan.pacific_transport_recovery_state, 1),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-recover-after-landing-loss",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.IDLE),
                ),
                goal(plan.pacific_transport_recovery_state, 1),
                parse_expression(
                    "(unit-type-count-total transport-ship < 1)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.RECOVERY),
                ),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-recover-on-loss",
            facts=(
                parse_expression(
                    f"(or "
                    f"{goal(plan.pacific_transport_lifecycle_state, int(PacificTransportLifecyclePhase.LOAD)).source} "
                    f"(or "
                    f"{goal(plan.pacific_transport_lifecycle_state, int(PacificTransportLifecyclePhase.TRANSIT)).source} "
                    f"(goal {plan.pacific_transport_lifecycle_state} {int(PacificTransportLifecyclePhase.UNLOAD)})))",
                    SourceLocation(1),
                ),
                parse_expression(
                    "(unit-type-count-total transport-ship < 1)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.RECOVERY),
                ),
                set_goal("pacific-transport-transit-witness", 0),
                set_goal("pacific-transport-unload-witness", 0),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-recover-after-rebuild",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.RECOVERY),
                ),
                goal(plan.pacific_transport_recovery_state, 1),
                parse_expression(
                    "(unit-type-count-total transport-ship >= 1)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.IDLE),
                ),
                set_goal("pacific-transport-transit-witness", 0),
                set_goal("pacific-transport-unload-witness", 0),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-rearm-after-loss",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.RECOVERY),
                ),
                goal(plan.pacific_opening_transport_state, 1),
                parse_expression(
                    "(unit-type-count-total transport-ship >= 1)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LOAD),
                ),
                set_goal("pacific-transport-transit-witness", 0),
                set_goal("pacific-transport-unload-witness", 0),
            ),
        ),
        NativeControlRule(
            "pacific-transport-lifecycle-close-at-feudal",
            facts=(
                goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.LANDED),
                ),
                parse_expression("(current-age >= feudal-age)", SourceLocation(1)),
            ),
            actions=(
                set_goal(
                    plan.pacific_transport_lifecycle_state,
                    int(PacificTransportLifecyclePhase.IDLE),
                ),
                set_goal("pacific-transport-transit-witness", 0),
                set_goal("pacific-transport-unload-witness", 0),
            ),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-open",
            facts=(
                water_map,
                parse_expression("(current-age >= feudal-age)", SourceLocation(1)),
                parse_expression("(unit-type-count-total transport-ship >= 1)", SourceLocation(1)),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                parse_expression(
                    f"(or (not {pacific.source}) "
                    f"(goal {plan.pacific_transport_escort_state} {int(PacificTransportEscortPhase.READY)}))",
                    SourceLocation(1),
                ),
                goal(plan.feudal_resource_island_transport_state, 0),
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 1),),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-close-nonwater",
            facts=(
                goal(plan.feudal_resource_island_transport_state, 1),
                parse_expression(
                    f"(not {water_map.source})",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 0),),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-close-before-feudal",
            facts=(
                goal(plan.feudal_resource_island_transport_state, 1),
                parse_expression(
                    "(not (current-age >= feudal-age))",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 0),),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-close-on-loss",
            facts=(
                goal(plan.feudal_resource_island_transport_state, 1),
                parse_expression(
                    "(not (unit-type-count-total transport-ship >= 1))",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 0),),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-close-on-escort-loss",
            facts=(
                goal(plan.feudal_resource_island_transport_state, 1),
                pacific,
                parse_expression(
                    f"(not (goal {plan.pacific_transport_escort_state} {int(PacificTransportEscortPhase.READY)}))",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 0),),
        ),
        NativeControlRule(
            "feudal-resource-island-transport-close-on-naval-pressure",
            facts=(
                goal(plan.feudal_resource_island_transport_state, 1),
                naval,
            ),
            actions=(set_goal(plan.feudal_resource_island_transport_state, 0),),
        ),
        NativeControlRule(
            "transport-objective-open",
            facts=(
                water_map,
                parse_expression("(goal byzantine-army-attack-ready 1)", SourceLocation(1)),
                parse_expression(
                    f"(not (goal {plan.pacific_harbor_defense_state} {int(PacificHarborDefensePhase.ACTIVE)}))",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(or (not {pacific.source}) "
                    f"(goal {plan.pacific_transport_escort_state} {int(PacificTransportEscortPhase.READY)}))",
                    SourceLocation(1),
                ),
                goal(plan.transport_objective_state, 0),
            ),
            actions=(set_goal(plan.transport_objective_state, 1),),
        ),
        NativeControlRule(
            "transport-objective-close-on-escort-loss",
            facts=(
                goal(plan.transport_objective_state, 1),
                pacific,
                parse_expression(
                    f"(not (goal {plan.pacific_transport_escort_state} {int(PacificTransportEscortPhase.READY)}))",
                    SourceLocation(1),
                ),
            ),
            actions=(set_goal(plan.transport_objective_state, 0),),
        ),
        NativeControlRule(
            "transport-objective-close",
            facts=(
                parse_expression(
                    f"(or (not {water_map.source}) "
                    f"(or (not (goal byzantine-army-attack-ready 1)) "
                    f"(goal {plan.pacific_harbor_defense_state} {int(PacificHarborDefensePhase.ACTIVE)})))",
                    SourceLocation(1),
                ),
                goal(plan.transport_objective_state, 1),
            ),
            actions=(set_goal(plan.transport_objective_state, 0),),
        ),
        NativeControlRule(
            "transport-rebuild-authorize",
            facts=(
                water_map,
                required,
                goal(phase_state, int(TransportExecutionPhase.RECOVER)),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
                parse_expression(
                    f"(not (goal {plan.pacific_harbor_defense_state} {int(PacificHarborDefensePhase.ACTIVE)}))",
                    SourceLocation(1),
                ),
                goal(plan.transport_rebuild_state, 0),
            ),
            actions=(set_goal(plan.transport_rebuild_state, 1),),
        ),
        NativeControlRule(
            "transport-phase-no-longer-required",
            facts=(
                parse_expression(
                    f"(or (not {water_map.source}) "
                    f"(or (not {required.source}) "
                    f"(goal {plan.pacific_harbor_defense_state} {int(PacificHarborDefensePhase.ACTIVE)})))",
                    SourceLocation(1),
                ),
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
                water_map,
                required,
                goal(phase_state, int(TransportExecutionPhase.READY)),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
            ),
            actions=(set_goal(phase_state, int(TransportExecutionPhase.RECOVER)),),
        ),
        NativeControlRule(
            "transport-phase-reopen",
            facts=(
                water_map,
                required,
                goal(phase_state, int(TransportExecutionPhase.RECOVER)),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
                parse_expression(
                    f"(not (goal {plan.pacific_harbor_defense_state} {int(PacificHarborDefensePhase.ACTIVE)}))",
                    SourceLocation(1),
                ),
                parse_expression(
                    f"(or (not {pacific.source}) "
                    f"(goal {plan.pacific_transport_escort_state} {int(PacificTransportEscortPhase.READY)}))",
                    SourceLocation(1),
                ),
                rebuild_open,
            ),
            actions=(
                set_goal(phase_state, int(TransportExecutionPhase.PREPARE)),
                set_goal(plan.transport_rebuild_state, 0),
            ),
        ),
        NativeControlRule(
            "transport-phase-prepare",
            facts=(
                water_map,
                required,
                goal(phase_state, int(TransportExecutionPhase.INACTIVE)),
                parse_expression(f"(not {capable.source})", SourceLocation(1)),
            ),
            actions=(set_goal(phase_state, int(TransportExecutionPhase.PREPARE)),),
        ),
        NativeControlRule(
            "transport-phase-ready",
            facts=(
                water_map,
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
            "water-posture-none-nonwater",
            facts=(parse_expression(f"(not {water_map.source})", SourceLocation(1)),),
            actions=(set_goal(posture_state, int(WaterPosture.NONE)),),
        ),
        NativeControlRule(
            "water-posture-transport",
            facts=(water_map, required),
            actions=(set_goal(posture_state, int(WaterPosture.TRANSPORT_SUPPORT)),),
        ),
        NativeControlRule(
            "water-posture-naval-control",
            facts=(
                water_map,
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                naval,
                warboats,
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NAVAL_CONTROL)),),
        ),
        NativeControlRule(
            "water-posture-naval-defense",
            facts=(
                water_map,
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                naval,
                parse_expression(f"(not {warboats.source})", SourceLocation(1)),
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NAVAL_DEFENSE)),),
        ),
        NativeControlRule(
            "water-posture-fishing",
            facts=(
                water_map,
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                dock,
            ),
            actions=(set_goal(posture_state, int(WaterPosture.FISHING)),),
        ),
        NativeControlRule(
            "water-posture-none",
            facts=(
                water_map,
                parse_expression(f"(not {required.source})", SourceLocation(1)),
                parse_expression(f"(not {naval.source})", SourceLocation(1)),
                parse_expression(f"(not {dock.source})", SourceLocation(1)),
            ),
            actions=(set_goal(posture_state, int(WaterPosture.NONE)),),
        ),
        # SN 61 is the native fishing-boat exploration-group control. Enable it
        # only after a live fishing ship exists so the one-shot write has a boat to task.
        NativeControlRule(
            "water-boat-exploration-enable",
            facts=(
                water_map,
                dock,
                parse_expression("(unit-type-count fishing-ship >= 1)", SourceLocation(1)),
            ),
            actions=(
                parse_expression(f"(set-strategic-number {boat_exploration_state} 1)", SourceLocation(1)),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        ),

    ]

    return NativeControlPlan(states=states, rules=tuple(rules))



def lower_water_strategy_arbitration_control_plan(profile):
    """Lower Byzantine water/land strategic arbitration into native Goals."""
    from ..ast import SourceLocation
    from ..runtime_binding import GoalSlotRequest
    from ..semantic.analyzer import parse_expression
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
    from .model import GoalRole, SemanticId, StorageRequestId

    state_names = (
        "arb-c01",
        "arb-c02",
        "arb-c03",
        "arb-o01",
        "arb-o02",
        "arb-o03",
        "arb-o04",
        "arb-o05",
        "arb-o06",
        "arb-o07",
        "arb-o08",
        "arb-o09",
        "strategic-primary-intent",
    )
    states = tuple(
        NativeControlState(
            name,
            GoalSlotRequest(
                StorageRequestId(
                    SemanticId("byzantine-water-arbitration", name),
                    name,
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        )
        for name in state_names
    )

    water = profile.observation("strategy-water-map").expression
    pacific = profile.observation("strategy-pacific-islands").expression
    enemy_pressure = profile.observation("strategy-enemy-pressure").expression
    arena = profile.observation("strategy-arena-map").expression
    tc_capability = profile.observation("strategy-town-center-capability").expression
    tc_complete = profile.observation("strategy-town-center-complete").expression

    def expr(source: str):
        return parse_expression(source, SourceLocation(1))

    def rule(identity: str, facts: tuple[str, ...], actions: tuple[str, ...]):
        return NativeControlRule(
            identity,
            facts=tuple(expr(item) for item in facts),
            actions=tuple(expr(item) for item in actions),
        )

    return NativeControlPlan(
        states=states,
        rules=(
            rule(
                "strategic-arbitration-state-initialize",
                ("(goal strategic-primary-intent 0)",),
                (
                    "(set-goal arb-o01 0)",
                    "(set-goal arb-o02 0)",
                    "(set-goal arb-o03 0)",
                    "(set-goal arb-o04 0)",
                    "(set-goal arb-o05 0)",
                    "(set-goal arb-o06 0)",
                    "(set-goal arb-o07 0)",
                    "(set-goal arb-o08 0)",
                    "(set-goal arb-o09 0)",
                    "(set-goal arb-c01 0)",
                    "(set-goal arb-c02 0)",
                    "(set-goal arb-c03 0)",
                    "(disable-self)",
                ),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-water-islands",
                ("(goal arb-o01 0)", water),
                ("(set-goal arb-o01 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-water-islands",
                ("(goal arb-o01 1)", f"(not {water})"),
                ("(set-goal arb-o01 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-current-feudal-age",
                ("(goal arb-o02 0)", "(current-age >= feudal-age)"),
                ("(set-goal arb-o02 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-current-feudal-age",
                ("(goal arb-o02 1)", "(not (current-age >= feudal-age))"),
                ("(set-goal arb-o02 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-castle-complete",
                (
                    "(goal arb-o03 0)",
                    "(and (current-age >= castle-age) (building-type-count-total castle >= 1))",
                ),
                ("(set-goal arb-o03 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-castle-complete",
                (
                    "(goal arb-o03 1)",
                    "(not (and (current-age >= castle-age) (building-type-count-total castle >= 1)))",
                ),
                ("(set-goal arb-o03 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-current-imperial-age",
                ("(goal arb-o04 0)", "(current-age >= imperial-age)"),
                ("(set-goal arb-o04 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-current-imperial-age",
                ("(goal arb-o04 1)", "(not (current-age >= imperial-age))"),
                ("(set-goal arb-o04 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-enemy-pressure",
                ("(goal arb-o05 0)", enemy_pressure),
                ("(set-goal arb-o05 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-enemy-pressure",
                ("(goal arb-o05 1)", f"(not {enemy_pressure})"),
                ("(set-goal arb-o05 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-castle-age",
                ("(goal arb-o06 0)", "(current-age >= castle-age)"),
                ("(set-goal arb-o06 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-castle-age",
                ("(goal arb-o06 1)", "(not (current-age >= castle-age))"),
                ("(set-goal arb-o06 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-arena-map",
                ("(goal arb-o07 0)", arena),
                ("(set-goal arb-o07 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-arena-map",
                ("(goal arb-o07 1)", f"(not {arena})"),
                ("(set-goal arb-o07 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-town-center-capability",
                ("(goal arb-o08 0)", tc_capability),
                ("(set-goal arb-o08 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-town-center-capability",
                ("(goal arb-o08 1)", f"(not {tc_capability})"),
                ("(set-goal arb-o08 0)",),
            ),
            rule(
                "strategic-arbitration-observation-enable-strategy-town-center-complete",
                ("(goal arb-o09 0)", tc_complete),
                ("(set-goal arb-o09 1)",),
            ),
            rule(
                "strategic-arbitration-observation-disable-strategy-town-center-complete",
                ("(goal arb-o09 1)", f"(not {tc_complete})"),
                ("(set-goal arb-o09 0)",),
            ),
            rule(
                "strategic-arbitration-candidate-enable-water-investment",
                ("(goal arb-c01 0)", "(goal arb-o01 1)", f"(not {pacific})"),
                ("(set-goal arb-c01 1)",),
            ),
            rule(
                "strategic-arbitration-candidate-disable-water-investment",
                (
                    "(goal arb-c01 1)",
                    "(or (not (goal arb-o01 1)) " + pacific + ")",
                ),
                ("(set-goal arb-c01 0)",),
            ),
            rule(
                "strategic-arbitration-candidate-enable-castle-trajectory",
                (
                    "(goal arb-c02 0)",
                    "(and (and (and (goal arb-o02 1) (goal arb-o03 0)) (goal arb-o04 0)) "
                    f"(or (not (goal arb-o01 1)) {pacific}))",
                ),
                ("(set-goal arb-c02 1)",),
            ),
            rule(
                "strategic-arbitration-candidate-disable-castle-trajectory",
                (
                    "(goal arb-c02 1)",
                    "(not (and (and (and (goal arb-o02 1) (goal arb-o03 0)) (goal arb-o04 0)) "
                    f"(or (not (goal arb-o01 1)) {pacific})))",
                ),
                ("(set-goal arb-c02 0)",),
            ),
            rule(
                "strategic-arbitration-candidate-enable-two-tc-expansion",
                (
                    "(goal arb-c03 0)",
                    "(and (and (and (goal arb-o06 1) (goal arb-o08 1)) (goal arb-o03 1)) "
                    f"(or (not (goal arb-o01 1)) {pacific}))",
                ),
                ("(set-goal arb-c03 1)",),
            ),
            rule(
                "strategic-arbitration-candidate-disable-two-tc-expansion",
                (
                    "(goal arb-c03 1)",
                    "(not (and (and (and (goal arb-o06 1) (goal arb-o08 1)) (goal arb-o03 1)) "
                    f"(or (not (goal arb-o01 1)) {pacific})))",
                ),
                ("(set-goal arb-c03 0)",),
            ),
            rule(
                "strategic-primary-intent-select-water-investment-from-0",
                ("(goal strategic-primary-intent 0)", "(goal arb-c01 1)"),
                ("(set-goal strategic-primary-intent 1)",),
            ),
            rule(
                "strategic-primary-intent-select-castle-trajectory-from-0",
                ("(goal strategic-primary-intent 0)", "(goal arb-c02 1)", "(not (goal arb-c01 1))"),
                ("(set-goal strategic-primary-intent 2)",),
            ),
            rule(
                "strategic-primary-intent-select-two-tc-expansion-from-0",
                ("(goal strategic-primary-intent 0)", "(goal arb-c03 1)", "(not (goal arb-c01 1))", "(not (goal arb-c02 1))"),
                ("(set-goal strategic-primary-intent 3)",),
            ),
            rule(
                "strategic-primary-intent-select-two-tc-expansion-from-2",
                ("(goal strategic-primary-intent 2)", "(goal arb-c03 1)"),
                ("(set-goal strategic-primary-intent 3)",),
            ),
            rule(
                "strategic-primary-intent-release-castle-trajectory",
                ("(goal strategic-primary-intent 2)", "(goal arb-o03 1)", "(not (goal arb-c03 1))"),
                ("(set-goal strategic-primary-intent 0)",),
            ),
            rule(
                "strategic-primary-intent-invalidate-castle-trajectory",
                ("(goal strategic-primary-intent 2)", "(goal arb-o04 1)"),
                ("(set-goal strategic-primary-intent 0)",),
            ),
        ),
    )


__all__ = [
    "TransportExecutionPhase",
    "WaterExecutionPlan",
    "WaterExecutionState",
    "WaterPosture",
    "derive_water_posture",
    "lower_water_execution_plan",
    "lower_water_strategy_arbitration_control_plan",
    "transition_transport_execution",
]
