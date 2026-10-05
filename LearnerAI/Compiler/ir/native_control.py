"""Typed native persistent-control-plane IR.

This is not a second source language.  It is an in-memory description of native
.per Facts/Actions plus explicit typed storage requests that are lowered to the
same native syntax used by community AIs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..ast import Expression, SourceLocation
from .model import GoalRole, StorageRequestId

if TYPE_CHECKING:
    from ..runtime_binding import StorageRequest


@dataclass(frozen=True)
class NativeControlState:
    """A symbolic native Goal/SN/Timer slot backed by the normal binder."""

    identifier: str
    request: "StorageRequest"
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identifier:
            raise ValueError("native control state identifier must not be empty")
        if not isinstance(self.identifier, str):
            raise TypeError("native control state identifier must be a string")


@dataclass(frozen=True)
class NativeControlRule:
    """One native defrule body in effective declaration order."""

    identity: str
    facts: tuple[Expression, ...]
    actions: tuple[Expression, ...]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("native control rule identity must not be empty")
        if not self.facts:
            raise ValueError(
                f"native control rule '{self.identity}' requires at least one fact"
            )
        if not isinstance(self.facts, tuple) or not isinstance(self.actions, tuple):
            raise TypeError("native control rule facts/actions must be tuples")


@dataclass(frozen=True)
class NativeControlPlan:
    """Typed collection of native persistent-control state, constants, and rules."""

    states: tuple[NativeControlState, ...] = ()
    rules: tuple[NativeControlRule, ...] = ()
    constants: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        names = tuple(name for name, _value in self.constants)
        if len(names) != len(set(names)):
            raise ValueError("native control constants must have unique identifiers")
        for name, value in self.constants:
            if not isinstance(name, str) or not name:
                raise ValueError("native control constant name must be a non-empty string")
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("native control constant value must be an integer")

    def state(self, identifier: str) -> NativeControlState:
        for state in self.states:
            if state.identifier == identifier:
                return state
        raise KeyError(identifier)

    @property
    def storage_requests(self) -> tuple["StorageRequest", ...]:
        return tuple(state.request for state in self.states)


__all__ = [
    "NativeControlPlan",
    "NativeControlRule",
    "NativeControlState",
]
