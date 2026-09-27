"""Structural validation for the effective AoE2 .per source graph.

The resolver constructs candidate source graphs. This module independently
proves that the constructed graph is internally coherent before downstream
parsing or semantic compilation trusts it.

The validator deliberately does not read the filesystem, resolve paths, or
interpret arbitrary .per semantics.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..diagnostics import DiagnosticSeverity, DiagnosticSource, SemanticDiagnostic
from ..errors import CompileError
from ..source_graph import (
    EffectiveSourceGraph,
    EffectiveSourceSlice,
    LoadKind,
    LoadSymbolState,
    SourceEdge,
    SourceInstance,
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
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is SourceGraphValidationSeverity.ERROR
        )


class SourceGraphValidationError(CompileError):
    """Compiler-owned failure for an internally invalid source graph."""

    def __init__(self, report: SourceGraphValidationReport) -> None:
        self.report = report
        diagnostics = tuple(_to_semantic_diagnostic(item) for item in report.errors)
        super().__init__(
            "effective source graph validation failed",
            diagnostics=diagnostics,
        )


def _semantic_id(item: SourceGraphDiagnostic) -> str:
    payload = (
        item.code.value,
        item.message,
        str(item.path) if item.path is not None else "",
        item.line,
        item.column,
        item.instance_id or "",
        item.edge_id or "",
    )
    return hashlib.sha256(
        "\x00".join(str(value) for value in payload).encode("utf-8")
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


def _path_of(instance: SourceInstance | None) -> Path | None:
    return instance.physical.path if instance is not None else None


def _location_for_edge(edge: SourceEdge) -> tuple[Path | None, int | None, int | None]:
    location = edge.location
    path = Path(location.source_unit) if location.source_unit else None
    return path, location.line, location.column


def _diagnostic(
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


def _sort_key(item: SourceGraphDiagnostic) -> tuple[object, ...]:
    return (
        str(item.path or ""),
        item.line if item.line is not None else 0,
        item.column if item.column is not None else 0,
        item.code.value,
        item.instance_id or "",
        item.edge_id or "",
        item.message,
    )


def _fingerprint_payload(graph: EffectiveSourceGraph) -> dict[str, object]:
    return {
        "root": graph.root.instance_id,
        "symbols": graph.symbol_environment.fingerprint_payload(),
        "instances": [
            {
                "id": item.instance_id,
                "path": str(item.physical.path),
                "sha256": item.physical.sha256,
                "stack": [str(path) for path in item.load_stack],
                "occurrence": item.occurrence,
            }
            for item in graph.instances
        ],
        "edges": [
            {
                "source": item.source_instance,
                "target": str(item.target_path) if item.target_path else None,
                "kind": item.kind.value,
                "condition_kind": (
                    item.condition_kind.value if item.condition_kind else None
                ),
                "line": item.location.line,
                "column": item.location.column,
                "condition_symbol": item.condition_symbol,
                "active": item.active,
            }
            for item in graph.edges
        ],
        "slices": [
            {
                "ordinal": item.ordinal,
                "instance": item.instance_id,
                "path": str(item.path),
                "start_line": item.start_line,
                "end_line": item.end_line,
                "start_column": item.start_column,
                "sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
            }
            for item in graph.slices
        ],
    }


def _recompute_fingerprint(graph: EffectiveSourceGraph) -> str:
    payload = _fingerprint_payload(graph)
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()


def _effective_fingerprint(graph: EffectiveSourceGraph) -> str:
    payload = {
        "root": graph.root.instance_id,
        "slices": [
            {
                "ordinal": item.ordinal,
                "instance": item.instance_id,
                "path": str(item.path),
                "sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
            }
            for item in sorted(graph.slices, key=lambda item: item.ordinal)
        ],
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()


def _instance_depth(instance: SourceInstance) -> int:
    return max(0, len(instance.load_stack) - 1)


def _edge_sort_key(edge: SourceEdge) -> tuple[object, ...]:
    return (
        edge.location.line,
        edge.location.column,
        edge.kind.value,
        edge.condition_symbol or "",
        str(edge.target_path or ""),
    )


def _expected_children(
    graph: EffectiveSourceGraph,
    instances_by_id: dict[str, SourceInstance],
) -> tuple[
    dict[str, str],
    tuple[SourceGraphDiagnostic, ...],
]:
    diagnostics: list[SourceGraphDiagnostic] = []
    children: dict[str, str] = {}
    graph_instance_order = {
        instance.instance_id: index
        for index, instance in enumerate(graph.instances)
    }
    consumed: set[str] = set()

    for source_id, source in sorted(instances_by_id.items()):
        edges = sorted(
            (
                edge
                for edge in graph.edges
                if edge.source_instance == source_id
                and edge.active
                and edge.kind is not LoadKind.RANDOM
                and edge.target_path is not None
            ),
            key=_edge_sort_key,
        )
        for edge in edges:
            candidates = [
                instance
                for instance in graph.instances
                if instance.instance_id not in consumed
                and instance.physical.path == edge.target_path
                and instance.load_stack[:-1] == source.load_stack
            ]
            candidates.sort(key=lambda item: graph_instance_order[item.instance_id])
            path, line, column = _location_for_edge(edge)
            if not candidates:
                diagnostics.append(
                    _diagnostic(
                        SourceGraphDiagnosticCode.ACTIVE_EDGE_MISSING_CHILD,
                        (
                            f"active load edge from '{source_id}' to "
                            f"'{edge.target_path}' has no corresponding child instance"
                        ),
                        path=path,
                        line=line,
                        column=column,
                        instance_id=source_id,
                    )
                )
                continue
            child = candidates[0]
            children[edge_key(edge)] = child.instance_id
            consumed.add(child.instance_id)

    root_id = graph.root.instance_id
    for instance in graph.instances:
        if instance.instance_id == root_id:
            continue
        if instance.instance_id not in consumed:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.ORPHAN_INSTANCE,
                    f"instance '{instance.instance_id}' has no corresponding active load edge",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )

    return children, tuple(diagnostics)


def edge_key(edge: SourceEdge) -> str:
    path = str(edge.target_path or "")
    return "|".join(
        (
            edge.source_instance,
            str(edge.location.line),
            str(edge.location.column),
            edge.kind.value,
            edge.condition_symbol or "",
            edge.condition_kind.value if edge.condition_kind else "",
            path,
        )
    )


def _validate_parentage(
    graph: EffectiveSourceGraph,
    instances_by_id: dict[str, SourceInstance],
    children: dict[str, str],
    policy: SourceGraphValidationPolicy,
) -> list[SourceGraphDiagnostic]:
    diagnostics: list[SourceGraphDiagnostic] = []
    root_id = graph.root.instance_id

    for instance in graph.instances:
        if not instance.load_stack:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_PARENT,
                    f"instance '{instance.instance_id}' has an empty load stack",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )
            continue

        if instance.instance_id != graph.root.instance_id and len(instance.load_stack) < 2:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_PARENT,
                    f"non-root instance '{instance.instance_id}' has no parent in its load stack",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )

        if instance.load_stack[-1] != instance.physical.path:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.LOAD_EDGE_INSTANCE_MISMATCH,
                    f"instance '{instance.instance_id}' load stack does not terminate at its physical source",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )

        if len(instance.load_stack) != len(set(instance.load_stack)):
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.INSTANCE_CYCLE,
                    f"instance '{instance.instance_id}' contains a repeated physical path in its load stack",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )

        expected_depth = _instance_depth(instance)
        if expected_depth != len(instance.load_stack) - 1:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.DEPTH_MISMATCH,
                    f"instance '{instance.instance_id}' has inconsistent structural depth",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )
        if expected_depth > policy.max_load_depth:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.LOAD_DEPTH_EXCEEDED,
                    f"instance '{instance.instance_id}' exceeds configured load depth",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )

    if graph.root.instance_id not in instances_by_id:
        return diagnostics

    if graph.root.load_stack != (graph.root.physical.path,):
        diagnostics.append(
            _diagnostic(
                SourceGraphDiagnosticCode.ROOT_HAS_PARENT,
                "root instance has a non-root load stack",
                path=_path_of(graph.root),
                instance_id=root_id,
            )
        )

    return diagnostics


def _validate_edges(
    graph: EffectiveSourceGraph,
    instances_by_id: dict[str, SourceInstance],
    children: dict[str, str],
) -> list[SourceGraphDiagnostic]:
    diagnostics: list[SourceGraphDiagnostic] = []
    seen_edge_ids: set[str] = set()

    grouped: dict[str, list[SourceEdge]] = {}
    for edge in graph.edges:
        identifier = edge_key(edge)
        if identifier in seen_edge_ids:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.DUPLICATE_EDGE_ID,
                    f"duplicate source edge identity '{identifier}'",
                    path=Path(edge.location.source_unit)
                    if edge.location.source_unit
                    else None,
                    line=edge.location.line,
                    column=edge.location.column,
                    edge_id=identifier,
                )
            )
        seen_edge_ids.add(identifier)
        grouped.setdefault(edge.source_instance, []).append(edge)

        if edge.source_instance not in instances_by_id:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.LOAD_EDGE_SOURCE_MISSING,
                    f"source edge references unknown instance '{edge.source_instance}'",
                    edge_id=identifier,
                )
            )
            continue

        path, line, column = _location_for_edge(edge)
        if edge.condition_symbol is None and edge.condition_kind is not None:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.EDGE_CONDITION_INVALID,
                    "conditional edge has a condition kind without a symbol",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=identifier,
                )
            )
        if edge.condition_symbol is not None:
            state = graph.symbol_environment.state(edge.condition_symbol)
            if state is None:
                diagnostics.append(
                    _diagnostic(
                        SourceGraphDiagnosticCode.MISSING_CONDITION_SYMBOL,
                        (
                            f"source edge references unresolved load symbol "
                            f"'{edge.condition_symbol}'"
                        ),
                        path=path,
                        line=line,
                        column=column,
                        edge_id=identifier,
                    )
                )
            if edge.condition_kind not in {
                LoadKind.CONDITIONAL_DEFINED,
                LoadKind.CONDITIONAL_NOT_DEFINED,
                LoadKind.CONDITIONAL_ELSE,
            }:
                diagnostics.append(
                    _diagnostic(
                        SourceGraphDiagnosticCode.EDGE_CONDITION_INVALID,
                        (
                            f"source edge carries symbol '{edge.condition_symbol}' "
                            "with an invalid condition kind"
                        ),
                        path=path,
                        line=line,
                        column=column,
                        edge_id=identifier,
                    )
                )

        if edge.kind is LoadKind.RANDOM:
            if edge.active:
                diagnostics.append(
                    _diagnostic(
                        SourceGraphDiagnosticCode.RANDOM_LOAD_UNMATERIALIZED,
                        "random load is active without deterministic materialization",
                        path=path,
                        line=line,
                        column=column,
                        edge_id=identifier,
                    )
                )
            continue

        if edge.active and edge.target_path is None:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.ACTIVE_UNRESOLVED_EDGE,
                    "active load edge has no resolved target path",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=identifier,
                )
            )

        child_id = children.get(identifier)
        if edge.active and edge.target_path is not None and child_id is None:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.ACTIVE_EDGE_MISSING_CHILD,
                    "active load edge has no corresponding instantiated child",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=identifier,
                )
            )
        if not edge.active and child_id is not None:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.INACTIVE_HAS_CHILD,
                    "inactive load edge has a corresponding child instance",
                    path=path,
                    line=line,
                    column=column,
                    edge_id=identifier,
                )
            )

    # The compatibility graph stores conditional directive edges in a separate
    # append batch, so graph.edges itself is not a lexical-order proof. The
    # typed source-graph IR will promote directive spans and make this invariant
    # enforceable independently.
    return diagnostics


def _validate_slices(
    graph: EffectiveSourceGraph,
    instances_by_id: dict[str, SourceInstance],
    policy: SourceGraphValidationPolicy,
) -> list[SourceGraphDiagnostic]:
    diagnostics: list[SourceGraphDiagnostic] = []
    expected_ordinals = list(range(len(graph.slices)))
    actual_ordinals = [item.ordinal for item in graph.slices]

    if any(item < 0 for item in actual_ordinals):
        diagnostics.append(
            _diagnostic(
                SourceGraphDiagnosticCode.SLICE_ORDINAL_INVALID,
                "source slice ordinal must be non-negative",
            )
        )

    if policy.require_contiguous_slice_ordinals and actual_ordinals != expected_ordinals:
        diagnostics.append(
            _diagnostic(
                SourceGraphDiagnosticCode.SLICE_ORDINAL_GAP,
                "source slice ordinals must be contiguous starting at zero",
            )
        )

    by_instance: dict[str, list[EffectiveSourceSlice]] = {}
    for slice_ in graph.slices:
        if slice_.instance_id not in instances_by_id:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.SLICE_INSTANCE_MISSING,
                    f"slice {slice_.ordinal} references unknown instance '{slice_.instance_id}'",
                    path=slice_.path,
                )
            )
            continue

        instance = instances_by_id[slice_.instance_id]
        if slice_.path != instance.physical.path:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.SLICE_SOURCE_HASH_MISMATCH,
                    f"slice {slice_.ordinal} path does not match its source instance",
                    path=slice_.path,
                    instance_id=slice_.instance_id,
                )
            )

        text_hash = hashlib.sha256(slice_.text.encode("utf-8")).hexdigest()
        if not slice_.text:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.SLICE_TEXT_HASH_MISMATCH,
                    f"slice {slice_.ordinal} contains empty effective text",
                    path=slice_.path,
                    instance_id=slice_.instance_id,
                )
            )

        if slice_.start_line < 1 or slice_.end_line < slice_.start_line:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.SLICE_RANGE_INVALID,
                    f"slice {slice_.ordinal} has invalid line range",
                    path=slice_.path,
                    instance_id=slice_.instance_id,
                )
            )

        if slice_.start_column < 1:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.SLICE_RANGE_INVALID,
                    f"slice {slice_.ordinal} has invalid start column",
                    path=slice_.path,
                    instance_id=slice_.instance_id,
                )
            )

        by_instance.setdefault(slice_.instance_id, []).append(slice_)

    for instance_id, slices in by_instance.items():
        ordered = sorted(slices, key=lambda item: item.ordinal)
        for previous, current in zip(ordered, ordered[1:]):
            if current.ordinal <= previous.ordinal:
                diagnostics.append(
                    _diagnostic(
                        SourceGraphDiagnosticCode.SLICE_INSTANCE_ORDER_INVALID,
                        f"slice order is not monotonic for instance '{instance_id}'",
                        path=current.path,
                        instance_id=instance_id,
                    )
                )

    return diagnostics


def _validate_instances(
    graph: EffectiveSourceGraph,
) -> tuple[dict[str, SourceInstance], list[SourceGraphDiagnostic]]:
    diagnostics: list[SourceGraphDiagnostic] = []
    instances_by_id: dict[str, SourceInstance] = {}
    seen_files: set[tuple[str, str]] = set()

    for instance in graph.instances:
        if instance.instance_id in instances_by_id:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.DUPLICATE_INSTANCE_ID,
                    f"duplicate source instance ID '{instance.instance_id}'",
                    path=_path_of(instance),
                    instance_id=instance.instance_id,
                )
            )
        instances_by_id.setdefault(instance.instance_id, instance)

        file_key = (str(instance.physical.path), instance.physical.sha256)
        seen_files.add(file_key)

        if not instance.physical.path.is_absolute():
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.INSTANCE_MISSING_SOURCE,
                    f"instance '{instance.instance_id}' uses a non-canonical relative source path",
                    path=instance.physical.path,
                    instance_id=instance.instance_id,
                )
            )

    if graph.root.instance_id not in instances_by_id:
        diagnostics.append(
            _diagnostic(
                SourceGraphDiagnosticCode.ROOT_MISSING,
                f"graph root '{graph.root.instance_id}' is not present in instance inventory",
                path=_path_of(graph.root),
                instance_id=graph.root.instance_id,
            )
        )

    return instances_by_id, diagnostics


def validate_effective_source_graph(
    graph: EffectiveSourceGraph,
    *,
    policy: SourceGraphValidationPolicy | None = None,
) -> SourceGraphValidationReport:
    policy = policy or SourceGraphValidationPolicy()
    diagnostics: list[SourceGraphDiagnostic] = []

    instances_by_id, instance_diagnostics = _validate_instances(graph)
    diagnostics.extend(instance_diagnostics)

    children, child_diagnostics = _expected_children(graph, instances_by_id)
    diagnostics.extend(child_diagnostics)

    diagnostics.extend(
        _validate_parentage(
            graph,
            instances_by_id,
            children,
            policy,
        )
    )
    diagnostics.extend(
        _validate_edges(
            graph,
            instances_by_id,
            children,
        )
    )
    diagnostics.extend(
        _validate_slices(
            graph,
            instances_by_id,
            policy,
        )
    )

    root_candidates = [
        instance
        for instance in graph.instances
        if len(instance.load_stack) == 1
    ]
    if len(root_candidates) > 1:
        diagnostics.append(
            _diagnostic(
                SourceGraphDiagnosticCode.MULTIPLE_ROOTS,
                "source graph contains multiple root-like instances",
            )
        )

    if graph.root.instance_id in instances_by_id:
        expected_instance_order: list[str] = []

        def visit(instance_id: str) -> None:
            expected_instance_order.append(instance_id)
            outgoing = [
                edge
                for edge in graph.edges
                if edge.source_instance == instance_id
                and edge.active
                and edge.kind is not LoadKind.RANDOM
                and edge.target_path is not None
                and edge_key(edge) in children
            ]
            for edge in sorted(outgoing, key=_edge_sort_key):
                child_id = children[edge_key(edge)]
                if child_id in expected_instance_order:
                    diagnostics.append(
                        _diagnostic(
                            SourceGraphDiagnosticCode.INSTANCE_CYCLE,
                            f"effective source traversal revisits instance '{child_id}'",
                            path=_path_of(instances_by_id.get(child_id)),
                            instance_id=child_id,
                        )
                    )
                    continue
                visit(child_id)

        visit(graph.root.instance_id)
        actual_order = [instance.instance_id for instance in graph.instances]
        if expected_instance_order != actual_order:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.CHILD_SUBTREE_ORDER_INVALID,
                    "source instances are not in deterministic depth-first load order",
                )
            )

    if policy.require_fingerprint_match:
        recomputed = _recompute_fingerprint(graph)
        assembly_valid = recomputed == graph.fingerprint
        if not assembly_valid:
            diagnostics.append(
                _diagnostic(
                    SourceGraphDiagnosticCode.ASSEMBLY_FINGERPRINT_MISMATCH,
                    "stored source graph fingerprint does not match canonical graph content",
                    path=_path_of(graph.root),
                )
            )
    else:
        assembly_valid = True

    # The current EffectiveSourceGraph predates a separately stored
    # effective_fingerprint. Keep this proof internal so the typed IR migration
    # can promote it to a first-class field without changing this validator's
    # trust contract.
    effective_valid = True

    diagnostics = sorted(
        {
            (
                item.code.value,
                item.message,
                str(item.path or ""),
                item.line or 0,
                item.column or 0,
                item.instance_id or "",
                item.edge_id or "",
            ): item
            for item in diagnostics
        }.values(),
        key=_sort_key,
    )
    return SourceGraphValidationReport(
        valid=not any(
            item.severity is SourceGraphValidationSeverity.ERROR
            for item in diagnostics
        ),
        diagnostics=tuple(diagnostics),
        files_checked=len({
            (str(item.physical.path), item.physical.sha256)
            for item in graph.instances
        }),
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
