"""Adversarial one-field mutations for the typed Effective Source Graph IR."""
from __future__ import annotations

import copy
import unittest
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Callable, Literal

from Compiler.ir.source_graph import (
    ConditionContext,
    ConditionPredicate,
    EffectiveSourceGraph,
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceEdge,
    SourceEdgeId,
    SourceFile,
    SourceInstance,
    SourceInstanceId,
    SourceRange,
)
from Compiler.semantic.source_graph_validation import (
    SourceGraphDiagnosticCode as Code,
    SourceGraphValidationReport,
    validate_effective_source_graph,
)
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


MutationScope = Literal["graph", "file", "instance", "edge", "slice"]


@dataclass(frozen=True)
class MutationCase:
    name: str
    fixture: str
    scope: MutationScope
    field: str
    mutate: Callable[[EffectiveSourceGraph], EffectiveSourceGraph]
    expected: SourceGraphDiagnosticCode


def _forge_field(obj, field: str, value):
    clone = copy.copy(obj)
    object.__setattr__(clone, field, value)
    return clone


def _replace_file(
    graph: EffectiveSourceGraph,
    index: int,
    field: str,
    value,
) -> EffectiveSourceGraph:
    files = list(graph.files)
    files[index] = _forge_field(files[index], field, value)
    return replace(graph, files=tuple(files))


def _replace_instance(
    graph: EffectiveSourceGraph,
    index: int,
    field: str,
    value,
) -> EffectiveSourceGraph:
    instances = list(graph.instances)
    instances[index] = _forge_field(instances[index], field, value)
    return replace(graph, instances=tuple(instances))


def _replace_edge(
    graph: EffectiveSourceGraph,
    index: int,
    field: str,
    value,
) -> EffectiveSourceGraph:
    edges = list(graph.edges)
    edges[index] = _forge_field(edges[index], field, value)
    return replace(graph, edges=tuple(edges))


def _replace_slice(
    graph: EffectiveSourceGraph,
    index: int,
    field: str,
    value,
) -> EffectiveSourceGraph:
    slices = list(graph.slices)
    slices[index] = _forge_field(slices[index], field, value)
    return replace(graph, slices=tuple(slices))


def _mutate_graph(field: str, value):
    def mutate(graph: EffectiveSourceGraph) -> EffectiveSourceGraph:
        return replace(graph, **{field: value})

    return mutate


def _index_of_child(graph: EffectiveSourceGraph) -> int:
    return next(
        index
        for index, item in enumerate(graph.instances)
        if item.identity != graph.root.identity
    )


def _index_of_active_load(graph: EffectiveSourceGraph) -> int:
    return next(
        index
        for index, item in enumerate(graph.edges)
        if item.active and item.target is not None
    )


def _index_of_active_conditional_load(graph: EffectiveSourceGraph) -> int:
    return next(
        index
        for index, item in enumerate(graph.edges)
        if item.target is not None and item.condition.predicates
    )


def _index_of_second_load(graph: EffectiveSourceGraph) -> int:
    load_indices = [
        index
        for index, item in enumerate(graph.edges)
        if item.kind in {LoadKind.FILE, LoadKind.RAW_LOAD, LoadKind.RANDOM}
    ]
    return load_indices[1]


def _resolve_index(
    graph: EffectiveSourceGraph,
    selector: int | Callable[[EffectiveSourceGraph], int],
) -> int:
    return selector(graph) if callable(selector) else selector


def _mutate_field(
    scope: MutationScope,
    field: str,
    target_index: int | Callable[[EffectiveSourceGraph], int] | None,
    value_factory: Callable[[EffectiveSourceGraph, object], object],
):
    def mutate(graph: EffectiveSourceGraph) -> EffectiveSourceGraph:
        if scope == "graph":
            current = getattr(graph, field)
            return replace(graph, **{field: value_factory(graph, current)})
        if target_index is None:
            raise AssertionError(f"{scope} mutation requires a target index")
        index = _resolve_index(graph, target_index)
        if scope == "file":
            target = graph.files[index]
            return _replace_file(
                graph, index, field, value_factory(graph, target)
            )
        if scope == "instance":
            target = graph.instances[index]
            return _replace_instance(
                graph, index, field, value_factory(graph, target)
            )
        if scope == "edge":
            target = graph.edges[index]
            return _replace_edge(
                graph, index, field, value_factory(graph, target)
            )
        if scope == "slice":
            target = graph.slices[index]
            return _replace_slice(
                graph, index, field, value_factory(graph, target)
            )
        raise AssertionError(f"unknown mutation scope {scope}")

    return mutate


def _constant(value):
    return lambda _graph, _target: value


