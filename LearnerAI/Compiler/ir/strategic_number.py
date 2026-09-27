"""Typed Strategic Number mutation IR for native AoE2 .per semantics."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation

STRATEGIC_NUMBER_MIN = -2_147_483_648
STRATEGIC_NUMBER_MAX = 2_147_483_647
CONSTANT_OPERAND_MIN = -32_768
CONSTANT_OPERAND_MAX = 32_767


class StrategicNumberMathOp(str, Enum):
    ASSIGN = "="
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    DIVIDE_FLOOR = "z/"
    MOD = "mod"
    MIN = "min"
    MAX = "max"
    NEGATE = "neg"
    PERCENT_MULTIPLY = "%*"
    PERCENT_DIVIDE = "%/"


class StrategicNumberOperandKind(str, Enum):
    CONSTANT = "CONSTANT"
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"


class StrategicNumberAccessKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


@dataclass(frozen=True)
class StrategicNumberOperand:
    kind: StrategicNumberOperandKind
    value: int | str

    @property
    def dependency_identifier(self) -> str | None:
        if self.kind is StrategicNumberOperandKind.CONSTANT:
            return None
        return str(self.value)


@dataclass(frozen=True)
class StrategicNumberDependency:
    kind: StrategicNumberOperandKind
    identifier: str
    rule_order: int
    within_rule_order: int
    section: str
    command: str
    location: SourceLocation | None


@dataclass(frozen=True)
class StrategicNumberAccess:
    identifier: str
    kind: StrategicNumberAccessKind
    rule_order: int
    within_rule_order: int
    section: str
    command: str
    location: SourceLocation | None


@dataclass(frozen=True)
class StrategicNumberMutation:
    target: str
    operator: StrategicNumberMathOp
    operand: StrategicNumberOperand
    rule_order: int | None
    within_rule_order: int
    section: str
    expression: Expression
    location: SourceLocation | None

    @property
    def target_access(self) -> StrategicNumberAccess:
        return StrategicNumberAccess(
            identifier=self.target,
            kind=StrategicNumberAccessKind.WRITE,
            rule_order=self.rule_order if self.rule_order is not None else -1,
            within_rule_order=self.within_rule_order,
            section=self.section,
            command=self.expression.head,
            location=self.location,
        )

    @property
    def operand_dependency(self) -> StrategicNumberDependency | None:
        if self.operand.kind is StrategicNumberOperandKind.CONSTANT:
            return None
        return StrategicNumberDependency(
            kind=self.operand.kind,
            identifier=str(self.operand.value),
            rule_order=self.rule_order if self.rule_order is not None else -1,
            within_rule_order=self.within_rule_order,
            section=self.section,
            command=self.expression.head,
            location=self.location,
        )


__all__ = [
    "CONSTANT_OPERAND_MAX",
    "CONSTANT_OPERAND_MIN",
    "STRATEGIC_NUMBER_MAX",
    "STRATEGIC_NUMBER_MIN",
    "StrategicNumberAccess",
    "StrategicNumberAccessKind",
    "StrategicNumberDependency",
    "StrategicNumberMathOp",
    "StrategicNumberMutation",
    "StrategicNumberOperand",
    "StrategicNumberOperandKind",
]
