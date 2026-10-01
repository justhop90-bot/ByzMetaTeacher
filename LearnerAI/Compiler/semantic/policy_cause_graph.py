"""Typed causal graph for policy diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from ..diagnostics import DiagnosticSeverity


class PolicyCauseRelation(str, Enum):
    PREREQUISITE = "prerequisite"
    INVALIDATES = "invalidates"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    DERIVES = "derives"


class PolicySuppressionReason(str, Enum):
    ROOT_CAUSE_INVALID = "root-cause-invalid"
    DUPLICATE = "duplicate"
    SUPERSEDED_BY_STRONGER_DIAGNOSTIC = "superseded-by-stronger-diagnostic"
    INVALID_PREREQUISITE = "invalid-prerequisite"


class PolicyDiagnosticPhase(str, Enum):
    RECIPE = "recipe"
    STRUCTURE = "structure"
    BINDING = "binding"
    RESOLUTION = "resolution"
    EVIDENCE = "evidence"
    APPLICABILITY = "applicability"


class PolicyCauseGraphErrorCode(str, Enum):
    UNKNOWN_NODE = "PCG-001"
    SELF_EDGE = "PCG-002"
    DUPLICATE_EDGE = "PCG-003"
    ILLEGAL_RELATION = "PCG-004"
    PHASE_ORDER = "PCG-005"
    SUBJECT_MISMATCH = "PCG-006"
    PRIORITY_VIOLATION = "PCG-007"
    CONTRADICTION_CANONICALIZATION = "PCG-008"
    CAUSAL_CYCLE = "PCG-009"
    WITNESS_MISMATCH = "PCG-010"
    INVALID_ROOT_REFERENCE = "PCG-011"
    SUPPRESSION_WITHOUT_CAUSE = "PCG-012"
    INVALID_CAUSE_DIRECTION = "PCG-013"
    INVALID_RELATION_ENDPOINT = "PCG-014"


@dataclass(frozen=True, order=True)
class PolicyDiagnosticKey:
    code: str
    policy_identity: str
    recipe_identity: str | None = None
    field: str | None = None
    related_field: str | None = None
    binding_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("policy diagnostic code must not be empty")
        if not self.policy_identity.strip():
            raise ValueError("policy diagnostic policy_identity must not be empty")


@dataclass(frozen=True, order=True)
class PolicyDiagnosticRef:
    key: PolicyDiagnosticKey


@dataclass(frozen=True)
class PolicyDiagnosticSubject:
    policy_identity: str
    recipe_identity: str | None = None
    field: str | None = None
    related_field: str | None = None
    binding_identity: str | None = None


@dataclass(frozen=True)
class PolicyCauseWitness:
    policy_identity: str
    recipe_identity: str | None = None
    field: str | None = None
    related_field: str | None = None
    binding_identity: str | None = None
    rule_id: str | None = None


@dataclass(frozen=True, order=True)
class PolicyCauseEdgeKey:
    source: PolicyDiagnosticRef
    target: PolicyDiagnosticRef
    relation: PolicyCauseRelation


@dataclass(frozen=True)
class PolicyCauseEdgeContext:
    source: PolicyDiagnosticRef
    target: PolicyDiagnosticRef
    relation: PolicyCauseRelation


@dataclass(frozen=True)
class PolicyCauseEdge:
    key: PolicyCauseEdgeKey
    witness: PolicyCauseWitness


@dataclass(frozen=True)
class PolicyDiagnostic:
    key: PolicyDiagnosticKey
    severity: DiagnosticSeverity
    phase: PolicyDiagnosticPhase
    priority: int
    subject: PolicyDiagnosticSubject
    message: str
    location: object | None = None


@dataclass(frozen=True)
class PolicySuppressionRef:
    suppressed: PolicyDiagnosticRef
    root_cause: PolicyDiagnosticRef | None
    via_edge: PolicyCauseEdgeKey | None


class PolicyCauseGraphError(ValueError):
    code: PolicyCauseGraphErrorCode

    def __init__(self, code: PolicyCauseGraphErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code.value}: {message}")


class PolicyCauseGraphUnknownNodeError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.UNKNOWN_NODE

    def __init__(self, *, missing, endpoint: str, edge=None) -> None:
        self.missing, self.endpoint, self.edge = missing, endpoint, edge
        super().__init__(self.code, f"causal edge {endpoint} diagnostic is not registered")


class PolicyCauseGraphSelfEdgeError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.SELF_EDGE

    def __init__(self, *, diagnostic, relation) -> None:
        self.diagnostic, self.relation = diagnostic, relation
        super().__init__(self.code, "causal diagnostic edge may not reference the same source and target")


class PolicyCauseGraphDuplicateEdgeError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.DUPLICATE_EDGE

    def __init__(self, *, edge) -> None:
        self.edge = edge
        super().__init__(self.code, f"duplicate causal edge for relation '{edge.relation.value}'")


class PolicyCauseGraphIllegalRelationError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.ILLEGAL_RELATION

    def __init__(self, *, edge, reason: str) -> None:
        self.edge, self.reason = edge, reason
        super().__init__(self.code, f"illegal causal relation: {reason}")


class PolicyCauseGraphPhaseOrderError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.PHASE_ORDER

    def __init__(self, *, edge, source_phase, target_phase, source_rank: int, target_rank: int) -> None:
        self.edge = edge
        self.source_phase, self.target_phase = source_phase, target_phase
        self.source_rank, self.target_rank = source_rank, target_rank
        super().__init__(self.code, f"relation '{edge.relation.value}' violates phase ordering: {source_phase.value} -> {target_phase.value}")


class PolicyCauseGraphSubjectMismatchError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.SUBJECT_MISMATCH

    def __init__(self, *, edge, source_subject, target_subject) -> None:
        self.edge = edge
        self.source_subject, self.target_subject = source_subject, target_subject
        super().__init__(self.code, f"causal edge subjects do not overlap for '{edge.relation.value}'")


class PolicyCauseGraphPriorityViolationError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.PRIORITY_VIOLATION

    def __init__(self, *, edge, source_priority: int, target_priority: int) -> None:
        self.edge = edge
        self.source_priority, self.target_priority = source_priority, target_priority
        super().__init__(self.code, f"superseding diagnostic has weaker or equal precedence ({source_priority} >= {target_priority})")


class PolicyCauseGraphContradictionCanonicalizationError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.CONTRADICTION_CANONICALIZATION

    def __init__(self, *, left, right, canonical_left, canonical_right) -> None:
        self.left, self.right = left, right
        self.canonical_left, self.canonical_right = canonical_left, canonical_right
        super().__init__(self.code, "contradiction pair is not in canonical diagnostic order")


class PolicyCauseGraphCausalCycleError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.CAUSAL_CYCLE

    def __init__(self, *, cycle: Sequence[PolicyDiagnosticRef], edges: Sequence[PolicyCauseEdgeKey]) -> None:
        self.cycle, self.edges = tuple(cycle), tuple(edges)
        if len(self.cycle) < 2:
            raise ValueError("causal cycle error requires at least two diagnostic references")
        super().__init__(self.code, f"causal graph contains directed cycle of {len(self.cycle) - 1} edge(s)")


class PolicyCauseGraphWitnessMismatchError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.WITNESS_MISMATCH

    def __init__(self, *, edge, witness, expected_subject) -> None:
        self.edge, self.witness, self.expected_subject = edge, witness, expected_subject
        super().__init__(self.code, "causal witness does not match diagnostic edge subject")


class PolicyCauseGraphInvalidRootReferenceError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.INVALID_ROOT_REFERENCE

    def __init__(self, *, suppression, referenced_root, actual_root) -> None:
        self.suppression = suppression
        self.referenced_root, self.actual_root = referenced_root, actual_root
        super().__init__(self.code, "suppression references a diagnostic that is not the canonical emitted root")


class PolicyCauseGraphSuppressionWithoutCauseError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.SUPPRESSION_WITHOUT_CAUSE

    def __init__(self, *, suppression) -> None:
        self.suppression = suppression
        super().__init__(self.code, "suppressed diagnostic has no matching causal edge")


class PolicyCauseGraphInvalidCauseDirectionError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.INVALID_CAUSE_DIRECTION

    def __init__(self, *, edge, expected_source, expected_target) -> None:
        self.edge = edge
        self.expected_source, self.expected_target = expected_source, expected_target
        super().__init__(self.code, f"relation '{edge.relation.value}' has invalid cause direction")


class PolicyCauseGraphInvalidRelationEndpointError(PolicyCauseGraphError):
    code = PolicyCauseGraphErrorCode.INVALID_RELATION_ENDPOINT

    def __init__(self, *, edge, source_subject, target_subject, reason: str) -> None:
        self.edge = edge
        self.source_subject, self.target_subject = source_subject, target_subject
        self.reason = reason
        super().__init__(self.code, f"invalid '{edge.relation.value}' endpoint combination: {reason}")


PHASE_RANK = {
    PolicyDiagnosticPhase.RECIPE: 0,
    PolicyDiagnosticPhase.STRUCTURE: 10,
    PolicyDiagnosticPhase.BINDING: 20,
    PolicyDiagnosticPhase.RESOLUTION: 30,
    PolicyDiagnosticPhase.EVIDENCE: 40,
    PolicyDiagnosticPhase.APPLICABILITY: 50,
}

DIAGNOSTIC_PRECEDENCE = {
    "POL-009": 0,
    "POL-010": 10,
    "POL-003": 20,
    "POL-004": 30,
    "POL-005": 40,
    "POL-001": 50,
    "POL-002": 60,
    "POL-008": 70,
    "POL-012": 80,
    "POL-006": 90,
    "POL-007": 100,
    "POL-011": 110,
}

CAUSE_RELATION_RANK = {
    PolicyCauseRelation.PREREQUISITE: 0,
    PolicyCauseRelation.INVALIDATES: 10,
    PolicyCauseRelation.SUPERSEDES: 20,
    PolicyCauseRelation.DERIVES: 30,
    PolicyCauseRelation.CONTRADICTS: 9999,
}

DIRECTED_CAUSAL_RELATIONS = frozenset({
    PolicyCauseRelation.PREREQUISITE,
    PolicyCauseRelation.INVALIDATES,
    PolicyCauseRelation.SUPERSEDES,
    PolicyCauseRelation.DERIVES,
})


def _as_ref(value):
    return value if isinstance(value, PolicyDiagnosticRef) else PolicyDiagnosticRef(value)


@dataclass(frozen=True)
class PolicyCauseGraph:
    nodes: tuple[PolicyDiagnostic, ...] = ()
    edges: tuple[PolicyCauseEdge, ...] = ()

    @classmethod
    def from_nodes(cls, nodes: Iterable[PolicyDiagnostic]) -> "PolicyCauseGraph":
        ordered = tuple(nodes)
        keys = [item.key for item in ordered]
        if len(keys) != len(set(keys)):
            raise ValueError("policy cause graph contains duplicate diagnostic keys")
        return cls(nodes=ordered)

    def _node_map(self):
        return {PolicyDiagnosticRef(item.key): item for item in self.nodes}

    def incoming(self, target: PolicyDiagnosticRef):
        return tuple(
            edge for edge in self.edges
            if edge.key.target == target and edge.key.relation in DIRECTED_CAUSAL_RELATIONS
        )

    def outgoing(self, source: PolicyDiagnosticRef):
        return tuple(
            edge for edge in self.edges
            if edge.key.source == source and edge.key.relation in DIRECTED_CAUSAL_RELATIONS
        )

    def add_raw_edge(self, source, target, relation, *, witness, validate: bool = True):
        source_ref, target_ref = _as_ref(source), _as_ref(target)
        try:
            relation = PolicyCauseRelation(relation)
        except ValueError as exc:
            raise PolicyCauseGraphIllegalRelationError(
                edge=PolicyCauseEdgeContext(source_ref, target_ref, PolicyCauseRelation.CONTRADICTS),
                reason=f"unsupported relation {relation!r}",
            ) from exc
        context = PolicyCauseEdgeContext(source_ref, target_ref, relation)
        nodes = self._node_map()
        if source_ref not in nodes:
            raise PolicyCauseGraphUnknownNodeError(missing=source_ref, endpoint="source", edge=context)
        if target_ref not in nodes:
            raise PolicyCauseGraphUnknownNodeError(missing=target_ref, endpoint="target", edge=context)
        if source_ref == target_ref:
            raise PolicyCauseGraphSelfEdgeError(diagnostic=source_ref, relation=relation)
        edge_key = PolicyCauseEdgeKey(source_ref, target_ref, relation)
        if edge_key in {edge.key for edge in self.edges}:
            raise PolicyCauseGraphDuplicateEdgeError(edge=edge_key)
        if relation is PolicyCauseRelation.CONTRADICTS:
            left, right = sorted((source_ref, target_ref))
            if source_ref != left or target_ref != right:
                raise PolicyCauseGraphContradictionCanonicalizationError(
                    left=source_ref, right=target_ref,
                    canonical_left=left, canonical_right=right,
                )
        result = PolicyCauseGraph(self.nodes, (*self.edges, PolicyCauseEdge(edge_key, witness)))
        if validate:
            validate_policy_cause_graph(result)
        return result

    def _default_witness(self, source):
        subject = self._node_map()[_as_ref(source)].subject
        return PolicyCauseWitness(
            policy_identity=subject.policy_identity,
            recipe_identity=subject.recipe_identity,
            field=subject.field,
            related_field=subject.related_field,
            binding_identity=subject.binding_identity,
        )

    def with_invalidation(self, source, target, *, witness=None):
        return self.add_raw_edge(
            source, target, PolicyCauseRelation.INVALIDATES,
            witness=witness or self._default_witness(source),
        )

    def with_prerequisite(self, source, target, *, witness=None):
        return self.add_raw_edge(
            source, target, PolicyCauseRelation.PREREQUISITE,
            witness=witness or self._default_witness(source),
        )

    def with_supersession(self, source, target, *, witness=None):
        return self.add_raw_edge(
            source, target, PolicyCauseRelation.SUPERSEDES,
            witness=witness or self._default_witness(source),
        )

    def with_derivation(self, source, target, *, witness=None):
        return self.add_raw_edge(
            source, target, PolicyCauseRelation.DERIVES,
            witness=witness or self._default_witness(source),
        )

    def with_contradiction(self, left, right, *, witness=None):
        left, right = sorted((left, right))
        return self.add_raw_edge(
            left, right, PolicyCauseRelation.CONTRADICTS,
            witness=witness or self._default_witness(left),
        )

    def validate_suppression(self, suppression: PolicySuppressionRef) -> None:
        if suppression.suppressed not in self._node_map():
            raise PolicyCauseGraphUnknownNodeError(missing=suppression.suppressed, endpoint="suppressed")
        if suppression.root_cause is None or suppression.via_edge is None:
            raise PolicyCauseGraphSuppressionWithoutCauseError(suppression=suppression)
        if suppression.root_cause not in self._node_map():
            raise PolicyCauseGraphUnknownNodeError(missing=suppression.root_cause, endpoint="root")
        edge = next((item for item in self.edges if item.key == suppression.via_edge), None)
        if edge is None:
            raise PolicyCauseGraphSuppressionWithoutCauseError(suppression=suppression)
        if edge.key.source != suppression.root_cause or edge.key.target != suppression.suppressed:
            raise PolicyCauseGraphInvalidRootReferenceError(
                suppression=suppression,
                referenced_root=suppression.root_cause,
                actual_root=edge.key.source,
            )
        actual = select_root_cause(self, suppression.suppressed.key)
        if actual is None or PolicyDiagnosticRef(actual) != suppression.root_cause:
            raise PolicyCauseGraphInvalidRootReferenceError(
                suppression=suppression,
                referenced_root=suppression.root_cause,
                actual_root=PolicyDiagnosticRef(actual) if actual else None,
            )


def build_diagnostic(
    *, code: str, policy_identity: str, recipe_identity: str | None = None,
    field: str | None = None, related_field: str | None = None,
    binding_identity: str | None = None,
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    phase: PolicyDiagnosticPhase = PolicyDiagnosticPhase.RESOLUTION,
    priority: int | None = None, message: str | None = None,
    location: object | None = None,
) -> PolicyDiagnostic:
    key = PolicyDiagnosticKey(code, policy_identity, recipe_identity, field, related_field, binding_identity)
    subject = PolicyDiagnosticSubject(policy_identity, recipe_identity, field, related_field, binding_identity)
    return PolicyDiagnostic(
        key=key, severity=severity, phase=phase,
        priority=DIAGNOSTIC_PRECEDENCE.get(code, 1000) if priority is None else priority,
        subject=subject, message=message or code, location=location,
    )


def _subjects_overlap(source, target) -> bool:
    if source.policy_identity != target.policy_identity:
        return False
    if source.recipe_identity is not None and target.recipe_identity is not None and source.recipe_identity != target.recipe_identity:
        return False
    if source.binding_identity is not None and target.binding_identity is not None and source.binding_identity != target.binding_identity:
        return False
    if source.field is None or target.field is None:
        return True
    return (
        source.field == target.field
        or source.field == target.related_field
        or source.related_field == target.field
        or source.related_field == target.related_field
    )


def _witness_matches_subject(witness, subject) -> bool:
    if witness.policy_identity != subject.policy_identity:
        return False
    if witness.recipe_identity is not None and witness.recipe_identity != subject.recipe_identity:
        return False
    if witness.binding_identity is not None and witness.binding_identity != subject.binding_identity:
        return False
    if witness.field is not None and witness.field not in {subject.field, subject.related_field}:
        return False
    if witness.related_field is not None and witness.related_field not in {subject.field, subject.related_field}:
        return False
    return True


def _validate_edge_endpoints(graph, edge):
    nodes = graph._node_map()
    source = nodes.get(edge.key.source)
    target = nodes.get(edge.key.target)
    if source is None:
        raise PolicyCauseGraphUnknownNodeError(
            missing=edge.key.source, endpoint="source",
            edge=PolicyCauseEdgeContext(edge.key.source, edge.key.target, edge.key.relation),
        )
    if target is None:
        raise PolicyCauseGraphUnknownNodeError(
            missing=edge.key.target, endpoint="target",
            edge=PolicyCauseEdgeContext(edge.key.source, edge.key.target, edge.key.relation),
        )
    return source, target


def _validate_relation_contract(edge, source, target) -> None:
    context = PolicyCauseEdgeContext(edge.key.source, edge.key.target, edge.key.relation)
    relation = edge.key.relation
    if edge.key.source == edge.key.target:
        raise PolicyCauseGraphSelfEdgeError(diagnostic=edge.key.source, relation=relation)
    if relation in DIRECTED_CAUSAL_RELATIONS:
        source_rank, target_rank = PHASE_RANK[source.phase], PHASE_RANK[target.phase]
        if source_rank > target_rank:
            raise PolicyCauseGraphPhaseOrderError(
                edge=context, source_phase=source.phase, target_phase=target.phase,
                source_rank=source_rank, target_rank=target_rank,
            )
        if not _subjects_overlap(source.subject, target.subject):
            raise PolicyCauseGraphSubjectMismatchError(
                edge=context, source_subject=source.subject, target_subject=target.subject,
            )
    if relation in {PolicyCauseRelation.PREREQUISITE, PolicyCauseRelation.INVALIDATES}:
        if source.severity is not DiagnosticSeverity.ERROR:
            raise PolicyCauseGraphInvalidRelationEndpointError(
                edge=context, source_subject=source.subject, target_subject=target.subject,
                reason="source diagnostic must be an error",
            )
    if relation is PolicyCauseRelation.SUPERSEDES:
        if not _subjects_overlap(source.subject, target.subject):
            raise PolicyCauseGraphInvalidRelationEndpointError(
                edge=context, source_subject=source.subject, target_subject=target.subject,
                reason="supersession requires overlapping semantic subjects",
            )
        if source.subject.field != target.subject.field:
            raise PolicyCauseGraphInvalidRelationEndpointError(
                edge=context, source_subject=source.subject, target_subject=target.subject,
                reason="supersession requires the same primary policy field",
            )
        if source.priority >= target.priority:
            raise PolicyCauseGraphPriorityViolationError(
                edge=context, source_priority=source.priority, target_priority=target.priority,
            )
    if relation is PolicyCauseRelation.CONTRADICTS:
        if not _subjects_overlap(source.subject, target.subject):
            raise PolicyCauseGraphSubjectMismatchError(
                edge=context, source_subject=source.subject, target_subject=target.subject,
            )
        left, right = sorted((edge.key.source, edge.key.target))
        if edge.key.source != left or edge.key.target != right:
            raise PolicyCauseGraphContradictionCanonicalizationError(
                left=edge.key.source, right=edge.key.target,
                canonical_left=left, canonical_right=right,
            )
    if not _witness_matches_subject(edge.witness, source.subject):
        raise PolicyCauseGraphWitnessMismatchError(
            edge=context, witness=edge.witness, expected_subject=source.subject,
        )


def _find_cycle(graph):
    adjacency = {}
    for edge in graph.edges:
        if edge.key.relation in DIRECTED_CAUSAL_RELATIONS:
            adjacency.setdefault(edge.key.source, []).append(edge)
    visiting, visiting_set, visited = [], set(), set()

    def dfs(node):
        if node in visiting_set:
            index = visiting.index(node)
            nodes = tuple((*visiting[index:], node))
            edges = []
            for left, right in zip(nodes, nodes[1:]):
                match = next(
                    edge for edge in adjacency.get(left, ())
                    if edge.key.target == right
                )
                edges.append(match.key)
            return nodes, tuple(edges)
        if node in visited:
            return None
        visiting.append(node)
        visiting_set.add(node)
        for edge in adjacency.get(node, ()):
            found = dfs(edge.key.target)
            if found is not None:
                return found
        visiting.pop()
        visiting_set.remove(node)
        visited.add(node)
        return None

    for node in sorted(PolicyDiagnosticRef(item.key) for item in graph.nodes):
        found = dfs(node)
        if found is not None:
            return found
    return None


def validate_cause_direction(edge, *, expected_source, expected_target) -> None:
    if edge.source != expected_source or edge.target != expected_target:
        raise PolicyCauseGraphInvalidCauseDirectionError(
            edge=edge, expected_source=expected_source, expected_target=expected_target,
        )


def validate_policy_cause_graph(graph: PolicyCauseGraph) -> None:
    if not isinstance(graph, PolicyCauseGraph):
        raise TypeError("graph must be a PolicyCauseGraph")
    keys = [item.key for item in graph.nodes]
    if len(keys) != len(set(keys)):
        raise ValueError("policy cause graph contains duplicate diagnostic keys")
    edge_keys = set()
    for edge in graph.edges:
        if edge.key in edge_keys:
            raise PolicyCauseGraphDuplicateEdgeError(edge=edge.key)
        edge_keys.add(edge.key)
        source, target = _validate_edge_endpoints(graph, edge)
        _validate_relation_contract(edge, source, target)
    cycle = _find_cycle(graph)
    if cycle is not None:
        nodes, edges = cycle
        raise PolicyCauseGraphCausalCycleError(cycle=nodes, edges=edges)


def _root_rank(root, *, relation):
    return (
        CAUSE_RELATION_RANK[relation],
        PHASE_RANK[root.phase],
        root.priority,
        root.subject.policy_identity,
        root.subject.field or "",
        root.subject.related_field or "",
        root.key,
    )


def select_root_cause(graph: PolicyCauseGraph, target: PolicyDiagnosticKey) -> PolicyDiagnosticKey | None:
    target_ref = PolicyDiagnosticRef(target)
    nodes = graph._node_map()
    if target_ref not in nodes:
        raise PolicyCauseGraphUnknownNodeError(missing=target_ref, endpoint="target")
    incoming = graph.incoming(target_ref)
    if not incoming:
        return None
    candidates = [
        (nodes[edge.key.source], edge.key.relation)
        for edge in incoming
        if edge.key.relation is not PolicyCauseRelation.CONTRADICTS
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: _root_rank(item[0], relation=item[1]))
    winner = candidates[0][0]
    while True:
        parents = [
            (nodes[edge.key.source], edge.key.relation)
            for edge in graph.incoming(PolicyDiagnosticRef(winner.key))
            if edge.key.relation is not PolicyCauseRelation.CONTRADICTS
        ]
        if not parents:
            return winner.key
        parents.sort(key=lambda item: _root_rank(item[0], relation=item[1]))
        winner = parents[0][0]


__all__ = [
    "CAUSE_RELATION_RANK", "DIAGNOSTIC_PRECEDENCE", "DIRECTED_CAUSAL_RELATIONS",
    "PHASE_RANK", "PolicyCauseEdge", "PolicyCauseEdgeContext", "PolicyCauseEdgeKey",
    "PolicyCauseGraph", "PolicyCauseGraphCausalCycleError",
    "PolicyCauseGraphContradictionCanonicalizationError", "PolicyCauseGraphDuplicateEdgeError",
    "PolicyCauseGraphError", "PolicyCauseGraphErrorCode", "PolicyCauseGraphIllegalRelationError",
    "PolicyCauseGraphInvalidCauseDirectionError", "PolicyCauseGraphInvalidRelationEndpointError",
    "PolicyCauseGraphInvalidRootReferenceError", "PolicyCauseGraphPhaseOrderError",
    "PolicyCauseGraphPriorityViolationError", "PolicyCauseGraphSelfEdgeError",
    "PolicyCauseGraphSubjectMismatchError", "PolicyCauseGraphSuppressionWithoutCauseError",
    "PolicyCauseGraphUnknownNodeError", "PolicyCauseGraphWitnessMismatchError",
    "PolicyCauseRelation", "PolicyCauseWitness", "PolicySuppressionReason",
    "PolicyDiagnostic", "PolicyDiagnosticKey", "PolicyDiagnosticPhase",
    "PolicyDiagnosticRef", "PolicyDiagnosticSubject", "PolicySuppressionRef",
    "build_diagnostic", "select_root_cause", "validate_cause_direction",
    "validate_policy_cause_graph",
]
