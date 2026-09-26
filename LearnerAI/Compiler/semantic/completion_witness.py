"""Validation of explicit completion-witness contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir import (
    CompletionWitnessContract,
    LifecycleState,
    SemanticDemand,
    WitnessEvidenceKind,
)
from ..primitives import PrimitiveRegistry


class WitnessStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"
    ORDER_VIOLATION = "ORDER-VIOLATION"
    OPEN_LOOP = "OPEN-LOOP"


class WitnessDiagnosticCode(str, Enum):
    MISSING_CONTRACT = "WIT-001"
    TIMING_EVIDENCE = "WIT-002"
    NO_COMPLETION_CAPABLE_OBSERVATION = "WIT-003"
    ACTION_COUPLING = "WIT-004"
    IDENTITY_MISMATCH = "WIT-005"
    ORDER_VIOLATION = "WIT-006"
    INVALID_EVIDENCE_KIND = "WIT-007"
    NATIVE_PRIMITIVE_INVALID = "WIT-008"


@dataclass(frozen=True)
class WitnessDiagnostic:
    code: WitnessDiagnosticCode
    severity: DiagnosticSeverity
    status: WitnessStatus
    message: str
    demand: object | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class WitnessValidationReport:
    diagnostics: tuple[WitnessDiagnostic, ...]

    @property
    def errors(self) -> tuple[WitnessDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _diag_key(item: WitnessDiagnostic) -> tuple[object, ...]:
    demand = item.demand
    return (
        item.code.value,
        getattr(demand, "source_unit", ""),
        getattr(demand, "local_name", ""),
        item.message,
    )


def _diag(
    code: WitnessDiagnosticCode,
    status: WitnessStatus,
    message: str,
    demand: object,
    *,
    location: SourceLocation | None = None,
) -> WitnessDiagnostic:
    return WitnessDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        status=status,
        message=message,
        demand=demand,
        location=location,
    )


def _contains_timing(expr, registry: PrimitiveRegistry) -> bool:
    primitive = registry.get(expr.head)
    if primitive is not None and primitive.role == "TIMING":
        return True
    return any(
        hasattr(argument, "head") and _contains_timing(argument, registry)
        for argument in expr.args
    )


def _contains_primitive(expr, name: str) -> bool:
    if expr.head == name:
        return True
    return any(
        hasattr(argument, "head") and _contains_primitive(argument, name)
        for argument in expr.args
    )


def _completion_primitive(expr, registry: PrimitiveRegistry) -> tuple[bool, str | None]:
    primitive = registry.get(expr.head)
    if primitive is not None:
        return primitive.completion_witness, expr.head
    for argument in expr.args:
        if hasattr(argument, "head"):
            valid, name = _completion_primitive(argument, registry)
            if valid:
                return True, name
    return False, None


def validate_completion_witnesses(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> WitnessValidationReport:
    diagnostics: list[WitnessDiagnostic] = []

    for demand in demands:
        contract = demand.completion_witness
        if contract is None:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.MISSING_CONTRACT,
                    WitnessStatus.BLOCKED,
                    f"demand '{demand.name}' has no completion witness contract",
                    demand.identity,
                )
            )
            continue

        if contract.evidence_kind is not WitnessEvidenceKind.WORLD_STATE:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.INVALID_EVIDENCE_KIND,
                    WitnessStatus.OPEN_LOOP,
                    f"completion witness for demand '{demand.name}' has invalid evidence kind "
                    f"'{contract.evidence_kind.value}'",
                    demand.identity,
                )
            )

        if contract.establishes != demand.identity:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.IDENTITY_MISMATCH,
                    WitnessStatus.CONFLICTING,
                    f"completion witness for demand '{demand.name}' establishes "
                    f"'{contract.establishes.local_name}', not '{demand.name}'",
                    demand.identity,
                )
            )

        if _contains_timing(contract.expression, registry):
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.TIMING_EVIDENCE,
                    WitnessStatus.OPEN_LOOP,
                    f"completion witness for demand '{demand.name}' contains timing evidence",
                    demand.identity,
                )
            )

        action_coupled = _contains_primitive(
            contract.expression,
            demand.action.expression.head,
        )
        completion_capable = False
        if action_coupled:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.ACTION_COUPLING,
                    WitnessStatus.CONFLICTING,
                    f"completion witness for demand '{demand.name}' reuses action primitive "
                    f"'{demand.action.expression.head}'",
                    demand.identity,
                )
            )
        else:
            primitive = registry.get(contract.primitive)
            if (
                primitive is None
                and contract.expression.head
                not in {"and", "or", "nand", "nor", "xor", "xnor", "not"}
            ):
                diagnostics.append(
                    _diag(
                        WitnessDiagnosticCode.NATIVE_PRIMITIVE_INVALID,
                        WitnessStatus.BLOCKED,
                        f"completion witness for demand '{demand.name}' references unknown "
                        f"primitive '{contract.primitive}'",
                        demand.identity,
                    )
                )
            completion_capable, _ = _completion_primitive(
                contract.expression,
                registry,
            )

        if not completion_capable and not action_coupled:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.NO_COMPLETION_CAPABLE_OBSERVATION,
                    WitnessStatus.OPEN_LOOP,
                    f"completion witness for demand '{demand.name}' contains no "
                    "completion-capable native observation",
                    demand.identity,
                )
            )

        if contract.source_order >= contract.issuance_source_order:
            diagnostics.append(
                _diag(
                    WitnessDiagnosticCode.ORDER_VIOLATION,
                    WitnessStatus.ORDER_VIOLATION,
                    f"completion witness for demand '{demand.name}' is not ordered before "
                    "action issuance",
                    demand.identity,
                )
            )

    return WitnessValidationReport(
        diagnostics=tuple(sorted(diagnostics, key=_diag_key)),
    )


__all__ = [
    "WitnessDiagnostic",
    "WitnessDiagnosticCode",
    "WitnessStatus",
    "WitnessValidationReport",
    "validate_completion_witnesses",
]
