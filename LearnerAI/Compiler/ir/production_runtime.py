"""Runtime evaluation for typed asynchronous production lifecycle evidence.

This module separates executable admission from provider, queue, timing, loss,
and later-pass observations. OPEN evidence never becomes action authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .production import ProductionLifecycle


class ProductionRuntimeStatus(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    QUEUED = "QUEUED"
    COMPLETE = "COMPLETE"
    UNKNOWN = "UNKNOWN"


class ProductionProviderTransition(str, Enum):
    UNKNOWN = "UNKNOWN"
    STABLE = "STABLE"
    LOST = "LOST"
    RECOVERED = "RECOVERED"


class ProductionBoundaryStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    NOT_OBSERVED = "NOT_OBSERVED"
    OBSERVED = "OBSERVED"

def _truth_enum():
    from .strategy_runtime import EvidenceTruth
    return EvidenceTruth


@dataclass(frozen=True)
class ProductionRuntimeState:
    identity: str
    unit: str
    native_unit_id: int
    target_admission: "EvidenceTruth"
    provider_state: "EvidenceTruth"
    provider_readiness: "EvidenceTruth"
    provider_availability: "EvidenceTruth"
    provider_usability: "EvidenceTruth"
    queue_capacity_control: "EvidenceTruth"
    queue_total: "EvidenceTruth"
    pending: "EvidenceTruth"
    completion: "EvidenceTruth"
    provider_transition: ProductionProviderTransition
    birth_boundary: ProductionBoundaryStatus
    queue_exit_boundary: ProductionBoundaryStatus
    next_pass_visibility: ProductionBoundaryStatus
    status: ProductionRuntimeStatus

    @property
    def runtime_open(self) -> bool:
        EvidenceTruth = _truth_enum()
        return any(
            value is EvidenceTruth.UNKNOWN
            for value in (
                self.target_admission,
                self.provider_state,
                self.provider_readiness,
                self.provider_availability,
                self.queue_capacity_control,
                self.queue_total,
                self.pending,
                self.completion,
            )
        )

    @property
    def can_authorize_train(self) -> bool:
        return False


def _truth_from_snapshot(snapshot, expression):
    EvidenceTruth = _truth_enum()
    if expression is None:
        return EvidenceTruth.UNKNOWN
    return snapshot.result_for(expression)


def _tri_all(truths):
    EvidenceTruth = _truth_enum()
    values = tuple(truths)
    if any(value is EvidenceTruth.FALSE for value in values):
        return EvidenceTruth.FALSE
    if any(value is EvidenceTruth.UNKNOWN for value in values):
        return EvidenceTruth.UNKNOWN
    return EvidenceTruth.TRUE


def _boundary_status(truths) -> ProductionBoundaryStatus:
    EvidenceTruth = _truth_enum()
    aggregate = _tri_all(truths)
    if aggregate is EvidenceTruth.TRUE:
        return ProductionBoundaryStatus.OBSERVED
    if aggregate is EvidenceTruth.FALSE:
        return ProductionBoundaryStatus.NOT_OBSERVED
    return ProductionBoundaryStatus.UNKNOWN


def _provider_transition(snapshot, expression):
    EvidenceTruth = _truth_enum()
    if expression is None:
        return ProductionProviderTransition.UNKNOWN
    current = snapshot.result_for(expression)
    previous = snapshot.previous_result_for(expression)
    if current is EvidenceTruth.TRUE and previous is EvidenceTruth.FALSE:
        return ProductionProviderTransition.RECOVERED
    if current is EvidenceTruth.FALSE and previous is EvidenceTruth.TRUE:
        return ProductionProviderTransition.LOST
    if (
        current is not EvidenceTruth.UNKNOWN
        and previous is not EvidenceTruth.UNKNOWN
    ):
        return ProductionProviderTransition.STABLE
    return ProductionProviderTransition.UNKNOWN


def _next_pass_visibility(snapshot, lifecycle: ProductionLifecycle):
    EvidenceTruth = _truth_enum()
    current_completion = snapshot.result_for(lifecycle.completion_witness)
    previous_completion = snapshot.previous_result_for(lifecycle.completion_witness)
    current_pending = snapshot.result_for(lifecycle.pending_fact)
    previous_pending = snapshot.previous_result_for(lifecycle.pending_fact)

    if (
        current_completion is EvidenceTruth.TRUE
        and previous_completion is EvidenceTruth.FALSE
    ):
        return ProductionBoundaryStatus.OBSERVED
    if (
        current_pending is EvidenceTruth.FALSE
        and previous_pending is EvidenceTruth.TRUE
    ):
        return ProductionBoundaryStatus.OBSERVED
    return ProductionBoundaryStatus.UNKNOWN


def _provider_usability(
    admission: "EvidenceTruth",
    provider_state: "EvidenceTruth",
    provider_readiness: "EvidenceTruth",
    provider_availability: "EvidenceTruth",
) -> "EvidenceTruth":
    EvidenceTruth = _truth_enum()
    values = (
        admission,
        provider_state,
        provider_readiness,
        provider_availability,
    )
    if any(value is EvidenceTruth.FALSE for value in values):
        return EvidenceTruth.FALSE
    if any(value is EvidenceTruth.UNKNOWN for value in values):
        return EvidenceTruth.UNKNOWN
    return EvidenceTruth.TRUE


def evaluate_production_runtime(
    identity: str,
    lifecycle: ProductionLifecycle,
    snapshot,
) -> ProductionRuntimeState:
    from .strategy_runtime import EvidenceTruth

    admission = _truth_from_snapshot(snapshot, lifecycle.target_admission.expression)
    provider_state = _truth_from_snapshot(
        snapshot,
        lifecycle.provider_state.expression if lifecycle.provider_state is not None else None,
    )
    provider_readiness = _truth_from_snapshot(
        snapshot,
        (
            lifecycle.provider_readiness_evidence.expression
            if lifecycle.provider_readiness_evidence is not None
            else None
        ),
    )
    provider_availability = _truth_from_snapshot(
        snapshot,
        (
            lifecycle.provider_availability_evidence.expression
            if lifecycle.provider_availability_evidence is not None
            else None
        ),
    )
    queue_capacity_control = _truth_from_snapshot(
        snapshot,
        (
            lifecycle.queue_capacity_control.expression
            if lifecycle.queue_capacity_control is not None
            else None
        ),
    )
    queue_total = _truth_from_snapshot(
        snapshot,
        lifecycle.queue_state.expression if lifecycle.queue_state is not None else None,
    )
    pending = _truth_from_snapshot(snapshot, lifecycle.pending_fact)
    completion = _truth_from_snapshot(snapshot, lifecycle.completion_witness)

    provider_usability = _provider_usability(
        admission,
        provider_state,
        provider_readiness,
        provider_availability,
    )

    if admission is EvidenceTruth.FALSE or provider_usability is EvidenceTruth.FALSE:
        status = ProductionRuntimeStatus.BLOCKED
    elif completion is EvidenceTruth.TRUE:
        status = ProductionRuntimeStatus.COMPLETE
    elif pending is EvidenceTruth.TRUE:
        status = ProductionRuntimeStatus.QUEUED
    elif admission is EvidenceTruth.TRUE and provider_usability is EvidenceTruth.TRUE:
        status = ProductionRuntimeStatus.READY
    else:
        status = ProductionRuntimeStatus.UNKNOWN

    birth_boundary = (
        _boundary_status(
            (
                snapshot.result_for(lifecycle.birth_timing_evidence.time_expression),
                snapshot.result_for(lifecycle.birth_timing_evidence.birth_expression),
            )
        )
        if lifecycle.birth_timing_evidence is not None
        else ProductionBoundaryStatus.UNKNOWN
    )
    queue_exit_boundary = (
        _boundary_status(
            (
                snapshot.result_for(
                    lifecycle.queue_exit_timing_evidence.time_expression
                ),
                snapshot.result_for(
                    lifecycle.queue_exit_timing_evidence.queue_total_expression
                ),
                snapshot.result_for(
                    lifecycle.queue_exit_timing_evidence.pending_expression
                ),
            )
        )
        if lifecycle.queue_exit_timing_evidence is not None
        else ProductionBoundaryStatus.UNKNOWN
    )

    return ProductionRuntimeState(
        identity=identity,
        unit=lifecycle.unit,
        native_unit_id=lifecycle.native_unit_id,
        target_admission=admission,
        provider_state=provider_state,
        provider_readiness=provider_readiness,
        provider_availability=provider_availability,
        provider_usability=provider_usability,
        queue_capacity_control=queue_capacity_control,
        queue_total=queue_total,
        pending=pending,
        completion=completion,
        provider_transition=_provider_transition(
            snapshot,
            lifecycle.provider_state.expression
            if lifecycle.provider_state is not None
            else None,
        ),
        birth_boundary=birth_boundary,
        queue_exit_boundary=queue_exit_boundary,
        next_pass_visibility=_next_pass_visibility(snapshot, lifecycle),
        status=status,
    )


__all__ = [
    "ProductionBoundaryStatus",
    "ProductionProviderTransition",
    "ProductionRuntimeState",
    "ProductionRuntimeStatus",
    "evaluate_production_runtime",
]
