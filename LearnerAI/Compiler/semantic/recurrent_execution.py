"""Path-sensitive recurrent execution analysis for effective .per rules.

This is a bounded abstract interpreter, not a game simulator. It tracks only
exact Goal/SN/Timer state established by known actions, rule enablement, and
native rule control transfer. Unknown world facts branch conservatively.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ..ast import Expression, SourceLocation
from .rule_execution import EffectiveRule, RuleExecutionReport, RulePassBehavior


class RecurrentExecutionStatus(str, Enum):
    NEVER_RUNNABLE = "NEVER_RUNNABLE"
    MAY_RUN = "MAY_RUN"
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"


class RecurrentDiagnosticCode(str, Enum):
    NEVER_RUNNABLE = "REX-001"
    RUNTIME_DEPENDENT = "REX-002"
    GUARANTEED_PREEMPTION = "REX-003"
    PERSISTENT_STATE_STARVATION = "REX-004"


class _Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RecurrentExecutionDiagnostic:
    code: str
    rule_order: int
    message: str
    location: SourceLocation
    related_rule_order: int | None = None
    state_kind: str | None = None
    state_identifier: str | None = None


@dataclass(frozen=True)
class RecurrentExecutionReport:
    statuses: tuple[tuple[int, RecurrentExecutionStatus], ...]
    reachable_rule_orders: tuple[int, ...]
    fired_rule_orders: tuple[int, ...]
    diagnostics: tuple[RecurrentExecutionDiagnostic, ...]
    explored_states: int
    truncated: bool = False

    def status_for_rule(self, rule_order: int) -> RecurrentExecutionStatus:
        for candidate, status in self.statuses:
            if candidate == rule_order:
                return status
        raise KeyError(rule_order)


@dataclass(frozen=True)
class _MachineState:
    cursor: int
    disabled: frozenset[int]
    values: tuple[tuple[str, str, object], ...]

    def value_map(self) -> dict[tuple[str, str], object]:
        return {(kind, ident): value for kind, ident, value in self.values}


def _normalize_values(values: Mapping[tuple[str, str], object]):
    return tuple(
        sorted(
            (
                (kind, ident, value)
                for (kind, ident), value in values.items()
            ),
            key=lambda item: (item[0], item[1], repr(item[2])),
        )
    )


def _int(value: object) -> int | None:
    try:
        return int(str(value), 10)
    except (TypeError, ValueError):
        return None


def _compare(actual: object, operator: str, expected: object) -> _Truth:
    if actual is None:
        return _Truth.UNKNOWN
    if operator in {"=", "=="}:
        return _Truth.TRUE if actual == expected else _Truth.FALSE
    if operator == "!=":
        return _Truth.TRUE if actual != expected else _Truth.FALSE
    if not isinstance(actual, int) or not isinstance(expected, int):
        return _Truth.UNKNOWN
    if operator == "<":
        return _Truth.TRUE if actual < expected else _Truth.FALSE
    if operator == "<=":
        return _Truth.TRUE if actual <= expected else _Truth.FALSE
    if operator == ">":
        return _Truth.TRUE if actual > expected else _Truth.FALSE
    if operator == ">=":
        return _Truth.TRUE if actual >= expected else _Truth.FALSE
    return _Truth.UNKNOWN


def _truth_not(value: _Truth) -> _Truth:
    return {
        _Truth.TRUE: _Truth.FALSE,
        _Truth.FALSE: _Truth.TRUE,
        _Truth.UNKNOWN: _Truth.UNKNOWN,
    }[value]


def _truth_and(left: _Truth, right: _Truth) -> _Truth:
    if left is _Truth.FALSE or right is _Truth.FALSE:
        return _Truth.FALSE
    if left is _Truth.TRUE and right is _Truth.TRUE:
        return _Truth.TRUE
    return _Truth.UNKNOWN


def _truth_or(left: _Truth, right: _Truth) -> _Truth:
    if left is _Truth.TRUE or right is _Truth.TRUE:
        return _Truth.TRUE
    if left is _Truth.FALSE and right is _Truth.FALSE:
        return _Truth.FALSE
    return _Truth.UNKNOWN


def _stateful_fact(
    expression: Expression,
    values: Mapping[tuple[str, str], object],
) -> _Truth | None:
    if expression.head == "goal":
        if len(expression.args) == 2:
            ident = str(expression.args[0])
            expected = _int(expression.args[1])
            if expected is None:
                return _Truth.UNKNOWN
            return _compare(values.get(("GOAL", ident), 0), "==", expected)
        if len(expression.args) == 3:
            ident = str(expression.args[0])
            expected = _int(expression.args[2])
            if expected is None:
                return _Truth.UNKNOWN
            return _compare(
                values.get(("GOAL", ident), 0),
                str(expression.args[1]),
                expected,
            )
        return _Truth.UNKNOWN

    if expression.head in {"strategic-number", "up-compare-sn"}:
        if len(expression.args) != 3:
            return _Truth.UNKNOWN
        ident = str(expression.args[0])
        expected = _int(expression.args[2])
        if expected is None:
            return _Truth.UNKNOWN
        return _compare(
            values.get(("SN", ident)),
            str(expression.args[1]),
            expected,
        )

    if expression.head == "up-timer-status":
        if len(expression.args) != 3:
            return _Truth.UNKNOWN
        ident = str(expression.args[0])
        operator = str(expression.args[1])
        if operator.startswith("c:"):
            operator = operator[2:]
        return _compare(
            values.get(("TIMER", ident)),
            operator,
            str(expression.args[2]).lower(),
        )

    if expression.head == "timer-triggered":
        return _Truth.UNKNOWN

    return None


def _evaluate_fact(
    expression: Expression,
    values: Mapping[tuple[str, str], object],
) -> _Truth:
    if expression.head == "true":
        return _Truth.TRUE

    stateful = _stateful_fact(expression, values)
    if stateful is not None:
        return stateful

    if expression.head == "not":
        if len(expression.args) != 1 or not isinstance(expression.args[0], Expression):
            return _Truth.UNKNOWN
        return _truth_not(_evaluate_fact(expression.args[0], values))

    if expression.head in {"and", "or"}:
        if len(expression.args) != 2 or not all(
            isinstance(argument, Expression) for argument in expression.args
        ):
            return _Truth.UNKNOWN
        left = _evaluate_fact(expression.args[0], values)
        right = _evaluate_fact(expression.args[1], values)
        return _truth_and(left, right) if expression.head == "and" else _truth_or(left, right)

    return _Truth.UNKNOWN


def _evaluate_guard(
    rule: EffectiveRule,
    values: Mapping[tuple[str, str], object],
) -> _Truth:
    result = _Truth.TRUE
    for fact in rule.facts:
        result = _truth_and(result, _evaluate_fact(fact, values))
    return result


def _apply_action(
    values: dict[tuple[str, str], object],
    expression: Expression,
) -> None:
    if expression.head == "set-goal" and len(expression.args) == 2:
        values[("GOAL", str(expression.args[0]))] = _int(expression.args[1])
    elif expression.head == "set-strategic-number" and len(expression.args) == 2:
        values[("SN", str(expression.args[0]))] = _int(expression.args[1])
    elif expression.head == "up-modify-sn" and expression.args:
        values[("SN", str(expression.args[0]))] = None
    elif expression.head == "enable-timer" and len(expression.args) == 2:
        values[("TIMER", str(expression.args[0]))] = "timer-running"
    elif expression.head == "disable-timer" and len(expression.args) == 1:
        values[("TIMER", str(expression.args[0]))] = "timer-disabled"
    elif expression.head == "up-set-timer" and len(expression.args) == 4:
        interval = _int(expression.args[3])
        values[("TIMER", str(expression.args[1]))] = (
            "timer-disabled"
            if interval is not None and interval < 0
            else "timer-running"
        )


def _jump_target(
    rule_index: int,
    rule: EffectiveRule,
    total_rules: int,
) -> int | None:
    jumps = [
        action.expression
        for action in rule.actions
        if action.expression.head == "up-jump-rule"
        and len(action.expression.args) == 1
    ]
    if not jumps:
        return None

    delta = _int(jumps[-1].args[0])
    if delta is None:
        return None

    target = rule_index + delta + 1
    return target if 0 <= target < total_rules else None


def _execute_actions(
    state: _MachineState,
    rule: EffectiveRule,
    rule_index: int,
    total_rules: int,
) -> tuple[_MachineState, int | None]:
    values = state.value_map()
    disabled = set(state.disabled)

    for action in rule.actions:
        expression = action.expression
        if expression.head == "disable-self":
            disabled.add(rule.rule_order)
        _apply_action(values, expression)

    target = _jump_target(rule_index, rule, total_rules)
    return (
        _MachineState(
            cursor=target if target is not None else rule_index + 1,
            disabled=frozenset(disabled),
            values=_normalize_values(values),
        ),
        target,
    )


def _guaranteed_exact_writer(
    rule: EffectiveRule,
    kind: str,
    ident: str,
    value: object,
) -> bool:
    if rule.pass_behavior is not RulePassBehavior.RECURRENT:
        return False
    if len(rule.facts) != 1 or rule.facts[0].head != "true":
        return False

    for action in rule.actions:
        expression = action.expression
        if kind == "GOAL" and expression.head == "set-goal" and len(expression.args) == 2:
            if str(expression.args[0]) == ident and _int(expression.args[1]) == value:
                return True
        if kind == "SN" and expression.head == "set-strategic-number" and len(expression.args) == 2:
            if str(expression.args[0]) == ident and _int(expression.args[1]) == value:
                return True
        if kind == "TIMER" and expression.head == "enable-timer" and len(expression.args) == 2:
            if str(expression.args[0]) == ident and value == "timer-running":
                return True
        if kind == "TIMER" and expression.head == "disable-timer" and len(expression.args) == 1:
            if str(expression.args[0]) == ident and value == "timer-disabled":
                return True
    return False


def _diagnostic_sort_key(
    item: RecurrentExecutionDiagnostic,
) -> tuple[object, ...]:
    return (
        item.rule_order,
        item.code,
        item.related_rule_order or -1,
        item.state_kind or "",
        item.state_identifier or "",
        item.message,
    )


def analyze_recurrent_execution(
    report: RuleExecutionReport,
    *,
    max_states: int = 4096,
) -> RecurrentExecutionReport:
    """Compute a conservative fixed point over recurrent pass states."""
    if not isinstance(report, RuleExecutionReport):
        raise TypeError("report must be a RuleExecutionReport")
    if max_states <= 0:
        raise ValueError("max_states must be positive")

    rules = report.rules
    if not rules:
        return RecurrentExecutionReport((), (), (), (), 0)

    initial = _MachineState(0, frozenset(), ())
    worklist = [initial]
    seen = {initial}
    reached: set[int] = set()
    fired: set[int] = set()
    blocked: dict[int, set[tuple[str, str, object]]] = {}
    guaranteed_preempted: dict[int, set[int]] = {}
    truncated = False

    while worklist:
        if len(seen) >= max_states:
            truncated = True
            break

        state = worklist.pop()
        if state.cursor >= len(rules):
            successor = _MachineState(0, state.disabled, state.values)
            if successor not in seen:
                seen.add(successor)
                worklist.append(successor)
            continue

        index = state.cursor
        rule = rules[index]
        reached.add(rule.rule_order)

        if rule.rule_order in state.disabled:
            successor = _MachineState(index + 1, state.disabled, state.values)
            if successor not in seen:
                seen.add(successor)
                worklist.append(successor)
            continue

        values = state.value_map()
        guard = _evaluate_guard(rule, values)

        if guard in {_Truth.FALSE, _Truth.UNKNOWN}:
            if guard is _Truth.FALSE:
                for fact in rule.facts:
                    fact_result = _stateful_fact(fact, values)
                    if fact_result is not _Truth.FALSE:
                        continue
                    if fact.head == "goal" and len(fact.args) >= 2:
                        ident = str(fact.args[0])
                        blocked.setdefault(rule.rule_order, set()).add(
                            ("GOAL", ident, values.get(("GOAL", ident), 0))
                        )
                    elif fact.head in {"strategic-number", "up-compare-sn"} and len(fact.args) == 3:
                        ident = str(fact.args[0])
                        blocked.setdefault(rule.rule_order, set()).add(
                            ("SN", ident, values.get(("SN", ident))
                        ))
                    elif fact.head == "up-timer-status" and len(fact.args) == 3:
                        ident = str(fact.args[0])
                        blocked.setdefault(rule.rule_order, set()).add(
                            ("TIMER", ident, values.get(("TIMER", ident))
                        )

            successor = _MachineState(index + 1, state.disabled, state.values)
            if successor not in seen:
                seen.add(successor)
                worklist.append(successor)

        if guard in {_Truth.TRUE, _Truth.UNKNOWN}:
            fired.add(rule.rule_order)
            successor, target = _execute_actions(
                state,
                rule,
                index,
                len(rules),
            )

            if (
                target is not None
                and target > index + 1
                and guard is _Truth.TRUE
                and rule.pass_behavior is RulePassBehavior.RECURRENT
            ):
                for skipped in range(index + 1, target):
                    guaranteed_preempted.setdefault(
                        rules[skipped].rule_order,
                        set(),
                    ).add(rule.rule_order)

            if successor.cursor < len(rules):
                if successor not in seen:
                    seen.add(successor)
                    worklist.append(successor)
            else:
                wrapped = _MachineState(
                    0,
                    successor.disabled,
                    successor.values,
                )
                if wrapped not in seen:
                    seen.add(wrapped)
                    worklist.append(wrapped)

    statuses: list[tuple[int, RecurrentExecutionStatus]] = []
    for rule in rules:
        if rule.rule_order in fired:
            status = RecurrentExecutionStatus.MAY_RUN
        elif truncated:
            status = RecurrentExecutionStatus.RUNTIME_DEPENDENT
        else:
            status = RecurrentExecutionStatus.NEVER_RUNNABLE
        statuses.append((rule.rule_order, status))

    diagnostics: list[RecurrentExecutionDiagnostic] = []
    status_by_rule = dict(statuses)

    for rule in rules:
        status = status_by_rule[rule.rule_order]
        if status is RecurrentExecutionStatus.MAY_RUN:
            continue
        if status is RecurrentExecutionStatus.RUNTIME_DEPENDENT:
            diagnostics.append(
                RecurrentExecutionDiagnostic(
                    code=RecurrentDiagnosticCode.RUNTIME_DEPENDENT.value,
                    rule_order=rule.rule_order,
                    message=(
                        f"rule {rule.rule_order} could not be classified because the "
                        f"recurrent state-space bound ({max_states}) was reached"
                    ),
                    location=rule.source_location,
                )
            )
            continue

        sources = guaranteed_preempted.get(rule.rule_order, set())
        if sources:
            source = min(sources)
            diagnostics.append(
                RecurrentExecutionDiagnostic(
                    code=RecurrentDiagnosticCode.GUARANTEED_PREEMPTION.value,
                    rule_order=rule.rule_order,
                    message=(
                        f"rule {rule.rule_order} is never runnable because recurrent "
                        f"rule {source} guarantees a forward jump over it on every reachable firing"
                    ),
                    location=rule.source_location,
                    related_rule_order=source,
                )
            )
            continue

        writer_match = None
        for kind, ident, actual in blocked.get(rule.rule_order, set()):
            if actual is None:
                continue
            for candidate in rules:
                if candidate.rule_order >= rule.rule_order:
                    continue
                if _guaranteed_exact_writer(candidate, kind, ident, actual):
                    writer_match = (candidate.rule_order, kind, ident)
        if writer_match is not None:
            source, kind, ident = writer_match
            diagnostics.append(
                RecurrentExecutionDiagnostic(
                    code=RecurrentDiagnosticCode.PERSISTENT_STATE_STARVATION.value,
                    rule_order=rule.rule_order,
                    message=(
                        f"rule {rule.rule_order} never becomes runnable because recurrent "
                        f"writer rule {source} keeps {kind.lower()} state '{ident}' "
                        "at a value incompatible with its guard"
                    ),
                    location=rule.source_location,
                    related_rule_order=source,
                    state_kind=kind,
                    state_identifier=ident,
                )
            )
            continue

        diagnostics.append(
            RecurrentExecutionDiagnostic(
                code=RecurrentDiagnosticCode.NEVER_RUNNABLE.value,
                rule_order=rule.rule_order,
                message=(
                    f"rule {rule.rule_order} has no reachable firing state in the "
                    "path-sensitive recurrent execution model"
                ),
                location=rule.source_location,
            )
        )

    return RecurrentExecutionReport(
        statuses=tuple(statuses),
        reachable_rule_orders=tuple(
            rule.rule_order for rule in rules if rule.rule_order in reached
        ),
        fired_rule_orders=tuple(
            rule.rule_order for rule in rules if rule.rule_order in fired
        ),
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_sort_key)),
        explored_states=len(seen),
        truncated=truncated,
    )


__all__ = [
    "RecurrentDiagnosticCode",
    "RecurrentExecutionDiagnostic",
    "RecurrentExecutionReport",
    "RecurrentExecutionStatus",
    "analyze_recurrent_execution",
]
