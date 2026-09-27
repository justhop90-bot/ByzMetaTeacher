"""Semantic validation and evaluation for native Strategic Number math."""
from __future__ import annotations

from dataclasses import dataclass
import math
from enum import Enum

from ..ast import Expression, SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir.strategic_number import (
    CONSTANT_OPERAND_MAX,
    CONSTANT_OPERAND_MIN,
    STRATEGIC_NUMBER_MAX,
    STRATEGIC_NUMBER_MIN,
    StrategicNumberAccess,
    StrategicNumberAccessKind,
    StrategicNumberDependency,
    StrategicNumberMathOp,
    StrategicNumberMutation,
    StrategicNumberOperand,
    StrategicNumberOperandKind,
)
from .rule_execution import EffectiveRule, RuleExecutionReport


class StrategicNumberSemanticError(ValueError):
    """Raised when native Strategic Number syntax or evaluation is invalid."""


class StrategicNumberCompilationError(StrategicNumberSemanticError):
    """Raised when SN semantic diagnostics must block artifact promotion."""

    def __init__(
        self,
        diagnostics: tuple["StrategicNumberDiagnostic", ...],
    ) -> None:
        self.diagnostics = tuple(diagnostics)
        message = "; ".join(item.message for item in diagnostics)
        super().__init__(message or "Strategic Number semantic validation failed")


class StrategicNumberDiagnosticCode(str, Enum):
    INVALID_ARITY = "SNSEM-001"
    INVALID_OPERATOR = "SNSEM-002"
    INVALID_OPERAND_PREFIX = "SNSEM-003"
    INVALID_LITERAL = "SNSEM-004"
    OUT_OF_RANGE_LITERAL = "SNSEM-005"
    CONSTANT_ZERO_DIVISOR = "SNSEM-006"
    MISSING_DEPENDENCY = "SNSEM-007"
    INVALID_TARGET = "SNSEM-008"
    FUTURE_SAME_RULE_DEPENDENCY = "SNSEM-009"


@dataclass(frozen=True)
class StrategicNumberDiagnostic:
    code: StrategicNumberDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    rule_order: int
    within_rule_order: int
    location: SourceLocation | None


@dataclass(frozen=True)
class StrategicNumberSemanticReport:
    mutations: tuple[StrategicNumberMutation, ...]
    accesses: tuple[StrategicNumberAccess, ...]
    dependencies: tuple[StrategicNumberDependency, ...]
    diagnostics: tuple[StrategicNumberDiagnostic, ...]

    @property
    def errors(self) -> tuple[StrategicNumberDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )


_OPERATOR_MAP = {
    "=": StrategicNumberMathOp.ASSIGN,
    "+": StrategicNumberMathOp.ADD,
    "-": StrategicNumberMathOp.SUBTRACT,
    "*": StrategicNumberMathOp.MULTIPLY,
    "/": StrategicNumberMathOp.DIVIDE,
    "z/": StrategicNumberMathOp.DIVIDE_FLOOR,
    "mod": StrategicNumberMathOp.MOD,
    "min": StrategicNumberMathOp.MIN,
    "max": StrategicNumberMathOp.MAX,
    "neg": StrategicNumberMathOp.NEGATE,
    "%*": StrategicNumberMathOp.PERCENT_MULTIPLY,
    "%/": StrategicNumberMathOp.PERCENT_DIVIDE,
}


def _validate_target(target: object) -> str:
    if not isinstance(target, str) or not target:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_TARGET.value}: "
            "Strategic Number target must be a non-empty identifier"
        )
    try:
        numeric_target = int(target, 10)
    except ValueError:
        return target
    if numeric_target < 0 or numeric_target > 511:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_TARGET.value}: "
            f"Strategic Number id {numeric_target} is outside 0..511"
        )
    return target