def _instance_mutation(field: str, value_factory, expected):
    return lambda graph: _replace_instance(
        graph,
        _index_of_child(graph),
        field,
        value_factory(graph, graph.instances[_index_of_child(graph)]),
    )


# The corpus deliberately covers every typed field that has a directly
# observable validation contract in this tranche.
MUTATION_CORPUS: tuple[MutationCase, ...] = (
    MutationCase(
        "graph-root-reference",
        "linear/root.perdsl",
        "graph",
        "root",
        _mutate_graph("root", lambda graph: graph.instances[_index_of_child(graph)]),
        Code.INSTANCE_MISSING_PARENT,
    ),
    MutationCase(
        "graph-instance-inventory",
        "linear/root.perdsl",
        "graph",
        "instances",
        _mutate_graph("instances", lambda graph: (graph.instances[0],)),
        Code.ACTIVE_EDGE_MISSING_CHILD,
    ),
    MutationCase(
        "graph-edge-inventory",
        "linear/root.perdsl",
        "graph",
        "edges",
        _mutate_graph("edges", lambda graph: ()),
        Code.ORPHAN_INSTANCE,
    ),
    MutationCase(
        "graph-slice-inventory",
        "linear/root.perdsl",
        "graph",
        "slices",
        _mutate_graph("slices", lambda graph: tuple(reversed(graph.slices))),
        Code.SLICE_ORDINAL_GAP,
    ),
    MutationCase(
        "graph-symbol-environment",
        "conditional-defined/root.perdsl",
        "graph",
        "symbol_environment",
        _mutate_graph("symbol_environment", _constant(LoadSymbolEnvironment(()))),
        Code.MISSING_CONDITION_SYMBOL,
    ),
    MutationCase(
        "graph-assembly-fingerprint",
        "linear/root.perdsl",
        "graph",
        "assembly_fingerprint",
        _mutate_graph("assembly_fingerprint", _constant("0" * 64)),
        Code.ASSEMBLY_FINGERPRINT_MISMATCH,
    ),
    MutationCase(
        "graph-effective-fingerprint",
        "linear/root.perdsl",
        "graph",
        "effective_fingerprint",
        _mutate_graph("effective_fingerprint", _constant("0" * 64)),
        Code.EFFECTIVE_FINGERPRINT_MISMATCH,
    ),
    MutationCase(
        "source-file-identity",
        "linear/root.perdsl",
        "file",
        "identity",
        _mutate_field(
            "file",
            "identity",
            0,
            lambda _graph, target: _forge_field(
                target.identity,
                "content_sha256",
                "0" * 64,
            ),
        ),
        Code.SLICE_SOURCE_HASH_MISMATCH,
    ),
    MutationCase(
        "source-file-path",
        "linear/root.perdsl",
        "file",
        "path",
        _mutate_field(
            "file",
            "path",
            0,
            lambda _graph, _target: Path("/forged/source.perdsl"),
        ),
        Code.INSTANCE_MISSING_SOURCE,
    ),
    MutationCase(
        "source-file-text",
        "linear/root.perdsl",
        "file",
        "text",
        _mutate_field(
            "file",
            "text",
            0,
            lambda _graph, target: target.text + "; forged\n",
        ),
        Code.SLICE_SOURCE_HASH_MISMATCH,
    ),
    MutationCase(
        "instance-identity",
        "duplicate/root.perdsl",
        "instance",
        "identity",
        _mutate_field(
            "instance",
            "identity",
            1,
            lambda graph, _target: graph.instances[0].identity,
        ),
        Code.DUPLICATE_INSTANCE_ID,
    ),
    MutationCase(
        "instance-physical-source",
        "linear/root.perdsl",
        "instance",
        "physical",
        _mutate_field(
            "instance",
            "physical",
            1,
            lambda graph, _target: graph.files[0],
        ),
        Code.LOAD_EDGE_INSTANCE_MISMATCH,
    ),
    MutationCase(
        "instance-parent",
        "linear/root.perdsl",
        "instance",
        "parent",
        _mutate_field("instance", "parent", 1, _constant(None)),
        Code.MULTIPLE_ROOTS,
    ),
    MutationCase(
        "instance-via-edge",
        "linear/root.perdsl",
        "instance",
        "via_edge",
        _mutate_field("instance", "via_edge", 1, _constant(None)),
        Code.INSTANCE_MISSING_LOAD_EDGE,
    ),
    MutationCase(
        "instance-ancestry",
        "linear/root.perdsl",
        "instance",
        "ancestry",
        _mutate_field(
            "instance",
            "ancestry",
            1,
            lambda _graph, target: target.ancestry + (target.source,),
        ),
        Code.INSTANCE_CYCLE,
    ),
    MutationCase(
        "instance-depth",
        "linear/root.perdsl",
        "instance",
        "depth",
        _mutate_field("instance", "depth", 1, _constant(0)),
        Code.DEPTH_MISMATCH,
    ),
    MutationCase(
        "instance-occurrence",
        "linear/root.perdsl",
        "instance",
        "occurrence",
        _mutate_field("instance", "occurrence", 1, _constant(99)),
        Code.ASSEMBLY_FINGERPRINT_MISMATCH,
    ),
    MutationCase(
        "edge-identity",
        "linear/root.perdsl",
        "edge",
        "identity",
        _mutate_field(
            "edge",
            "identity",
            _index_of_active_load,
            lambda _graph, _target: SourceEdgeId("forged-edge"),
        ),
        Code.EDGE_CONDITION_INVALID,
    ),
    MutationCase(
        "edge-source",
        "linear/root.perdsl",
        "edge",
        "source",
        _mutate_field(
            "edge",
            "source",
            _index_of_active_load,
            lambda _graph, _target: type(_target.source)("unknown-source"),
        ),
        Code.LOAD_EDGE_SOURCE_MISSING,
    ),
    MutationCase(
        "edge-target",
        "linear/root.perdsl",
        "edge",
        "target",
        _mutate_field("edge", "target", _index_of_active_load, _constant(None)),
        Code.ACTIVE_UNRESOLVED_EDGE,
    ),
    MutationCase(
        "edge-child",
        "linear/root.perdsl",
        "edge",
        "child",
        _mutate_field("edge", "child", _index_of_active_load, _constant(None)),
        Code.ACTIVE_EDGE_MISSING_CHILD,
    ),
    MutationCase(
        "edge-kind-random",
        "linear/root.perdsl",
        "edge",
        "kind",
        _mutate_field("edge", "kind", _index_of_active_load, _constant(LoadKind.RANDOM)),
        Code.RANDOM_LOAD_UNMATERIALIZED,
    ),
    MutationCase(
        "edge-condition",
        "conditional-defined/root.perdsl",
        "edge",
        "condition",
        _mutate_field("edge", "condition", _index_of_active_conditional_load, _constant(ConditionContext())),
        Code.EDGE_CONDITION_INVALID,
    ),
    MutationCase(
        "edge-active",
        "linear/root.perdsl",
        "edge",
        "active",
        _mutate_field("edge", "active", _index_of_active_load, _constant(False)),
        Code.INACTIVE_HAS_CHILD,
    ),
    MutationCase(
        "edge-lexical-order",
        "duplicate/root.perdsl",
        "edge",
        "lexical_order",
        _mutate_field(
            "edge",
            "lexical_order",
            _index_of_second_load,
            _constant(0),
        ),
        Code.EDGE_ORDER_NOT_MONOTONIC,
    ),
    MutationCase(
        "edge-target-text",
        "linear/root.perdsl",
        "edge",
        "target_text",
        _mutate_field(
            "edge",
            "target_text",
            _index_of_active_load,
            _constant("forged-child.perdsl"),
        ),
        Code.EDGE_CONDITION_INVALID,
    ),
    MutationCase(
        "edge-span",
        "linear/root.perdsl",
        "edge",
        "span",
        _mutate_field(
            "edge",
            "span",
            _index_of_active_load,
            lambda _graph, target: _forge_field(
                target.span,
                "start_line",
                target.span.start_line + 1,
            ),
        ),
        Code.EDGE_CONDITION_INVALID,
    ),
    MutationCase(
        "edge-condition-predicate-symbol",
        "conditional-defined/root.perdsl",
        "edge",
        "condition",
        _mutate_field(
            "edge",
            "condition",
            _index_of_active_conditional_load,
            lambda _graph, target: ConditionContext(
                (
                    _forge_field(
                        target.condition.predicates[0],
                        "symbol",
                        "UNKNOWN_SYMBOL",
                    ),
                    *target.condition.predicates[1:],
                )
            ),
        ),
        Code.MISSING_CONDITION_SYMBOL,
    ),
    MutationCase(
        "slice-ordinal",
        "linear/root.perdsl",
        "slice",
        "ordinal",
        _mutate_field("slice", "ordinal", 0, _constant(1)),
        Code.SLICE_ORDINAL_GAP,
    ),
    MutationCase(
        "slice-instance",
        "linear/root.perdsl",
        "slice",
        "instance",
        _mutate_field(
            "slice",
            "instance",
            0,
            lambda graph, _target: graph.instances[_index_of_child(graph)].identity,
        ),
        Code.SLICE_SOURCE_HASH_MISMATCH,
    ),
    MutationCase(
        "slice-physical-range",
        "linear/root.perdsl",
        "slice",
        "physical_range",
        _mutate_field(
            "slice",
            "physical_range",
            0,
            lambda _graph, target: _forge_field(
                target.physical_range,
                "end_offset",
                target.physical_range.end_offset + 1000,
            ),
        ),
        Code.SLICE_RANGE_INVALID,
    ),
    MutationCase(
        "slice-text",
        "linear/root.perdsl",
        "slice",
        "text",
        _mutate_field(
            "slice",
            "text",
            0,
            lambda _graph, target: target.text + "; forged\n",
        ),
        Code.EFFECTIVE_FINGERPRINT_MISMATCH,
    ),
)


