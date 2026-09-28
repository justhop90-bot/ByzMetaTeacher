"""Typed internal DUC execution-plan IR.

DUC plans are compiler-owned in-memory structures. They are not source syntax and
do not introduce a second scripting language. The plan carries already-parsed
native expressions into the normal binder/emitter boundary.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression, SourceLocation


@dataclass(frozen=True)
class NativeDucRule:
    """One deterministic native DUC defrule body."""

    identity: str
    order: int
    facts: tuple[Expression, ...]
    actions: tuple[Expression, ...]
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native DUC rule identity must not be empty")
        if self.order < 0:
            raise ValueError("native DUC rule order must be non-negative")
        if not self.facts and not self.actions:
            raise ValueError(
                f"native DUC rule '{self.identity}' requires a fact or action"
            )
        if not isinstance(self.facts, tuple) or not isinstance(self.actions, tuple):
            raise TypeError("native DUC rule facts/actions must be tuples")


@dataclass(frozen=True)
class NativeDucPlan:
    """Ordered compiler-owned native DUC rules with no source-language surface."""

    rules: tuple[NativeDucRule, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native DUC rule identity")
        keys = tuple((rule.order, rule.identity) for rule in self.rules)
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native DUC rules must be declared in deterministic order"
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
        return tuple(sorted({expression.head for expression in self.expressions}))

    @property
    def empty(self) -> bool:
        return not self.rules


__all__ = ["NativeDucPlan", "NativeDucRule"]