def _parse_constant(value: object) -> int:
    try:
        parsed = int(str(value), 10)
    except (TypeError, ValueError) as exc:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_LITERAL.value}: "
            f"constant Strategic Number operand '{value}' is not an integer"
        ) from exc
    if not CONSTANT_OPERAND_MIN <= parsed <= CONSTANT_OPERAND_MAX:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.OUT_OF_RANGE_LITERAL.value}: "
            f"constant Strategic Number operand {parsed} is outside "
            f"{CONSTANT_OPERAND_MIN}..{CONSTANT_OPERAND_MAX}"
        )
    return parsed


def _parse_operand(operator_token: str, value: object) -> tuple[StrategicNumberMathOp, StrategicNumberOperand]:
    if not isinstance(operator_token, str) or ":" not in operator_token:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_OPERATOR.value}: "
            f"Strategic Number math operator must use c:/g:/s: prefix, got '{operator_token}'"
        )

    prefix, raw_operator = operator_token.split(":", 1)
    operand_kind = {
        "c": StrategicNumberOperandKind.CONSTANT,
        "g": StrategicNumberOperandKind.GOAL,
        "s": StrategicNumberOperandKind.STRATEGIC_NUMBER,
    }.get(prefix)
    if operand_kind is None:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_OPERAND_PREFIX.value}: "
            f"unknown Strategic Number operand prefix '{prefix}:'"
        )

    operator = _OPERATOR_MAP.get(raw_operator)
    if operator is None:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_OPERATOR.value}: "
            f"unknown Strategic Number math operator '{raw_operator}'"
        )

    if operand_kind is StrategicNumberOperandKind.CONSTANT:
        operand = StrategicNumberOperand(operand_kind, _parse_constant(value))
        if operator in {
            StrategicNumberMathOp.DIVIDE,
            StrategicNumberMathOp.DIVIDE_FLOOR,
            StrategicNumberMathOp.MOD,
            StrategicNumberMathOp.PERCENT_DIVIDE,
        } and operand.value == 0:
            raise StrategicNumberSemanticError(
                f"{StrategicNumberDiagnosticCode.CONSTANT_ZERO_DIVISOR.value}: "
                f"operator '{operator.value}' cannot use constant divisor 0"
            )
        return operator, operand

    if not isinstance(value, str) or not value:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_LITERAL.value}: "
            "Goal/Strategic Number operand must be a non-empty identifier"
        )

    return operator, StrategicNumberOperand(operand_kind, value)


def parse_strategic_number_mutation(
    expression: Expression,
    *,
    rule_order: int | None = None,
    within_rule_order: int = 0,
    section: str = "ACTION",
) -> StrategicNumberMutation:
    if not isinstance(expression, Expression):
        raise TypeError("expression must be an Expression")
    if expression.head != "up-modify-sn":
        raise StrategicNumberSemanticError(
            f"expected up-modify-sn, got '{expression.head}'"
        )
    if len(expression.args) != 3:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.INVALID_ARITY.value}: "
            "up-modify-sn requires SnId, mathOp, and Value"
        )

    target = _validate_target(expression.args[0])
    operator, operand = _parse_operand(
        str(expression.args[1]),
        expression.args[2],
    )

    return StrategicNumberMutation(
        target=target,
        operator=operator,
        operand=operand,
        rule_order=rule_order,
        within_rule_order=within_rule_order,
        section=section,
        expression=expression,
        location=expression.location,
    )


