"""Unified strategy dependency/deadlock correlation."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Iterable

from ..diagnostics import DiagnosticSeverity
from ..ir.capability import CapabilityGraph, CapabilityProvider
from ..ir.native_duc import NativeDucLifecycleStage
from .capability_validation import CapabilityDiagnosticCode, ValidationReport
from .persistent_state import PersistentStateDiagnosticCode, PersistentStateReport
from .rule_execution import RuleExecutionReport


class FeatureStage(str, Enum):
    INPUT = "INPUT"
    EFFECTIVE_CIV = "EFFECTIVE_CIV"
    STRATEGY_PROFILE = "STRATEGY_PROFILE"
    RESOLVED_PROFILE = "RESOLVED_PROFILE"
    STRATEGY_IR = "STRATEGY_IR"
    SEMANTIC_IR = "SEMANTIC_IR"
    SEMANTIC_VALIDATION = "SEMANTIC_VALIDATION"
    CAPABILITY_GRAPH = "CAPABILITY_GRAPH"
    OPERATIONAL_PLAN = "OPERATIONAL_PLAN"
    CONTROL_PLAN = "CONTROL_PLAN"
    STORAGE_BINDING = "STORAGE_BINDING"
    NATIVE_LOWERING = "NATIVE_LOWERING"
    EMISSION = "EMISSION"
    ARTIFACT_ANALYSIS = "ARTIFACT_ANALYSIS"
    NATIVE_VALIDATION = "NATIVE_VALIDATION"
    RUNTIME_ASSEMBLY = "RUNTIME_ASSEMBLY"
    RUNTIME_PROMOTION = "RUNTIME_PROMOTION"
    RUNTIME = "RUNTIME"


FEATURE_STAGE_ORDER: tuple[FeatureStage, ...] = (
    FeatureStage.INPUT,
    FeatureStage.EFFECTIVE_CIV,
    FeatureStage.STRATEGY_PROFILE,
    FeatureStage.RESOLVED_PROFILE,
    FeatureStage.STRATEGY_IR,
    FeatureStage.SEMANTIC_IR,
    FeatureStage.SEMANTIC_VALIDATION,
    FeatureStage.CAPABILITY_GRAPH,
    FeatureStage.OPERATIONAL_PLAN,
    FeatureStage.CONTROL_PLAN,
    FeatureStage.STORAGE_BINDING,
    FeatureStage.NATIVE_LOWERING,
    FeatureStage.EMISSION,
    FeatureStage.ARTIFACT_ANALYSIS,
    FeatureStage.NATIVE_VALIDATION,
    FeatureStage.RUNTIME_ASSEMBLY,
    FeatureStage.RUNTIME_PROMOTION,
    FeatureStage.RUNTIME,
)

_FEATURE_STAGE_INDEX = {
    stage: index for index, stage in enumerate(FEATURE_STAGE_ORDER)
}


class FeatureNodeStatus(str, Enum):
    PASS = "PASS"
    MISSING = "MISSING"
    INVALID = "INVALID"
    BLOCKED = "BLOCKED"
    OPEN = "OPEN"
    UNKNOWN = "UNKNOWN"


class FeatureEdgeStatus(str, Enum):
    SATISFIED = "SATISFIED"
    BROKEN = "BROKEN"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FeatureNode:
    feature_id: str
    stage: FeatureStage
    identity: str
    status: FeatureNodeStatus
    fingerprint: str | None = None
    source_unit: str | None = None
    location: str | None = None
    rule_orders: tuple[int, ...] = ()
    artifact_sha256: str | None = None
    evidence: tuple[str, ...] = ()
    diagnostic_codes: tuple[str, ...] = ()

    @property
    def node_id(self) -> str:
        return (
            f"feature:{self.feature_id}:"
            f"{self.stage.value.lower()}:{self.identity}"
        )


@dataclass(frozen=True)
class FeatureEdge:
    feature_id: str
    source: FeatureStage
    target: FeatureStage
    contract: str
    expected_identity: str
    observed_identity: str | None
    status: FeatureEdgeStatus
    diagnostic_code: str | None = None
    message: str | None = None
    source_node_id: str | None = None
    target_node_id: str | None = None
    evidence: tuple[str, ...] = ()

    @property
    def edge_id(self) -> str:
        return (
            f"feature-edge:{self.feature_id}:"
            f"{self.source.value.lower()}->"
            f"{self.target.value.lower()}:"
            f"{self.contract}"
        )

    @property
    def order(self) -> tuple[int, int, str, str]:
        return (
            _FEATURE_STAGE_INDEX[self.source],
            _FEATURE_STAGE_INDEX[self.target],
            self.contract,
            self.expected_identity,
        )



@dataclass(frozen=True)
class FeatureTraceDiagnostic:
    code: str
    feature_id: str
    stage: FeatureStage
    source_stage: FeatureStage
    target_stage: FeatureStage
    severity: DiagnosticSeverity
    message: str
    expected: str
    observed: str | None
    chain: tuple[str, ...]
    locations: tuple[str, ...] = ()
    rule_orders: tuple[int, ...] = ()


@dataclass(frozen=True)
class FeatureTrace:
    feature_id: str
    root_stage: FeatureStage
    nodes: tuple[FeatureNode, ...]
    edges: tuple[FeatureEdge, ...]
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def ordered_nodes(self) -> tuple[FeatureNode, ...]:
        return tuple(sorted(
            self.nodes,
            key=lambda node: (
                _FEATURE_STAGE_INDEX[node.stage],
                node.identity,
                node.node_id,
            ),
        ))

    @property
    def ordered_edges(self) -> tuple[FeatureEdge, ...]:
        return tuple(sorted(self.edges, key=lambda edge: edge.order))

    @property
    def first_broken_edge(self) -> FeatureEdge | None:
        return first_broken_edge(self)

    @property
    def status(self) -> FeatureNodeStatus:
        broken = self.first_broken_edge
        if broken is not None:
            return FeatureNodeStatus.INVALID
        if any(edge.status is FeatureEdgeStatus.UNKNOWN for edge in self.edges):
            return FeatureNodeStatus.UNKNOWN
        if any(edge.status is FeatureEdgeStatus.BLOCKED for edge in self.edges):
            return FeatureNodeStatus.BLOCKED
        statuses = {node.status for node in self.nodes}
        if FeatureNodeStatus.INVALID in statuses:
            return FeatureNodeStatus.INVALID
        if FeatureNodeStatus.MISSING in statuses:
            return FeatureNodeStatus.MISSING
        if FeatureNodeStatus.BLOCKED in statuses:
            return FeatureNodeStatus.BLOCKED
        if FeatureNodeStatus.UNKNOWN in statuses:
            return FeatureNodeStatus.UNKNOWN
        if FeatureNodeStatus.OPEN in statuses:
            return FeatureNodeStatus.OPEN
        return FeatureNodeStatus.PASS

    def diagnostic(self) -> FeatureTraceDiagnostic | None:
        edge = self.first_broken_edge
        if edge is None:
            return None
        stage_index = _FEATURE_STAGE_INDEX[edge.target]
        chain = tuple(
            node.node_id
            for node in self.ordered_nodes
            if _FEATURE_STAGE_INDEX[node.stage] <= stage_index
        )
        locations = tuple(sorted({
            node.location
            for node in self.ordered_nodes
            if node.location is not None
        }))
        rule_orders = tuple(sorted({
            rule_order
            for node in self.ordered_nodes
            if _FEATURE_STAGE_INDEX[node.stage] <= stage_index
            for rule_order in node.rule_orders
        }))
        return FeatureTraceDiagnostic(
            code=edge.diagnostic_code or "BYZ-TRACE-FIRST-BROKEN",
            feature_id=self.feature_id,
            stage=edge.target,
            source_stage=edge.source,
            target_stage=edge.target,
            severity=DiagnosticSeverity.ERROR,
            message=edge.message or (
                f"feature {self.feature_id!r} violates contract {edge.contract!r}"
            ),
            expected=edge.expected_identity,
            observed=edge.observed_identity,
            chain=chain,
            locations=locations,
            rule_orders=rule_orders,
        )


class FeatureTraceBuilder:
    """Mutable assembly surface for one immutable feature trace."""

    def __init__(self, feature_id: str):
        if not feature_id:
            raise ValueError("feature_id must be non-empty")
        self.feature_id = feature_id
        self._nodes: dict[tuple[FeatureStage, str], FeatureNode] = {}
        self._edges: dict[str, FeatureEdge] = {}

    def add_node(self, node: FeatureNode) -> "FeatureTraceBuilder":
        self._validate_feature_id(node.feature_id)
        key = (node.stage, node.identity)
        existing = self._nodes.get(key)
        if existing is not None and existing != node:
            raise ValueError(f"conflicting feature node {node.node_id}")
        self._nodes[key] = node
        return self

    def add_edge(self, edge: FeatureEdge) -> "FeatureTraceBuilder":
        self._validate_feature_id(edge.feature_id)
        if _FEATURE_STAGE_INDEX[edge.target] <= _FEATURE_STAGE_INDEX[edge.source]:
            raise ValueError("feature edges must move forward through stage order")
        existing = self._edges.get(edge.edge_id)
        if existing is not None and existing != edge:
            raise ValueError(f"conflicting feature edge {edge.edge_id}")
        self._edges[edge.edge_id] = edge
        return self

    def build(
        self,
        *,
        root_stage: FeatureStage,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> FeatureTrace:
        if self._nodes:
            minimum_stage = min(
                (node.stage for node in self._nodes.values()),
                key=_FEATURE_STAGE_INDEX.__getitem__,
            )
            if _FEATURE_STAGE_INDEX[root_stage] > _FEATURE_STAGE_INDEX[minimum_stage]:
                raise ValueError("root_stage cannot follow earliest feature evidence")
        node_ids = {node.node_id for node in self._nodes.values()}
        for edge in self._edges.values():
            if edge.source_node_id is not None and edge.source_node_id not in node_ids:
                raise ValueError(f"unknown source node {edge.source_node_id}")
            if edge.target_node_id is not None and edge.target_node_id not in node_ids:
                raise ValueError(f"unknown target node {edge.target_node_id}")
        return FeatureTrace(
            feature_id=self.feature_id,
            root_stage=root_stage,
            nodes=tuple(sorted(
                self._nodes.values(),
                key=lambda node: (
                    _FEATURE_STAGE_INDEX[node.stage],
                    node.identity,
                    node.node_id,
                ),
            )),
            edges=tuple(sorted(self._edges.values(), key=lambda edge: edge.order)),
            metadata=tuple(sorted(metadata)),
        )

    def _validate_feature_id(self, feature_id: str) -> None:
        if feature_id != self.feature_id:
            raise ValueError(
                f"feature id mismatch: expected {self.feature_id!r}, got {feature_id!r}"
            )


def first_broken_edge(trace: FeatureTrace) -> FeatureEdge | None:
    for edge in trace.ordered_edges:
        if edge.status is FeatureEdgeStatus.BROKEN:
            return edge
    return None


def _feature_semantic_identity(demand) -> str:
    return f"{demand.identity.source_unit}:{demand.identity.local_name}"


def _feature_source_unit(demand) -> str:
    return str(demand.identity.source_unit)


def _feature_location(demand) -> str | None:
    location = getattr(demand, "location", None)
    return str(location) if location is not None else None


def _capability_demand_for(capability_graph: CapabilityGraph, demand):
    for candidate in capability_graph.demands:
        if (
            candidate.identity.source_unit == demand.identity.source_unit
            and candidate.identity.local_name == demand.identity.local_name
        ):
            return candidate
    return None


def _feature_edge(
    *,
    feature_id: str,
    source: FeatureStage,
    target: FeatureStage,
    contract: str,
    expected: str,
    observed: str | None,
    status: FeatureEdgeStatus,
    message: str | None = None,
) -> FeatureEdge:
    return FeatureEdge(
        feature_id=feature_id,
        source=source,
        target=target,
        contract=contract,
        expected_identity=expected,
        observed_identity=observed,
        status=status,
        diagnostic_code=(
            StrategyDependencyCode.FEATURE_FIRST_BROKEN_EDGE.value
            if status is FeatureEdgeStatus.BROKEN
            else None
        ),
        message=message,
    )


def build_feature_traces(
    demands: Iterable[object],
    capability_graph: CapabilityGraph,
    bindings,
    artifact: str | bytes,
    *,
    verified_stage_identities: frozenset[str] = frozenset(),
) -> tuple[FeatureTrace, ...]:
    """Populate causal feature traces from verified compiler-stage outputs.

    This helper is intentionally invoked only after the existing semantic,
    capability, binding, and native-lowering gates have succeeded. It does
    not invent downstream runtime evidence. Emission is treated as an
    executed compiler stage; Artifact Analysis is the first stage that
    consults emitted bytes for a feature-owned marker.
    """
    payload = artifact.encode("utf-8") if isinstance(artifact, str) else artifact
    artifact_sha256 = hashlib.sha256(payload).hexdigest()
    artifact_text = payload.decode("utf-8")
    traces: list[FeatureTrace] = []

    ordered_demands = tuple(
        sorted(
            demands,
            key=lambda demand: (
                str(
                    getattr(
                        getattr(demand, "strategic_binding", None),
                        "strategic_id",
                        "",
                    )
                ),
                str(demand.identity.source_unit),
                str(demand.identity.local_name),
            ),
        )
    )
    feature_bases = tuple(
        (
            str(
                getattr(
                    getattr(demand, "strategic_binding", None),
                    "strategic_id",
                    "",
                )
            )
            or _feature_semantic_identity(demand),
            _feature_semantic_identity(demand),
        )
        for demand in ordered_demands
    )
    feature_base_counts = Counter(base for base, _ in feature_bases)
    for demand, (feature_base, semantic_identity) in zip(
        ordered_demands,
        feature_bases,
    ):
        strategic_binding = getattr(demand, "strategic_binding", None)
        feature_id = (
            feature_base
            if feature_base_counts[feature_base] == 1
            else f"{feature_base}::{semantic_identity}"
        )
        root_stage = (
            FeatureStage.STRATEGY_IR
            if strategic_binding is not None
            else FeatureStage.SEMANTIC_IR
        )
        source_unit = _feature_source_unit(demand)
        location = _feature_location(demand)
        builder = FeatureTraceBuilder(feature_id)

        if strategic_binding is not None:
            builder.add_node(
                FeatureNode(
                    feature_id=feature_id,
                    stage=FeatureStage.STRATEGY_IR,
                    identity=feature_id,
                    status=FeatureNodeStatus.PASS,
                    source_unit=source_unit,
                    location=location,
                    evidence=("strategic_binding",),
                )
            )

        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.SEMANTIC_IR,
                identity=semantic_identity,
                status=FeatureNodeStatus.PASS,
                source_unit=source_unit,
                location=location,
                evidence=("semantic_demand",),
            )
        )
        if strategic_binding is not None:
            builder.add_edge(
                _feature_edge(
                    feature_id=feature_id,
                    source=FeatureStage.STRATEGY_IR,
                    target=FeatureStage.SEMANTIC_IR,
                    contract="strategy-ir-semantic-lowering",
                    expected=semantic_identity,
                    observed=semantic_identity,
                    status=FeatureEdgeStatus.SATISFIED,
                )
            )

        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.SEMANTIC_VALIDATION,
                identity=semantic_identity,
                status=FeatureNodeStatus.PASS,
                source_unit=source_unit,
                location=location,
                evidence=("semantic-validation-gate",),
            )
        )
        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.SEMANTIC_IR,
                target=FeatureStage.SEMANTIC_VALIDATION,
                contract="semantic-validation",
                expected=semantic_identity,
                observed=semantic_identity,
                status=FeatureEdgeStatus.SATISFIED,
            )
        )

        capability_demand = _capability_demand_for(capability_graph, demand)
        capability_identity = (
            f"{capability_demand.identity.source_unit}:{capability_demand.identity.local_name}"
            if capability_demand is not None
            else semantic_identity
        )
        capability_status = (
            FeatureNodeStatus.PASS
            if capability_demand is not None
            else FeatureNodeStatus.MISSING
        )
        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.CAPABILITY_GRAPH,
                identity=capability_identity,
                status=capability_status,
                source_unit=source_unit,
                location=location,
                evidence=("capability-graph",),
            )
        )
        if capability_demand is None:
            builder.add_edge(
                _feature_edge(
                    feature_id=feature_id,
                    source=FeatureStage.SEMANTIC_VALIDATION,
                    target=FeatureStage.CAPABILITY_GRAPH,
                    contract="semantic-capability-projection",
                    expected=semantic_identity,
                    observed=None,
                    status=FeatureEdgeStatus.BROKEN,
                    message=(
                        f"semantic demand '{semantic_identity}' has no projected "
                        "CapabilityDemand"
                    ),
                )
            )
            traces.append(
                builder.build(
                    root_stage=root_stage,
                    metadata=(("artifact_sha256", artifact_sha256),),
                )
            )
            continue

        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.SEMANTIC_VALIDATION,
                target=FeatureStage.CAPABILITY_GRAPH,
                contract="semantic-capability-projection",
                expected=semantic_identity,
                observed=capability_identity,
                status=FeatureEdgeStatus.SATISFIED,
            )
        )

        try:
            binding = bindings.binding_for(demand.lifecycle.slot.request_id)
        except (KeyError, AttributeError):
            binding = None
        binding_identity = (
            str(getattr(binding, "provenance_id", binding))
            if binding is not None
            else None
        )
        binding_status = (
            FeatureNodeStatus.PASS
            if binding is not None
            else FeatureNodeStatus.MISSING
        )
        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.STORAGE_BINDING,
                identity=binding_identity or semantic_identity,
                status=binding_status,
                source_unit=source_unit,
                location=location,
                evidence=("runtime-binding",),
            )
        )
        if binding is None:
            builder.add_edge(
                _feature_edge(
                    feature_id=feature_id,
                    source=FeatureStage.CAPABILITY_GRAPH,
                    target=FeatureStage.STORAGE_BINDING,
                    contract="capability-storage-binding",
                    expected=str(demand.lifecycle.slot.request_id),
                    observed=None,
                    status=FeatureEdgeStatus.BROKEN,
                    message=(
                        f"lifecycle storage request for '{semantic_identity}' "
                        "has no runtime binding"
                    ),
                )
            )
            traces.append(
                builder.build(
                    root_stage=root_stage,
                    metadata=(("artifact_sha256", artifact_sha256),),
                )
            )
            continue

        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.CAPABILITY_GRAPH,
                target=FeatureStage.STORAGE_BINDING,
                contract="capability-storage-binding",
                expected=str(demand.lifecycle.slot.request_id),
                observed=binding_identity,
                status=FeatureEdgeStatus.SATISFIED,
            )
        )

        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.NATIVE_LOWERING,
                identity=semantic_identity,
                status=(
                    FeatureNodeStatus.PASS
                    if semantic_identity in verified_stage_identities
                    else FeatureNodeStatus.UNKNOWN
                ),
                source_unit=source_unit,
                location=location,
                evidence=("native-lowering-gate",),
            )
        )
        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.STORAGE_BINDING,
                target=FeatureStage.NATIVE_LOWERING,
                contract="storage-native-lowering",
                expected=semantic_identity,
                observed=semantic_identity,
                status=FeatureEdgeStatus.SATISFIED,
            )
        )

        emission_identity = f"demand-{demand.identity.local_name}"
        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.EMISSION,
                identity=emission_identity,
                status=FeatureNodeStatus.PASS,
                source_unit=source_unit,
                location=location,
                evidence=("emitter-returned-artifact",),
            )
        )
        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.NATIVE_LOWERING,
                target=FeatureStage.EMISSION,
                contract="native-emission",
                expected=emission_identity,
                observed=emission_identity,
                status=FeatureEdgeStatus.SATISFIED,
            )
        )

        marker = f"(goal demand-{demand.identity.local_name} "
        marker_found = marker in artifact_text
        artifact_identity = f"sha256:{artifact_sha256}"
        builder.add_node(
            FeatureNode(
                feature_id=feature_id,
                stage=FeatureStage.ARTIFACT_ANALYSIS,
                identity=artifact_identity,
                status=(
                    FeatureNodeStatus.PASS
                    if marker_found
                    else FeatureNodeStatus.MISSING
                ),
                fingerprint=artifact_sha256,
                source_unit=source_unit,
                location=location,
                artifact_sha256=artifact_sha256,
                evidence=("emitted-demand-marker",),
            )
        )
        builder.add_edge(
            _feature_edge(
                feature_id=feature_id,
                source=FeatureStage.EMISSION,
                target=FeatureStage.ARTIFACT_ANALYSIS,
                contract="emission-artifact-coverage",
                expected=marker,
                observed=marker if marker_found else None,
                status=(
                    FeatureEdgeStatus.SATISFIED
                    if marker_found
                    else FeatureEdgeStatus.BROKEN
                ),
                message=(
                    None
                    if marker_found
                    else (
                        f"emitted artifact does not contain feature marker "
                        f"{marker!r}"
                    )
                ),
            )
        )
        traces.append(
            builder.build(
                root_stage=root_stage,
                metadata=(("artifact_sha256", artifact_sha256),),
            )
        )

    return tuple(sorted(traces, key=lambda trace: trace.feature_id))

class StrategyDependencyProof(str, Enum):
    PROVEN = "PROVEN"
    CONDITIONAL = "CONDITIONAL"
    OPEN = "OPEN"


class StrategyDependencyCode(str, Enum):
    PROVIDERLESS_DEMAND = "SDDR-001"
    UNFED_CAPABILITY = "SDDR-002"
    EXECUTION_UNREACHABLE = "SDDR-003"
    STATE_BLOCKED = "SDDR-004"
    COMPLETION_BLOCKED = "SDDR-005"
    UNROOTED_CYCLE = "SDDR-010"
    RECURRENT_PREEMPTION = "SDDR-013"
    STATE_CONSUMER_PATH_BLOCKED = "SDDR-014"
    MISSING_STATE_PRODUCER = "SDDR-020"
    STATE_CONSUMER_BEFORE_WRITER = "SDDR-021"
    PERSISTENT_STATE_STARVATION = "SDDR-022"
    OPEN_STATE_LOOP = "SDDR-023"
    ARBITRATION_BLOCKED = "SDDR-031"
    UNKNOWN_RUNTIME_BLOCK = "SDDR-040"
    RELIC_LIFECYCLE_CONNECTED = "SDDR-050"
    RELIC_PICKUP_WITNESS_MISSING = "SDDR-051"
    RELIC_RETURN_PATH_MISSING = "SDDR-052"
    RELIC_RECOVERY_PATH_MISSING = "SDDR-053"
    RELIC_RELEASE_WITNESS_OPEN = "SDDR-054"
    FEATURE_FIRST_BROKEN_EDGE = "SDDR-060"


@dataclass(frozen=True)
class StrategyDependencyNode:
    node_id: str
    kind: str
    label: str
    source_unit: str | None = None
    local_name: str | None = None
    rule_order: int | None = None


@dataclass(frozen=True)
class StrategyDependencyEdge:
    source: str
    target: str
    kind: str


@dataclass(frozen=True)
class StrategyDependencyFinding:
    finding_id: str
    code: StrategyDependencyCode
    severity: DiagnosticSeverity
    proof: StrategyDependencyProof
    message: str
    root_demand: str | None = None
    blocking_node: str | None = None
    chain: tuple[str, ...] = ()
    contributing_codes: tuple[str, ...] = ()
    rule_orders: tuple[int, ...] = ()
    locations: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyDependencyReport:
    schema_version: int
    demands: int
    capabilities: int
    providers: int
    rules: int
    persistent_states: int
    nodes: tuple[StrategyDependencyNode, ...]
    edges: tuple[StrategyDependencyEdge, ...]
    findings: tuple[StrategyDependencyFinding, ...]
    runtime_open_dependencies: int = 0
    artifact_sha256: str | None = None
    feature_traces: tuple[FeatureTrace, ...] = ()

    @property
    def errors(self):
        return tuple(x for x in self.findings if x.severity is DiagnosticSeverity.ERROR)

    @property
    def warnings(self):
        return tuple(x for x in self.findings if x.severity is DiagnosticSeverity.WARNING)

    @property
    def first_broken_edge_diagnostics(self) -> tuple[FeatureTraceDiagnostic, ...]:
        diagnostics = tuple(
            diagnostic
            for trace in self.feature_traces
            if (diagnostic := trace.diagnostic()) is not None
        )
        return tuple(sorted(
            diagnostics,
            key=lambda diagnostic: (
                _FEATURE_STAGE_INDEX[diagnostic.target_stage],
                diagnostic.feature_id,
                diagnostic.code,
                diagnostic.source_stage.value,
            ),
        ))

    def feature_trace(self, feature_id: str) -> FeatureTrace | None:
        for trace in self.feature_traces:
            if trace.feature_id == feature_id:
                return trace
        return None

    def with_feature_traces(
        self,
        feature_traces: Iterable[FeatureTrace],
    ) -> "StrategyDependencyReport":
        traces = tuple(feature_traces)
        feature_ids = tuple(trace.feature_id for trace in traces)
        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("feature_traces must have unique feature_id values")
        ordered = tuple(sorted(traces, key=lambda trace: trace.feature_id))
        return replace(self, feature_traces=ordered)

    def with_artifact(self, artifact: str | bytes) -> "StrategyDependencyReport":
        payload = artifact.encode() if isinstance(artifact, str) else artifact
        return replace(
            self,
            artifact_sha256=hashlib.sha256(payload).hexdigest(),
        )

    def to_json(self) -> str:
        return json.dumps({
            "schema_version": self.schema_version,
            "artifact_sha256": self.artifact_sha256,
            "feature_traces": [asdict(x) for x in self.feature_traces],
            "first_broken_edge_diagnostics": [
                asdict(x) for x in self.first_broken_edge_diagnostics
            ],
            "summary": {
                "demands": self.demands,
                "capabilities": self.capabilities,
                "providers": self.providers,
                "rules": self.rules,
                "persistent_states": self.persistent_states,
                "proven_errors": len(self.errors),
                "warnings": len(self.warnings),
                "runtime_open_dependencies": self.runtime_open_dependencies,
            },
            "nodes": [vars(x) for x in self.nodes],
            "edges": [vars(x) for x in self.edges],
            "findings": [{
                "finding_id": x.finding_id,
                "code": x.code.value,
                "severity": x.severity.value,
                "proof": x.proof.value,
                "message": x.message,
                "root_demand": x.root_demand,
                "blocking_node": x.blocking_node,
                "chain": list(x.chain),
                "contributing_codes": list(x.contributing_codes),
                "rule_orders": list(x.rule_orders),
                "locations": list(x.locations),
            } for x in self.findings],
        }, indent=2, sort_keys=True) + "\n"

    def write_json(self, path: Path) -> None:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        stage = path.with_name("." + path.name + ".stage")
        stage.write_text(self.to_json(), encoding="utf-8")
        stage.replace(path)


def _node_id(node: object) -> str:
    if isinstance(node, int):
        return f"rule:{node}"
    source = getattr(node, "source_unit", "")
    local = getattr(node, "local_name", "")
    return f"{type(node).__name__}:{source}:{local}"


def _loc(value: object) -> str | None:
    if value is None:
        return None
    path = getattr(value, "path", None)
    line = getattr(value, "line", None)
    column = getattr(value, "column", None)
    if path is None:
        return None
    text = str(path)
    if line is not None:
        text += f":{line}"
        if column is not None:
            text += f":{column}"
    return text


def _action_sig(head: str, args: Iterable[object]):
    return head, tuple(str(x) for x in args)


def _rule_sigs(rule: object):
    return tuple(
        _action_sig(action.expression.head, action.expression.args)
        for action in getattr(rule, "actions", ())
    )


def _provider_rules(provider: CapabilityProvider, report: RuleExecutionReport):
    if provider.action is None:
        return ()
    wanted = _action_sig(provider.action.primitive, provider.action.arguments)
    return tuple(sorted(
        rule.rule_order for rule in report.rules if wanted in _rule_sigs(rule)
    ))


def _diag_codes(items):
    return tuple(sorted({
        getattr(getattr(x, "code", None), "value", str(getattr(x, "code", "")))
        for x in items
    }))


def _fid(code, root, blocking, chain):
    raw = "\0".join((code.value, root or "", blocking or "", *chain))
    return f"{code.value.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _finding(code, severity, proof, message, *, root=None, blocking=None,
             chain=(), codes=(), rules=(), locations=()):
    return StrategyDependencyFinding(
        _fid(code, root, blocking, chain), code, severity, proof, message,
        root, blocking, tuple(chain), tuple(sorted(set(codes))),
        tuple(sorted(set(rules))), tuple(sorted({x for x in locations if x})),
    )


def analyze_strategy_dependencies(
    demands,
    capability_graph: CapabilityGraph,
    capability_report: ValidationReport,
    rule_report: RuleExecutionReport,
    persistent_state_report: PersistentStateReport,
    persistent_control_report=None,
    duc_plan=None,
    feature_traces: Iterable[FeatureTrace] = (),
) -> StrategyDependencyReport:
    """Correlate existing compiler reports; never reparses or invents semantics."""
    if not isinstance(capability_graph, CapabilityGraph):
        raise TypeError("capability_graph must be CapabilityGraph")
    if not isinstance(capability_report, ValidationReport):
        raise TypeError("capability_report must be ValidationReport")
    if not isinstance(rule_report, RuleExecutionReport):
        raise TypeError("rule_report must be RuleExecutionReport")
    if not isinstance(persistent_state_report, PersistentStateReport):
        raise TypeError("persistent_state_report must be PersistentStateReport")

    nodes = {}
    edge_set = set()

    def add_node(node, kind, label, rule_order=None):
        ident = _node_id(node)
        nodes.setdefault(ident, StrategyDependencyNode(
            ident, kind, label,
            getattr(node, "source_unit", None),
            getattr(node, "local_name", None),
            rule_order,
        ))
        return ident

    def add_named_node(node_id, kind, label, rule_order=None):
        nodes.setdefault(
            node_id,
            StrategyDependencyNode(
                node_id,
                kind,
                label,
                rule_order=rule_order,
            ),
        )
        return node_id

    for demand in capability_graph.demands:
        did = add_node(demand.identity, "STRATEGIC_DEMAND", demand.identity.local_name)
        cid = add_node(demand.target, "CAPABILITY", demand.target.local_name)
        edge_set.add((did, cid, "REQUIRES"))
        for provider in capability_graph.providers_of(demand.target):
            pid = add_node(provider.identity, "CAPABILITY_PROVIDER", provider.identity.local_name)
            edge_set.add((cid, pid, "PROVIDED_BY"))
            for prereq in provider.prerequisites:
                qid = add_node(prereq, "CAPABILITY", prereq.local_name)
                edge_set.add((pid, qid, "REQUIRES"))
            if provider.witness is not None:
                wid = add_node(provider.witness, "COMPLETION_WITNESS", provider.witness.local_name)
                edge_set.add((pid, wid, "WITNESSED_BY"))
            for order in _provider_rules(provider, rule_report):
                rid = add_node(order, "RULE", f"rule {order}", order)
                edge_set.add((pid, rid, "EXECUTES"))

    for access in persistent_state_report.accesses:
        rid = add_node(access.rule_order, "RULE", f"rule {access.rule_order}", access.rule_order)
        sid = f"persistent:{access.state.kind.value}:{access.state.identifier}"
        nodes.setdefault(sid, StrategyDependencyNode(
            sid, "PERSISTENT_STATE",
            f"{access.state.kind.value}:{access.state.identifier}",
        ))
        edge_set.add((rid, sid, "WRITES" if access.effect.value == "WRITE" else "READS"))

    # Keep the existing capability graph edges visible without giving them new semantics.
    for edge in capability_graph.edges:
        source = add_node(edge.source, "CAPABILITY_GRAPH_NODE", getattr(edge.source, "local_name", str(edge.source)))
        target = add_node(edge.target, "CAPABILITY_GRAPH_NODE", getattr(edge.target, "local_name", str(edge.target)))
        edge_set.add((source, target, edge.kind.value))

    cap_by_node = {}
    for diagnostic in capability_report.diagnostics:
        if diagnostic.node is not None:
            cap_by_node.setdefault(_node_id(diagnostic.node), []).append(diagnostic)

    reachability = rule_report.reachability
    reachable = None if reachability is None else set(reachability.reachable_rule_orders)
    findings = []

    for demand in sorted(capability_graph.demands, key=lambda x: _node_id(x.identity)):
        root = _node_id(demand.identity)
        providers = capability_graph.providers_of(demand.target)
        if not providers:
            diags = cap_by_node.get(_node_id(demand.identity), ())
            findings.append(_finding(
                StrategyDependencyCode.PROVIDERLESS_DEMAND,
                DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                f"demand '{demand.identity.local_name}' has no capability provider",
                root=root, blocking=_node_id(demand.target),
                chain=(root, _node_id(demand.target)),
                codes=_diag_codes(diags), locations=(_loc(demand.location),),
            ))
            continue

        for provider in providers:
            pid = _node_id(provider.identity)
            pdiags = cap_by_node.get(pid, ())
            pcodes = _diag_codes(pdiags)
            orders = _provider_rules(provider, rule_report)

            if provider.action is None and provider.kind.value != "OBSERVATION":
                findings.append(_finding(
                    StrategyDependencyCode.UNFED_CAPABILITY,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    f"provider '{provider.identity.local_name}' has no executable action",
                    root=root, blocking=pid,
                    chain=(root, _node_id(demand.target), pid),
                    codes=pcodes, locations=(_loc(provider.location),),
                ))
                continue

            if provider.action is not None and not orders:
                findings.append(_finding(
                    StrategyDependencyCode.EXECUTION_UNREACHABLE,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    f"provider '{provider.identity.local_name}' has an action but no emitted rule executes it",
                    root=root, blocking=pid,
                    chain=(root, _node_id(demand.target), pid),
                    codes=pcodes, locations=(_loc(provider.location),),
                ))
            elif orders and reachable is not None and not any(x in reachable for x in orders):
                findings.append(_finding(
                    StrategyDependencyCode.EXECUTION_UNREACHABLE,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    f"all executor rules for provider '{provider.identity.local_name}' are statically unreachable",
                    root=root, blocking=pid,
                    chain=(root, _node_id(demand.target), pid, *(f"rule:{x}" for x in orders)),
                    codes=pcodes, rules=orders, locations=(_loc(provider.location),),
                ))

            cycle_diags = tuple(
                item
                for key in (root, _node_id(demand.target), pid)
                for item in cap_by_node.get(key, ())
                if getattr(item.code, "value", item.code) == CapabilityDiagnosticCode.CYCLE.value
            )
            if cycle_diags:
                cycle = cycle_diags[0]
                related = tuple(_node_id(x) for x in getattr(cycle, "related", ()))
                findings.append(_finding(
                    StrategyDependencyCode.UNROOTED_CYCLE,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    "unrooted capability dependency cycle affects this demand",
                    root=root, blocking=_node_id(demand.target),
                    chain=(root, _node_id(demand.target), *related),
                    codes=_diag_codes(cycle_diags),
                    locations=(_loc(getattr(cycle, "location", None)), _loc(provider.location)),
                ))

            for diagnostic in persistent_state_report.diagnostics:
                if diagnostic.rule_order not in orders:
                    continue
                mapping = {
                    PersistentStateDiagnosticCode.CONSUMER_STARVED_BY_RECURRENT_WRITER:
                        StrategyDependencyCode.PERSISTENT_STATE_STARVATION,
                    PersistentStateDiagnosticCode.SAME_PASS_CONSUMER_PATH_BLOCKED:
                        StrategyDependencyCode.STATE_CONSUMER_PATH_BLOCKED,
                    PersistentStateDiagnosticCode.CONSUMER_BEFORE_WRITER:
                        StrategyDependencyCode.STATE_CONSUMER_BEFORE_WRITER,
                    PersistentStateDiagnosticCode.OPEN_LOOP_WRITE_WITHOUT_CONSUMER:
                        StrategyDependencyCode.OPEN_STATE_LOOP,
                }
                code = mapping.get(diagnostic.code)
                if code is None:
                    continue
                proof = (
                    StrategyDependencyProof.PROVEN
                    if diagnostic.severity is DiagnosticSeverity.ERROR
                    else StrategyDependencyProof.CONDITIONAL
                )
                sid = f"persistent:{diagnostic.access.state.kind.value}:{diagnostic.access.state.identifier}"
                findings.append(_finding(
                    code, diagnostic.severity, proof, diagnostic.message,
                    root=root, blocking=sid,
                    chain=(root, _node_id(demand.target), pid, f"rule:{diagnostic.rule_order}", sid),
                    codes=(diagnostic.code.value,), rules=(diagnostic.rule_order,),
                    locations=(_loc(diagnostic.location), _loc(diagnostic.access.location)),
                ))

            if any(getattr(x.code, "value", x.code) in {
                CapabilityDiagnosticCode.PROVIDER_BLOCKED.value,
                CapabilityDiagnosticCode.CONFLICT_NO_ARBITRATION.value,
                CapabilityDiagnosticCode.INVALID_RESOURCE_ARBITRATION.value,
            } for x in pdiags):
                findings.append(_finding(
                    StrategyDependencyCode.ARBITRATION_BLOCKED,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    f"provider '{provider.identity.local_name}' has blocked or invalid action arbitration",
                    root=root, blocking=pid,
                    chain=(root, _node_id(demand.target), pid),
                    codes=pcodes, locations=(_loc(provider.location),),
                ))

            if any(getattr(x.code, "value", x.code) in {
                CapabilityDiagnosticCode.PROVIDER_NO_WITNESS.value,
                CapabilityDiagnosticCode.WITNESS_NOT_ESTABLISHING.value,
                CapabilityDiagnosticCode.TIMING_CANNOT_WITNESS.value,
                CapabilityDiagnosticCode.WITNESS_NO_WORLD_STATE.value,
                CapabilityDiagnosticCode.RELEASE_NO_COMPLETION_PATH.value,
                CapabilityDiagnosticCode.PENDING_NO_WITNESS.value,
            } for x in pdiags):
                findings.append(_finding(
                    StrategyDependencyCode.COMPLETION_BLOCKED,
                    DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                    f"provider '{provider.identity.local_name}' has an invalid completion/witness contract",
                    root=root, blocking=pid,
                    chain=(root, _node_id(demand.target), pid),
                    codes=pcodes, locations=(_loc(provider.location),),
                ))

    # Correlate compiler-owned relic lifecycle metadata carried by the existing DUC plan.
    if duc_plan is not None:
        relic_rules = tuple(
            rule for rule in duc_plan.rules
            if (
                "relic" in rule.identity
                or any(
                    "relic" in str(expression.source).lower()
                    or "monk-with-relic" in str(expression.source).lower()
                    for expression in (*rule.facts, *rule.actions)
                )
            )
            and getattr(rule, "lifecycle", ())
        )
        if relic_rules:
            relic_root = "strategy:byzantine-relic-acquisition"
            relic_capability = "capability:relic-acquisition"
            add_named_node(relic_root, "STRATEGIC_DEMAND", "byzantine-relic-acquisition")
            add_named_node(relic_capability, "CAPABILITY", "relic-acquisition")
            edge_set.add((relic_root, relic_capability, "REQUIRES"))
            stage_rules: dict[NativeDucLifecycleStage, list] = {}
            for rule in sorted(relic_rules, key=lambda item: (item.order, item.identity)):
                rule_id = add_named_node(
                    f"duc:{rule.identity}",
                    "DUC_RULE",
                    rule.identity,
                    rule_order=rule.order,
                )
                edge_set.add((relic_capability, rule_id, "PROVIDED_BY"))
                for stage in rule.lifecycle:
                    stage_rules.setdefault(stage, []).append(rule)

            required = (
                NativeDucLifecycleStage.ADMISSIBILITY,
                NativeDucLifecycleStage.TARGET,
                NativeDucLifecycleStage.DISPATCH,
                NativeDucLifecycleStage.PICKUP_WITNESS,
                NativeDucLifecycleStage.RETURN,
                NativeDucLifecycleStage.RELEASE_WITNESS,
                NativeDucLifecycleStage.RECOVERY,
            )
            missing = tuple(stage for stage in required if stage not in stage_rules)
            if not missing:
                findings.append(_finding(
                    StrategyDependencyCode.RELIC_LIFECYCLE_CONNECTED,
                    DiagnosticSeverity.INFO,
                    StrategyDependencyProof.PROVEN,
                    "Byzantine relic acquisition has compiler-owned admissibility, Gaia targeting, Monk dispatch, pickup witness, return, release witness, and recovery",
                    root=relic_root,
                    blocking=relic_capability,
                    chain=(relic_root, relic_capability, *(f"duc:{rule.identity}" for rule in relic_rules)),
                    rules=(rule.order for rule in relic_rules),
                ))
            if NativeDucLifecycleStage.PICKUP_WITNESS not in stage_rules:
                findings.append(_finding(
                    StrategyDependencyCode.RELIC_PICKUP_WITNESS_MISSING,
                    DiagnosticSeverity.ERROR,
                    StrategyDependencyProof.PROVEN,
                    "relic acquisition has no compiler-owned monk-with-relic pickup witness",
                    root=relic_root,
                    blocking=relic_capability,
                    chain=(relic_root, relic_capability),
                ))
            if NativeDucLifecycleStage.RETURN not in stage_rules:
                findings.append(_finding(
                    StrategyDependencyCode.RELIC_RETURN_PATH_MISSING,
                    DiagnosticSeverity.ERROR,
                    StrategyDependencyProof.PROVEN,
                    "relic acquisition has no compiler-owned return path for a Monk carrying a relic",
                    root=relic_root,
                    blocking=relic_capability,
                    chain=(relic_root, relic_capability),
                ))
            if NativeDucLifecycleStage.RECOVERY not in stage_rules:
                findings.append(_finding(
                    StrategyDependencyCode.RELIC_RECOVERY_PATH_MISSING,
                    DiagnosticSeverity.ERROR,
                    StrategyDependencyProof.PROVEN,
                    "relic acquisition has no compiler-owned recovery/reacquisition path",
                    root=relic_root,
                    blocking=relic_capability,
                    chain=(relic_root, relic_capability),
                ))
            if NativeDucLifecycleStage.RELEASE_WITNESS in stage_rules:
                release_rule = stage_rules[NativeDucLifecycleStage.RELEASE_WITNESS][0]
                release_id = f"duc:{release_rule.identity}"
                edge_set.add((release_id, relic_capability, "RELEASES"))
                findings.append(_finding(
                    StrategyDependencyCode.RELIC_RELEASE_WITNESS_OPEN,
                    DiagnosticSeverity.INFO,
                    StrategyDependencyProof.OPEN,
                    "relic return/drop release is represented by a world-state observation, but native monastery deposit cannot be statically proven; this witness remains OPEN",
                    root=relic_root,
                    blocking=release_id,
                    chain=(relic_root, relic_capability, release_id),
                    rules=(release_rule.order,),
                ))

    for boundary in persistent_state_report.boundaries:
        if boundary.readers and boundary.first_writer is None:
            sid = f"persistent:{boundary.state.kind.value}:{boundary.state.identifier}"
            rules = tuple(sorted({x.rule_order for x in boundary.readers}))
            findings.append(_finding(
                StrategyDependencyCode.MISSING_STATE_PRODUCER,
                DiagnosticSeverity.ERROR, StrategyDependencyProof.PROVEN,
                f"persistent state '{boundary.state.identifier}' is read but has no writer",
                blocking=sid, chain=(sid, *(f"rule:{x}" for x in rules)),
                rules=rules, locations=(_loc(x.location) for x in boundary.readers),
            ))

    unique = {x.finding_id: x for x in findings}
    ordered = tuple(sorted(
        unique.values(),
        key=lambda x: (0 if x.severity is DiagnosticSeverity.ERROR else 1, x.code.value,
                       x.root_demand or "", x.blocking_node or "", x.finding_id),
    ))
    edges = tuple(StrategyDependencyEdge(*x) for x in sorted(edge_set))
    ordered_nodes = tuple(sorted(
        nodes.values(),
        key=lambda x: (x.kind, x.source_unit or "", x.local_name or "",
                       x.rule_order if x.rule_order is not None else -1, x.node_id),
    ))
    runtime_open = sum(
        provider.action is not None and getattr(provider, "admissibility", None) is not None
        for provider in capability_graph.providers
    )
    _ = demands, persistent_control_report
    report = StrategyDependencyReport(
        schema_version=1,
        demands=len(capability_graph.demands),
        capabilities=len(capability_graph.capabilities),
        providers=len(capability_graph.providers),
        rules=len(rule_report.rules),
        persistent_states=len({
            (x.state.kind.value, x.state.identifier)
            for x in persistent_state_report.accesses
        }),
        nodes=ordered_nodes,
        edges=edges,
        findings=ordered,
        runtime_open_dependencies=runtime_open,
    )
    return report.with_feature_traces(feature_traces)


__all__ = [
    "FEATURE_STAGE_ORDER",
    "FeatureEdge",
    "FeatureEdgeStatus",
    "FeatureNode",
    "FeatureNodeStatus",
    "FeatureStage",
    "FeatureTrace",
    "FeatureTraceBuilder",
    "FeatureTraceDiagnostic",
    "StrategyDependencyCode",
    "StrategyDependencyEdge",
    "StrategyDependencyFinding",
    "StrategyDependencyNode",
    "StrategyDependencyProof",
    "StrategyDependencyReport",
    "analyze_strategy_dependencies",
    "first_broken_edge",
]
