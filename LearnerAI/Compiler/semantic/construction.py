"""Construction lifecycle transition semantics."""
from __future__ import annotations

from ..errors import CompileError
from ..ir.construction import (
    ConstructionObservation,
    ConstructionPhase,
    ConstructionState,
    ConstructionTransitionKind,
    ConstructionTransitionRule,
)
from ..ir.model import LifecycleState
from ..ast import Expression


_CONSTRUCTION_TRANSITION_RULES = (
    ConstructionTransitionRule(
        kind=ConstructionTransitionKind.COMPLETE,
        source_lifecycles=(LifecycleState.ISSUED, LifecycleState.PENDING),
        target=ConstructionState(LifecycleState.COMPLETE, ConstructionPhase.COMPLETE),
        precedence=100,
    ),
    ConstructionTransitionRule(
        kind=ConstructionTransitionKind.FOUNDATION_PENDING,
        source_lifecycles=(LifecycleState.ISSUED, LifecycleState.PENDING),
        target=ConstructionState(
            LifecycleState.PENDING,
            ConstructionPhase.FOUNDATION_PENDING,
        ),
        precedence=90,
    ),
    ConstructionTransitionRule(
        kind=ConstructionTransitionKind.PLACEMENT_PENDING,
        source_lifecycles=(LifecycleState.ISSUED, LifecycleState.PENDING),
        target=ConstructionState(
            LifecycleState.PENDING,
            ConstructionPhase.PLACEMENT_PENDING,
        ),
        precedence=80,
    ),
    ConstructionTransitionRule(
        kind=ConstructionTransitionKind.RETRY,
        source_lifecycles=(LifecycleState.ISSUED, LifecycleState.PENDING),
        target=ConstructionState(LifecycleState.ACTIVE, ConstructionPhase.NONE),
        precedence=70,
    ),
)


def construction_transition_rules() -> tuple[ConstructionTransitionRule, ...]:
    """Return the single deterministic construction transition plan used by lowering."""
    return _CONSTRUCTION_TRANSITION_RULES


def canonical_build_completion_witness(
    building: str,
    witness: Expression,
) -> Expression:
    """Require and canonicalize completed-presence evidence for one build target."""
    if witness.head != "building-type-count" or len(witness.args) != 3:
        raise CompileError(
            f"CONSTRUCTION-WITNESS: build completion witness for target '{building}' "
            "must use building-type-count"
        )
    target, compare_op, value = witness.args
    if not isinstance(target, str) or target != building:
        raise CompileError(
            f"CONSTRUCTION-WITNESS: build completion witness must target '{building}'"
        )
    if (compare_op, value) not in ((">", "0"), (">=", "1")):
        raise CompileError(
            f"CONSTRUCTION-WITNESS: build completion witness for target '{building}' "
            "must establish at least one completed building"
        )
    return Expression(
        source=f"(building-type-count {building} >= 1)",
        head="building-type-count",
        args=(building, ">=", "1"),
        location=witness.location,
    )


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

    if lifecycle not in {
        LifecycleState.ISSUED,
        LifecycleState.PENDING,
    }:
        return ConstructionState(
            lifecycle=lifecycle,
            phase=ConstructionPhase.NONE,
        )

    observations = {
        ConstructionTransitionKind.COMPLETE: observation.completed,
        ConstructionTransitionKind.FOUNDATION_PENDING: observation.foundation_pending,
        ConstructionTransitionKind.PLACEMENT_PENDING: observation.placement_pending,
    }
    for rule in _CONSTRUCTION_TRANSITION_RULES:
        if rule.kind in observations and observations[rule.kind]:
            return rule.target

    return _CONSTRUCTION_TRANSITION_RULES[-1].target


def is_construction_retryable(state: ConstructionState) -> bool:
    return (
        state.lifecycle is LifecycleState.ACTIVE
        and state.phase is ConstructionPhase.NONE
    )


__all__ = [
    "canonical_build_completion_witness",
    "construction_transition_rules",
    "is_construction_retryable",
    "transition_construction",
]
