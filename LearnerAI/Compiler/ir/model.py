"""Validated semantic intermediate representation."""
from __future__ import annotations
from dataclasses import dataclass
from ..ast import Expression


@dataclass(frozen=True)
class SemanticRequirement:
    expression: Expression
    role: str


@dataclass(frozen=True)
class SemanticAction:
    expression: Expression
    role: str


@dataclass(frozen=True)
class PendingDiagnostic:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class SemanticDemand:
    name: str
    goal: int
    requirements: tuple[SemanticRequirement, ...]
    action: SemanticAction
    witness: Expression
    release: Expression
    pending_goal: int
    completed_goal: int
    pending_diagnostics: tuple[PendingDiagnostic, ...] = ()
