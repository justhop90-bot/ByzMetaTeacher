"""Typed capability/admissibility semantic IR for Basilisk."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .resource import ResourceClaim

from ..ast import Expression, SourceLocation
from .model import LifecycleStorage, SemanticId
from .strategy import StrategicBinding


class CapabilityKind(str, Enum):
    ECONOMIC = "ECONOMIC"
    CONSTRUCTION = "CONSTRUCTION"
    PRODUCTION = "PRODUCTION"
    RESEARCH = "RESEARCH"
    MILITARY = "MILITARY"
    OBSERVED = "OBSERVED"


class ProviderKind(str, Enum):
    OBSERVATION = "OBSERVATION"
    CONSTRUCTION = "CONSTRUCTION"
    PRODUCTION = "PRODUCTION"
    RESEARCH = "RESEARCH"
    ECONOMIC = "ECONOMIC"
    MILITARY = "MILITARY"


class PredicateKind(str, Enum):
    OBSERVATION = "OBSERVATION"
    FEASIBILITY = "FEASIBILITY"
    RESOURCE = "RESOURCE"
    ARBITRATION = "ARBITRATION"
    OWNERSHIP = "OWNERSHIP"
    STRATEGY = "STRATEGY"
    DEPENDENCY = "DEPENDENCY"
    ADMISSIBILITY = "ADMISSIBILITY"
    TIMING = "TIMING"
    WITNESS = "WITNESS"


class WitnessKind(str, Enum):
    WORLD_STATE = "WORLD_STATE"
    OBJECT_STATE = "OBJECT_STATE"
    COUNT_STATE = "COUNT_STATE"
    RESEARCH_STATE = "RESEARCH_STATE"


class EdgeKind(str, Enum):
    DEMAND_REQUIRES = "DEMAND_REQUIRES"
    CAPABILITY_PROVIDED_BY = "CAPABILITY_PROVIDED_BY"
    PROVIDER_REQUIRES = "PROVIDER_REQUIRES"
    PROVIDER_GUARDED_BY = "PROVIDER_GUARDED_BY"
    PROVIDER_ISSUES = "PROVIDER_ISSUES"
    PROVIDER_WITNESSED_BY = "PROVIDER_WITNESSED_BY"
    WITNESS_ESTABLISHES = "WITNESS_ESTABLISHES"
    DEMAND_RELEASES = "DEMAND_RELEASES"


@dataclass(frozen=True, order=True)
class CapabilityId:
    source_unit: str
    local_name: str


@dataclass(frozen=True, order=True)
class ProviderId:
    source_unit: str
    local_name: str


@dataclass(frozen=True, order=True)
class DemandId:
    source_unit: str
    local_name: str


@dataclass(frozen=True, order=True)
class WitnessId:
    source_unit: str
    local_name: str


NodeId: TypeAlias = CapabilityId | ProviderId | DemandId | WitnessId


@dataclass(frozen=True)
class PredicateAtom:
    kind: PredicateKind
    primitive: str
    arguments: tuple[object, ...]
    expression: Expression


@dataclass(frozen=True)
class Predicate:
    all_of: tuple["PredicateNode", ...] = ()
    any_of: tuple["PredicateNode", ...] = ()
    negated: bool = False


PredicateNode: TypeAlias = PredicateAtom | Predicate


@dataclass(frozen=True)
class ActionSpec:
    primitive: str
    arguments: tuple[object, ...]
    issue_guards: tuple[PredicateNode, ...] = ()
    conflict_class: str | None = None
    arbitration: tuple[SemanticId, ...] = ()
    retryable: bool = True
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CompletionWitness:
    identity: WitnessId
    kind: WitnessKind
    predicate: PredicateNode
    establishes: CapabilityId
    location: SourceLocation | None = None


@dataclass(frozen=True)
class Capability:
    identity: CapabilityId
    kind: CapabilityKind
    providers: tuple[ProviderId, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CapabilityProvider:
    identity: ProviderId
    capability: CapabilityId
    kind: ProviderKind
    prerequisites: tuple[CapabilityId, ...] = ()
    admissibility: PredicateNode | None = None
    action: ActionSpec | None = None
    witness: WitnessId | None = None
    resource_claim: "ResourceClaim | None" = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CapabilityDemand:
    identity: DemandId
    target: CapabilityId
    lifecycle: LifecycleStorage
    activation: tuple[PredicateNode, ...] = ()
    release: tuple[PredicateNode, ...] = ()
    owner: SemanticId | None = None
    strategic_binding: StrategicBinding | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class GraphEdge:
    source: NodeId
    target: NodeId
    kind: EdgeKind
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CapabilityGraph:
    demands: tuple[CapabilityDemand, ...]
    capabilities: tuple[Capability, ...]
    providers: tuple[CapabilityProvider, ...]
    witnesses: tuple[CompletionWitness, ...]
    edges: tuple[GraphEdge, ...] = ()

    def _index(self, values, identity):
        return tuple(item for item in values if item.identity == identity)

    def demands_for(self, identity: DemandId) -> tuple[CapabilityDemand, ...]:
        return self._index(self.demands, identity)

    def capabilities_for(self, identity: CapabilityId) -> tuple[Capability, ...]:
        return self._index(self.capabilities, identity)

    def providers_for(self, identity: ProviderId) -> tuple[CapabilityProvider, ...]:
        return self._index(self.providers, identity)

    def witnesses_for(self, identity: WitnessId) -> tuple[CompletionWitness, ...]:
        return self._index(self.witnesses, identity)

    def providers_of(
        self,
        capability: CapabilityId,
    ) -> tuple[CapabilityProvider, ...]:
        return tuple(
            provider
            for provider in self.providers
            if provider.capability == capability
        )

    def demands_for_capability(
        self,
        capability: CapabilityId,
    ) -> tuple[CapabilityDemand, ...]:
        return tuple(
            demand
            for demand in self.demands
            if demand.target == capability
        )

    def witnesses_for_capability(
        self,
        capability: CapabilityId,
    ) -> tuple[CompletionWitness, ...]:
        return tuple(
            witness
            for witness in self.witnesses
            if witness.establishes == capability
        )

    def prerequisites_of(
        self,
        provider: CapabilityProvider,
    ) -> tuple[Capability, ...]:
        return tuple(
            capability
            for prerequisite in provider.prerequisites
            for capability in self.capabilities_for(prerequisite)
        )

    def capability_ids(self) -> tuple[CapabilityId, ...]:
        return tuple(
            sorted({capability.identity for capability in self.capabilities})
        )


class CapabilityGraphBuilder:
    """Mutable construction surface; build() returns a deterministic immutable graph."""

    def __init__(self) -> None:
        self._demands: list[CapabilityDemand] = []
        self._capabilities: list[Capability] = []
        self._providers: list[CapabilityProvider] = []
        self._witnesses: list[CompletionWitness] = []
        self._edges: list[GraphEdge] = []

    def add_demand(self, demand: CapabilityDemand) -> None:
        self._demands.append(demand)

    def add_capability(self, capability: Capability) -> None:
        self._capabilities.append(capability)

    def add_provider(self, provider: CapabilityProvider) -> None:
        self._providers.append(provider)

    def add_witness(self, witness: CompletionWitness) -> None:
        self._witnesses.append(witness)

    def connect(
        self,
        source: NodeId,
        target: NodeId,
        kind: EdgeKind,
        location: SourceLocation | None = None,
    ) -> None:
        self._edges.append(GraphEdge(source, target, kind, location))

    def _derived_edges(self) -> list[GraphEdge]:
        edges: list[GraphEdge] = []

        for demand in self._demands:
            edges.append(
                GraphEdge(
                    demand.identity,
                    demand.target,
                    EdgeKind.DEMAND_REQUIRES,
                    demand.location,
                )
            )
            if demand.release:
                edges.append(
                    GraphEdge(
                        demand.identity,
                        demand.target,
                        EdgeKind.DEMAND_RELEASES,
                        demand.location,
                    )
                )

        capability_locations = {
            capability.identity: capability.location
            for capability in self._capabilities
        }
        for provider in self._providers:
            edges.append(
                GraphEdge(
                    provider.capability,
                    provider.identity,
                    EdgeKind.CAPABILITY_PROVIDED_BY,
                    capability_locations.get(provider.capability),
                )
            )

        for provider in self._providers:
            for prerequisite in provider.prerequisites:
                edges.append(
                    GraphEdge(
                        provider.identity,
                        prerequisite,
                        EdgeKind.PROVIDER_REQUIRES,
                        provider.location,
                    )
                )
            if provider.witness is not None:
                edges.append(
                    GraphEdge(
                        provider.identity,
                        provider.witness,
                        EdgeKind.PROVIDER_WITNESSED_BY,
                        provider.location,
                    )
                )

        for witness in self._witnesses:
            edges.append(
                GraphEdge(
                    witness.identity,
                    witness.establishes,
                    EdgeKind.WITNESS_ESTABLISHES,
                    witness.location,
                )
            )

        return edges

    @staticmethod
    def _sort_key(item) -> tuple[str, str]:
        identity = item.identity
        return (identity.source_unit, identity.local_name)

    def build(self) -> CapabilityGraph:
        capability_by_id: dict[CapabilityId, Capability] = {}
        for capability in self._capabilities:
            existing = capability_by_id.get(capability.identity)
            if existing is not None:
                if existing.kind is not capability.kind:
                    raise ValueError(
                        f"capability '{capability.identity.source_unit}:{capability.identity.local_name}' "
                        f"has conflicting kinds {existing.kind.value} and {capability.kind.value}"
                    )
                continue
            capability_by_id[capability.identity] = capability

        provider_ids_by_capability: dict[CapabilityId, tuple[ProviderId, ...]] = {
            identity: ()
            for identity in capability_by_id
        }
        for provider in self._providers:
            provider_ids_by_capability[provider.capability] = tuple(
                sorted(
                    (
                        *provider_ids_by_capability.get(provider.capability, ()),
                        provider.identity,
                    )
                )
            )

        capabilities = tuple(
            sorted(
                (
                    Capability(
                        identity=capability.identity,
                        kind=capability.kind,
                        providers=provider_ids_by_capability.get(capability.identity, ()),
                        location=capability.location,
                    )
                    for capability in capability_by_id.values()
                ),
                key=self._sort_key,
            )
        )

        derived = self._derived_edges()
        edges = tuple(
            sorted(
                self._edges + derived,
                key=lambda edge: (
                    edge.kind.value,
                    type(edge.source).__name__,
                    getattr(edge.source, "source_unit", ""),
                    getattr(edge.source, "local_name", ""),
                    type(edge.target).__name__,
                    getattr(edge.target, "source_unit", ""),
                    getattr(edge.target, "local_name", ""),
                ),
            )
        )
        return CapabilityGraph(
            demands=tuple(sorted(self._demands, key=self._sort_key)),
            capabilities=capabilities,
            providers=tuple(sorted(self._providers, key=self._sort_key)),
            witnesses=tuple(sorted(self._witnesses, key=self._sort_key)),
            edges=edges,
        )
