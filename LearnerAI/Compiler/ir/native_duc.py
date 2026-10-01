"""Typed internal DUC execution-plan IR.

DUC plans are compiler-owned in-memory structures. They are not source syntax and
do not introduce a second scripting language. The plan carries already-parsed
native expressions into the normal binder/emitter boundary.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression, SourceLocation
from .model import GoalSlotRequest, GoalSpanRequest


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
class NativeDucOutputRequest:
    rule_identity: str
    section: str
    expression_index: int
    request: GoalSlotRequest | GoalSpanRequest
    command: str
    argument_index: int = 0

    def __post_init__(self) -> None:
        if not self.rule_identity.strip():
            raise ValueError("native DUC output request rule identity must not be empty")
        if self.section not in {"FACT", "ACTION"}:
            raise ValueError("native DUC output request section must be FACT or ACTION")
        if self.expression_index < 0 or self.argument_index < 0:
            raise ValueError("native DUC output request indexes must be non-negative")
        if not self.command.strip():
            raise ValueError("native DUC output request command must not be empty")

    @property
    def site_key(self) -> tuple[str, str, int]:
        return (self.rule_identity, self.section, self.expression_index)


@dataclass(frozen=True)
class NativeDucGoalInputRequest:
    """One goal-identity handoff read inside a DUC plan rule.

    The reader operand at (rule_identity, section, expression_index,
    argument_index) is rewritten at emission to the bound goal of the
    writer's storage request (`source`). The writer must be a GoalSlot
    output request in the same plan; the reader operand must be a `g:`
    typeOp reference. Readers never allocate storage: they resolve the
    writer's slot, so STORE_ID -> REACQUIRE stays one deterministic slot.
    """

    rule_identity: str
    section: str
    expression_index: int
    argument_index: int
    source: StorageRequestId

    def __post_init__(self) -> None:
        if not self.rule_identity.strip():
            raise ValueError("native DUC input request rule identity must not be empty")
        if self.section not in {"FACT", "ACTION"}:
            raise ValueError("native DUC input request section must be FACT or ACTION")
        if self.expression_index < 0 or self.argument_index < 0:
            raise ValueError("native DUC input request indexes must be non-negative")

    @property
    def site_key(self) -> tuple[str, str, int, int]:
        return (
            self.rule_identity,
            self.section,
            self.expression_index,
            self.argument_index,
        )


@dataclass(frozen=True)
class NativeDucPlan:
    """Ordered compiler-owned native DUC rules with no source-language surface."""

    rules: tuple[NativeDucRule, ...] = ()
    output_requests: tuple[NativeDucOutputRequest, ...] = ()
    input_requests: tuple[NativeDucGoalInputRequest, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native DUC rule identity")
        keys = tuple((rule.order, rule.identity) for rule in self.rules)
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native DUC rules must be declared in deterministic order"
            )
        request_sites = tuple(request.site_key for request in self.output_requests)
        if len(request_sites) != len(set(request_sites)):
            raise ValueError("duplicate native DUC output request site")
        request_ids = tuple(
            request.request.request_id for request in self.output_requests
        )
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("duplicate native DUC output request storage id")
        input_sites = tuple(request.site_key for request in self.input_requests)
        if len(input_sites) != len(set(input_sites)):
            raise ValueError("duplicate native DUC input request site")
        output_sites = tuple(
            (request.rule_identity, request.section, request.expression_index, request.argument_index)
            for request in self.output_requests
        )
        if set(input_sites) & set(output_sites):
            raise ValueError(
                "native DUC input request collides with an output request site"
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


__all__ = [
    "NativeDucGoalInputRequest",
    "NativeDucOutputRequest",
    "NativeDucPlan",
    "NativeDucRule",
]
