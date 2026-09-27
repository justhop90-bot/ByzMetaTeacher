"""Minimum recurrent timer state and generation semantics.

This module intentionally models timer lifetime without simulating the AoE2
engine clock. The pass scheduler owns elapsed-time advancement and pending
expiry delivery.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class TimerStatus(str, Enum):
    DISABLED = "DISABLED"
    RUNNING = "RUNNING"
    TRIGGERED = "TRIGGERED"


class TimerReadKind(str, Enum):
    STATUS = "STATUS"
    TRIGGERED = "TRIGGERED"


@dataclass(frozen=True)
class PendingTimerExpiry:
    timer_id: str
    generation: int
    deadline: float


@dataclass(frozen=True)
class TimerRuntimeState:
    timer_id: str
    initialized: bool
    generation: int
    status: TimerStatus
    deadline: float | None
    trigger_generation: int | None

    def enable(self, duration_seconds: int | float, now_seconds: float) -> "TimerRuntimeState":
        if not self.initialized:
            raise ValueError(f"timer '{self.timer_id}' is not initialized")
        if duration_seconds < 0:
            raise ValueError("timer duration must be non-negative")
        generation = self.generation + 1
        return replace(
            self,
            generation=generation,
            status=TimerStatus.RUNNING,
            deadline=now_seconds + float(duration_seconds),
            trigger_generation=None,
        )

    def disable(self) -> "TimerRuntimeState":
        if not self.initialized:
            raise ValueError(f"timer '{self.timer_id}' is not initialized")
        return replace(
            self,
            generation=self.generation + 1,
            status=TimerStatus.DISABLED,
            deadline=None,
            trigger_generation=None,
        )

    def reset(self) -> "TimerRuntimeState":
        return self.disable()

    def stage_expiry(self, now_seconds: float) -> PendingTimerExpiry:
        if self.status is not TimerStatus.RUNNING or self.deadline is None:
            raise ValueError(
                f"timer '{self.timer_id}' is not running and cannot stage expiry"
            )
        if now_seconds < self.deadline:
            raise ValueError(
                f"timer '{self.timer_id}' has not reached its deadline"
            )
        return PendingTimerExpiry(
            timer_id=self.timer_id,
            generation=self.generation,
            deadline=self.deadline,
        )

    def can_commit_pending_expiry(self, pending: PendingTimerExpiry) -> bool:
        return (
            self.initialized
            and self.timer_id == pending.timer_id
            and self.generation == pending.generation
            and self.status is TimerStatus.RUNNING
            and self.deadline is not None
            and self.deadline == pending.deadline
        )

    def commit_expiry(self) -> "TimerRuntimeState":
        if self.status is not TimerStatus.RUNNING or self.deadline is None:
            raise ValueError(
                f"timer '{self.timer_id}' is not running and cannot trigger"
            )
        return replace(
            self,
            status=TimerStatus.TRIGGERED,
            trigger_generation=self.generation,
        )


def create_initialized_timer(timer_id: str) -> TimerRuntimeState:
    if not isinstance(timer_id, str) or not timer_id:
        raise ValueError("timer_id must be a non-empty string")
    return TimerRuntimeState(
        timer_id=timer_id,
        initialized=True,
        generation=0,
        status=TimerStatus.DISABLED,
        deadline=None,
        trigger_generation=None,
    )


def read_timer_triggered(timer: TimerRuntimeState) -> bool:
    return (
        timer.status is TimerStatus.TRIGGERED
        and timer.trigger_generation == timer.generation
    )


__all__ = [
    "PendingTimerExpiry",
    "TimerReadKind",
    "TimerRuntimeState",
    "TimerStatus",
    "create_initialized_timer",
    "read_timer_triggered",
]