def _trunc_div(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise StrategicNumberSemanticError("Strategic Number division by zero")
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _nearest_div(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise StrategicNumberSemanticError("Strategic Number division by zero")
    quotient, remainder = divmod(abs(numerator), abs(denominator))
    if remainder * 2 >= abs(denominator):
        quotient += 1
    if (numerator < 0) != (denominator < 0):
        return -quotient
    return quotient


def _resolve_operand(
    operand: StrategicNumberOperand,
    *,
    goals: dict[str, int],
    strategic_numbers: dict[str, int],
) -> int:
    if operand.kind is StrategicNumberOperandKind.CONSTANT:
        return int(operand.value)
    if operand.kind is StrategicNumberOperandKind.GOAL:
        try:
            return int(goals[str(operand.value)])
        except KeyError as exc:
            raise StrategicNumberSemanticError(
                f"{StrategicNumberDiagnosticCode.MISSING_DEPENDENCY.value}: "
                f"Goal '{operand.value}' is not available"
            ) from exc
    try:
        return int(strategic_numbers[str(operand.value)])
    except KeyError as exc:
        raise StrategicNumberSemanticError(
            f"{StrategicNumberDiagnosticCode.MISSING_DEPENDENCY.value}: "
            f"Strategic Number '{operand.value}' is not available"
        ) from exc


def _clamp(value: int) -> int:
    return max(STRATEGIC_NUMBER_MIN, min(STRATEGIC_NUMBER_MAX, value))


def evaluate_strategic_number_mutation(
    mutation: StrategicNumberMutation,
    *,
    current_value: int,
    goals: dict[str, int],
    strategic_numbers: dict[str, int],
) -> int:
    operand = _resolve_operand(
        mutation.operand,
        goals=goals,
        strategic_numbers=strategic_numbers,
    )
    current_value = int(current_value)
    operator = mutation.operator

    if operator is StrategicNumberMathOp.ASSIGN:
        result = operand
    elif operator is StrategicNumberMathOp.ADD:
        result = current_value + operand
    elif operator is StrategicNumberMathOp.SUBTRACT:
        result = current_value - operand
    elif operator is StrategicNumberMathOp.MULTIPLY:
        result = current_value * operand
    elif operator is StrategicNumberMathOp.DIVIDE:
        result = _nearest_div(current_value, operand)
    elif operator is StrategicNumberMathOp.DIVIDE_FLOOR:
        if operand == 0:
            raise StrategicNumberSemanticError("Strategic Number division by zero")
        result = math.floor(current_value / operand)
    elif operator is StrategicNumberMathOp.MOD:
        if operand == 0:
            raise StrategicNumberSemanticError("Strategic Number modulo by zero")
        result = current_value - _trunc_div(current_value, operand) * operand
    elif operator is StrategicNumberMathOp.MIN:
        result = min(current_value, operand)
    elif operator is StrategicNumberMathOp.MAX:
        result = max(current_value, operand)
    elif operator is StrategicNumberMathOp.NEGATE:
        result = -operand
    elif operator is StrategicNumberMathOp.PERCENT_MULTIPLY:
        result = _trunc_div(current_value * operand, 100)
    elif operator is StrategicNumberMathOp.PERCENT_DIVIDE:
        if operand == 0:
            raise StrategicNumberSemanticError("Strategic Number percentage division by zero")
        result = _trunc_div(current_value * 100, operand)
    else:
        raise StrategicNumberSemanticError(
            f"unsupported Strategic Number operator '{operator.value}'"
        )

    return _clamp(int(result))


def _walk(expressions: tuple[Expression, ...] | list[Expression]):
    for expression in expressions:
        yield expression
        for argument in expression.args:
            if isinstance(argument, Expression):
                yield from _walk((argument,))


def _writers_in_rule(rule: EffectiveRule) -> tuple[StrategicNumberAccess, ...]:
    accesses: list[StrategicNumberAccess] = []
    for index, expression in enumerate(_walk(rule.facts)):
        if expression.head == "set-strategic-number" and len(expression.args) >= 1:
            accesses.append(
                StrategicNumberAccess(
                    identifier=str(expression.args[0]),
                    kind=StrategicNumberAccessKind.WRITE,
                    rule_order=rule.rule_order,
                    within_rule_order=index,
                    section="GUARD",
                    command=expression.head,
                    location=expression.location or rule.source_location,
                )
            )
        elif expression.head == "up-modify-sn" and expression.args:
            accesses.append(
                StrategicNumberAccess(
                    identifier=str(expression.args[0]),
                    kind=StrategicNumberAccessKind.WRITE,
                    rule_order=rule.rule_order,
                    within_rule_order=index,
                    section="GUARD",
                    command=expression.head,
                    location=expression.location or rule.source_location,
                )
            )
    for action in rule.actions:
        expression = action.expression
        if expression.head == "set-strategic-number" and len(expression.args) >= 1:
            accesses.append(
                StrategicNumberAccess(
                    identifier=str(expression.args[0]),
                    kind=StrategicNumberAccessKind.WRITE,
                    rule_order=rule.rule_order,
                    within_rule_order=action.within_rule_order,
                    section="ACTION",
                    command=expression.head,
                    location=expression.location or rule.source_location,
                )
            )
        elif expression.head == "up-modify-sn" and expression.args:
            accesses.append(
                StrategicNumberAccess(
                    identifier=str(expression.args[0]),
                    kind=StrategicNumberAccessKind.WRITE,
                    rule_order=rule.rule_order,
                    within_rule_order=action.within_rule_order,
                    section="ACTION",
                    command=expression.head,
                    location=expression.location or rule.source_location,
                )
            )
    return tuple(accesses)


def _all_same_rule_writers(
    rule: EffectiveRule,
) -> tuple[tuple[str, str, str, int], ...]:
    writers: list[tuple[str, str, str, int]] = []
    for index, expression in enumerate(_walk(rule.facts)):
        if expression.head in {"set-goal", "set-strategic-number"} and expression.args:
            state_kind = "GOAL" if expression.head == "set-goal" else "STRATEGIC_NUMBER"
            writers.append((state_kind, str(expression.args[0]), "GUARD", index))
        elif expression.head == "up-modify-sn" and len(expression.args) == 3:
            writers.append(("STRATEGIC_NUMBER", str(expression.args[0]), "GUARD", index))
    for action in rule.actions:
        expression = action.expression
        if expression.head in {"set-goal", "set-strategic-number"} and expression.args:
            state_kind = "GOAL" if expression.head == "set-goal" else "STRATEGIC_NUMBER"
            writers.append((state_kind, str(expression.args[0]), "ACTION", action.within_rule_order))
        elif expression.head == "up-modify-sn" and len(expression.args) == 3:
            writers.append(("STRATEGIC_NUMBER", str(expression.args[0]), "ACTION", action.within_rule_order))
    return tuple(writers)


def _is_after(
    dependency_section: str,
    dependency_order: int,
    writer_section: str,
    writer_order: int,
) -> bool:
    dependency_key = (0 if dependency_section == "GUARD" else 1, dependency_order)
    writer_key = (0 if writer_section == "GUARD" else 1, writer_order)
    return writer_key > dependency_key


def _diagnostic_code_from_error(
    error: StrategicNumberSemanticError,
) -> StrategicNumberDiagnosticCode:
    prefix = str(error).split(":", 1)[0]
    for code in StrategicNumberDiagnosticCode:
        if code.value == prefix:
            return code
    return StrategicNumberDiagnosticCode.INVALID_OPERATOR


def analyze_strategic_number_expressions(
    report: RuleExecutionReport,
) -> StrategicNumberSemanticReport:
    if not isinstance(report, RuleExecutionReport):
        raise TypeError("report must be a RuleExecutionReport")

    mutations: list[StrategicNumberMutation] = []
    accesses: list[StrategicNumberAccess] = []
    dependencies: list[StrategicNumberDependency] = []
    diagnostics: list[StrategicNumberDiagnostic] = []

    for rule in report.rules:
        rule_writers = _writers_in_rule(rule)
        accesses.extend(rule_writers)

        expressions: list[tuple[str, int, Expression]] = []
        for index, expression in enumerate(_walk(rule.facts)):
            expressions.append(("GUARD", index, expression))
        expressions.extend(
            ("ACTION", action.within_rule_order, action.expression)
            for action in rule.actions
        )

        for section, within_rule_order, expression in expressions:
            if expression.head != "up-modify-sn":
                continue
            try:
                mutation = parse_strategic_number_mutation(
                    expression,
                    rule_order=rule.rule_order,
                    within_rule_order=within_rule_order,
                    section=section,
                )
            except StrategicNumberSemanticError as exc:
                diagnostics.append(
                    StrategicNumberDiagnostic(
                        code=_diagnostic_code_from_error(exc),
                        severity=DiagnosticSeverity.ERROR,
                        message=str(exc),
                        rule_order=rule.rule_order,
                        within_rule_order=within_rule_order,
                        location=expression.location or rule.source_location,
                    )
                )
                continue

            mutations.append(mutation)
            dependency = mutation.operand_dependency
            if dependency is None:
                continue
            dependencies.append(dependency)

            if dependency.kind is StrategicNumberOperandKind.STRATEGIC_NUMBER:
                prior_or_same_writes = [
                    writer
                    for writer in rule_writers
                    if writer.identifier == dependency.identifier
                    and (
                        writer.section == section
                        and writer.within_rule_order <= within_rule_order
                    )
                ]
                future_writes = [
                    (writer_section, writer_order)
                    for kind, identifier, writer_section, writer_order in _all_same_rule_writers(rule)
                    if kind == "STRATEGIC_NUMBER"
                    and identifier == dependency.identifier
                    and _is_after(section, within_rule_order, writer_section, writer_order)
                ]
                if future_writes:
                    diagnostics.append(
                        StrategicNumberDiagnostic(
                            code=StrategicNumberDiagnosticCode.FUTURE_SAME_RULE_DEPENDENCY,
                            severity=DiagnosticSeverity.ERROR,
                            message=(
                                f"Strategic Number '{dependency.identifier}' is read by "
                                f"rule {rule.rule_order} before a later same-rule writer"
                            ),
                            rule_order=rule.rule_order,
                            within_rule_order=within_rule_order,
                            location=dependency.location,
                        )
                    )
            elif dependency.kind is StrategicNumberOperandKind.GOAL:
                future_writes = [
                    writer
                    for kind, identifier, writer_section, writer_order in _all_same_rule_writers(rule)
                    if kind == "GOAL"
                    and identifier == dependency.identifier
                    and _is_after(section, within_rule_order, writer_section, writer_order)
                ]
                if future_writes:
                    diagnostics.append(
                        StrategicNumberDiagnostic(
                            code=StrategicNumberDiagnosticCode.FUTURE_SAME_RULE_DEPENDENCY,
                            severity=DiagnosticSeverity.ERROR,
                            message=(
                                f"Goal '{dependency.identifier}' is read by rule "
                                f"{rule.rule_order} before a later same-rule writer"
                            ),
                            rule_order=rule.rule_order,
                            within_rule_order=within_rule_order,
                            location=dependency.location,
                        )
                    )

    deduped: dict[tuple[object, ...], StrategicNumberDiagnostic] = {}
    for diagnostic in diagnostics:
        key = (
            diagnostic.code.value,
            diagnostic.rule_order,
            diagnostic.within_rule_order,
            diagnostic.message,
        )
        deduped[key] = diagnostic

    return StrategicNumberSemanticReport(
        mutations=tuple(mutations),
        accesses=tuple(
            sorted(
                accesses,
                key=lambda access: (
                    access.rule_order,
                    0 if access.section == "GUARD" else 1,
                    access.within_rule_order,
                    access.identifier,
                    access.kind.value,
                ),
            )
        ),
        dependencies=tuple(
            sorted(
                dependencies,
                key=lambda dependency: (
                    dependency.rule_order,
                    dependency.within_rule_order,
                    dependency.kind.value,
                    dependency.identifier,
                ),
            )
        ),
        diagnostics=tuple(
            sorted(
                deduped.values(),
                key=lambda diagnostic: (
                    diagnostic.rule_order,
                    diagnostic.within_rule_order,
                    diagnostic.code.value,
                ),
            )
        ),
    )


__all__ = [
    "StrategicNumberCompilationError",
    "StrategicNumberDiagnostic",
    "StrategicNumberDiagnosticCode",
    "StrategicNumberSemanticError",
    "StrategicNumberSemanticReport",
    "analyze_strategic_number_expressions",
    "evaluate_strategic_number_mutation",
    "parse_strategic_number_mutation",
]
