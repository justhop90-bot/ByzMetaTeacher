"""Typed Strategic Number mutation IR for native AoE2 .per semantics."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from .model import GoalRole, StorageRequestId

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


class StrategicNumberOrigin(str, Enum):
    NATIVE_REFERENCE = "NATIVE_REFERENCE"
    COMPILER_ALLOCATION = "COMPILER_ALLOCATION"


class StrategicNumberOperandKind(str, Enum):
    CONSTANT = "CONSTANT"
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"


class StrategicNumberAccessKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class StrategicNumberCompareOp(str, Enum):
    EQUAL = "=="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="


@dataclass(frozen=True)
class StrategicNumberStorageRequest:
    request_id: StorageRequestId
    why_not_goal: str
    stability_key: str
    role: GoalRole = GoalRole.PERSISTENT_STATE
    native_contract_id: str | None = None

    def __post_init__(self) -> None:
        if self.role is not GoalRole.PERSISTENT_STATE:
            raise ValueError(
                "compiler-owned Strategic Number storage must use PERSISTENT_STATE role"
            )
        if not self.why_not_goal.strip():
            raise ValueError(
                f"Strategic Number request {self.request_id} requires WHY_NOT_GOAL justification"
            )
        if not self.stability_key.strip():
            raise ValueError(
                f"Strategic Number request {self.request_id} requires a stability_key"
            )


@dataclass(frozen=True)
class StrategicNumberState:
    name: str
    initial_value: int
    request: StrategicNumberStorageRequest
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Strategic Number state name must not be empty")
        if not -32768 <= self.initial_value <= 32767:
            raise ValueError(
                f"Strategic Number initial value {self.initial_value} is outside -32768..32767"
            )
        if self.request.request_id.purpose != f"strategic-number:{self.name}":
            raise ValueError(
                "Strategic Number request purpose must match its state name"
            )


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
class StrategicNumberComparison:
    target: str
    operator: StrategicNumberCompareOp
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
            kind=StrategicNumberAccessKind.READ,
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
    "StrategicNumberOrigin",
    "StrategicNumberAccessKind",
    "StrategicNumberComparison",
    "StrategicNumberCompareOp",
    "StrategicNumberDependency",
    "StrategicNumberMathOp",
    "StrategicNumberMutation",
    "StrategicNumberOperand",
    "StrategicNumberOperandKind",
    "StrategicNumberState",
    "StrategicNumberStorageRequest",
]
