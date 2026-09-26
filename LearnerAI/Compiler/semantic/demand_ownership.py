"""Demand ownership and deterministic lifecycle access analysis."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir.model import (
    AccessKind,
    DemandOwnership,
    SemanticDemand,
    SemanticId,
    StateAccess,
    StateStorageKind,
    StorageRequestId,
)


class OwnershipStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    UNCONSUMED = "UNCONSUMED"
    CONFLICTING = "CONFLICTING"
    ORDER_VIOLATION = "ORDER-VIOLATION"


class OwnershipDiagnosticCode(str, Enum):
    DEMAND_MISSING_OWNERSHIP = "OWN-001"
    DEMAND_OWNERSHIP_MISMATCH = "OWN-002"
    STATE_ACCESS_MISSING_OWNER = "OWN-003"
    CONFLICTING_WRITERS = "OWN-004"
    DUPLICATE_WRITER_PHASE = "OWN-005"
    STATE_NO_WRITER = "OWN-006"
    STATE_UNCONSUMED = "OWN-007"
    CONSUMER_BEFORE_WRITER = "OWN-008"
    STATE_ACCESS_MISMATCH = "OWN-009"
    STATE_ACCESS_MISSING_RULE_SCOPE = "OWN-010"


@dataclass(frozen=True)
class OwnershipDiagnostic:
    code: OwnershipDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    status: OwnershipStatus
    demand: SemanticId | None = None
    state: object | None = None
    access: StateAccess | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class OwnershipBoundary:
    state: StorageRequestId
    first_writer: StateAccess | None
    first_consumer: StateAccess | None


@dataclass(frozen=True)
class OwnershipReport:
    diagnostics: tuple[OwnershipDiagnostic, ...]
    boundaries: tuple[OwnershipBoundary, ...]

    @property
    def errors(self) -> tuple[OwnershipDiagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _semantic_key(identity: SemanticId | None) -> tuple[str, str]:
    if identity is None:
        return ("", "")
    return (identity.source_unit, identity.local_name)


def _access_key(access: StateAccess) -> tuple[object, ...]:
    return (
        access.source_order,
        access.phase.value,
        access.operation,
        _semantic_key(access.owner),
        _semantic_key(access.demand),
    )


def _state_key(state: StorageRequestId) -> tuple[str, str, str]:
    return (
        state.owner.source_unit,
        state.owner.local_name,
        state.purpose,
    )


def _diagnostic_key(item: OwnershipDiagnostic) -> tuple[object, ...]:
    return (
        item.code.value,
        _semantic_key(item.demand),
        _state_key(item.state) if item.state is not None else ("", "", ""),
        _access_key(item.access) if item.access is not None else (),
        item.message,
    )


def _diag(
    code: OwnershipDiagnosticCode,
    message: str,
    *,
    status: OwnershipStatus,
    demand: SemanticId | None = None,
    state: StorageRequestId | None = None,
    access: StateAccess | None = None,
    location: SourceLocation | None = None,
) -> OwnershipDiagnostic:
    return OwnershipDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        status=status,
        demand=demand,
        state=state,
        access=access,
        location=location,
    )


def _ownership_for(demand: SemanticDemand) -> DemandOwnership | None:
    return demand.ownership


def analyze_demand_ownership(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> OwnershipReport:
    diagnostics: list[OwnershipDiagnostic] = []
    boundaries: list[OwnershipBoundary] = []

    ordered_demands = tuple(
        sorted(
            demands,
            key=lambda item: (
                item.identity.source_unit,
                item.identity.local_name,
            ),
        )
    )

    grouped: dict[object, list[StateAccess]] = {}
    state_locations = {
        demand.lifecycle.slot.request_id: demand.location
        for demand in ordered_demands
    }

    for demand in ordered_demands:
        ownership = _ownership_for(demand)
        state = demand.lifecycle.slot.request_id

        if ownership is None or ownership.owner is None:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.DEMAND_MISSING_OWNERSHIP,
                    f"demand '{demand.identity.local_name}' has no semantic owner",
                    status=OwnershipStatus.BLOCKED,
                    demand=demand.identity,
                    state=state,
                    location=demand.location,
                )
            )
            continue

        if ownership.demand != demand.identity or ownership.state != state:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.DEMAND_OWNERSHIP_MISMATCH,
                    f"demand '{demand.identity.local_name}' ownership contract does not "
                    "match its semantic identity and lifecycle state",
                    status=OwnershipStatus.BLOCKED,
                    demand=demand.identity,
                    state=state,
                    location=state_locations.get(state),
                )
            )

        if state.owner != ownership.owner:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.DEMAND_OWNERSHIP_MISMATCH,
                    f"demand '{demand.identity.local_name}' owner "
                    f"'{ownership.owner.source_unit}:{ownership.owner.local_name}' does not "
                    f"own lifecycle state '{state.owner.source_unit}:{state.purpose}'",
                    status=OwnershipStatus.CONFLICTING,
                    demand=demand.identity,
                    state=state,
                    location=state_locations.get(state),
                )
            )

        if not demand.state_accesses:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.STATE_NO_WRITER,
                    f"demand '{demand.identity.local_name}' has no lifecycle state accesses",
                    status=OwnershipStatus.BLOCKED,
                    demand=demand.identity,
                    state=state,
                    location=state_locations.get(state),
                )
            )
            continue

        for access in demand.state_accesses:
            if access.storage_kind is not StateStorageKind.LIFECYCLE:
                continue
            grouped.setdefault(access.state, []).append(access)
            if access.owner is None:
                diagnostics.append(
                    _diag(
                        OwnershipDiagnosticCode.STATE_ACCESS_MISSING_OWNER,
                        f"state access '{access.operation}' for demand "
                        f"'{demand.identity.local_name}' has no owner",
                        status=OwnershipStatus.BLOCKED,
                        demand=demand.identity,
                        state=state,
                        access=access,
                        location=demand.location,
                    )
                )
            if access.state != state or access.demand != demand.identity:
                diagnostics.append(
                    _diag(
                        OwnershipDiagnosticCode.STATE_ACCESS_MISMATCH,
                        f"state access '{access.operation}' for demand "
                        f"'{demand.identity.local_name}' does not match its lifecycle state",
                        status=OwnershipStatus.CONFLICTING,
                        demand=demand.identity,
                        state=state,
                        access=access,
                        location=demand.location,
                    )
                )

    for state in sorted(grouped, key=_state_key):
        accesses = tuple(sorted(grouped[state], key=_access_key))
        writers = tuple(access for access in accesses if access.kind is AccessKind.WRITE)
        consumers = tuple(access for access in accesses if access.kind is AccessKind.READ)
        first_writer = writers[0] if writers else None
        first_consumer = consumers[0] if consumers else None

        boundaries.append(
            OwnershipBoundary(
                state=state,
                first_writer=first_writer,
                first_consumer=first_consumer,
            )
        )

        if first_writer is None:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.STATE_NO_WRITER,
                    f"lifecycle state '{state.owner.source_unit}:{state.purpose}' has no writer",
                    status=OwnershipStatus.BLOCKED,
                    state=state,
                    location=state_locations.get(state),
                )
            )
        if first_consumer is None:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.STATE_UNCONSUMED,
                    f"lifecycle state '{state.owner.source_unit}:{state.purpose}' is never consumed",
                    status=OwnershipStatus.UNCONSUMED,
                    state=state,
                    location=state_locations.get(state),
                )
            )

        if (
            first_writer is not None
            and first_consumer is not None
            and first_consumer.source_order < first_writer.source_order
        ):
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.CONSUMER_BEFORE_WRITER,
                    f"lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                    f"consumer '{first_consumer.operation}' precedes first writer "
                    f"'{first_writer.operation}'",
                    status=OwnershipStatus.ORDER_VIOLATION,
                    state=state,
                    access=first_consumer,
                    location=state_locations.get(state),
                )
            )

        writer_owners = {
            access.owner
            for access in writers
            if access.owner is not None
        }
        if len(writer_owners) > 1:
            names = ", ".join(
                f"{owner.source_unit}:{owner.local_name}"
                for owner in sorted(writer_owners, key=_semantic_key)
            )
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.CONFLICTING_WRITERS,
                    f"lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                    f"has conflicting writers: {names}",
                    status=OwnershipStatus.CONFLICTING,
                    state=state,
                    location=state_locations.get(state),
                )
            )

        if len(writer_owners) <= 1:
            phases: dict[object, list[StateAccess]] = {}
            for access in writers:
                phases.setdefault(access.phase, []).append(access)
            for phase, phase_writers in sorted(
                phases.items(),
                key=lambda item: item[0].value,
            ):
                if len(phase_writers) > 1:
                    diagnostics.append(
                        _diag(
                            OwnershipDiagnosticCode.DUPLICATE_WRITER_PHASE,
                            f"lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                            f"has multiple writers in phase '{phase.value}'",
                            status=OwnershipStatus.CONFLICTING,
                            state=state,
                            access=max(phase_writers, key=_access_key),
                            location=state_locations.get(state),
                        )
                    )

    return OwnershipReport(
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_key)),
        boundaries=tuple(
            sorted(
                boundaries,
                key=lambda item: _state_key(item.state),
            )
        ),
    )


def validate_demand_ownership(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> OwnershipReport:
    return analyze_demand_ownership(demands)


__all__ = [
    "OwnershipBoundary",
    "OwnershipDiagnostic",
    "OwnershipDiagnosticCode",
    "OwnershipReport",
    "OwnershipStatus",
    "analyze_demand_ownership",
    "validate_demand_ownership",
]
