"""Typed internal IR for the minimal native attack lifecycle slice.

This IR represents a controller-owned attack issuance boundary. It is not source
syntax and it does not claim native completion or release semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation


class AttackLifecycleObservation(str, Enum):
    ADMISSION_REQUIRED = "ADMISSION_REQUIRED"
    ISSUE = "ISSUE"
    COMPLETION_UNOBSERVED = "COMPLETION_UNOBSERVED"
    REASSESS_REQUIRED = "REASSESS_REQUIRED"


_REQUIRED_LIFECYCLE = (
    AttackLifecycleObservation.ADMISSION_REQUIRED,
    AttackLifecycleObservation.ISSUE,
    AttackLifecycleObservation.COMPLETION_UNOBSERVED,
    AttackLifecycleObservation.REASSESS_REQUIRED,
)


@dataclass(frozen=True)
class NativeAttackRule:
    """One deterministic native attack-lifecycle defrule body."""

    identity: str
    order: int
    facts: tuple[Expression, ...]
    actions: tuple[Expression, ...]
    lifecycle: tuple[AttackLifecycleObservation, ...]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native attack rule identity must not be empty")
        if self.order < 0:
            raise ValueError("native attack rule order must be non-negative")
        if not isinstance(self.facts, tuple) or not isinstance(self.actions, tuple):
            raise TypeError("native attack rule facts/actions must be tuples")
        if not isinstance(self.lifecycle, tuple):
            raise TypeError("native attack rule lifecycle must be a tuple")
        if not self.facts and not self.actions:
            raise ValueError(
                f"native attack rule '{self.identity}' requires a fact or action"
            )
        if self.lifecycle != _REQUIRED_LIFECYCLE:
            raise ValueError(
                f"native attack rule '{self.identity}' requires lifecycle "
                f"{tuple(item.value for item in _REQUIRED_LIFECYCLE)} in exact order"
            )


@dataclass(frozen=True)
class NativeAttackLifecyclePlan:
    """Ordered compiler-owned native attack lifecycle rules."""

    rules: tuple[NativeAttackRule, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native attack rule identity")
        keys = tuple((rule.order, rule.identity) for rule in self.rules)
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native attack rules must be declared in deterministic order"
            )

    @property
    def expressions(self) -> tuple[Expression, ...]:
        return tuple(
            expression
            for rule in self.rules
            for expression in (*rule.facts, *rule.actions)
        )

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(
            sorted({expression.head for expression in self.expressions})
        )

    @property
    def empty(self) -> bool:
        return not self.rules


__all__ = [
    "AttackLifecycleObservation",
    "NativeAttackLifecyclePlan",
    "NativeAttackRule",
]
