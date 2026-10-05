"""Typed Byzantine Imperial military band policy and pure resolver."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ImperialMilitaryBand(IntEnum):
    STANDING_FLOOR = 0
    OPEN_FIELD = 1
    FORTIFIED_PUSH = 2
    GOLD_STARVED_TRASH = 3


class ImperialMilitaryReason(IntEnum):
    NONE = 0
    FLOOR_BREAK = 10
    FORTIFIED_ESCALATION = 20
    ECONOMIC_COLLAPSE = 30
    GOLD_STARVED = 40
    GOLD_RECOVERY = 50
    OPEN_FIELD_ELIGIBLE = 60
    FORTIFIED_CLEAR = 70
    OBJECTIVE_LOST = 80
    HOLD_DWELL = 90
    HOLD_COOLDOWN = 91


@dataclass(frozen=True)
class ImperialMilitaryPlan:
    floor: tuple[int, int, int] = (18, 18, 12)
    floor_recovery_resources: tuple[int, int, int] = (2000, 1700, 1600)
    open_entry_resources: tuple[int, int, int] = (2400, 2000, 2000)
    open_exit_resources: tuple[int, int] = (1800, 1500)
    fortified_resources: tuple[int, int, int] = (2400, 2400, 2600)
    trash_resource_floor: tuple[int, int] = (2400, 2200)
    trash_entry_gold: int = 800
    trash_exit_gold: int = 1800
    siege_entry_floor: int = 2
    minimum_dwell: dict[ImperialMilitaryBand, int] = field(
        default_factory=lambda: {
            ImperialMilitaryBand.STANDING_FLOOR: 30,
            ImperialMilitaryBand.OPEN_FIELD: 60,
            ImperialMilitaryBand.FORTIFIED_PUSH: 45,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 90,
        }
    )
    guard_dwell: dict[ImperialMilitaryBand, int] = field(
        default_factory=lambda: {
            ImperialMilitaryBand.OPEN_FIELD: 20,
            ImperialMilitaryBand.FORTIFIED_PUSH: 15,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 30,
        }
    )
    rearm: dict[ImperialMilitaryBand, int] = field(
        default_factory=lambda: {
            ImperialMilitaryBand.OPEN_FIELD: 30,
            ImperialMilitaryBand.FORTIFIED_PUSH: 30,
            ImperialMilitaryBand.GOLD_STARVED_TRASH: 45,
        }
    )
    economic_collapse_dwell: int = 30
    fortified_clear_dwell: int = 20
    gold_recovery_dwell: int = 30

    def __post_init__(self) -> None:
        if self.floor != (18, 18, 12):
            raise ValueError("Imperial military floor must remain 18/18/12")
        if self.open_entry_resources != (2400, 2000, 2000):
            raise ValueError("open-field entry resources are fixed at 2400/2000/2000")
        if self.fortified_resources != (2400, 2400, 2600):
            raise ValueError("fortified resources are fixed at 2400/2400/2600")
        if self.trash_entry_gold != 800 or self.trash_exit_gold != 1800:
            raise ValueError("trash-war gold hysteresis must remain 800/1800")
        if self.siege_entry_floor != 2:
            raise ValueError("fortified siege entry floor must remain 2")

    @property
    def floor_recovery_ready(self):
        return (
            lambda halberdiers, elite_skirmishers, hussars, food, wood, gold:
            halberdiers >= self.floor[0]
            and elite_skirmishers >= self.floor[1]
            and hussars >= self.floor[2]
            and food >= self.floor_recovery_resources[0]
            and wood >= self.floor_recovery_resources[1]
            and gold >= self.floor_recovery_resources[2]
        )


@dataclass(frozen=True)
class ImperialMilitaryInput:
    current: ImperialMilitaryBand
    halberdiers: int
    elite_skirmishers: int
    hussars: int
    food: int
    wood: int
    gold: int
    siege: int
    objective_claimed: bool
    fortification_threat: bool
    siege_approach_fortified: bool
    fortified_guard_seconds: int = 0
    trash_guard_seconds: int = 0
    open_guard_seconds: int = 0
    economic_collapse_seconds: int = 0
    fortified_clear_seconds: int = 0
    gold_recovery_seconds: int = 0
    dwell_seconds: int = 0
    candidate_band: ImperialMilitaryBand | None = None
    guard_seconds: int = 0
    rearm_band: ImperialMilitaryBand | None = None
    rearm_seconds: int = 0

    def floor_broken(self, plan: ImperialMilitaryPlan) -> bool:
        return (
            self.halberdiers < plan.floor[0]
            or self.elite_skirmishers < plan.floor[1]
            or self.hussars < plan.floor[2]
        )

    def floor_recovered(self, plan: ImperialMilitaryPlan) -> bool:
        return bool(
            plan.floor_recovery_ready(
                self.halberdiers,
                self.elite_skirmishers,
                self.hussars,
                self.food,
                self.wood,
                self.gold,
            )
        )

    def fortified_executable(self, plan: ImperialMilitaryPlan) -> bool:
        return (
            self.fortification_threat
            and self.siege_approach_fortified
            and self.objective_claimed
            and self.siege >= plan.siege_entry_floor
            and self.food >= plan.fortified_resources[0]
            and self.wood >= plan.fortified_resources[1]
            and self.gold >= plan.fortified_resources[2]
        )

    def open_eligible(self, plan: ImperialMilitaryPlan) -> bool:
        return (
            self.floor_recovered(plan)
            and self.objective_claimed
            and not self.fortification_threat
            and self.food >= plan.open_entry_resources[0]
            and self.wood >= plan.open_entry_resources[1]
            and self.gold >= plan.open_entry_resources[2]
        )

    def trash_eligible(self, plan: ImperialMilitaryPlan) -> bool:
        return (
            self.floor_recovered(plan)
            and self.gold <= plan.trash_entry_gold
            and self.food >= plan.trash_resource_floor[0]
            and self.wood >= plan.trash_resource_floor[1]
            and not self.fortification_threat
        )


@dataclass(frozen=True)
class ImperialMilitaryDecision:
    destination: ImperialMilitaryBand
    reason: ImperialMilitaryReason
    candidate: ImperialMilitaryBand | None = None
    guard_dwell_seconds: int = 0
    cooldown_blocked: bool = False


def _candidate_ready(
    state: ImperialMilitaryInput,
    destination: ImperialMilitaryBand,
    required_guard: int,
    *,
    allow_rearm: bool = False,
) -> bool:
    if state.candidate_band is not destination:
        return False
    if state.guard_seconds < required_guard:
        return False
    if (
        not allow_rearm
        and state.rearm_band is destination
        and state.rearm_seconds < default_imperial_military_plan().rearm[destination]
    ):
        return False
    return True


def _cooldown_blocks(
    state: ImperialMilitaryInput,
    destination: ImperialMilitaryBand,
    plan: ImperialMilitaryPlan,
) -> bool:
    return (
        state.rearm_band is destination
        and state.rearm_seconds < plan.rearm[destination]
    )


def resolve_imperial_military(
    state: ImperialMilitaryInput,
    plan: ImperialMilitaryPlan | None = None,
) -> ImperialMilitaryDecision:
    plan = plan or default_imperial_military_plan()

    # P0: floor break is absolute.
    if state.floor_broken(plan):
        return ImperialMilitaryDecision(
            ImperialMilitaryBand.STANDING_FLOOR,
            ImperialMilitaryReason.FLOOR_BREAK,
        )

    # P1: executable fortified escalation.
    if state.fortified_executable(plan) and state.current is not ImperialMilitaryBand.FORTIFIED_PUSH:
        required = plan.guard_dwell[ImperialMilitaryBand.FORTIFIED_PUSH]
        if (
            state.candidate_band is ImperialMilitaryBand.FORTIFIED_PUSH
            and state.guard_seconds >= required
            and not _cooldown_blocks(state, ImperialMilitaryBand.FORTIFIED_PUSH, plan)
        ):
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.FORTIFIED_PUSH,
                ImperialMilitaryReason.FORTIFIED_ESCALATION,
            )
        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.HOLD_COOLDOWN
            if _cooldown_blocks(state, ImperialMilitaryBand.FORTIFIED_PUSH, plan)
            else ImperialMilitaryReason.HOLD_DWELL,
            candidate=ImperialMilitaryBand.FORTIFIED_PUSH,
            guard_dwell_seconds=required,
            cooldown_blocked=_cooldown_blocks(
                state, ImperialMilitaryBand.FORTIFIED_PUSH, plan
            ),
        )

    # P2: persistent economic collapse can force floor recovery after its dwell.
    economic_collapse = state.food < plan.open_exit_resources[0] or state.wood < plan.open_exit_resources[1]
    if economic_collapse and state.current is not ImperialMilitaryBand.STANDING_FLOOR:
        if state.economic_collapse_seconds >= plan.economic_collapse_dwell:
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.STANDING_FLOOR,
                ImperialMilitaryReason.ECONOMIC_COLLAPSE,
            )
        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.HOLD_DWELL,
            candidate=ImperialMilitaryBand.STANDING_FLOOR,
            guard_dwell_seconds=plan.economic_collapse_dwell,
        )

    # Standing-floor recovery must be fully recovered before ordinary scaling.
    if state.current is ImperialMilitaryBand.STANDING_FLOOR:
        if not state.floor_recovered(plan):
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.STANDING_FLOOR,
                ImperialMilitaryReason.NONE,
            )
        if state.dwell_seconds < plan.minimum_dwell[ImperialMilitaryBand.STANDING_FLOOR]:
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.STANDING_FLOOR,
                ImperialMilitaryReason.HOLD_DWELL,
            )

        if state.trash_eligible(plan):
            required = plan.guard_dwell[ImperialMilitaryBand.GOLD_STARVED_TRASH]
            if (
                state.candidate_band is ImperialMilitaryBand.GOLD_STARVED_TRASH
                and state.guard_seconds >= required
                and not _cooldown_blocks(state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan)
            ):
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    ImperialMilitaryReason.GOLD_STARVED,
                )
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.STANDING_FLOOR,
                ImperialMilitaryReason.HOLD_COOLDOWN
                if _cooldown_blocks(state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan)
                else ImperialMilitaryReason.HOLD_DWELL,
                candidate=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                guard_dwell_seconds=required,
                cooldown_blocked=_cooldown_blocks(
                    state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan
                ),
            )

        if state.open_eligible(plan):
            required = plan.guard_dwell[ImperialMilitaryBand.OPEN_FIELD]
            if (
                state.candidate_band is ImperialMilitaryBand.OPEN_FIELD
                and state.guard_seconds >= required
                and not _cooldown_blocks(state, ImperialMilitaryBand.OPEN_FIELD, plan)
            ):
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.OPEN_FIELD,
                    ImperialMilitaryReason.OPEN_FIELD_ELIGIBLE,
                )
            return ImperialMilitaryDecision(
                ImperialMilitaryBand.STANDING_FLOOR,
                ImperialMilitaryReason.HOLD_COOLDOWN
                if _cooldown_blocks(state, ImperialMilitaryBand.OPEN_FIELD, plan)
                else ImperialMilitaryReason.HOLD_DWELL,
                candidate=ImperialMilitaryBand.OPEN_FIELD,
                guard_dwell_seconds=required,
                cooldown_blocked=_cooldown_blocks(
                    state, ImperialMilitaryBand.OPEN_FIELD, plan
                ),
            )

        return ImperialMilitaryDecision(
            ImperialMilitaryBand.STANDING_FLOOR,
            ImperialMilitaryReason.NONE,
        )

    # P3: minimum dwell for scaling bands.
    if state.dwell_seconds < plan.minimum_dwell[state.current]:
        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.HOLD_DWELL,
        )

    if state.current is ImperialMilitaryBand.OPEN_FIELD:
        if state.trash_eligible(plan):
            required = plan.guard_dwell[ImperialMilitaryBand.GOLD_STARVED_TRASH]
            if (
                state.candidate_band is ImperialMilitaryBand.GOLD_STARVED_TRASH
                and state.guard_seconds >= required
                and not _cooldown_blocks(state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan)
            ):
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    ImperialMilitaryReason.GOLD_STARVED,
                )
            return ImperialMilitaryDecision(
                state.current,
                ImperialMilitaryReason.HOLD_COOLDOWN
                if _cooldown_blocks(state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan)
                else ImperialMilitaryReason.HOLD_DWELL,
                candidate=ImperialMilitaryBand.GOLD_STARVED_TRASH,
                guard_dwell_seconds=required,
                cooldown_blocked=_cooldown_blocks(
                    state, ImperialMilitaryBand.GOLD_STARVED_TRASH, plan
                ),
            )

        if state.open_eligible(plan):
            return ImperialMilitaryDecision(
                state.current,
                ImperialMilitaryReason.NONE,
            )

        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.OBJECTIVE_LOST,
        )

    if state.current is ImperialMilitaryBand.FORTIFIED_PUSH:
        fortification_cleared = not state.fortification_threat
        if fortification_cleared and state.fortified_clear_seconds >= plan.fortified_clear_dwell:
            if state.open_eligible(plan):
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.OPEN_FIELD,
                    ImperialMilitaryReason.FORTIFIED_CLEAR,
                )
            if state.trash_eligible(plan):
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.GOLD_STARVED_TRASH,
                    ImperialMilitaryReason.FORTIFIED_CLEAR,
                )
        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.NONE,
        )

    if state.current is ImperialMilitaryBand.GOLD_STARVED_TRASH:
        if state.gold >= plan.trash_exit_gold and state.open_eligible(plan):
            if state.gold_recovery_seconds >= plan.gold_recovery_dwell:
                return ImperialMilitaryDecision(
                    ImperialMilitaryBand.OPEN_FIELD,
                    ImperialMilitaryReason.GOLD_RECOVERY,
                )
            return ImperialMilitaryDecision(
                state.current,
                ImperialMilitaryReason.HOLD_DWELL,
                candidate=ImperialMilitaryBand.OPEN_FIELD,
                guard_dwell_seconds=plan.gold_recovery_dwell,
            )
        return ImperialMilitaryDecision(
            state.current,
            ImperialMilitaryReason.NONE,
        )

    raise ValueError(f"unsupported Imperial military band {state.current!r}")


def default_imperial_military_plan() -> ImperialMilitaryPlan:
    return ImperialMilitaryPlan()
