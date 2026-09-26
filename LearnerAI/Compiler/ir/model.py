"""Validated semantic intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression
from ..runtime_binding import GoalRole, GoalSlotRequest, SemanticId


class LifecycleState(str, Enum):
    RELEASED = "RELEASED"
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class SemanticRequirement:
    expression: Expression
    role: str


@dataclass(frozen=True)
class SemanticAction:
    expression: Expression
    role: str


@dataclass(frozen=True)
class PendingDiagnostic:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class LifecycleStorage:
    slot: GoalSlotRequest
    initial_state: LifecycleState = LifecycleState.ACTIVE


@dataclass(frozen=True)
class SemanticDemand:
    identity: SemanticId
    lifecycle: LifecycleStorage
    requirements: tuple[SemanticRequirement, ...]
    action: SemanticAction
    witness: Expression
    release: Expression
    pending_diagnostics: tuple[PendingDiagnostic, ...] = ()

    @property
    def name(self) -> str:
        return self.identity.local_name
