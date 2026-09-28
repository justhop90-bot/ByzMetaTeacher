"""Semantic gate for typed native persistent-control plans.

The control plane reuses the checked-in native command schema and the shared
engine-effect catalog.  It does not make those commands ordinary lifecycle
primitives and it does not invent a scheduler or alternate source language.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..ast import Expression
from ..ir.native_control import NativeControlPlan
from ..primitives.native_binder import NativeSupportState
from ..primitives.native_engine_effects import (
    NativeEffectKind,
    NativeStateDomain,
)
from ..runtime_binding import (
    GoalSlotRequest,
    StrategicNumberRequest,
    TimerRequest,
)
from .strategic_number_semantics import (
    StrategicNumberSemanticError,
    parse_strategic_number_comparison,
    parse_strategic_number_mutation,
)

_LOGICAL_ARITY = {
    "and": 2,
    "or": 2,
    "nand": 2,
    "nor": 2,
    "xor": 2,
    "xnor": 2,
    "not": 1,
}
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

_GOAL_COMMANDS = frozenset(
    {"set-goal", "goal", "up-compare-goal", "up-modify-goal"}
)
_SN_COMMANDS = frozenset(
    {"set-strategic-number", "strategic-number", "up-compare-sn", "up-modify-sn"}
)
_TIMER_COMMANDS = frozenset(
    {"enable-timer", "disable-timer", "timer-triggered", "up-timer-status", "up-set-timer"}
)

# Native control commands are allowed to cross the primitive-support boundary
# only through this explicit plan gate.
_CONTROL_COMMANDS = frozenset(
    {
        "set-goal",
        "goal",
        "up-compare-goal",
        "up-modify-goal",
        "set-strategic-number",
        "strategic-number",
        "up-compare-sn",
        "up-modify-sn",
        "enable-timer",
        "disable-timer",
        "timer-triggered",
        "up-set-timer",
        "up-timer-status",
        "disable-self",
        "up-jump-rule",
    }
)


@dataclass(frozen=True)
class NativeControlValidationReport:
    state_identifiers: tuple[str, ...]
    rule_identities: tuple[str, ...]
    control_commands: tuple[str, ...]


def _walk(expressions: tuple[Expression, ...]):
    for expression in expressions:
        yield expression
        for argument in expression.args:
            if isinstance(argument, Expression):
                yield from _walk((argument,))


def _request_kind(request: object) -> str:
    if isinstance(request, GoalSlotRequest):
        return "GOAL"
    if isinstance(request, StrategicNumberRequest):
        return "STRATEGIC_NUMBER"
    if isinstance(request, TimerRequest):
        return "TIMER"
    raise ValueError(
        f"native control state uses unsupported storage request "
        f"{type(request).__name__}"
    )


def _validate_storage_request_names(plan: NativeControlPlan) -> dict[str, str]:
    states: dict[str, str] = {}
    requests = []
    for state in plan.states:
        if not _IDENTIFIER_RE.fullmatch(state.identifier):
            raise ValueError(
                f"native control state '{state.identifier}' is not a valid .per identifier"
            )
        if state.identifier in states:
            raise ValueError(
                f"duplicate native control state identifier '{state.identifier}'"
            )
        kind = _request_kind(state.request)
        states[state.identifier] = kind
        requests.append(state.request.request_id)

    if len(requests) != len(set(requests)):
        raise ValueError("duplicate native control storage request identity")
    return states


def _require_state(
    identifier: str,
    expected_kind: str,
    states: dict[str, str],
    *,
    command: str,
    argument_index: int,
) -> None:
    if identifier not in states:
        raise ValueError(
            f"undeclared {expected_kind} state '{identifier}' referenced by "
            f"{command} argument {argument_index}"
        )
    actual = states[identifier]
    if actual != expected_kind:
        raise ValueError(
            f"native control command '{command}' expects {expected_kind} state "
            f"at argument {argument_index}, got {actual} state '{identifier}'"
        )


def _validate_typed_operand(
    command: str,
    expression: Expression,
    states: dict[str, str],
) -> None:
    if len(expression.args) != 3:
        return
    operator = str(expression.args[1])
    value = str(expression.args[2])
    prefix = operator[:2].lower() if len(operator) >= 2 else ""
    if prefix == "g:":
        _require_state(
            value,
            "GOAL",
            states,
            command=command,
            argument_index=2,
        )
    elif prefix == "s:":
        _require_state(
            value,
            "STRATEGIC_NUMBER",
            states,
            command=command,
            argument_index=2,
        )
    elif prefix.startswith(("g", "s")) and len(operator) >= 2 and operator[1] == ":":
        raise ValueError(
            f"native control command '{command}' has an invalid typed operand '{operator}'"
        )


def _validate_leaf(
    expression: Expression,
    *,
    is_action: bool,
    registry,
    states: dict[str, str],
) -> None:
    head = expression.head
    if head in _LOGICAL_ARITY:
        if is_action:
            raise ValueError(
                f"native control rule action cannot be logical operator '{head}'"
            )
        expected = _LOGICAL_ARITY[head]
        if len(expression.args) != expected:
            raise ValueError(
                f"logical operator '{head}' requires {expected} operands"
            )
        for child in expression.args:
            if not isinstance(child, Expression):
                raise ValueError(
                    f"logical operator '{head}' requires nested native Facts"
                )
            _validate_leaf(
                child,
                is_action=False,
                registry=registry,
                states=states,
            )
        return

    if not isinstance(head, str) or not head:
        raise ValueError("native control expression has no command name")

    native = registry.native(head)
    if native is None:
        raise ValueError(f"native command '{head}' is absent from the checked-in schema")

    expected_arity = native.parameter_count
    if len(expression.args) != expected_arity:
        raise ValueError(
            f"native command '{head}' expects exactly {expected_arity} "
            f"argument(s), got {len(expression.args)}"
        )

    assessment = registry.assess_support(head)
    if assessment.state not in {
        NativeSupportState.ENGINE_SEMANTICS_MAPPED,
        NativeSupportState.EXECUTABLE_SAFE,
    }:
        raise ValueError(
            f"native control command '{head}' is not semantically executable: "
            f"{assessment.message}"
        )

    if is_action:
        if native.command_type not in {"Action", "Fact/Action"}:
            raise ValueError(
                f"native control action '{head}' is declared as {native.command_type}"
            )
    elif native.command_type not in {"Fact", "Fact/Action"}:
        raise ValueError(
            f"native control Fact '{head}' is declared as {native.command_type}"
        )

    if head not in _CONTROL_COMMANDS:
        return

    if head in _GOAL_COMMANDS:
        index = 0
        _require_state(
            str(expression.args[index]),
            "GOAL",
            states,
            command=head,
            argument_index=index,
        )
    elif head in _SN_COMMANDS:
        _require_state(
            str(expression.args[0]),
            "STRATEGIC_NUMBER",
            states,
            command=head,
            argument_index=0,
        )
    elif head in _TIMER_COMMANDS:
        timer_index = 1 if head == "up-set-timer" else 0
        _require_state(
            str(expression.args[timer_index]),
            "TIMER",
            states,
            command=head,
            argument_index=timer_index,
        )

    if head in {
        "up-compare-goal",
        "up-modify-goal",
        "up-compare-sn",
        "up-modify-sn",
        "strategic-number",
    }:
        _validate_typed_operand(head, expression, states)
        try:
            semantic_expression = expression
            if head in {"up-compare-goal"}:
                from dataclasses import replace
                semantic_expression = replace(expression, head="up-compare-sn")
                parse_strategic_number_comparison(semantic_expression)
            elif head == "up-modify-goal":
                from dataclasses import replace
                semantic_expression = replace(expression, head="up-modify-sn")
                parse_strategic_number_mutation(semantic_expression)
            elif head in {"up-compare-sn", "strategic-number"}:
                parse_strategic_number_comparison(semantic_expression)
            elif head == "up-modify-sn":
                parse_strategic_number_mutation(semantic_expression)
        except StrategicNumberSemanticError as exc:
            raise ValueError(
                f"native control command '{head}' has invalid typed arithmetic: {exc}"
            ) from exc

    if head == "up-set-timer":
        timer_selector = str(expression.args[0])
        if timer_selector not in {"c:", "c"}:
            raise ValueError(
                "native control plan requires up-set-timer to use a constant TimerId selector"
            )
        interval_type = str(expression.args[2]).lower()
        interval_value = str(expression.args[3])
        if interval_type in {"g:", "g"}:
            _require_state(
                interval_value,
                "GOAL",
                states,
                command=head,
                argument_index=3,
            )
        elif interval_type in {"s:", "s"}:
            _require_state(
                interval_value,
                "STRATEGIC_NUMBER",
                states,
                command=head,
                argument_index=3,
            )
        elif interval_type not in {"c:", "c"}:
            raise ValueError(
                f"native control command '{head}' has invalid interval typeOp "
                f"'{interval_type}'"
            )

    if head == "up-jump-rule":
        try:
            int(str(expression.args[0]), 10)
        except ValueError as exc:
            raise ValueError("up-jump-rule RuleDelta must be an integer constant") from exc


def validate_native_control_plan(
    plan: NativeControlPlan,
    registry,
) -> NativeControlValidationReport:
    if not isinstance(plan, NativeControlPlan):
        raise TypeError("plan must be a NativeControlPlan")

    states = _validate_storage_request_names(plan)
    rule_identities: set[str] = set()
    commands: set[str] = set()

    for rule in plan.rules:
        if not _IDENTIFIER_RE.fullmatch(rule.identity):
            raise ValueError(
                f"native control rule '{rule.identity}' is not a valid identifier"
            )
        if rule.identity in rule_identities:
            raise ValueError(
                f"duplicate native control rule identity '{rule.identity}'"
            )
        rule_identities.add(rule.identity)

        for fact in rule.facts:
            _validate_leaf(
                fact,
                is_action=False,
                registry=registry,
                states=states,
            )
            commands.update(
                expression.head
                for expression in _walk((fact,))
                if expression.head in _CONTROL_COMMANDS
            )
        for action in rule.actions:
            _validate_leaf(
                action,
                is_action=True,
                registry=registry,
                states=states,
            )
            commands.update(
                expression.head
                for expression in _walk((action,))
                if expression.head in _CONTROL_COMMANDS
            )

    return NativeControlValidationReport(
        state_identifiers=tuple(sorted(states)),
        rule_identities=tuple(rule.identity for rule in plan.rules),
        control_commands=tuple(sorted(commands)),
    )


def storage_requests_for_plan(plan: NativeControlPlan):
    validate_native_control_plan_shape(plan)
    return plan.storage_requests


def validate_native_control_plan_shape(plan: NativeControlPlan) -> None:
    """Validate request identities without requiring a native registry."""
    _validate_storage_request_names(plan)


__all__ = [
    "NativeControlValidationReport",
    "storage_requests_for_plan",
    "validate_native_control_plan",
    "validate_native_control_plan_shape",
]