class SourceGraphMutationCorpusTests(unittest.TestCase):
    FIXTURES = Path(__file__).parent / "fixtures" / "source_graph"

    def _resolve(self, relative: str) -> EffectiveSourceGraph:
        symbols = ()
        if relative == "conditional-defined/root.perdsl":
            symbols = (("TEST", LoadSymbolState.DEFINED),)
        return SourceGraphResolver().resolve(
            SourceGraphRequest(
                entrypoint=self.FIXTURES / relative,
                load_symbols=LoadSymbolEnvironment(symbols),
            )
        )

    @staticmethod
    def _field_names(value) -> tuple[str, ...]:
        return tuple(item.name for item in fields(value))

    def _assert_single_field_change(
        self,
        before: EffectiveSourceGraph,
        after: EffectiveSourceGraph,
        case: MutationCase,
    ) -> None:
        if case.scope == "graph":
            before_names = self._field_names(before)
            after_names = self._field_names(after)
            self.assertEqual(before_names, after_names)
            changed = [
                name
                for name in before_names
                if getattr(before, name) != getattr(after, name)
            ]
            self.assertEqual(
                changed,
                [case.field],
                f"{case.name} changed fields {changed}",
            )
            return

        if case.scope == "file":
            self._assert_collection_mutation(before.files, after.files, case, "file")
        elif case.scope == "instance":
            self._assert_collection_mutation(
                before.instances, after.instances, case, "instance"
            )
        elif case.scope == "edge":
            self._assert_collection_mutation(before.edges, after.edges, case, "edge")
        elif case.scope == "slice":
            self._assert_collection_mutation(
                before.slices, after.slices, case, "slice"
            )

    def _assert_collection_mutation(self, before, after, case, label):
        self.assertEqual(len(before), len(after))
        changed_indices = [
            index for index, (left, right) in enumerate(zip(before, after))
            if left != right
        ]
        self.assertEqual(
            changed_indices,
            [case.target_index],
            f"{case.name} changed {label} indices {changed_indices}",
        )
        index = changed_indices[0]
        original = before[index]
        mutated = after[index]
        changed_fields = [
            item.name
            for item in fields(original)
            if getattr(original, item.name) != getattr(mutated, item.name)
        ]
        self.assertEqual(
            changed_fields,
            [case.field],
            f"{case.name} changed {label} fields {changed_fields}",
        )

    def test_corpus_cases_are_unique_and_nonempty(self):
        self.assertEqual(len(MUTATION_CORPUS), len({item.name for item in MUTATION_CORPUS}))
        self.assertGreaterEqual(len(MUTATION_CORPUS), 25)

    def test_every_corpus_mutation_is_exactly_one_field(self):
        for case in MUTATION_CORPUS:
            with self.subTest(case=case.name):
                baseline = self._resolve(case.fixture)
                self.assertTrue(
                    validate_effective_source_graph(baseline).valid,
                    case.name,
                )
                mutated = case.mutate(baseline)
                self._assert_single_field_change(baseline, mutated, case)

    def test_every_corpus_mutation_produces_expected_diagnostic(self):
        for case in MUTATION_CORPUS:
            with self.subTest(case=case.name):
                baseline = self._resolve(case.fixture)
                mutated = case.mutate(baseline)
                report: SourceGraphValidationReport = validate_effective_source_graph(
                    mutated
                )
                self.assertFalse(report.valid)
                codes = {item.code for item in report.errors}
                self.assertIn(
                    case.expected,
                    codes,
                    f"{case.name}: expected {case.expected}, got {sorted(c.value for c in codes)}",
                )

    def test_corpus_spans_all_declared_mutation_scopes(self):
        self.assertEqual(
            {"graph", "file", "instance", "edge", "slice"},
            {item.scope for item in MUTATION_CORPUS},
        )


if __name__ == "__main__":
    unittest.main()
