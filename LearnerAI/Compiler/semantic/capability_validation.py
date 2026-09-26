"""Validation passes for Basilisk capability/admissibility graphs."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from ..ast import SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..primitives import PrimitiveRegistry
from ..ir.capability import (
    CapabilityDemand,
    CapabilityGraph,
    CapabilityId,
    CapabilityProvider,
    DemandId,
    NodeId,
    Predicate,
    PredicateAtom,
    PredicateNode,
    PredicateKind,
    ProviderKind,
    WitnessId,
)


class GraphStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DEAD_END = "DEAD-END"
    UNFED = "UNFED"
    BLOCKED = "BLOCKED"
    FUNCTIONALLY_DISCONNECTED = "FUNCTIONALLY-DISCONNECTED"
    OPEN_LOOP = "OPEN-LOOP"
    UNFINISHED = "UNFINISHED"
    DUPLICATE_CONFLICTING = "DUPLICATE-CONFLICTING"


class CapabilityDiagnosticCode(str, Enum):
    UNKNOWN_CAPABILITY = "CAP-001"
    PROVIDERLESS_CAPABILITY = "CAP-002"
    UNKNOWN_PREREQUISITE = "CAP-003"
    PROVIDER_NO_WITNESS = "CAP-004"
    WITNESS_NOT_ESTABLISHING = "CAP-005"
    PROVIDER_ACTION_MISSING = "CAP-006"
    ACTION_NOT_NATIVE = "CAP-007"
    INVALID_ADMISSIBILITY = "CAP-008"
    DUPLICATE_CONFLICTING = "CAP-025"

    UNFED = "CAP-020"
    DEAD_END = "CAP-021"
    CYCLE = "CAP-022"
    OPEN_LOOP = "CAP-023"
    FUNCTIONALLY_DISCONNECTED = "CAP-024"

    PROVIDER_BLOCKED = "CAP-040"
    FEASIBILITY_MISSING = "CAP-041"
    TIMING_ONLY_ADMISSIBILITY = "CAP-042"
    INVALID_RESOURCE_ARBITRATION = "CAP-043"
    CONFLICT_NO_ARBITRATION = "CAP-044"

    ACTION_WITNESS_MISMATCH = "CAP-060"
    WITNESS_ACTION_COUPLING = "CAP-061"
    TIMING_CANNOT_WITNESS = "CAP-062"
    RELEASE_NO_COMPLETION_PATH = "CAP-063"
    PENDING_NO_WITNESS = "CAP-064"
    ISSUANCE_AMBIGUOUS = "CAP-065"
    WITNESS_NO_WORLD_STATE = "CAP-066"
    TIMING_RELEASE_WITHOUT_WORLD_EVIDENCE = "CAP-067"
    DEMAND_MISSING_OWNER = "CAP-068"
    TIMING_ONLY_ACTIVATION = "CAP-069"


@dataclass(frozen=True)
class GraphDiagnostic:
    code: CapabilityDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    status: GraphStatus | None = None
    node: NodeId | None = None
    related: tuple[NodeId, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ValidationContext:
    graph: CapabilityGraph
    primitive_registry: PrimitiveRegistry


@dataclass(frozen=True)
class ValidationReport:
    diagnostics: tuple[GraphDiagnostic, ...]

    @property
    def errors(self) -> tuple[GraphDiagnostic, ...]:
        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is DiagnosticSeverity.ERROR
        )

    @property
    def valid(self) -> bool:
        return not self.errors


class ValidationPass(Protocol):
    name: str

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        ...


def _node_key(node: NodeId | None) -> tuple[str, str, str]:
    if node is None:
        return ("", "", "")
    return (
        type(node).__name__,
        getattr(node, "source_unit", ""),
        getattr(node, "local_name", ""),
    )


def _diagnostic_key(diagnostic: GraphDiagnostic) -> tuple[object, ...]:
    location = diagnostic.location
    line = getattr(location, "line", 0) if location is not None else 0
    column = getattr(location, "column", 0) if location is not None else 0
    return (
        line,
        column,
        diagnostic.code.value,
        _node_key(diagnostic.node),
        tuple(_node_key(node) for node in diagnostic.related),
        diagnostic.message,
    )


def _diag(
    code: CapabilityDiagnosticCode,
    message: str,
    *,
    node: NodeId | None = None,
    related: Iterable[NodeId] = (),
    status: GraphStatus | None = None,
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    location: SourceLocation | None = None,
) -> GraphDiagnostic:
    return GraphDiagnostic(
        code=code,
        severity=severity,
        message=message,
        status=status,
        node=node,
        related=tuple(sorted(related, key=_node_key)),
        location=location,
    )


def _atoms(node: PredicateNode) -> tuple[PredicateAtom, ...]:
    if isinstance(node, PredicateAtom):
        return (node,)
    atoms: list[PredicateAtom] = []
    for child in node.all_of:
        atoms.extend(_atoms(child))
    for child in node.any_of:
        atoms.extend(_atoms(child))
    return tuple(atoms)


def _kinds(node: PredicateNode | None) -> frozenset[PredicateKind]:
    if node is None:
        return frozenset()
    return frozenset(atom.kind for atom in _atoms(node))


def _contains_kind(
    predicates: Iterable[PredicateNode],
    kind: PredicateKind,
) -> bool:
    return any(kind in _kinds(predicate) for predicate in predicates)


def _has_operational_evidence(kinds: frozenset[PredicateKind]) -> bool:
    return bool(
        kinds
        & {
            PredicateKind.OBSERVATION,
            PredicateKind.FEASIBILITY,
            PredicateKind.RESOURCE,
            PredicateKind.ARBITRATION,
            PredicateKind.OWNERSHIP,
            PredicateKind.STRATEGY,
            PredicateKind.DEPENDENCY,
        }
    )


def _is_statically_false(node: PredicateNode | None) -> bool:
    if not isinstance(node, Predicate):
        return False
    return (
        not node.all_of
        and not node.any_of
        and node.negated
    )


def _validate_predicate_primitives(
    node: PredicateNode | None,
    registry: PrimitiveRegistry,
) -> tuple[str, ...]:
    if node is None:
        return ()
    errors: list[str] = []
    for atom in _atoms(node):
        primitive = registry.get(atom.primitive)
        if primitive is None:
            errors.append(f"unknown primitive '{atom.primitive}'")
            continue
        try:
            registry.validate_native_signature(
                atom.primitive,
                len(atom.expression.args),
            )
            registry.validate_adapter_contract(primitive)
        except (KeyError, ValueError) as exc:
            errors.append(str(exc))
    return tuple(errors)


class StructuralValidationPass:
    name = "structural"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        diagnostics: list[GraphDiagnostic] = []

        for identity, items, label in (
            (
                "demand",
                graph.demands,
                lambda item: item.identity,
            ),
            (
                "capability",
                graph.capabilities,
                lambda item: item.identity,
            ),
            (
                "provider",
                graph.providers,
                lambda item: item.identity,
            ),
            (
                "witness",
                graph.witnesses,
                lambda item: item.identity,
            ),
        ):
            _ = identity
            seen: dict[object, object] = {}
            for item in items:
                key = label(item)
                if key in seen:
                    diagnostics.append(
                        _diag(
                            CapabilityDiagnosticCode.DUPLICATE_CONFLICTING,
                            f"duplicate {identity} identity '{key.source_unit}:{key.local_name}'",
                            node=key,
                            status=GraphStatus.DUPLICATE_CONFLICTING,
                            location=getattr(item, "location", None),
                        )
                    )
                else:
                    seen[key] = item

        capability_ids = {
            capability.identity for capability in graph.capabilities
        }
        witness_ids = {
            witness.identity for witness in graph.witnesses
        }

        for demand in graph.demands:
            if demand.owner is None:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.DEMAND_MISSING_OWNER,
                        f"demand '{demand.identity.local_name}' has no semantic owner",
                        node=demand.identity,
                        location=demand.location,
                    )
                )
            if demand.target not in capability_ids:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.UNKNOWN_CAPABILITY,
                        f"demand '{demand.identity.local_name}' references unknown capability "
                        f"'{demand.target.local_name}'",
                        node=demand.identity,
                        status=GraphStatus.UNFED,
                        location=demand.location,
                    )
                )

        for provider in graph.providers:
            if provider.capability not in capability_ids:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.UNKNOWN_CAPABILITY,
                        f"provider '{provider.identity.local_name}' targets unknown capability "
                        f"'{provider.capability.local_name}'",
                        node=provider.identity,
                        status=GraphStatus.DEAD_END,
                        location=provider.location,
                    )
                )
            for prerequisite in provider.prerequisites:
                if prerequisite not in capability_ids:
                    diagnostics.append(
                        _diag(
                            CapabilityDiagnosticCode.UNKNOWN_PREREQUISITE,
                            f"provider '{provider.identity.local_name}' references unknown "
                            f"prerequisite '{prerequisite.local_name}'",
                            node=provider.identity,
                            related=(prerequisite,),
                            status=GraphStatus.DEAD_END,
                            location=provider.location,
                        )
                    )
            if provider.witness is not None and provider.witness not in witness_ids:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.PROVIDER_NO_WITNESS,
                        f"provider '{provider.identity.local_name}' references missing witness "
                        f"'{provider.witness.local_name}'",
                        node=provider.identity,
                        status=GraphStatus.OPEN_LOOP,
                        location=provider.location,
                    )
                )

        for witness in graph.witnesses:
            if witness.establishes not in capability_ids:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.UNKNOWN_CAPABILITY,
                        f"witness '{witness.identity.local_name}' establishes unknown "
                        f"capability '{witness.establishes.local_name}'",
                        node=witness.identity,
                        status=GraphStatus.DEAD_END,
                        location=witness.location,
                    )
                )

        return tuple(diagnostics)


class ProviderContractValidationPass:
    name = "provider-contract"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        registry = context.primitive_registry
        diagnostics: list[GraphDiagnostic] = []

        for provider in graph.providers:
            if provider.action is None:
                if provider.kind is not ProviderKind.OBSERVATION:
                    diagnostics.append(
                        _diag(
                            CapabilityDiagnosticCode.PROVIDER_ACTION_MISSING,
                            f"provider '{provider.identity.local_name}' has no action",
                            node=provider.identity,
                            status=GraphStatus.DEAD_END,
                            location=provider.location,
                        )
                    )
            else:
                primitive = registry.get(provider.action.primitive)
                if primitive is None:
                    diagnostics.append(
                        _diag(
                            CapabilityDiagnosticCode.ACTION_NOT_NATIVE,
                            f"provider '{provider.identity.local_name}' uses unknown action "
                            f"'{provider.action.primitive}'",
                            node=provider.identity,
                            status=GraphStatus.DEAD_END,
                            location=provider.action.location or provider.location,
                        )
                    )
                else:
                    if primitive.kind != "ACTION":
                        diagnostics.append(
                            _diag(
                                CapabilityDiagnosticCode.ACTION_NOT_NATIVE,
                                f"provider '{provider.identity.local_name}' action "
                                f"'{provider.action.primitive}' is not an action primitive",
                                node=provider.identity,
                                status=GraphStatus.DEAD_END,
                                location=provider.action.location or provider.location,
                            )
                        )
                    try:
                        registry.validate_native_signature(
                            provider.action.primitive,
                            len(provider.action.arguments),
                        )
                        registry.validate_adapter_contract(primitive)
                    except (KeyError, ValueError) as exc:
                        diagnostics.append(
                            _diag(
                                CapabilityDiagnosticCode.ACTION_NOT_NATIVE,
                                f"provider '{provider.identity.local_name}': {exc}",
                                node=provider.identity,
                                status=GraphStatus.DEAD_END,
                                location=provider.action.location or provider.location,
                            )
                        )

                if provider.action.conflict_class and not provider.action.arbitration:
                    diagnostics.append(
                        _diag(
                            CapabilityDiagnosticCode.CONFLICT_NO_ARBITRATION,
                            f"provider '{provider.identity.local_name}' declares conflict class "
                            f"'{provider.action.conflict_class}' without arbitration ownership",
                            node=provider.identity,
                            status=GraphStatus.BLOCKED,
                            location=provider.action.location or provider.location,
                        )
                    )

            if provider.witness is None:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.PROVIDER_NO_WITNESS,
                        f"provider '{provider.identity.local_name}' has no completion witness",
                        node=provider.identity,
                        status=GraphStatus.OPEN_LOOP,
                        location=provider.location,
                    )
                )

            if provider.admissibility is None and provider.action is not None:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.FEASIBILITY_MISSING,
                        f"provider '{provider.identity.local_name}' has an action but no "
                        "admissibility predicate",
                        node=provider.identity,
                        status=GraphStatus.BLOCKED,
                        location=provider.location,
                    )
                )

        return tuple(diagnostics)


class WitnessValidationPass:
    name = "witness"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        registry = context.primitive_registry
        diagnostics: list[GraphDiagnostic] = []
        witnesses = {
            witness.identity: witness
            for witness in graph.witnesses
        }

        for witness in graph.witnesses:
            primitive_errors = _validate_predicate_primitives(
                witness.predicate,
                registry,
            )
            for error in primitive_errors:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.WITNESS_NO_WORLD_STATE,
                        f"witness '{witness.identity.local_name}': {error}",
                        node=witness.identity,
                        status=GraphStatus.OPEN_LOOP,
                        location=witness.location,
                    )
                )

            if PredicateKind.TIMING in _kinds(witness.predicate):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.TIMING_CANNOT_WITNESS,
                        f"witness '{witness.identity.local_name}' contains timing evidence",
                        node=witness.identity,
                        status=GraphStatus.OPEN_LOOP,
                        location=witness.location,
                    )
                )

            if not any(
                registry.require(atom.primitive).completion_witness
                for atom in _atoms(witness.predicate)
                if registry.get(atom.primitive) is not None
            ):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.WITNESS_NO_WORLD_STATE,
                        f"witness '{witness.identity.local_name}' contains no "
                        "completion-capable native observation",
                        node=witness.identity,
                        status=GraphStatus.OPEN_LOOP,
                        location=witness.location,
                    )
                )

        for provider in graph.providers:
            if provider.witness is None:
                continue
            witness = witnesses.get(provider.witness)
            if witness is None:
                continue
            if witness.establishes != provider.capability:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.WITNESS_NOT_ESTABLISHING,
                        f"witness '{witness.identity.local_name}' establishes "
                        f"'{witness.establishes.local_name}', not provider capability "
                        f"'{provider.capability.local_name}'",
                        node=provider.identity,
                        related=(witness.identity, provider.capability),
                        status=GraphStatus.OPEN_LOOP,
                        location=witness.location or provider.location,
                    )
                )

        return tuple(diagnostics)


class AdmissibilityValidationPass:
    name = "admissibility"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        registry = context.primitive_registry
        diagnostics: list[GraphDiagnostic] = []

        allowed_by_kind = {
            PredicateKind.OBSERVATION: {"OBSERVATION"},
            PredicateKind.FEASIBILITY: {"FEASIBILITY"},
            PredicateKind.RESOURCE: {"RESOURCE_ARBITRATION"},
            PredicateKind.ARBITRATION: {"RESOURCE_ARBITRATION"},
            PredicateKind.TIMING: {"TIMING"},
            PredicateKind.OWNERSHIP: {"OWNERSHIP"},
            PredicateKind.STRATEGY: {"STRATEGY", "OBSERVATION"},
            PredicateKind.DEPENDENCY: {"OBSERVATION"},
            PredicateKind.WITNESS: {"WITNESS"},
        }

        for provider in graph.providers:
            predicates = []
            if provider.admissibility is not None:
                predicates.append(provider.admissibility)
            if provider.action is not None:
                predicates.extend(provider.action.issue_guards)

            kinds = frozenset()
            for predicate in predicates:
                kinds = kinds | _kinds(predicate)
                for atom in _atoms(predicate):
                    primitive = registry.get(atom.primitive)
                    if primitive is None:
                        diagnostics.append(
                            _diag(
                                CapabilityDiagnosticCode.INVALID_ADMISSIBILITY,
                                f"provider '{provider.identity.local_name}' references unknown "
                                f"predicate primitive '{atom.primitive}'",
                                node=provider.identity,
                                location=provider.location,
                            )
                        )
                        continue
                    expected_roles = allowed_by_kind.get(atom.kind, set())
                    if primitive.role not in expected_roles:
                        diagnostics.append(
                            _diag(
                                CapabilityDiagnosticCode.INVALID_ADMISSIBILITY,
                                f"provider '{provider.identity.local_name}' predicate "
                                f"'{atom.primitive}' has role '{primitive.role}', "
                                f"not valid for '{atom.kind.value}'",
                                node=provider.identity,
                                location=provider.location,
                            )
                        )

            if provider.action is None:
                continue

            if provider.admissibility is None:
                continue

            if kinds == frozenset({PredicateKind.TIMING}):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.TIMING_ONLY_ADMISSIBILITY,
                        f"provider '{provider.identity.local_name}' uses timing as its "
                        "only admissibility evidence",
                        node=provider.identity,
                        status=GraphStatus.BLOCKED,
                        location=provider.location,
                    )
                )
            elif not _has_operational_evidence(kinds):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.INVALID_ADMISSIBILITY,
                        f"provider '{provider.identity.local_name}' admissibility has no "
                        "world-state, feasibility, resource, or arbitration evidence",
                        node=provider.identity,
                        status=GraphStatus.BLOCKED,
                        location=provider.location,
                    )
                )

            if PredicateKind.FEASIBILITY not in kinds:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.FEASIBILITY_MISSING,
                        f"provider '{provider.identity.local_name}' has no native feasibility "
                        "predicate",
                        node=provider.identity,
                        status=GraphStatus.BLOCKED,
                        location=provider.location,
                    )
                )

            if _is_statically_false(provider.admissibility):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.PROVIDER_BLOCKED,
                        f"provider '{provider.identity.local_name}' has a statically false "
                        "admissibility predicate",
                        node=provider.identity,
                        status=GraphStatus.BLOCKED,
                        location=provider.location,
                    )
                )

        return tuple(diagnostics)


def _tarjan_scc(
    adjacency: dict[CapabilityId, tuple[CapabilityId, ...]],
) -> tuple[tuple[CapabilityId, ...], ...]:
    index = 0
    indices: dict[CapabilityId, int] = {}
    lowlink: dict[CapabilityId, int] = {}
    stack: list[CapabilityId] = []
    on_stack: set[CapabilityId] = set()
    components: list[tuple[CapabilityId, ...]] = []

    def strong_connect(node: CapabilityId) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in adjacency.get(node, ()):
            if target not in indices:
                strong_connect(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])

        if lowlink[node] == indices[node]:
            component: list[CapabilityId] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(tuple(sorted(component)))

    for node in sorted(adjacency):
        if node not in indices:
            strong_connect(node)

    return tuple(
        sorted(
            components,
            key=lambda component: tuple(
                (item.source_unit, item.local_name) for item in component
            ),
        )
    )


class DependencyValidationPass:
    name = "dependency"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        diagnostics: list[GraphDiagnostic] = []

        capabilities = {
            capability.identity
            for capability in graph.capabilities
        }
        providers_by_capability: dict[
            CapabilityId,
            tuple[CapabilityProvider, ...],
        ] = {
            identity: tuple(
                provider
                for provider in graph.providers
                if provider.capability == identity
            )
            for identity in sorted(capabilities)
        }

        adjacency: dict[CapabilityId, tuple[CapabilityId, ...]] = {}
        for capability in sorted(capabilities):
            prerequisites = {
                prerequisite
                for provider in providers_by_capability.get(capability, ())
                for prerequisite in provider.prerequisites
                if prerequisite in capabilities
            }
            adjacency[capability] = tuple(sorted(prerequisites))

        satisfiable: set[CapabilityId] = set()
        for capability, providers in providers_by_capability.items():
            for provider in providers:
                if provider.witness is None:
                    continue
                if not provider.prerequisites:
                    satisfiable.add(capability)
                    break

        changed = True
        while changed:
            changed = False
            for capability in sorted(capabilities):
                if capability in satisfiable:
                    continue
                for provider in providers_by_capability.get(capability, ()):
                    if provider.witness is None:
                        continue
                    if all(
                        prerequisite in satisfiable
                        for prerequisite in provider.prerequisites
                    ):
                        satisfiable.add(capability)
                        changed = True
                        break

        reachable: set[CapabilityId] = set()
        pending = sorted(
            {
                demand.target
                for demand in graph.demands
                if demand.target in capabilities
            }
        )
        while pending:
            current = pending.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            pending.extend(
                prerequisite
                for prerequisite in adjacency.get(current, ())
                if prerequisite not in reachable
            )
            pending.sort()

        for component in _tarjan_scc(adjacency):
            cyclic = len(component) > 1 or (
                len(component) == 1
                and component[0] in adjacency.get(component[0], ())
            )
            if not cyclic or not set(component) & reachable:
                continue
            if any(item in satisfiable for item in component):
                continue
            diagnostics.append(
                _diag(
                    CapabilityDiagnosticCode.CYCLE,
                    "unrooted capability dependency cycle: "
                    + " -> ".join(
                        f"{item.source_unit}:{item.local_name}"
                        for item in component
                    ),
                    node=component[0],
                    related=component,
                    status=GraphStatus.DEAD_END,
                )
            )

        for demand in sorted(graph.demands, key=lambda item: item.identity):
            if demand.target not in capabilities:
                continue
            providers = providers_by_capability.get(demand.target, ())
            if not providers:
                continue

            if demand.target not in satisfiable:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.DEAD_END,
                        f"demand '{demand.identity.local_name}' has no satisfiable "
                        f"provider path to capability '{demand.target.local_name}'",
                        node=demand.identity,
                        related=tuple(
                            provider.identity
                            for provider in providers
                        ),
                        status=GraphStatus.DEAD_END,
                        location=demand.location,
                    )
                )

        for capability in sorted(capabilities):
            if capability not in reachable:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.FUNCTIONALLY_DISCONNECTED,
                        f"capability '{capability.local_name}' is not reachable from any demand",
                        node=capability,
                        status=GraphStatus.FUNCTIONALLY_DISCONNECTED,
                        severity=DiagnosticSeverity.WARNING,
                    )
                )

        return tuple(diagnostics)


class LifecycleClosureValidationPass:
    name = "lifecycle-closure"

    def validate(
        self,
        context: ValidationContext,
    ) -> tuple[GraphDiagnostic, ...]:
        graph = context.graph
        diagnostics: list[GraphDiagnostic] = []

        for demand in graph.demands:
            if not demand.release:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.RELEASE_NO_COMPLETION_PATH,
                        f"demand '{demand.identity.local_name}' has no release condition",
                        node=demand.identity,
                        status=GraphStatus.UNFINISHED,
                        location=demand.location,
                    )
                )
            elif all(
                _kinds(predicate) == frozenset({PredicateKind.TIMING})
                for predicate in demand.release
            ):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.TIMING_RELEASE_WITHOUT_WORLD_EVIDENCE,
                        f"demand '{demand.identity.local_name}' release is timing-only",
                        node=demand.identity,
                        status=GraphStatus.UNFINISHED,
                        location=demand.location,
                    )
                )

            if demand.activation and all(
                _kinds(predicate) == frozenset({PredicateKind.TIMING})
                for predicate in demand.activation
            ):
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.TIMING_ONLY_ACTIVATION,
                        f"demand '{demand.identity.local_name}' activation is timing-only",
                        node=demand.identity,
                        status=GraphStatus.BLOCKED,
                        location=demand.location,
                    )
                )

            providers = graph.providers_of(demand.target)
            if not providers:
                continue

            witness_paths = []
            for provider in providers:
                if provider.witness is None:
                    continue
                witnesses = graph.witnesses_for(provider.witness)
                if any(
                    witness.establishes == provider.capability
                    and not (
                        PredicateKind.TIMING in _kinds(witness.predicate)
                    )
                    for witness in witnesses
                ):
                    witness_paths.append(provider.identity)

            if not witness_paths:
                diagnostics.append(
                    _diag(
                        CapabilityDiagnosticCode.OPEN_LOOP,
                        f"demand '{demand.identity.local_name}' has no provider path "
                        "with a world-state completion witness",
                        node=demand.identity,
                        related=tuple(provider.identity for provider in providers),
                        status=GraphStatus.OPEN_LOOP,
                        location=demand.location,
                    )
                )

        return tuple(diagnostics)


def validate_capability_graph(
    graph: CapabilityGraph,
    primitive_registry: PrimitiveRegistry,
) -> ValidationReport:
    context = ValidationContext(
        graph=graph,
        primitive_registry=primitive_registry,
    )
    passes: tuple[ValidationPass, ...] = (
        StructuralValidationPass(),
        ProviderContractValidationPass(),
        WitnessValidationPass(),
        AdmissibilityValidationPass(),
        DependencyValidationPass(),
        LifecycleClosureValidationPass(),
    )

    diagnostics: list[GraphDiagnostic] = []
    for validation_pass in passes:
        diagnostics.extend(validation_pass.validate(context))

    return ValidationReport(
        diagnostics=tuple(
            sorted(diagnostics, key=_diagnostic_key)
        )
    )


__all__ = [
    "CapabilityDiagnosticCode",
    "DiagnosticSeverity",
    "DependencyValidationPass",
    "GraphDiagnostic",
    "GraphStatus",
    "LifecycleClosureValidationPass",
    "ProviderContractValidationPass",
    "StructuralValidationPass",
    "ValidationContext",
    "ValidationReport",
    "ValidationPass",
    "WitnessValidationPass",
    "AdmissibilityValidationPass",
    "validate_capability_graph",
]
