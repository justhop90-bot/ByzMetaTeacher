from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Mapping


class ImperialBand(IntEnum):
    STANDING_FLOOR = 0
    OPEN_FIELD = 1
    FORTIFIED_PUSH = 2
    GOLD_STARVED_TRASH = 3


class ImperialReason(IntEnum):
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
class ImperialResolverInput:
    current: ImperialBand
    halberdiers: int
    elite_skirmishers: int
    hussars: int
    food: int
    wood: int
    gold: int
    siege: int
    offensive_objective: bool
    fortification_threat: bool
    siege_approach: str
    enemy_field_army: int
    fortified_objective_requires_siege: bool


@dataclass(frozen=True)
class ImperialDecision:
    destination: ImperialBand
    reason: ImperialReason


class ImperialResolver:
    FLOOR_HALBERDIER = 18
    FLOOR_ELITE_SKIRMISHER = 18
    FLOOR_HUSSAR = 12

    OPEN_FOOD_IN = 2400
    OPEN_WOOD_IN = 2000
    OPEN_GOLD_IN = 2000
    OPEN_FOOD_OUT = 1800
    OPEN_WOOD_OUT = 1500

    FORT_FOOD_IN = 2400
    FORT_WOOD_IN = 2400
    FORT_GOLD_IN = 2600
    FORT_SIEGE_MIN = 2

    TRASH_FOOD_IN = 2400
    TRASH_WOOD_IN = 2200
    TRASH_GOLD_IN = 800
    TRASH_GOLD_OUT = 1800

    FLOOR_RECOVERY_DWELL = 30
    OPEN_ENTRY_DWELL = 20
    OPEN_MIN_DWELL = 60
    FORT_ENTRY_DWELL = 15
    FORT_MIN_DWELL = 45
    FORT_CLEAR_DWELL = 20
    TRASH_ENTRY_DWELL = 30
    TRASH_MIN_DWELL = 90
    GOLD_RECOVERY_DWELL = 30
    ECONOMIC_COLLAPSE_DWELL = 30

    REARM_SECONDS: Mapping[ImperialBand, int] = {
        ImperialBand.OPEN_FIELD: 30,
        ImperialBand.FORTIFIED_PUSH: 30,
        ImperialBand.GOLD_STARVED_TRASH: 45,
    }

    @classmethod
    def floor_broken(cls, value: ImperialResolverInput) -> bool:
        return (
            value.halberdiers < cls.FLOOR_HALBERDIER
            or value.elite_skirmishers < cls.FLOOR_ELITE_SKIRMISHER
            or value.hussars < cls.FLOOR_HUSSAR
        )

    @classmethod
    def floor_recovered(cls, value: ImperialResolverInput) -> bool:
        return not cls.floor_broken(value)

    @classmethod
    def fortified_executable(cls, value: ImperialResolverInput) -> bool:
        return (
            value.fortification_threat
            and value.siege_approach == "fortified"
            and value.offensive_objective
            and value.siege >= cls.FORT_SIEGE_MIN
            and value.food >= cls.FORT_FOOD_IN
            and value.wood >= cls.FORT_WOOD_IN
            and value.gold >= cls.FORT_GOLD_IN
        )

    @classmethod
    def open_field_eligible(cls, value: ImperialResolverInput) -> bool:
        return (
            cls.floor_recovered(value)
            and value.offensive_objective
            and not value.fortification_threat
            and not value.fortified_objective_requires_siege
            and value.enemy_field_army >= 12
            and value.food >= cls.OPEN_FOOD_IN
            and value.wood >= cls.OPEN_WOOD_IN
            and value.gold >= cls.OPEN_GOLD_IN
        )

    @classmethod
    def gold_recovery_open_eligible(cls, value: ImperialResolverInput) -> bool:
        """Allow the agreed 1800-gold Trash->Open recovery band."""
        return (
            cls.floor_recovered(value)
            and value.offensive_objective
            and not value.fortification_threat
            and not value.fortified_objective_requires_siege
            and value.enemy_field_army >= 12
            and value.food >= cls.OPEN_FOOD_IN
            and value.wood >= cls.OPEN_WOOD_IN
            and value.gold >= cls.TRASH_GOLD_OUT
        )

    @classmethod
    def gold_starved_eligible(cls, value: ImperialResolverInput) -> bool:
        return (
            cls.floor_recovered(value)
            and value.gold <= cls.TRASH_GOLD_IN
            and value.food >= cls.TRASH_FOOD_IN
            and value.wood >= cls.TRASH_WOOD_IN
            and not value.fortification_threat
            and not cls.fortified_executable(value)
        )

    @classmethod
    def _economic_collapse(cls, value: ImperialResolverInput) -> bool:
        return value.food < cls.OPEN_FOOD_OUT or value.wood < cls.OPEN_WOOD_OUT

    @classmethod
    def _cooldown_active(
        cls,
        band: ImperialBand,
        *,
        rearm_seconds: int,
        rearm_band: ImperialBand | None,
    ) -> bool:
        return (
            rearm_band is band
            and rearm_seconds < cls.REARM_SECONDS[band]
        )

    @classmethod
    def resolve(
        cls,
        value: ImperialResolverInput,
        *,
        dwell_seconds: int,
        guard_seconds: int,
        rearm_seconds: int,
        rearm_band: ImperialBand | None = None,
    ) -> ImperialDecision:
        current = value.current

        # P0: the standing military floor is a hard invariant.
        if cls.floor_broken(value):
            return ImperialDecision(
                ImperialBand.STANDING_FLOOR,
                ImperialReason.FLOOR_BREAK,
            )

        # P1: a complete fortified package outranks ordinary posture changes.
        if cls.fortified_executable(value) and current is not ImperialBand.FORTIFIED_PUSH:
            if (
                guard_seconds >= cls.FORT_ENTRY_DWELL
                and not cls._cooldown_active(
                    ImperialBand.FORTIFIED_PUSH,
                    rearm_seconds=rearm_seconds,
                    rearm_band=rearm_band,
                )
                and (
                    current is not ImperialBand.STANDING_FLOOR
                    or dwell_seconds >= cls.FLOOR_RECOVERY_DWELL
                )
            ):
                return ImperialDecision(
                    ImperialBand.FORTIFIED_PUSH,
                    ImperialReason.FORTIFIED_ESCALATION,
                )

        # P2: persistent economic collapse forces recovery after its dwell.
        if cls._economic_collapse(value):
            if dwell_seconds >= cls.ECONOMIC_COLLAPSE_DWELL:
                return ImperialDecision(
                    ImperialBand.STANDING_FLOOR,
                    ImperialReason.ECONOMIC_COLLAPSE,
                )
            return ImperialDecision(
                current,
                ImperialReason.HOLD_DWELL,
            )

        if current is ImperialBand.STANDING_FLOOR:
            if dwell_seconds < cls.FLOOR_RECOVERY_DWELL:
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)
            if not cls.floor_recovered(value):
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            if cls.fortified_executable(value):
                if guard_seconds >= cls.FORT_ENTRY_DWELL and not cls._cooldown_active(
                    ImperialBand.FORTIFIED_PUSH,
                    rearm_seconds=rearm_seconds,
                    rearm_band=rearm_band,
                ):
                    return ImperialDecision(
                        ImperialBand.FORTIFIED_PUSH,
                        ImperialReason.FORTIFIED_ESCALATION,
                    )
                return ImperialDecision(current, ImperialReason.HOLD_COOLDOWN)

            if cls.gold_starved_eligible(value):
                if (
                    guard_seconds >= cls.TRASH_ENTRY_DWELL
                    and not cls._cooldown_active(
                        ImperialBand.GOLD_STARVED_TRASH,
                        rearm_seconds=rearm_seconds,
                        rearm_band=rearm_band,
                    )
                ):
                    return ImperialDecision(
                        ImperialBand.GOLD_STARVED_TRASH,
                        ImperialReason.GOLD_STARVED,
                    )
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            if cls.open_field_eligible(value):
                if (
                    guard_seconds >= cls.OPEN_ENTRY_DWELL
                    and not cls._cooldown_active(
                        ImperialBand.OPEN_FIELD,
                        rearm_seconds=rearm_seconds,
                        rearm_band=rearm_band,
                    )
                ):
                    return ImperialDecision(
                        ImperialBand.OPEN_FIELD,
                        ImperialReason.OPEN_FIELD_ELIGIBLE,
                    )
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            return ImperialDecision(current, ImperialReason.HOLD_DWELL)

        if current is ImperialBand.OPEN_FIELD:
            if dwell_seconds < cls.OPEN_MIN_DWELL:
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            if cls.gold_starved_eligible(value):
                if (
                    guard_seconds >= cls.TRASH_ENTRY_DWELL
                    and not cls._cooldown_active(
                        ImperialBand.GOLD_STARVED_TRASH,
                        rearm_seconds=rearm_seconds,
                        rearm_band=rearm_band,
                    )
                ):
                    return ImperialDecision(
                        ImperialBand.GOLD_STARVED_TRASH,
                        ImperialReason.GOLD_STARVED,
                    )
                return ImperialDecision(current, ImperialReason.HOLD_COOLDOWN)

            return ImperialDecision(current, ImperialReason.OPEN_FIELD_ELIGIBLE)

        if current is ImperialBand.FORTIFIED_PUSH:
            if cls.fortified_executable(value):
                return ImperialDecision(
                    current,
                    ImperialReason.NONE,
                )
            if dwell_seconds < cls.FORT_MIN_DWELL:
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            if (
                not value.fortification_threat
                and not value.fortified_objective_requires_siege
                and guard_seconds >= cls.FORT_CLEAR_DWELL
            ):
                if cls.open_field_eligible(value):
                    return ImperialDecision(
                        ImperialBand.OPEN_FIELD,
                        ImperialReason.FORTIFIED_CLEAR,
                    )
                if cls.gold_starved_eligible(value):
                    return ImperialDecision(
                        ImperialBand.GOLD_STARVED_TRASH,
                        ImperialReason.FORTIFIED_CLEAR,
                    )
                if not cls._cooldown_active(
                    ImperialBand.STANDING_FLOOR,
                    rearm_seconds=rearm_seconds,
                    rearm_band=rearm_band,
                ):
                    return ImperialDecision(
                        ImperialBand.STANDING_FLOOR,
                        ImperialReason.OBJECTIVE_LOST,
                    )

            return ImperialDecision(current, ImperialReason.HOLD_DWELL)

        if current is ImperialBand.GOLD_STARVED_TRASH:
            if cls.fortified_executable(value):
                if (
                    guard_seconds >= cls.FORT_ENTRY_DWELL
                    and not cls._cooldown_active(
                        ImperialBand.FORTIFIED_PUSH,
                        rearm_seconds=rearm_seconds,
                        rearm_band=rearm_band,
                    )
                ):
                    return ImperialDecision(
                        ImperialBand.FORTIFIED_PUSH,
                        ImperialReason.FORTIFIED_ESCALATION,
                    )
                return ImperialDecision(current, ImperialReason.HOLD_COOLDOWN)

            if dwell_seconds < cls.TRASH_MIN_DWELL:
                return ImperialDecision(current, ImperialReason.HOLD_DWELL)

            if (
                value.gold >= cls.TRASH_GOLD_OUT
                and cls.gold_recovery_open_eligible(value)
                and guard_seconds >= cls.GOLD_RECOVERY_DWELL
                and not cls._cooldown_active(
                    ImperialBand.OPEN_FIELD,
                    rearm_seconds=rearm_seconds,
                    rearm_band=rearm_band,
                )
            ):
                return ImperialDecision(
                    ImperialBand.OPEN_FIELD,
                    ImperialReason.GOLD_RECOVERY,
                )

            return ImperialDecision(current, ImperialReason.GOLD_STARVED)

        return ImperialDecision(current, ImperialReason.NONE)


__all__ = [
    "ImperialBand",
    "ImperialDecision",
    "ImperialReason",
    "ImperialResolver",
    "ImperialResolverInput",
]
