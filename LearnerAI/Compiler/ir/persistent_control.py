"""Typed compiler-owned persistent-control projections.

This module defines semantic identity and lifetime policy for persistent native
control state. It deliberately does not model runtime timer expiry.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .model import SemanticId


class PersistentControlKind(str, Enum):
    TIMER = "TIMER"
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"


class PersistentControlLifetime(str, Enum):
    UNTIL_OWNER_RELEASE = "UNTIL_OWNER_RELEASE"
    RECURRENT = "RECURRENT"
    UNKNOWN = "UNKNOWN"


class CleanupStatus(str, Enum):
    REQUIRED = "REQUIRED"
    SATISFIED = "SATISFIED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, order=True)
class PersistentControlId:
    source_unit: str
    local_name: str

    def __post_init__(self) -> None:
        if not self.source_unit.strip():
            raise ValueError("persistent-control source_unit must not be empty")
        if not self.local_name.strip():
            raise ValueError("persistent-control local_name must not be empty")


@dataclass(frozen=True)
class PersistentControlRef:
    id: PersistentControlId
    kind: PersistentControlKind
    owner: SemanticId
    lifetime: PersistentControlLifetime = PersistentControlLifetime.UNTIL_OWNER_RELEASE
    native_binding: int | None = None

    def __post_init__(self) -> None:
        if self.kind is PersistentControlKind.TIMER and self.native_binding is not None:
            if not 1 <= self.native_binding <= 50:
                raise ValueError("timer native binding must be in range 1..50")


@dataclass(frozen=True)
class PersistentControlCleanupObligation:
    control: PersistentControlId
    owner: SemanticId
    release_contract: SemanticId
    status: CleanupStatus
    cleanup_commands: tuple[str, ...] = ()
    release_rule_order: int | None = None
    cleanup_rule_orders: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if len(self.cleanup_commands) != len(set(self.cleanup_commands)):
            raise ValueError("cleanup commands must be unique")
        if any(not command.strip() for command in self.cleanup_commands):
            raise ValueError("cleanup commands must not be empty")


__all__ = [
    "CleanupStatus",
    "PersistentControlCleanupObligation",
    "PersistentControlId",
    "PersistentControlKind",
    "PersistentControlLifetime",
    "PersistentControlRef",
]
