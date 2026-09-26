"""Validation of explicit action issuance versus pending admission."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir import (
    ActionIssuanceFailure,
    ActionIssuancePhase,
    LifecycleState,
    SemanticDemand,
)
from ..primitives import PrimitiveRegistry


class IssuanceStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    ORDER_VIOLATION = "ORDER-VIOLATION"
    CONFLICTING = "CONFLICTING"


class IssuanceDiagnosticCode(str, Enum):
    MISSING_CONTRACT = "ISS-001"
    FEASIBILITY_MISSING = "ISS-002"
    ISSUED_PENDING_COLLAPSE = "ISS-003"
    FAILURE_PENDING_COLLAPSE = "ISS-004"
    INVALID_PHASE = "ISS-005"
    INVALID_STATE = "ISS-006"


@dataclass(frozen=True)
class IssuanceDiagnostic:
    code: IssuanceDiagnosticCode
    severity: DiagnosticSeverity
    status: IssuanceStatus
    message: str
    demand: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class IssuanceValidationReport:
    diagnostics: tuple[IssuanceDiagnostic, ...]

    @property
    def errors(self) -> tuple[IssuanceDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _has_feasibility_guard(
    demand: SemanticDemand,
    registry: PrimitiveRegistry,
) -> bool:
    def has_role(expr):
        primitive = registry.get(expr.head)
        if primitive is not None and primitive.role == "FEASIBILITY":
            return True
        return any(
            hasattr(argument, "head") and has_role(argument)
            for argument in expr.args
        )

    return any(has_role(requirement.expression) for requirement in demand.requirements)


def _key(item: IssuanceDiagnostic) -> tuple[object, ...]:
    demand = item.demand
    return (
        item.code.value,
        getattr(demand, "source_unit", ""),
        getattr(demand, "local_name", ""),
        item.message,
    )


def _diag(code, status, message, demand, *, location=None):
    return IssuanceDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        status=status,
        message=message,
        demand=demand,
        location=location,
    )


def validate_action_issuance(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> IssuanceValidationReport:
    diagnostics: list[IssuanceDiagnostic] = []

    for demand in demands:
        issuance = demand.action_issuance
        if issuance is None:
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.MISSING_CONTRACT,
                    IssuanceStatus.BLOCKED,
                    f"demand '{demand.name}' has no action issuance contract",
                    demand.identity,
                )
            )
            continue

        if not _has_feasibility_guard(demand, registry):
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.FEASIBILITY_MISSING,
                    IssuanceStatus.BLOCKED,
                    f"action issuance for demand '{demand.name}' has no native feasibility guard",
                    demand.identity,
                )
            )

        if issuance.phase is not ActionIssuancePhase.ATTEMPT:
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.INVALID_PHASE,
                    IssuanceStatus.CONFLICTING,
                    f"action issuance for demand '{demand.name}' has invalid phase "
                    f"'{issuance.phase.value}'",
                    demand.identity,
                )
            )

        if issuance.issued_state is not LifecycleState.ISSUED:
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.INVALID_STATE,
                    IssuanceStatus.CONFLICTING,
                    f"action issuance for demand '{demand.name}' does not enter ISSUED state",
                    demand.identity,
                )
            )

        if issuance.issued_state is issuance.pending_state:
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.ISSUED_PENDING_COLLAPSE,
                    IssuanceStatus.CONFLICTING,
                    f"action issuance for demand '{demand.name}' collapses ISSUED and PENDING",
                    demand.identity,
                )
            )

        if issuance.failure is ActionIssuanceFailure.RETAIN_ACTIVE and (
            issuance.pending_state is LifecycleState.ACTIVE
        ):
            diagnostics.append(
                _diag(
                    IssuanceDiagnosticCode.FAILURE_PENDING_COLLAPSE,
                    IssuanceStatus.CONFLICTING,
                    f"action issuance for demand '{demand.name}' uses ACTIVE as pending state",
                    demand.identity,
                )
            )

    return IssuanceValidationReport(
        diagnostics=tuple(sorted(diagnostics, key=_key)),
    )


__all__ = [
    "IssuanceDiagnostic",
    "IssuanceDiagnosticCode",
    "IssuanceStatus",
    "IssuanceValidationReport",
    "validate_action_issuance",
]
