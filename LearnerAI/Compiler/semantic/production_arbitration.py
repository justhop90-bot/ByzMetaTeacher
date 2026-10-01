"""Compiler-policy production/train arbitration projection.

Phase 1 (ROADMAP): connect ordinary `train` demands carrying a
ProductionLifecycle to the existing ResourceClaim / arbitration system
without inventing a native train conflict class.

What this module knows (new compiler policy):
- an ordinary `train` demand may derive exactly one compiler-policy
  production claim with conflict class TRAIN_ARBITRATION;
- the claim owner is the strategic owner for strategy-lowered demands
  (`StrategicBinding` mapped into the demand source unit, so every
  execution demand of one strategic spec arbitrates together);
- ordinary demands without a strategic binding arbitrate under the shared
  unit execution-memory owner (the `build` convention in `analyzer.py`):
  this keeps ordinary multi-train programs expressible instead of turning
  every pair of unit trains into a spurious ownership conflict;
- the provider UnitId stays provider identity only (the capability bridge
  already names the claimant `{demand}-provider`; this module changes
  nothing about providers, admission, pending, or observations);
- distinct arbitration owners in one conflict class stay separated by the
  existing deterministic RES-006 diagnostic (no silent merge).

What this module explicitly does NOT know (remains OPEN):
- `can-train` stays admission/feasibility only and never authorizes the
  claim on its own (a demand without a `train` action + ProductionLifecycle
  derives nothing);
- `train` stays action issuance only; `up-pending-objects` stays
  duplicate-queue protection; `unit-type-count-total` stays observation;
- provider readiness, provider availability, and queue-capacity control
  (including SN 264) are never arbitration inputs;
- DUC-directed training never inherits ordinary train arbitration
  (DUC requirements mark a demand as DUC-directed and it derives nothing);
- exact DE busy/queue interaction, same-pass arbitration, starvation,
  provider loss, and queue timing remain OPEN runtime research.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Iterator

from ..ast import Expression
from ..ir.model import (
    GoalRole,
    GoalSlotRequest,
    SemanticDemand,
    SemanticId,
    StorageRequestId,
)

#: Compiler-policy conflict class for ordinary production/train arbitration.
#: This class is never attached to the native `train` Primitive
#: (which keeps `conflict_class=None`), so no native pass-constraint or
#: native storage contract is implied. It flows through the existing generic
#: `action-claim:{CLASS}` goal mechanism (`emitter/per.py:_claim_name`).
PRODUCTION_TRAIN_CONFLICT_CLASS = "TRAIN_ARBITRATION"

#: Shared arbitration owner for ordinary (non-strategy-bound) train demands.
#: Mirrors the `build` convention (`analyzer.py` derives build claims under
#: `{source_unit}:__execution_memory__`): the unit's execution memory
#: arbitrates ordinary production, so everyday multi-train programs keep
#: compiling under one deterministic contract.
PRODUCTION_ARBITRATION_EXECUTION_OWNER = "__execution_memory__"

#: Request purpose for the derived production arbitration claim, following
#: the existing `action-claim:{CLASS}` convention (`analyzer.py` build path,
#: `capability_bridge.py`, `emitter/per.py`).
PRODUCTION_TRAIN_CLAIM_PURPOSE = (
    f"action-claim:{PRODUCTION_TRAIN_CONFLICT_CLASS}"
)

#: Native command heads that mark a train demand as DUC-directed. Sourced
#: from the pinned DUC command inventory
#: (`primitives/engine_semantics.py:_DUC_COMMAND_SPECS`, `duc.*` family)
#: plus the point-target consumer recognized by `semantic/duc.py`
#: (`POINT_TARGET_CONSUMERS`). A demand referencing any of these in its
#: requirements, witness, or release expressions trains under DUC direction
#: and must not inherit ordinary train arbitration.
DUC_DIRECTED_COMMAND_HEADS = frozenset(
    {
        "up-can-search",
        "up-get-search-state",
        "up-get-group-size",
        "up-get-cost-delta",
        "up-get-point",
        "up-get-object-data",
        "up-create-group",
        "up-reset-group",
        "up-set-group",
        "up-group-size",
        "up-modify-group-flag",
        "up-get-object-target-data",
        "up-find-local",
        "up-find-status-local",
        "up-find-remote",
        "up-find-status-remote",
        "up-find-resource",
        "up-filter-distance",
        "up-filter-exclude",
        "up-filter-garrison",
        "up-filter-include",
        "up-filter-range",
        "up-filter-status",
        "up-reset-filters",
        "up-reset-search",
        "up-full-reset-search",
        "up-clean-search",
        "up-remove-objects",
        "up-add-object-by-id",
        "up-set-target-by-id",
        "up-set-target-object",
        "up-set-target-point",
        "up-target-objects",
        "up-target-point",
    }
)


def _expression_heads(expression: Expression) -> Iterator[str]:
    """Yield this expression head and every nested argument head."""
    yield expression.head
    for argument in expression.args:
        if isinstance(argument, Expression):
            yield from _expression_heads(argument)


def is_duc_directed_train(demand: SemanticDemand) -> bool:
    """Whether a train demand trains under DUC direction.

    Any DUC search/target/group requirement, witness, or release expression
    marks the demand as DUC-directed. Such demands keep the distinct DUC
    execution path and never inherit ordinary train arbitration.
    """
    if demand.action.expression.head != "train":
        return False
    expressions = (
        tuple(requirement.expression for requirement in demand.requirements)
        + (demand.witness, demand.release)
    )
    return any(
        head in DUC_DIRECTED_COMMAND_HEADS
        for expression in expressions
        for head in _expression_heads(expression)
    )


def production_arbitration_owner(demand: SemanticDemand) -> SemanticId:
    """Resolve the arbitration owner for a production demand.

    Strategy-lowered demands normally arbitrate under their strategic
    identity (mapped into the demand source unit so every execution demand
    of one strategic spec shares one contract). A strategy may explicitly
    set a production-arbitration group to share that contract across
    several distinct strategic demands. Ordinary demands
    arbitrate under the shared unit execution-memory owner, mirroring the
    `build` claim convention. The provider UnitId is never an owner: it
    remains provider identity carried by the lifecycle.
    """
    binding = demand.strategic_binding
    if binding is not None:
        return SemanticId(
            demand.identity.source_unit,
            binding.production_arbitration_group
            or binding.strategic_id,
        )
    return SemanticId(
        demand.identity.source_unit,
        PRODUCTION_ARBITRATION_EXECUTION_OWNER,
    )


def production_arbitration_request(
    demand: SemanticDemand,
) -> GoalSlotRequest | None:
    """Derive the compiler-policy arbitration request for one demand.

    Returns None (no claim) unless every condition holds:
    - the action is an ordinary `train` issuance;
    - the demand carries a ProductionLifecycle (admission alone, pending
      alone, or observation alone never authorizes a claim);
    - no arbitration request already exists (derivation never overwrites);
    - the demand is not DUC-directed.
    """
    if demand.action.expression.head != "train":
        return None
    if demand.production_lifecycle is None:
        return None
    if demand.action.arbitration_request is not None:
        return None
    if is_duc_directed_train(demand):
        return None
    return GoalSlotRequest(
        request_id=StorageRequestId(
            owner=production_arbitration_owner(demand),
            purpose=PRODUCTION_TRAIN_CLAIM_PURPOSE,
        ),
        role=GoalRole.EXECUTION_MEMORY,
    )


def derive_production_arbitration(
    demands: Iterable[SemanticDemand],
) -> list[SemanticDemand]:
    """Project ordinary train demands into the arbitration graph.

    Pure, order-preserving, idempotent: demands that already carry an
    arbitration request (including native `build` claims) pass through
    untouched, and running the projection twice changes nothing.
    """
    derived: list[SemanticDemand] = []
    for demand in demands:
        request = production_arbitration_request(demand)
        if request is None:
            derived.append(demand)
            continue
        derived.append(
            replace(
                demand,
                action=replace(
                    demand.action,
                    arbitration_request=request,
                ),
            )
        )
    return derived


__all__ = [
    "DUC_DIRECTED_COMMAND_HEADS",
    "PRODUCTION_ARBITRATION_EXECUTION_OWNER",
    "PRODUCTION_TRAIN_CLAIM_PURPOSE",
    "PRODUCTION_TRAIN_CONFLICT_CLASS",
    "derive_production_arbitration",
    "is_duc_directed_train",
    "production_arbitration_owner",
    "production_arbitration_request",
]
