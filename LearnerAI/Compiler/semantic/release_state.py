"""Validation of explicit release-state lifecycle contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..diagnostics import DiagnosticSeverity
from ..ir import (
    LifecycleState,
    ReleaseEvidenceKind,
    SemanticDemand,
)
from ..primitives import PrimitiveRegistry


_LOGICAL_HEADS = {"and", "or", "nand", "nor", "xor", "xnor", "not"}


class ReleaseStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"
    ORDER_VIOLATION = "ORDER-VIOLATION"
    OPEN_LOOP = "OPEN-LOOP"


class ReleaseDiagnosticCode(str, Enum):
    MISSING_CONTRACT = "REL-001"
    TIMING_EVIDENCE = "REL-002"
    NO_WORLD_STATE = "REL-003"
    ACTION_COUPLING = "REL-004"
    IDENTITY_MISMATCH = "REL-005"
    INVALID_FROM_STATE = "REL-006"
    INVALID_TO_STATE = "REL-007"
    ORDER_VIOLATION = "REL-008"
    INVALID_EVIDENCE_KIND = "REL-009"
    NATIVE_PRIMITIVE_INVALID = "REL-010"


@dataclass(frozen=True)
class ReleaseDiagnostic:
    code: ReleaseDiagnosticCode
    severity: DiagnosticSeverity
    status: ReleaseStatus
    message: str
    demand: object | None = None


@dataclass(frozen=True)
class ReleaseValidationReport:
    diagnostics: tuple[ReleaseDiagnostic, ...]

    @property
    def errors(self) -> tuple[ReleaseDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _diag_key(item: ReleaseDiagnostic) -> tuple[object, ...]:
    demand = item.demand
    return (
        item.code.value,
        getattr(demand, "source_unit", ""),
        getattr(demand, "local_name", ""),
        item.message,
    )


def _diag(code, status, message, demand):
    return ReleaseDiagnostic(
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


def validate_release_states(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> ReleaseValidationReport:
    diagnostics: list[ReleaseDiagnostic] = []

    for demand in demands:
        contract = demand.release_state
        if contract is None:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.MISSING_CONTRACT,
                    ReleaseStatus.BLOCKED,
                    f"demand '{demand.name}' has no release-state contract",
                    demand.identity,
                )
            )
            continue

        if contract.evidence_kind is not ReleaseEvidenceKind.WORLD_STATE:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.INVALID_EVIDENCE_KIND,
                    ReleaseStatus.OPEN_LOOP,
                    f"release for demand '{demand.name}' has invalid evidence kind "
                    f"'{contract.evidence_kind.value}'",
                    demand.identity,
                )
            )

        if contract.establishes != demand.identity:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.IDENTITY_MISMATCH,
                    ReleaseStatus.CONFLICTING,
                    f"release for demand '{demand.name}' establishes "
                    f"'{contract.establishes.local_name}', not '{demand.name}'",
                    demand.identity,
                )
            )

        if contract.from_state is not LifecycleState.COMPLETE:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.INVALID_FROM_STATE,
                    ReleaseStatus.CONFLICTING,
                    f"release for demand '{demand.name}' must transition from COMPLETE, "
                    f"not {contract.from_state.value}",
                    demand.identity,
                )
            )

        if contract.to_state is not LifecycleState.RELEASED:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.INVALID_TO_STATE,
                    ReleaseStatus.CONFLICTING,
                    f"release for demand '{demand.name}' must transition to RELEASED, "
                    f"not {contract.to_state.value}",
                    demand.identity,
                )
            )

        roles, primitives = _walk(contract.expression, registry)

        if "TIMING" in roles:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.TIMING_EVIDENCE,
                    ReleaseStatus.OPEN_LOOP,
                    f"release for demand '{demand.name}' contains timing evidence",
                    demand.identity,
                )
            )

        if "ACTION" in roles:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.ACTION_COUPLING,
                    ReleaseStatus.CONFLICTING,
                    f"release for demand '{demand.name}' reuses action primitive "
                    f"'{demand.action.expression.head}'",
                    demand.identity,
                )
            )

        if roles.isdisjoint({"OBSERVATION", "WITNESS"}) and "ACTION" not in roles:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.NO_WORLD_STATE,
                    ReleaseStatus.OPEN_LOOP,
                    f"release for demand '{demand.name}' contains no world-state observation",
                    demand.identity,
                )
            )

        if contract.primitive not in _LOGICAL_HEADS:
            primitive = registry.get(contract.primitive)
            if primitive is None:
                diagnostics.append(
                    _diag(
                        ReleaseDiagnosticCode.NATIVE_PRIMITIVE_INVALID,
                        ReleaseStatus.BLOCKED,
                        f"release for demand '{demand.name}' references unknown "
                        f"primitive '{contract.primitive}'",
                        demand.identity,
                    )
                )

        if contract.source_order >= contract.witness_source_order:
            diagnostics.append(
                _diag(
                    ReleaseDiagnosticCode.ORDER_VIOLATION,
                    ReleaseStatus.ORDER_VIOLATION,
                    f"release for demand '{demand.name}' must be emitted before its "
                    "completion witness rule",
                    demand.identity,
                )
            )

    return ReleaseValidationReport(
        diagnostics=tuple(sorted(diagnostics, key=_diag_key)),
    )


__all__ = [
    "ReleaseDiagnostic",
    "ReleaseDiagnosticCode",
    "ReleaseStatus",
    "ReleaseValidationReport",
    "validate_release_states",
]
