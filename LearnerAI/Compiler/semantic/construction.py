"""Construction lifecycle transition semantics."""
from __future__ import annotations

from dataclasses import replace

from ..errors import CompileError
from ..ir.construction import (
    ConstructionObservation,
    ConstructionPhase,
    ConstructionState,
    ConstructionTransitionKind,
    ConstructionTransitionRule,
)
from ..ir.model import LifecycleState, SemanticDemand
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
    *,
    demand_name: str | None = None,
) -> Expression:
    """Require and canonicalize completed-presence evidence for one build target."""
    subject = (
        f"demand '{demand_name}' build completion witness"
        if demand_name is not None
        else "build completion witness"
    )
    if witness.head != "building-type-count" or len(witness.args) != 3:
        raise CompileError(
            f"CONSTRUCTION-WITNESS: {subject} must use building-type-count"
        )
    target, compare_op, value = witness.args
    if not isinstance(target, str) or target != building:
        raise CompileError(
            f"CONSTRUCTION-WITNESS: {subject} must target '{building}'"
        )
    if compare_op == ">":
        if value != "0":
            raise CompileError(
                f"CONSTRUCTION-WITNESS: {subject} must establish at least one completed building"
            )
        minimum = 1
    elif compare_op == ">=":
        try:
            minimum = int(value)
        except (TypeError, ValueError):
            minimum = 0
        if minimum < 1:
            raise CompileError(
                f"CONSTRUCTION-WITNESS: {subject} must establish at least one completed building"
            )
    else:
        raise CompileError(
            f"CONSTRUCTION-WITNESS: {subject} must establish at least one completed building"
        )
    return Expression(
        source=f"(building-type-count {building} >= {minimum})",
        head="building-type-count",
        args=(building, ">=", str(minimum)),
        location=witness.location,
    )


def canonicalize_construction_witnesses(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> tuple[SemanticDemand, ...]:
    """Canonicalize build witnesses after generic witness validation has passed."""
    result: list[SemanticDemand] = []
    for demand in demands:
        if demand.construction_lifecycle is None:
            result.append(demand)
            continue
        canonical = canonical_build_completion_witness(
            demand.construction_lifecycle.building,
            demand.witness,
            demand_name=demand.identity.local_name,
        )
        completion_witness = demand.completion_witness
        if completion_witness is None:
            raise CompileError(
                f"CONSTRUCTION-WITNESS: demand '{demand.name}' has no completion witness contract"
            )
        construction = replace(
            demand.construction_lifecycle,
            completion_witness=canonical,
        )
        result.append(
            replace(
                demand,
                witness=canonical,
                completion_witness=replace(
                    completion_witness,
                    primitive=canonical.head,
                    expression=canonical,
                ),
                construction_lifecycle=construction,
            )
        )
    return tuple(result)


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
    "canonicalize_construction_witnesses",
    "construction_transition_rules",
    "is_construction_retryable",
    "transition_construction",
]
