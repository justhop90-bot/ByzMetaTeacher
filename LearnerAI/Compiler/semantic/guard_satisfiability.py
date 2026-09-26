"""Static satisfiability analysis for parsed .per guard expressions.

The analysis is deliberately runtime-independent. It proves only:
* literal boolean guards,
* proposition truth explicitly supplied by FactSemanticAdapter,
* boolean-algebra identities and exact structural negation.

A runtime-dependent native fact is UNKNOWN, never FALSE.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from ..ast import Expression
from .fact_evaluation import evaluate_static_truth
from .fact_registry import NativeFactRegistry
from .fact_values import StaticTruth


_LOGICAL_ARITY = {
    "and": 2,
    "or": 2,
    "nand": 2,
    "nor": 2,
    "xor": 2,
    "xnor": 2,
    "not": 1,
}


class GuardSatisfiability(str, Enum):
    """Static classification of whether a guard can be satisfied."""

    UNSATISFIABLE = "UNSATISFIABLE"
    SATISFIABLE = "SATISFIABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class _GuardResult:
    status: GuardSatisfiability
    key: tuple | None = None
    truth: StaticTruth = StaticTruth.UNKNOWN


def _expression_key(expr: Expression) -> tuple:
    return (
        expr.head,
        tuple(
            _expression_key(arg) if isinstance(arg, Expression) else ("atom", arg)
            for arg in expr.args
        ),
    )


def _truth_to_result(truth: StaticTruth, key: tuple | None = None) -> _GuardResult:
    if truth is StaticTruth.TRUE:
        return _GuardResult(
            GuardSatisfiability.SATISFIABLE,
            key=key,
            truth=StaticTruth.TRUE,
        )
    if truth is StaticTruth.FALSE:
        return _GuardResult(
            GuardSatisfiability.UNSATISFIABLE,
            key=key,
            truth=StaticTruth.FALSE,
        )
    return _GuardResult(
        GuardSatisfiability.UNKNOWN,
        key=key,
        truth=StaticTruth.UNKNOWN,
    )


def _result_to_truth(result: _GuardResult) -> StaticTruth:
    return result.truth


def _invert_truth(truth: StaticTruth) -> StaticTruth:
    if truth is StaticTruth.TRUE:
        return StaticTruth.FALSE
    if truth is StaticTruth.FALSE:
        return StaticTruth.TRUE
    return StaticTruth.UNKNOWN


def _combine_two(op: str, left: StaticTruth, right: StaticTruth) -> StaticTruth:
    if op == "and":
        if left is StaticTruth.FALSE or right is StaticTruth.FALSE:
            return StaticTruth.FALSE
        if left is StaticTruth.TRUE and right is StaticTruth.TRUE:
            return StaticTruth.TRUE
        return StaticTruth.UNKNOWN

    if op == "or":
        if left is StaticTruth.TRUE or right is StaticTruth.TRUE:
            return StaticTruth.TRUE
        if left is StaticTruth.FALSE and right is StaticTruth.FALSE:
            return StaticTruth.FALSE
        return StaticTruth.UNKNOWN

    if op == "xor":
        if left is StaticTruth.UNKNOWN or right is StaticTruth.UNKNOWN:
            return StaticTruth.UNKNOWN
        return StaticTruth.TRUE if left is not right else StaticTruth.FALSE

    if op == "xnor":
        if left is StaticTruth.UNKNOWN or right is StaticTruth.UNKNOWN:
            return StaticTruth.UNKNOWN
        return StaticTruth.TRUE if left is right else StaticTruth.FALSE

    if op == "nand":
        return _invert_truth(_combine_two("and", left, right))

    if op == "nor":
        return _invert_truth(_combine_two("or", left, right))

    raise ValueError(f"unsupported logical operator '{op}'")


def _is_negation_pair(left: Expression, right: Expression) -> bool:
    if left.head == "not" and isinstance(left.args[0], Expression):
        return _expression_key(left.args[0]) == _expression_key(right)
    if right.head == "not" and isinstance(right.args[0], Expression):
        return _expression_key(right.args[0]) == _expression_key(left)
    return False


def _key_without_not(expr: Expression) -> tuple:
    if expr.head == "not" and isinstance(expr.args[0], Expression):
        return _expression_key(expr.args[0])
    return _expression_key(expr)


def _combine_logical(op: str, children: Sequence[_GuardResult]) -> _GuardResult:
    left, right = children

    same = left.key is not None and left.key == right.key
    negated = False
    if isinstance(left.key, tuple) and isinstance(right.key, tuple):
        # Keys include the explicit "not" wrapper.  Reconstruct the source
        # expressions below only when necessary for exact negation detection.
        pass

    truth_left = _result_to_truth(left)
    truth_right = _result_to_truth(right)

    # Boolean identities that remain decidable even when the operand itself is
    # runtime-dependent.
    if same:
        if op in {"xor", "nand"}:
            if op == "xor":
                return _truth_to_result(StaticTruth.FALSE, left.key)
            # NAND(x, x) == NOT(x): retain runtime dependence.
            return _truth_to_result(StaticTruth.UNKNOWN, left.key)
        if op in {"xnor"}:
            return _truth_to_result(StaticTruth.TRUE, left.key)
        if op == "nor":
            # NOR(x, x) == NOT(x): retain runtime dependence.
            return _truth_to_result(StaticTruth.UNKNOWN, left.key)

    result = _combine_two(op, truth_left, truth_right)
    return _truth_to_result(result)


def _analyze(expr: Expression, fact_registry: NativeFactRegistry) -> _GuardResult:
    if expr.head == "true":
        return _truth_to_result(StaticTruth.TRUE, _expression_key(expr))
    if expr.head == "false":
        return _truth_to_result(StaticTruth.FALSE, _expression_key(expr))

    if expr.head in _LOGICAL_ARITY:
        expected = _LOGICAL_ARITY[expr.head]
        if len(expr.args) != expected:
            raise ValueError(
                f"logical operator '{expr.head}' requires {expected} operands"
            )
        if any(not isinstance(arg, Expression) for arg in expr.args):
            raise ValueError(
                f"logical operator '{expr.head}' requires nested expressions"
            )

        if expr.head == "not":
            child = _analyze(expr.args[0], fact_registry)
            truth = _invert_truth(child.truth)
            return _truth_to_result(truth, _expression_key(expr))

        children = tuple(
            _analyze(child, fact_registry)
            for child in expr.args
        )

        if _is_negation_pair(expr.args[0], expr.args[1]):
            static_truth = {
                "and": StaticTruth.FALSE,
                "or": StaticTruth.TRUE,
                "xor": StaticTruth.TRUE,
                "xnor": StaticTruth.FALSE,
                "nand": StaticTruth.TRUE,
                "nor": StaticTruth.FALSE,
            }.get(expr.head)
            if static_truth is not None:
                return _truth_to_result(static_truth, _expression_key(expr))

        return _combine_logical(expr.head, children)

    try:
        fact = fact_registry.normalize(expr.head, expr.args)
    except (KeyError, TypeError, ValueError):
        return _truth_to_result(StaticTruth.UNKNOWN, _expression_key(expr))

    adapter = fact_registry.require(expr.head)
    return _truth_to_result(
        evaluate_static_truth(fact, adapter),
        _expression_key(expr),
    )


def analyze_guard(
    expression: Expression,
    fact_registry: NativeFactRegistry,
) -> GuardSatisfiability:
    """Classify a parsed rule-condition tree without simulating runtime state."""
    if not isinstance(expression, Expression):
        raise TypeError("expression must be an Expression")
    if not isinstance(fact_registry, NativeFactRegistry):
        raise TypeError("fact_registry must be a NativeFactRegistry")
    return _analyze(expression, fact_registry).status


__all__ = [
    "GuardSatisfiability",
    "analyze_guard",
]
