"""Projection from the current demand IR into the typed capability graph."""
from __future__ import annotations

from ..ast import Expression
from ..errors import CompileError
from ..ir import SemanticDemand
from ..ir.resource import ResourceClaim, ResourceClaimId, ResourceKind, ResourceScope
from ..ir.capability import (
    ActionSpec,
    Capability,
    CapabilityDemand,
    CapabilityGraph,
    CapabilityGraphBuilder,
    CapabilityId,
    CapabilityKind,
    CapabilityProvider,
    CompletionWitness,
    DemandId,
    Predicate,
    PredicateAtom,
    PredicateKind,
    PredicateNode,
    ProviderId,
    ProviderKind,
    WitnessId,
    WitnessKind,
)
from ..primitives import PrimitiveRegistry
from .capability_validation import ValidationReport, validate_capability_graph

_LOGICAL_HEADS = {"and", "or", "nand", "nor", "xor", "xnor", "not"}

_ROLE_TO_KIND = {
    "OBSERVATION": PredicateKind.OBSERVATION,
    "TIMING": PredicateKind.TIMING,
    "ADMISSIBILITY": PredicateKind.ADMISSIBILITY,
    "FEASIBILITY": PredicateKind.FEASIBILITY,
    "RESOURCE_ARBITRATION": PredicateKind.RESOURCE,
    "WITNESS": PredicateKind.WITNESS,
}

_ACTION_TYPES = {
    "build": (CapabilityKind.CONSTRUCTION, ProviderKind.CONSTRUCTION),
    "train": (CapabilityKind.PRODUCTION, ProviderKind.PRODUCTION),
    "research": (CapabilityKind.RESEARCH, ProviderKind.RESEARCH),
}


def _predicate(expr: Expression, registry: PrimitiveRegistry) -> PredicateNode:
    if expr.head in _LOGICAL_HEADS:
        children = tuple(
            _predicate(child, registry)
            for child in expr.args
            if isinstance(child, Expression)
        )
        if len(children) != len(expr.args):
            raise CompileError(
                f"capability bridge: logical operator '{expr.head}' has non-expression operands"
            )
        if expr.head == "and":
            return Predicate(all_of=children)
        if expr.head == "or":
            return Predicate(any_of=children)
        if expr.head == "nand":
            return Predicate(all_of=children, negated=True)
        if expr.head == "nor":
            return Predicate(any_of=children, negated=True)
        if expr.head == "xor":
            return Predicate(
                all_of=(
                    Predicate(any_of=children),
                    Predicate(all_of=children, negated=True),
                )
            )
        if expr.head == "xnor":
            return Predicate(
                all_of=(
                    Predicate(any_of=children),
                    Predicate(all_of=children, negated=True),
                ),
                negated=True,
            )
        return Predicate(all_of=(children[0],), negated=True)

    primitive = registry.require(expr.head)
    kind = _ROLE_TO_KIND.get(primitive.role)
    if kind is None:
        raise CompileError(
            f"capability bridge: primitive '{expr.head}' role '{primitive.role}' "
            "has no capability predicate kind"
        )
    return PredicateAtom(
        kind=kind,
        primitive=expr.head,
        arguments=tuple(expr.args),
        expression=expr,
    )


def _all_of(predicates: tuple[PredicateNode, ...]) -> PredicateNode | None:
    if not predicates:
        return None
    if len(predicates) == 1:
        return predicates[0]
    return Predicate(all_of=predicates)


def _provider_shape(action_primitive: str) -> tuple[CapabilityKind, ProviderKind]:
    try:
        return _ACTION_TYPES[action_primitive]
    except KeyError as exc:
        raise CompileError(
            f"capability bridge: action primitive '{action_primitive}' has no provider mapping"
        ) from exc


def project_capability_graph(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> CapabilityGraph:
    """Project today's demand IR without inventing a second source language."""
    builder = CapabilityGraphBuilder()

    for demand in demands:
        capability_id = CapabilityId(
            demand.identity.source_unit,
            demand.identity.local_name,
        )
        action_kind, provider_kind = _provider_shape(demand.action.expression.head)

        requirements = tuple(
            _predicate(requirement.expression, registry)
            for requirement in demand.requirements
        )
        admissibility = _all_of(requirements)

        witness_predicate = _predicate(demand.witness, registry)
        release_predicate = _predicate(demand.release, registry)

        provider_id = ProviderId(
            demand.identity.source_unit,
            f"{demand.identity.local_name}-provider",
        )
        witness_id = WitnessId(
            demand.identity.source_unit,
            f"{demand.identity.local_name}-witness",
        )

        arbitration_request = demand.action.arbitration_request
        conflict_class = None
        arbitration = ()
        if arbitration_request is not None:
            conflict_class = arbitration_request.request_id.purpose.split(":", 1)[1]
            arbitration = (arbitration_request.request_id.owner,)

        builder.add_capability(
            Capability(
                identity=capability_id,
                kind=action_kind,
            )
        )
        builder.add_witness(
            CompletionWitness(
                identity=witness_id,
                kind=WitnessKind.WORLD_STATE,
                predicate=witness_predicate,
                establishes=capability_id,
            )
        )
        resource_claim = None
        if conflict_class is not None and len(arbitration) == 1:
            resource_claim = ResourceClaim(
                identity=ResourceClaimId(
                    demand.identity.source_unit,
                    f"{demand.identity.local_name}-resource-claim",
                ),
                kind=ResourceKind.ACTION_EXCLUSION,
                scope=ResourceScope.TRANSIENT,
                claimant=demand.identity,
                conflict_class=conflict_class,
                arbitration_owner=arbitration[0],
            )
        builder.add_provider(
            CapabilityProvider(
                identity=provider_id,
                capability=capability_id,
                kind=provider_kind,
                admissibility=admissibility,
                action=ActionSpec(
                    primitive=demand.action.expression.head,
                    arguments=tuple(demand.action.expression.args),
                    issue_guards=requirements,
                    conflict_class=conflict_class,
                    arbitration=arbitration,
                ),
                witness=witness_id,
                resource_claim=resource_claim,
            )
        )
        builder.add_demand(
            CapabilityDemand(
                identity=DemandId(
                    demand.identity.source_unit,
                    demand.identity.local_name,
                ),
                target=capability_id,
                lifecycle=demand.lifecycle,
                activation=requirements,
                release=(release_predicate,),
                owner=demand.identity,
            )
        )

    return builder.build()


def validate_projected_capabilities(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    registry: PrimitiveRegistry,
) -> ValidationReport:
    graph = project_capability_graph(demands, registry)
    return validate_capability_graph(graph, registry)
