"""Typed construction lifecycle observation IR."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression
from .model import LifecycleState


class ConstructionPhase(str, Enum):
    NONE = "NONE"
    PLACEMENT_PENDING = "PLACEMENT_PENDING"
    FOUNDATION_PENDING = "FOUNDATION_PENDING"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True)
class ConstructionObservation:
    completed: bool = False
    foundation_pending: bool = False
    placement_pending: bool = False
    invalidated: bool = False


@dataclass(frozen=True)
class ConstructionState:
    lifecycle: LifecycleState
    phase: ConstructionPhase


@dataclass(frozen=True)
class ConstructionLifecycle:
    building: str
    completion_witness: Expression
    pending_foundation_fact: Expression
    pending_placement_fact: Expression


__all__ = [
    "ConstructionLifecycle",
    "ConstructionObservation",
    "ConstructionPhase",
    "ConstructionState",
]
