"""Structural validation for the typed effective AoE2 .per source graph."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..diagnostics import DiagnosticSeverity, DiagnosticSource, SemanticDiagnostic
from ..errors import CompileError
from ..ir.source_graph import (
    ConditionContext,
    EffectiveSourceGraph,
    EffectiveSourceSlice,
    LoadKind,
    LoadSymbolEnvironment,
    SourceEdge,
    SourceEdgeId,
    SourceFile,
    SourceFileId,
    SourceInstance,
    SourceInstanceId,
    structural_edge_id,
    structural_instance_id,
)


class SourceGraphValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class SourceGraphDiagnosticCode(str, Enum):
    DUPLICATE_FILE_ID = "SOURCE-GRAPH-VAL-001"
    DUPLICATE_INSTANCE_ID = "SOURCE-GRAPH-VAL-002"
    DUPLICATE_EDGE_ID = "SOURCE-GRAPH-VAL-003"
    ROOT_MISSING = "SOURCE-GRAPH-VAL-004"
    MULTIPLE_ROOTS = "SOURCE-GRAPH-VAL-005"
    ROOT_HAS_PARENT = "SOURCE-GRAPH-VAL-006"

    INSTANCE_MISSING_SOURCE = "SOURCE-GRAPH-VAL-010"
    INSTANCE_MISSING_PARENT = "SOURCE-GRAPH-VAL-011"
    INSTANCE_MISSING_LOAD_EDGE = "SOURCE-GRAPH-VAL-012"
    LOAD_EDGE_SOURCE_MISSING = "SOURCE-GRAPH-VAL-013"
    LOAD_EDGE_TARGET_MISSING = "SOURCE-GRAPH-VAL-014"
    LOAD_EDGE_INSTANCE_MISMATCH = "SOURCE-GRAPH-VAL-015"
    MULTIPLE_PARENT_EDGES = "SOURCE-GRAPH-VAL-016"
    ORPHAN_INSTANCE = "SOURCE-GRAPH-VAL-017"

    INSTANCE_CYCLE = "SOURCE-GRAPH-VAL-020"
    DEPTH_MISMATCH = "SOURCE-GRAPH-VAL-021"
    LOAD_DEPTH_EXCEEDED = "SOURCE-GRAPH-VAL-022"

    ACTIVE_UNRESOLVED_EDGE = "SOURCE-GRAPH-VAL-030"
    INACTIVE_HAS_CHILD = "SOURCE-GRAPH-VAL-031"
    ACTIVE_EDGE_MISSING_CHILD = "SOURCE-GRAPH-VAL-032"
    EDGE_PARENTAGE_MISMATCH = "SOURCE-GRAPH-VAL-033"
    EDGE_ORDER_NOT_MONOTONIC = "SOURCE-GRAPH-VAL-034"
    ACTIVE_EDGE_MULTIPLE_CHILDREN = "SOURCE-GRAPH-VAL-035"
    EDGE_CONDITION_INVALID = "SOURCE-GRAPH-VAL-036"

    INVALID_CONDITION_CONTEXT = "SOURCE-GRAPH-VAL-040"
    MISSING_CONDITION_SYMBOL = "SOURCE-GRAPH-VAL-041"
    CONDITION_DEPTH_EXCEEDED = "SOURCE-GRAPH-VAL-042"

    SLICE_ORDINAL_INVALID = "SOURCE-GRAPH-VAL-050"
    SLICE_ORDINAL_GAP = "SOURCE-GRAPH-VAL-051"
    SLICE_INSTANCE_MISSING = "SOURCE-GRAPH-VAL-052"
    SLICE_RANGE_INVALID = "SOURCE-GRAPH-VAL-053"
    SLICE_INSTANCE_ORDER_INVALID = "SOURCE-GRAPH-VAL-054"
    SLICE_OVERLAP = "SOURCE-GRAPH-VAL-055"
    SLICE_TEXT_HASH_MISMATCH = "SOURCE-GRAPH-VAL-056"
    SLICE_SOURCE_HASH_MISMATCH = "SOURCE-GRAPH-VAL-057"

    LOAD_SPLICE_ORDER_INVALID = "SOURCE-GRAPH-VAL-060"
    CHILD_SUBTREE_ORDER_INVALID = "SOURCE-GRAPH-VAL-061"
    EFFECTIVE_ORDER_DUPLICATED = "SOURCE-GRAPH-VAL-062"

    ASSEMBLY_FINGERPRINT_MISMATCH = "SOURCE-GRAPH-VAL-070"
    EFFECTIVE_FINGERPRINT_MISMATCH = "SOURCE-GRAPH-VAL-071"

    RANDOM_LOAD_UNMATERIALIZED = "SOURCE-GRAPH-VAL-080"


@dataclass(frozen=True)
class SourceGraphValidationPolicy:
    max_load_depth: int = 10
    max_conditional_depth: int = 50
    require_contiguous_slice_ordinals: bool = True
    require_fingerprint_match: bool = True
    reject_random_loads: bool = True


@dataclass(frozen=True)
class SourceGraphDiagnostic:
    code: SourceGraphDiagnosticCode
    severity: SourceGraphValidationSeverity
    message: str
    path: Path | None = None
    line: int | None = None
    column: int | None = None
    instance_id: str | None = None
    edge_id: str | None = None


@dataclass(frozen=True)
class SourceGraphValidationReport:
    valid: bool
    diagnostics: tuple[SourceGraphDiagnostic, ...]
    files_checked: int
    instances_checked: int
    edges_checked: int
    slices_checked: int
    assembly_fingerprint_valid: bool
    effective_fingerprint_valid: bool

    @property
    def errors(self) -> tuple[SourceGraphDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is SourceGraphValidationSeverity.ERROR
        )


class SourceGraphValidationError(CompileError):
    def __init__(self, report: SourceGraphValidationReport) -> None:
        self.report = report
        diagnostics = tuple(_to_semantic_diagnostic(item) for item in report.errors)
        super().__init__(
            "effective source graph validation failed",
            diagnostics=diagnostics,
        )


def _semantic_id(item: SourceGraphDiagnostic) -> str:
    return hashlib.sha256(
        "\x00".join(
            (
                item.code.value,
                item.message,
                str(item.path or ""),
                str(item.line or ""),
                str(item.column or ""),
                item.instance_id or "",
                item.edge_id or "",
            )
        ).encode("utf-8")
    ).hexdigest()


def _to_semantic_diagnostic(item: SourceGraphDiagnostic) -> SemanticDiagnostic:
    return SemanticDiagnostic(
        id=_semantic_id(item),
        source=DiagnosticSource.LEARNERAI,
        code=item.code.value,
        severity=DiagnosticSeverity(item.severity.value),
        message=item.message,
        path=item.path,
        line=item.line,
        column=item.column,
    )


def _diag(
    code: SourceGraphDiagnosticCode,
    message: str,
    *,
    path: Path | None = None,
    line: int | None = None,
    column: int | None = None,
    instance_id: str | None = None,
    edge_id: str | None = None,
) -> SourceGraphDiagnostic:
    return SourceGraphDiagnostic(
        code=code,
        severity=SourceGraphValidationSeverity.ERROR,
        message=message,
        path=path,
        line=line,
        column=column,
        instance_id=instance_id,
        edge_id=edge_id,
    )


def _diag_key(item: SourceGraphDiagnostic) -> tuple[object, ...]:
    return (
        str(item.path or ""),
        item.line or 0,
        item.column or 0,
        item.code.value,
        item.instance_id or "",
        item.edge_id or "",
        item.message,
    )


def _instance_path(instance: SourceInstance | None) -> Path | None:
    return instance.physical.path if instance is not None else None


def _edge_location(edge: SourceEdge) -> tuple[Path, int, int]:
    return (
        edge.span.source.path,
        edge.span.start_line,
        edge.span.start_column,
    )


def _index_instances(
    graph: EffectiveSourceGraph,
    diagnostics: list[SourceGraphDiagnostic],
) -> dict[SourceInstanceId, SourceInstance]:
    result: dict[SourceInstanceId, SourceInstance] = {}
    for instance in graph.instances:
        if instance.identity in result:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.DUPLICATE_INSTANCE_ID,
                    f"duplicate source instance identity '{instance.identity.value}'",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        else:
            result[instance.identity] = instance
    return result


def _index_files(
    graph: EffectiveSourceGraph,
    diagnostics: list[SourceGraphDiagnostic],
) -> dict[SourceFileId, SourceFile]:
    result: dict[SourceFileId, SourceFile] = {}
    for source in graph.files:
        if source.identity in result:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.DUPLICATE_FILE_ID,
                    f"duplicate source file identity '{source.identity.canonical_path}'",
                    path=source.path,
                )
            )
        else:
            result[source.identity] = source
    return result


def _index_edges(
    graph: EffectiveSourceGraph,
    diagnostics: list[SourceGraphDiagnostic],
) -> dict[SourceEdgeId, SourceEdge]:
    result: dict[SourceEdgeId, SourceEdge] = {}
    for edge in graph.edges:
        if edge.identity in result:
            path, line, column = _edge_location(edge)
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.DUPLICATE_EDGE_ID,
                    f"duplicate source edge identity '{edge.edge_id}'",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )
        else:
            result[edge.identity] = edge
    return result


def _validate_files(
    graph: EffectiveSourceGraph,
    files: dict[SourceFileId, SourceFile],
    diagnostics: list[SourceGraphDiagnostic],
) -> None:
    for source in graph.files:
        if source.identity.path != source.path:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_SOURCE,
                    "source file identity path does not match the physical path",
                    path=source.path,
                )
            )
        if source.identity.content_sha256 != hashlib.sha256(
            source.text.encode("utf-8")
        ).hexdigest():
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_SOURCE_HASH_MISMATCH,
                    "source file content does not match its identity hash",
                    path=source.path,
                )
            )


def _validate_instances(
    graph: EffectiveSourceGraph,
    files: dict[SourceFileId, SourceFile],
    instances: dict[SourceInstanceId, SourceInstance],
    edges: dict[SourceEdgeId, SourceEdge],
    policy: SourceGraphValidationPolicy,
    diagnostics: list[SourceGraphDiagnostic],
) -> None:
    roots = [item for item in graph.instances if item.parent is None]
    if not roots:
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.ROOT_MISSING,
                "source graph has no root instance",
            )
        )
    elif len(roots) != 1:
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.MULTIPLE_ROOTS,
                "source graph has multiple root instances",
            )
        )

    if graph.root.identity not in instances:
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.ROOT_MISSING,
                f"declared root '{graph.root.instance_id}' is not in instance inventory",
                path=_instance_path(graph.root),
                instance_id=graph.root.instance_id,
            )
        )

    for instance in graph.instances:
        if instance.source not in files:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_SOURCE,
                    f"instance '{instance.instance_id}' references unknown source file",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.instance_id != graph.root.instance_id and instance.parent is None:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_PARENT,
                    f"non-root instance '{instance.instance_id}' has no parent",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.parent is not None and instance.parent not in instances:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_PARENT,
                    f"instance '{instance.instance_id}' references unknown parent '{instance.parent.value}'",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.via_edge is None and instance.identity != graph.root.identity:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_LOAD_EDGE,
                    f"instance '{instance.instance_id}' has no incoming load edge",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.via_edge is not None and instance.via_edge not in edges:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_LOAD_EDGE,
                    f"instance '{instance.instance_id}' references unknown load edge '{instance.via_edge.value}'",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )

        expected_identity = structural_instance_id(
            source=instance.source,
            parent=instance.parent,
            via_edge=instance.via_edge,
        )
        if expected_identity != instance.identity:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.LOAD_EDGE_INSTANCE_MISMATCH,
                    f"instance '{instance.instance_id}' is not the structural identity of its source and ancestry",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )

        expected_depth = 0 if instance.parent is None else instances.get(
            instance.parent
        ).depth + 1 if instances.get(instance.parent) else -1
        if expected_depth != instance.depth:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.DEPTH_MISMATCH,
                    f"instance '{instance.instance_id}' has depth {instance.depth}, expected {expected_depth}",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.depth > policy.max_load_depth:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.LOAD_DEPTH_EXCEEDED,
                    f"instance '{instance.instance_id}' exceeds load depth {policy.max_load_depth}",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )

        if not instance.ancestry or instance.ancestry[-1] != instance.source:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.LOAD_EDGE_INSTANCE_MISMATCH,
                    f"instance '{instance.instance_id}' ancestry does not terminate at its source",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if len(instance.ancestry) != len(set(instance.ancestry)):
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_CYCLE,
                    f"instance '{instance.instance_id}' ancestry contains a repeated source file",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        if instance.parent is None:
            if instance.ancestry != (instance.source,):
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.ROOT_HAS_PARENT,
                        f"root instance '{instance.instance_id}' has non-root ancestry",
                        path=_instance_path(instance),
                        instance_id=instance.instance_id,
                    )
                )
        elif instance.parent in instances:
            parent = instances[instance.parent]
            if instance.ancestry != parent.ancestry + (instance.source,):
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.LOAD_EDGE_INSTANCE_MISMATCH,
                        f"instance '{instance.instance_id}' ancestry does not match its parent",
                        path=_instance_path(instance),
                        instance_id=instance.instance_id,
                    )
                )

    state: dict[SourceInstanceId, int] = {}

    def visit(instance_id: SourceInstanceId) -> None:
        marker = state.get(instance_id, 0)
        if marker == 1:
            instance = instances.get(instance_id)
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INSTANCE_CYCLE,
                    f"source instance parent cycle reaches '{instance_id.value}'",
                    path=_instance_path(instance),
                    instance_id=instance_id.value,
                )
            )
            return
        if marker == 2 or instance_id not in instances:
            return
        state[instance_id] = 1
        parent = instances[instance_id].parent
        if parent is not None:
            visit(parent)
        state[instance_id] = 2

    for instance in graph.instances:
        visit(instance.identity)


def _validate_edges(
    graph: EffectiveSourceGraph,
    instances: dict[SourceInstanceId, SourceInstance],
    edges: dict[SourceEdgeId, SourceEdge],
    symbols: LoadSymbolEnvironment,
    policy: SourceGraphValidationPolicy,
    diagnostics: list[SourceGraphDiagnostic],
) -> None:
    incoming: dict[SourceInstanceId, list[SourceEdge]] = {}
    outgoing: dict[SourceInstanceId, list[SourceEdge]] = {}

    for edge in graph.edges:
        path, line, column = _edge_location(edge)
        if edge.source not in instances:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.LOAD_EDGE_SOURCE_MISSING,
                    f"edge '{edge.edge_id}' references unknown source instance",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )
            continue

        outgoing.setdefault(edge.source, []).append(edge)

        if edge.condition.depth > policy.max_conditional_depth:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.CONDITION_DEPTH_EXCEEDED,
                    f"edge '{edge.edge_id}' exceeds conditional depth {policy.max_conditional_depth}",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )

        for predicate in edge.condition.predicates:
            if symbols.state(predicate.symbol) is None:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.MISSING_CONDITION_SYMBOL,
                        f"edge '{edge.edge_id}' references unresolved load symbol '{predicate.symbol}'",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=edge.edge_id,
                    )
                )
        if edge.active != edge.condition.evaluate(symbols):
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.EDGE_CONDITION_INVALID,
                    f"edge '{edge.edge_id}' active state disagrees with its condition context",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )

        expected_edge_id = structural_edge_id(
            source=edge.source,
            span=edge.span,
            kind=edge.kind,
            condition=edge.condition,
            target_text=edge.target_text,
        )
        if expected_edge_id != edge.identity:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.EDGE_CONDITION_INVALID,
                    f"edge '{edge.edge_id}' is not the structural identity of its source span",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )

        if edge.kind is LoadKind.RANDOM:
            if edge.active and policy.reject_random_loads:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.RANDOM_LOAD_UNMATERIALIZED,
                        f"random load edge '{edge.edge_id}' has no deterministic materialization",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=edge.edge_id,
                    )
                )
            continue

        if edge.target is None and edge.kind not in {
            LoadKind.CONDITIONAL_DEFINED,
            LoadKind.CONDITIONAL_NOT_DEFINED,
            LoadKind.CONDITIONAL_ELSE,
        }:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.ACTIVE_UNRESOLVED_EDGE,
                    f"load edge '{edge.edge_id}' has no target source",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )

        if edge.kind in {
            LoadKind.CONDITIONAL_DEFINED,
            LoadKind.CONDITIONAL_NOT_DEFINED,
            LoadKind.CONDITIONAL_ELSE,
        }:
            if edge.child is not None:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.INACTIVE_HAS_CHILD,
                        f"conditional directive edge '{edge.edge_id}' cannot own a child instance",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=edge.edge_id,
                    )
                )
            continue

        if edge.active:
            if edge.target is None:
                continue
            if edge.child is None:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.ACTIVE_EDGE_MISSING_CHILD,
                        f"active load edge '{edge.edge_id}' has no child instance",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=edge.edge_id,
                    )
                )
                continue
            child = instances.get(edge.child)
            if child is None:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.ACTIVE_EDGE_MISSING_CHILD,
                        f"active load edge '{edge.edge_id}' references unknown child '{edge.child.value}'",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=edge.edge_id,
                    )
                )
                continue
            incoming.setdefault(child.identity, []).append(edge)
            if child.parent != edge.source or child.via_edge != edge.identity:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.EDGE_PARENTAGE_MISMATCH,
                        f"edge '{edge.edge_id}' does not agree with child '{child.instance_id}' parentage",
                        path=path,
                        line=line,
                        column=column,
                        instance_id=child.instance_id,
                        edge_id=edge.edge_id,
                    )
                )
            if child.source != edge.target:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.LOAD_EDGE_INSTANCE_MISMATCH,
                        f"edge '{edge.edge_id}' target does not match child '{child.instance_id}' source",
                        path=path,
                        line=line,
                        column=column,
                        instance_id=child.instance_id,
                        edge_id=edge.edge_id,
                    )
                )
        elif edge.child is not None:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.INACTIVE_HAS_CHILD,
                    f"inactive load edge '{edge.edge_id}' has child instance '{edge.child.value}'",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )

    for instance in graph.instances:
        if instance.identity == graph.root.identity:
            continue
        links = incoming.get(instance.identity, [])
        if len(links) == 0:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.ORPHAN_INSTANCE,
                    f"instance '{instance.instance_id}' has no incoming active load edge",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )
        elif len(links) > 1:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.MULTIPLE_PARENT_EDGES,
                    f"instance '{instance.instance_id}' has {len(links)} incoming active load edges",
                    path=_instance_path(instance),
                    instance_id=instance.instance_id,
                )
            )

    for source_id, source_edges in outgoing.items():
        loads = [
            edge
            for edge in source_edges
            if edge.kind in {LoadKind.FILE, LoadKind.RAW_LOAD, LoadKind.RANDOM}
        ]
        orders = [edge.lexical_order for edge in sorted(loads, key=lambda item: item.lexical_order)]
        if orders != sorted(orders) or len(orders) != len(set(orders)):
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.EDGE_ORDER_NOT_MONOTONIC,
                    f"load edge lexical order is not strictly increasing for instance '{source_id.value}'",
                    instance_id=source_id.value,
                )
            )


def _validate_slices(
    graph: EffectiveSourceGraph,
    instances: dict[SourceInstanceId, SourceInstance],
    files: dict[SourceFileId, SourceFile],
    diagnostics: list[SourceGraphDiagnostic],
) -> None:
    ordinals = [item.ordinal for item in graph.slices]
    if ordinals != list(range(len(graph.slices))):
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.SLICE_ORDINAL_GAP,
                "effective source slice ordinals must be contiguous starting at zero",
            )
        )

    by_instance: dict[SourceInstanceId, list[EffectiveSourceSlice]] = {}
    for slice_ in graph.slices:
        instance = instances.get(slice_.instance)
        if instance is None:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_INSTANCE_MISSING,
                    f"slice {slice_.ordinal} references unknown instance '{slice_.instance.value}'",
                    path=slice_.path,
                )
            )
            continue
        if slice_.physical_range.source != instance.source:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_SOURCE_HASH_MISMATCH,
                    f"slice {slice_.ordinal} source identity does not match its instance",
                    path=slice_.path,
                    instance_id=instance.instance_id,
                )
            )
        source = files.get(slice_.physical_range.source)
        if source is None:
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_SOURCE_HASH_MISMATCH,
                    f"slice {slice_.ordinal} references unknown source file",
                    path=slice_.path,
                    instance_id=instance.instance_id,
                )
            )
            continue
        if slice_.physical_range.end_offset > len(source.text):
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_RANGE_INVALID,
                    f"slice {slice_.ordinal} ends beyond source length",
                    path=slice_.path,
                    instance_id=instance.instance_id,
                )
            )
        by_instance.setdefault(slice_.instance, []).append(slice_)

    for instance_id, slices in by_instance.items():
        ordered = sorted(slices, key=lambda item: item.physical_range.start_offset)
        previous_end = -1
        for item in ordered:
            if item.physical_range.start_offset < previous_end:
                diagnostics.append(
                    _diag(
                        SourceGraphDiagnosticCode.SLICE_OVERLAP,
                        f"slice {item.ordinal} overlaps another slice for instance '{instance_id.value}'",
                        path=item.path,
                        instance_id=instance_id.value,
                    )
                )
            previous_end = max(previous_end, item.physical_range.end_offset)
        ords = [item.ordinal for item in ordered]
        if ords != sorted(ords):
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.SLICE_INSTANCE_ORDER_INVALID,
                    f"slice ordinals are not physical-source ordered for instance '{instance_id.value}'",
                    path=ordered[0].path if ordered else None,
                    instance_id=instance_id.value,
                )
            )


def _validate_effective_splicing(
    graph: EffectiveSourceGraph,
    instances: dict[SourceInstanceId, SourceInstance],
    diagnostics: list[SourceGraphDiagnostic],
) -> None:
    slices_by_instance: dict[SourceInstanceId, list[EffectiveSourceSlice]] = {}
    for slice_ in graph.slices:
        slices_by_instance.setdefault(slice_.instance, []).append(slice_)

    descendants_cache: dict[SourceInstanceId, set[SourceInstanceId]] = {}

    def descendants(root: SourceInstanceId) -> set[SourceInstanceId]:
        if root in descendants_cache:
            return descendants_cache[root]
        result: set[SourceInstanceId] = {root}
        changed = True
        while changed:
            changed = False
            for instance in graph.instances:
                if instance.parent in result and instance.identity not in result:
                    result.add(instance.identity)
                    changed = True
        descendants_cache[root] = result
        return result

    for edge in graph.edges:
        if not edge.active or edge.kind not in {LoadKind.FILE, LoadKind.RAW_LOAD}:
            continue
        if edge.child is None:
            continue
        child_slices = [
            slice_
            for instance_id in descendants(edge.child)
            for slice_ in slices_by_instance.get(instance_id, ())
        ]
        if not child_slices:
            continue
        child_min = min(item.ordinal for item in child_slices)
        child_max = max(item.ordinal for item in child_slices)
        parent_slices = slices_by_instance.get(edge.source, ())
        before = [
            item
            for item in parent_slices
            if item.physical_range.end_offset <= edge.span.start_offset
        ]
        after = [
            item
            for item in parent_slices
            if item.physical_range.start_offset >= edge.span.end_offset
        ]
        lower = max((item.ordinal for item in before), default=-1)
        upper = min((item.ordinal for item in after), default=len(graph.slices))
        if not (lower < child_min <= child_max < upper):
            path, line, column = _edge_location(edge)
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.LOAD_SPLICE_ORDER_INVALID,
                    f"load edge '{edge.edge_id}' does not bracket its child subtree in effective order",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )
            continue
        subtree_ids = descendants(edge.child)
        interleaved = [
            item
            for item in graph.slices
            if child_min <= item.ordinal <= child_max
            and item.instance not in subtree_ids
        ]
        if interleaved:
            path, line, column = _edge_location(edge)
            diagnostics.append(
                _diag(
                    SourceGraphDiagnosticCode.CHILD_SUBTREE_ORDER_INVALID,
                    f"load edge '{edge.edge_id}' has an unrelated slice interleaved with its child subtree",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=edge.edge_id,
                )
            )


def _validate_fingerprints(
    graph: EffectiveSourceGraph,
    policy: SourceGraphValidationPolicy,
    diagnostics: list[SourceGraphDiagnostic],
) -> tuple[bool, bool]:
    if not policy.require_fingerprint_match:
        return True, True
    assembly = EffectiveSourceGraph.compute_assembly_fingerprint(
        root=graph.root,
        files=graph.files,
        instances=graph.instances,
        edges=graph.edges,
        slices=graph.slices,
        symbols=graph.symbol_environment,
    )
    effective = EffectiveSourceGraph.compute_effective_fingerprint(
        root=graph.root,
        slices=graph.slices,
    )
    if assembly != graph.assembly_fingerprint:
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.ASSEMBLY_FINGERPRINT_MISMATCH,
                "stored assembly fingerprint does not match canonical graph content",
                path=_instance_path(graph.root),
                instance_id=graph.root.instance_id,
            )
        )
    if effective != graph.effective_fingerprint:
        diagnostics.append(
            _diag(
                SourceGraphDiagnosticCode.EFFECTIVE_FINGERPRINT_MISMATCH,
                "stored effective fingerprint does not match effective source content",
                path=_instance_path(graph.root),
                instance_id=graph.root.instance_id,
            )
        )
    return assembly == graph.assembly_fingerprint, effective == graph.effective_fingerprint


def validate_effective_source_graph(
    graph: EffectiveSourceGraph,
    *,
    policy: SourceGraphValidationPolicy | None = None,
) -> SourceGraphValidationReport:
    policy = policy or SourceGraphValidationPolicy()
    diagnostics: list[SourceGraphDiagnostic] = []

    files = _index_files(graph, diagnostics)
    instances = _index_instances(graph, diagnostics)
    edges = _index_edges(graph, diagnostics)

    _validate_files(graph, files, diagnostics)
    _validate_instances(graph, files, instances, edges, policy, diagnostics)
    _validate_edges(
        graph,
        instances,
        edges,
        graph.symbol_environment,
        policy,
        diagnostics,
    )
    _validate_slices(graph, instances, files, diagnostics)
    _validate_effective_splicing(graph, instances, diagnostics)
    assembly_valid, effective_valid = _validate_fingerprints(
        graph,
        policy,
        diagnostics,
    )

    ordered = tuple(sorted(diagnostics, key=_diag_key))
    return SourceGraphValidationReport(
        valid=not ordered,
        diagnostics=ordered,
        files_checked=len(graph.files),
        instances_checked=len(graph.instances),
        edges_checked=len(graph.edges),
        slices_checked=len(graph.slices),
        assembly_fingerprint_valid=assembly_valid,
        effective_fingerprint_valid=effective_valid,
    )


__all__ = [
    "SourceGraphDiagnostic",
    "SourceGraphDiagnosticCode",
    "SourceGraphValidationError",
    "SourceGraphValidationPolicy",
    "SourceGraphValidationReport",
    "SourceGraphValidationSeverity",
    "validate_effective_source_graph",
]
