"""Typed internal IR for the minimal native attack lifecycle slice.

This IR represents a controller-owned attack issuance boundary. It is not source
syntax and it does not claim native completion or release semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, TYPE_CHECKING
from enum import Enum

from ..ast import Expression, SourceLocation
if TYPE_CHECKING:
    from ..runtime_binding import GoalSlotRequest
from .strategic_number_arbitration import StrategicNumberActionAttachment


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
class NativeAttackGoalInputRequest:
    """Bind a Goal-backed attack Fact operand to the shared Goal allocator."""

    identity: str
    rule_identity: str
    section: str
    expression_index: int
    argument_index: int
    request: "GoalSlotRequest"

    @property
    def site_key(self) -> tuple[str, str, int, int]:
        return (
            self.rule_identity,
            self.section,
            self.expression_index,
            self.argument_index,
        )

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native attack Goal input identity must not be empty")
        if self.section not in {"FACT", "ACTION"}:
            raise ValueError("native attack Goal input section must be FACT or ACTION")
        if self.expression_index < 0 or self.argument_index < 0:
            raise ValueError("native attack Goal input indexes must be non-negative")
        from ..runtime_binding import GoalSlotRequest
        if not isinstance(self.request, GoalSlotRequest):
            raise TypeError("native attack Goal input request must be a GoalSlotRequest")


@dataclass(frozen=True)
class NativeAttackLifecyclePlan:
    """Ordered compiler-owned native attack lifecycle rules."""

    rules: tuple[NativeAttackRule, ...] = ()
    strategic_number_action_attachments: tuple[
        StrategicNumberActionAttachment, ...
    ] = ()
    goal_input_requests: tuple[NativeAttackGoalInputRequest, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native attack rule identity")
        keys = tuple((rule.order, rule.identity) for rule in self.rules)
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native attack rules must be declared in deterministic order"
            )
        if not isinstance(self.goal_input_requests, tuple):
            raise TypeError("native attack Goal input requests must be a tuple")
        goal_sites = tuple(request.site_key for request in self.goal_input_requests)
        if len(goal_sites) != len(set(goal_sites)):
            raise ValueError("duplicate native attack Goal input request site")
        rule_by_identity = {rule.identity: rule for rule in self.rules}
        for request in self.goal_input_requests:
            rule = rule_by_identity.get(request.rule_identity)
            if rule is None:
                raise ValueError(
                    f"native attack Goal input '{request.identity}' references unknown "
                    f"rule '{request.rule_identity}'"
                )
            expressions = rule.facts if request.section == "FACT" else rule.actions
            if request.expression_index >= len(expressions):
                raise ValueError(
                    f"native attack Goal input '{request.identity}' expression index "
                    "is outside its owned rule"
                )
            expression = expressions[request.expression_index]
            if expression.head not in {"goal", "up-compare-goal"}:
                raise ValueError(
                    f"native attack Goal input '{request.identity}' can only bind "
                    "goal or up-compare-goal expressions"
                )
            if request.argument_index != 0:
                raise ValueError(
                    f"native attack Goal input '{request.identity}' must bind "
                    "argument 0"
                )

        if not isinstance(self.strategic_number_action_attachments, tuple):
            raise TypeError(
                "native attack Strategic Number attachments must be a tuple"
            )

        attachment_identities = tuple(
            attachment.identity
            for attachment in self.strategic_number_action_attachments
        )
        if len(attachment_identities) != len(set(attachment_identities)):
            raise ValueError(
                "duplicate native attack Strategic Number attachment identity"
            )

        rule_by_identity = {rule.identity: rule for rule in self.rules}
        target_keys = set()
        for attachment in self.strategic_number_action_attachments:
            if attachment.owned_rule_identity is None:
                raise ValueError(
                    f"native attack Strategic Number attachment "
                    f"'{attachment.identity}' requires an owned rule identity"
                )
            rule = rule_by_identity.get(attachment.owned_rule_identity)
            if rule is None:
                raise ValueError(
                    f"native attack Strategic Number attachment "
                    f"'{attachment.identity}' references unknown owned rule "
                    f"'{attachment.owned_rule_identity}'"
                )
            assert attachment.action_index is not None
            if attachment.action_index >= len(rule.actions):
                raise ValueError(
                    f"native attack Strategic Number attachment "
                    f"'{attachment.identity}' action_index {attachment.action_index} "
                    f"is outside owned rule '{rule.identity}'"
                )
            action = rule.actions[attachment.action_index]
            if action.head != attachment.action_identity:
                raise ValueError(
                    f"native attack Strategic Number attachment "
                    f"'{attachment.identity}' action identity '{attachment.action_identity}' "
                    f"does not match owned rule '{rule.identity}' action {attachment.action_index} "
                    f"('{action.head}')"
                )
            target_key = (rule.identity, attachment.action_index)
            if target_key in target_keys:
                raise ValueError(
                    f"duplicate native attack Strategic Number attachment target "
                    f"'{rule.identity}[{attachment.action_index}]'"
                )
            target_keys.add(target_key)

        ordered_attachments = tuple(
            sorted(
                self.strategic_number_action_attachments,
                key=lambda attachment: (
                    attachment.owned_rule_identity or "",
                    attachment.action_index if attachment.action_index is not None else -1,
                    attachment.identity,
                ),
            )
        )
        object.__setattr__(
            self,
            "strategic_number_action_attachments",
            ordered_attachments,
        )

    def bind_strategic_number_action_attachments(
        self,
        attachments: tuple[StrategicNumberActionAttachment, ...],
        *,
        owned_actions: Mapping[str, tuple[str, int]],
    ) -> "NativeAttackLifecyclePlan":
        """Bind controller attachments to exact native attack rule/action positions."""
        bound = []
        for attachment in attachments:
            try:
                rule_identity, action_index = owned_actions[
                    attachment.controller_identity
                ]
            except KeyError as exc:
                raise ValueError(
                    f"native attack Strategic Number attachment "
                    f"'{attachment.identity}' has no owned action binding for "
                    f"controller '{attachment.controller_identity}'"
                ) from exc
            bound.append(
                replace(
                    attachment,
                    owned_rule_identity=rule_identity,
                    action_index=action_index,
                )
            )
        return NativeAttackLifecyclePlan(
            rules=self.rules,
            strategic_number_action_attachments=tuple(bound),
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
    "NativeAttackGoalInputRequest",
    "NativeAttackLifecyclePlan",
    "NativeAttackRule",
]
