"""Construction lifecycle transition semantics."""
from __future__ import annotations

from ..ir.construction import (
    ConstructionObservation,
    ConstructionPhase,
    ConstructionState,
)
from ..ir.model import LifecycleState


def transition_construction(
    lifecycle: LifecycleState,
    observation: ConstructionObservation,
) -> ConstructionState:
    """Apply native construction observations in deterministic precedence order."""
    if observation.invalidated and lifecycle in {
        LifecycleState.ACTIVE,
        LifecycleState.ISSUED,
        LifecycleState.PENDING,
    }:
        return ConstructionState(
            lifecycle=LifecycleState.CANCELLED,
            phase=ConstructionPhase.NONE,
        )

    if lifecycle is LifecycleState.COMPLETE:
        return ConstructionState(
            lifecycle=LifecycleState.COMPLETE,
            phase=ConstructionPhase.COMPLETE,
        )

    if lifecycle not in {LifecycleState.ISSUED, LifecycleState.PENDING}:
        return ConstructionState(
            lifecycle=lifecycle,
            phase=ConstructionPhase.NONE,
        )

    if observation.completed:
        return ConstructionState(
            lifecycle=LifecycleState.COMPLETE,
            phase=ConstructionPhase.COMPLETE,
        )

    if observation.foundation_pending:
        return ConstructionState(
            lifecycle=LifecycleState.PENDING,
            phase=ConstructionPhase.FOUNDATION_PENDING,
        )

    if observation.placement_pending:
        return ConstructionState(
            lifecycle=LifecycleState.PENDING,
            phase=ConstructionPhase.PLACEMENT_PENDING,
        )

    # No stronger native witness remains. Re-enter the original demand's
    # ACTIVE state so its normal issuance path can retry on a later pass.
    return ConstructionState(
        lifecycle=LifecycleState.ACTIVE,
        phase=ConstructionPhase.NONE,
    )


def is_construction_retryable(state: ConstructionState) -> bool:
    return (
        state.lifecycle is LifecycleState.ACTIVE
        and state.phase is ConstructionPhase.NONE
    )


__all__ = [
    "is_construction_retryable",
    "transition_construction",
]
