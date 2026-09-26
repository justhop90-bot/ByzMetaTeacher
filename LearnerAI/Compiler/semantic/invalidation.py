"""Validation of explicit strategic invalidation and cancellation semantics."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..diagnostics import DiagnosticSeverity
from ..ir import (
    CancellationStateContract,
    InvalidationEvidenceKind,
    LifecycleState,
    SemanticDemand,
)
from ..primitives import PrimitiveRegistry


_LOGICAL_HEADS = {"and", "or", "nand", "nor", "xor", "xnor", "not"}
_WORLD_STATE_ROLES = {"OBSERVATION", "ADMISSIBILITY", "WITNESS"}


class InvalidationStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"
    ORDER_VIOLATION = "ORDER-VIOLATION"
    OPEN_LOOP = "OPEN-LOOP"


class InvalidationDiagnosticCode(str, Enum):
    MISSING_CONTRACT = "INV-001"
    TIMING_EVIDENCE = "INV-002"
    ACTION_COUPLING = "INV-003"
    NO_WORLD_STATE = "INV-004"
    IDENTITY_MISMATCH = "INV-005"
    NATIVE_PRIMITIVE_INVALID = "INV-006"
    ORDER_VIOLATION = "INV-007"
    INVALID_EVIDENCE_KIND = "INV-008"


class CancellationDiagnosticCode(str, Enum):
    MISSING_CONTRACT = "CXL-001"
    INVALID_FROM_STATES = "CXL-002"
    INVALID_TO_STATE = "CXL-003"
    TRIGGER_MISMATCH = "CXL-004"


@dataclass(frozen=True)
class InvalidationDiagnostic:
    code: InvalidationDiagnosticCode | CancellationDiagnosticCode
    severity: DiagnosticSeverity
    status: InvalidationStatus
    message: str
    demand: object | None = None


@dataclass(frozen=True)
class InvalidationValidationReport:
    diagnostics: tuple[InvalidationDiagnostic, ...]

    @property
    def errors(self) -> tuple[InvalidationDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _diag_key(item: InvalidationDiagnostic) -> tuple[object, ...]:
    demand = item.demand
    return (
        item.code.value,
        getattr(demand, "source_unit", ""),
        getattr(demand, "local_name", ""),
        item.message,
    )


def _diag(code, status, message, demand):
    return InvalidationDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        status=status,
        message=message,
        demand=demand,
    )


def _walk(expr, registry: PrimitiveRegistry, *, roles=None, primitives=None):
    roles = set() if roles is None else roles
    primitives = [] if primitives is None else primitives
    primitive = registry.get(expr.head)
    if primitive is not None:
        roles.add(primitive.role)
        primitives.append((expr.head, primitive))
    for argument in expr.args:
        if hasattr(argument, "head"):
            _walk(argument, registry, roles=roles, primitives=primitives)
    return roles, tuple(primitives)


def validate_invalidation_contracts(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> InvalidationValidationReport:
    diagnostics: list[InvalidationDiagnostic] = []

    for demand in demands:
        invalidation = demand.invalidation
        cancellation = demand.cancellation

        if invalidation is None:
            continue

        if invalidation.evidence_kind is not InvalidationEvidenceKind.WORLD_STATE:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.INVALID_EVIDENCE_KIND,
                    InvalidationStatus.OPEN_LOOP,
                    f"invalidation for demand '{demand.name}' has invalid evidence kind "
                    f"'{invalidation.evidence_kind.value}'",
                    demand.identity,
                )
            )

        if invalidation.invalidates != demand.identity:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.IDENTITY_MISMATCH,
                    InvalidationStatus.CONFLICTING,
                    f"invalidation for demand '{demand.name}' invalidates "
                    f"'{invalidation.invalidates.local_name}', not '{demand.name}'",
                    demand.identity,
                )
            )

        roles, _primitives = _walk(invalidation.expression, registry)

        if "TIMING" in roles:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.TIMING_EVIDENCE,
                    InvalidationStatus.OPEN_LOOP,
                    f"invalidation for demand '{demand.name}' contains timing evidence",
                    demand.identity,
                )
            )

        if "ACTION" in roles:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.ACTION_COUPLING,
                    InvalidationStatus.CONFLICTING,
                    f"invalidation for demand '{demand.name}' reuses action primitive "
                    f"'{demand.action.expression.head}'",
                    demand.identity,
                )
            )

        if roles.isdisjoint(_WORLD_STATE_ROLES) and "ACTION" not in roles:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.NO_WORLD_STATE,
                    InvalidationStatus.OPEN_LOOP,
                    f"invalidation for demand '{demand.name}' contains no world-state evidence",
                    demand.identity,
                )
            )

        if invalidation.primitive not in _LOGICAL_HEADS:
            primitive = registry.get(invalidation.primitive)
            if primitive is None:
                diagnostics.append(
                    _diag(
                        InvalidationDiagnosticCode.NATIVE_PRIMITIVE_INVALID,
                        InvalidationStatus.BLOCKED,
                        f"invalidation for demand '{demand.name}' references unknown "
                        f"primitive '{invalidation.primitive}'",
                        demand.identity,
                    )
                )

        if invalidation.source_order >= invalidation.action_source_order:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.ORDER_VIOLATION,
                    InvalidationStatus.ORDER_VIOLATION,
                    f"invalidation for demand '{demand.name}' must precede action issuance",
                    demand.identity,
                )
            )

        release = demand.release_state
        if release is not None and invalidation.source_order >= release.source_order:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.ORDER_VIOLATION,
                    InvalidationStatus.ORDER_VIOLATION,
                    f"invalidation for demand '{demand.name}' must precede release",
                    demand.identity,
                )
            )

        if cancellation is None:
            diagnostics.append(
                _diag(
                    CancellationDiagnosticCode.MISSING_CONTRACT,
                    InvalidationStatus.BLOCKED,
                    f"demand '{demand.name}' has invalidation evidence but no cancellation contract",
                    demand.identity,
                )
            )
            continue

        expected_states = (
            LifecycleState.ACTIVE,
            LifecycleState.ISSUED,
            LifecycleState.PENDING,
        )

        if cancellation.from_states != expected_states:
            diagnostics.append(
                _diag(
                    CancellationDiagnosticCode.INVALID_FROM_STATES,
                    InvalidationStatus.CONFLICTING,
                    f"cancellation for demand '{demand.name}' must cover ACTIVE, ISSUED, "
                    "and PENDING, and must not cancel COMPLETE",
                    demand.identity,
                )
            )

        if cancellation.to_state is not LifecycleState.CANCELLED:
            diagnostics.append(
                _diag(
                    CancellationDiagnosticCode.INVALID_TO_STATE,
                    InvalidationStatus.CONFLICTING,
                    f"cancellation for demand '{demand.name}' must transition to CANCELLED, "
                    f"not {cancellation.to_state.value}",
                    demand.identity,
                )
            )

        if cancellation.trigger != invalidation.identity:
            diagnostics.append(
                _diag(
                    CancellationDiagnosticCode.TRIGGER_MISMATCH,
                    InvalidationStatus.CONFLICTING,
                    f"cancellation for demand '{demand.name}' does not reference its invalidation contract",
                    demand.identity,
                )
            )

        if cancellation.source_order >= cancellation.release_source_order:
            diagnostics.append(
                _diag(
                    InvalidationDiagnosticCode.ORDER_VIOLATION,
                    InvalidationStatus.ORDER_VIOLATION,
                    f"cancellation for demand '{demand.name}' must precede release",
                    demand.identity,
                )
            )

    return InvalidationValidationReport(
        diagnostics=tuple(sorted(diagnostics, key=_diag_key)),
    )


__all__ = [
    "CancellationDiagnosticCode",
    "InvalidationDiagnostic",
    "InvalidationDiagnosticCode",
    "InvalidationStatus",
    "InvalidationValidationReport",
    "validate_invalidation_contracts",
]
