"""Non-lifecycle state visibility and source-order analysis."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir.model import (
    AccessKind,
    SemanticId,
    SemanticDemand,
    StateAccess,
    StateStorageKind,
    StorageRequestId,
)
from .demand_ownership import (
    OwnershipDiagnostic,
    OwnershipDiagnosticCode,
    OwnershipStatus,
)


class StateOrderVisibility(str, Enum):
    SAME_RULE_SEQUENTIAL = "SAME_RULE_SEQUENTIAL"
    CROSS_RULE_PERSISTED = "CROSS_RULE_PERSISTED"
    CONSUMER_BEFORE_WRITER = "CONSUMER_BEFORE_WRITER"
    MISSING_WRITER = "MISSING_WRITER"
    UNCONSUMED = "UNCONSUMED"
    INVALID_SCOPE = "INVALID_SCOPE"


@dataclass(frozen=True)
class StateOrderBoundary:
    state: StorageRequestId
    storage_kind: StateStorageKind
    first_writer: StateAccess | None
    first_consumer: StateAccess | None
    visibility: StateOrderVisibility


@dataclass(frozen=True)
class SourceOrderReport:
    diagnostics: tuple[OwnershipDiagnostic, ...]
    boundaries: tuple[StateOrderBoundary, ...]

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


def _state_key(state: StorageRequestId) -> tuple[str, str, str]:
    return (
        state.owner.source_unit,
        state.owner.local_name,
        state.purpose,
    )


def _access_key(access: StateAccess) -> tuple[object, ...]:
    return (
        access.rule_order if access.rule_order is not None else -1,
        access.within_rule_order,
        access.source_order,
        access.operation,
        _semantic_key(access.owner),
        _semantic_key(access.demand),
    )


def _diag(
    code: OwnershipDiagnosticCode,
    message: str,
    *,
    status: OwnershipStatus,
    state: StorageRequestId,
    access: StateAccess | None = None,
    location: SourceLocation | None = None,
) -> OwnershipDiagnostic:
    return OwnershipDiagnostic(
        code=code,
        severity=DiagnosticSeverity.ERROR,
        message=message,
        status=status,
        state=state,
        access=access,
        location=location,
    )


def _diagnostic_key(item: OwnershipDiagnostic) -> tuple[object, ...]:
    access = item.access
    return (
        item.code.value,
        _state_key(item.state) if item.state is not None else ("", "", ""),
        (
            access.rule_order if access is not None and access.rule_order is not None else -1,
            access.within_rule_order if access is not None else -1,
            access.source_order if access is not None else -1,
            access.operation if access is not None else "",
        ),
        item.message,
    )


def _ordinary_accesses(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> tuple[StateAccess, ...]:
    accesses = [
        access
        for demand in demands
        for access in demand.state_accesses
        if access.storage_kind is not StateStorageKind.LIFECYCLE
    ]
    return tuple(sorted(accesses, key=_access_key))


def analyze_non_lifecycle_source_order(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> SourceOrderReport:
    diagnostics: list[OwnershipDiagnostic] = []
    boundaries: list[StateOrderBoundary] = []
    grouped: dict[tuple[StorageRequestId, StateStorageKind], list[StateAccess]] = {}

    for access in _ordinary_accesses(demands):
        grouped.setdefault((access.state, access.storage_kind), []).append(access)

    by_state: dict[StorageRequestId, list[tuple[StateStorageKind, StateAccess]]] = {}
    for (state, storage_kind), accesses in grouped.items():
        for access in accesses:
            by_state.setdefault(state, []).append((storage_kind, access))

    for state in sorted(by_state, key=_state_key):
        entries = by_state[state]
        storage_kinds = sorted(
            {kind for kind, _ in entries},
            key=lambda item: item.value,
        )
        accesses = tuple(sorted((access for _, access in entries), key=_access_key))
        writers = tuple(access for access in accesses if access.kind is AccessKind.WRITE)
        readers = tuple(access for access in accesses if access.kind is AccessKind.READ)
        first_writer = writers[0] if writers else None
        first_consumer = readers[0] if readers else None

        if len(storage_kinds) != 1:
            boundaries.append(
                StateOrderBoundary(
                    state=state,
                    storage_kind=storage_kinds[0],
                    first_writer=first_writer,
                    first_consumer=first_consumer,
                    visibility=StateOrderVisibility.INVALID_SCOPE,
                )
            )
            for _, access in entries:
                diagnostics.append(
                    _diag(
                        OwnershipDiagnosticCode.STATE_ACCESS_MISMATCH,
                        f"state '{state.owner.source_unit}:{state.purpose}' is accessed "
                        f"as multiple storage kinds: {', '.join(kind.value for kind in storage_kinds)}",
                        status=OwnershipStatus.CONFLICTING,
                        state=state,
                        access=access,
                        location=access.location,
                    )
                )
            continue

        storage_kind = storage_kinds[0]

        missing_scope = tuple(
            access
            for access in accesses
            if access.rule_order is None
        )
        if missing_scope:
            for access in missing_scope:
                diagnostics.append(
                    _diag(
                        OwnershipDiagnosticCode.STATE_ACCESS_MISSING_RULE_SCOPE,
                        f"non-lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                        f"access '{access.operation}' has no emitted rule scope",
                        status=OwnershipStatus.BLOCKED,
                        state=state,
                        access=access,
                        location=access.location,
                    )
                )
            visibility = StateOrderVisibility.INVALID_SCOPE
        elif first_writer is None:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.STATE_NO_WRITER,
                    f"non-lifecycle state '{state.owner.source_unit}:{state.purpose}' has no writer",
                    status=OwnershipStatus.BLOCKED,
                    state=state,
                    location=(
                        first_consumer.location
                        if first_consumer is not None
                        else None
                    ),
                )
            )
            visibility = StateOrderVisibility.MISSING_WRITER
        elif first_consumer is None:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.STATE_UNCONSUMED,
                    f"non-lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                    "is never consumed",
                    status=OwnershipStatus.UNCONSUMED,
                    state=state,
                    location=first_writer.location,
                )
            )
            visibility = StateOrderVisibility.UNCONSUMED
        elif first_consumer.rule_order < first_writer.rule_order:
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.CONSUMER_BEFORE_WRITER,
                    f"non-lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                    f"consumer '{first_consumer.operation}' in rule {first_consumer.rule_order} "
                    f"precedes first writer '{first_writer.operation}' in rule "
                    f"{first_writer.rule_order}",
                    status=OwnershipStatus.ORDER_VIOLATION,
                    state=state,
                    access=first_consumer,
                    location=first_consumer.location,
                )
            )
            visibility = StateOrderVisibility.CONSUMER_BEFORE_WRITER
        elif (
            first_consumer.rule_order == first_writer.rule_order
            and first_consumer.within_rule_order <= first_writer.within_rule_order
        ):
            diagnostics.append(
                _diag(
                    OwnershipDiagnosticCode.CONSUMER_BEFORE_WRITER,
                    f"non-lifecycle state '{state.owner.source_unit}:{state.purpose}' "
                    f"consumer '{first_consumer.operation}' precedes first writer "
                    f"'{first_writer.operation}' in rule {first_writer.rule_order}",
                    status=OwnershipStatus.ORDER_VIOLATION,
                    state=state,
                    access=first_consumer,
                    location=first_consumer.location,
                )
            )
            visibility = StateOrderVisibility.CONSUMER_BEFORE_WRITER
        elif first_consumer.rule_order == first_writer.rule_order:
            visibility = StateOrderVisibility.SAME_RULE_SEQUENTIAL
        else:
            visibility = StateOrderVisibility.CROSS_RULE_PERSISTED

        boundaries.append(
            StateOrderBoundary(
                state=state,
                storage_kind=storage_kind,
                first_writer=first_writer,
                first_consumer=first_consumer,
                visibility=visibility,
            )
        )

    return SourceOrderReport(
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_key)),
        boundaries=tuple(
            sorted(
                boundaries,
                key=lambda boundary: _state_key(boundary.state),
            )
        ),
    )


def validate_non_lifecycle_source_order(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> SourceOrderReport:
    return analyze_non_lifecycle_source_order(demands)


__all__ = [
    "SourceOrderReport",
    "StateOrderBoundary",
    "StateOrderVisibility",
    "analyze_non_lifecycle_source_order",
    "validate_non_lifecycle_source_order",
]
