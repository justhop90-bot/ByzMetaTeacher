import unittest
from dataclasses import replace
from pathlib import Path

from Compiler.errors import CompileError
from Compiler.source_graph import (
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceEdge,
    SourceGraphRequest,
    SourceGraphResolver,
)
from Compiler.semantic.source_graph_validation import (
    SourceGraphDiagnosticCode,
    SourceGraphValidationError,
    validate_effective_source_graph,
)


class SourceGraphValidationTests(unittest.TestCase):
    FIXTURES = Path(__file__).parent / "fixtures" / "source_graph"

    def _resolve(self, relative: str, symbols=()):
        return SourceGraphResolver().resolve(
            SourceGraphRequest(
                entrypoint=self.FIXTURES / relative,
                load_symbols=LoadSymbolEnvironment(tuple(symbols)),
            )
        )

    def test_valid_linear_graph_is_closed(self):
        graph = self._resolve("linear/root.perdsl")
        report = validate_effective_source_graph(graph)
        self.assertTrue(report.valid, report.diagnostics)
        self.assertEqual(report.errors, ())
        self.assertTrue(report.assembly_fingerprint_valid)
        self.assertEqual(report.instances_checked, len(graph.instances))

    def test_duplicate_loads_remain_valid_distinct_instances(self):
        graph = self._resolve("duplicate/root.perdsl")
        report = validate_effective_source_graph(graph)
        self.assertTrue(report.valid, report.diagnostics)

    def test_nested_load_order_is_validated(self):
        graph = self._resolve("nested/root.perdsl")
        report = validate_effective_source_graph(graph)
        self.assertTrue(report.valid, report.diagnostics)

    def test_conditional_load_graph_is_valid(self):
        graph = self._resolve(
            "conditional-defined/root.perdsl",
            (("TEST", LoadSymbolState.DEFINED),),
        )
        report = validate_effective_source_graph(graph)
        self.assertTrue(report.valid, report.diagnostics)

    def test_forged_fingerprint_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        forged = replace(graph, assembly_fingerprint="0" * 64)
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.ASSEMBLY_FINGERPRINT_MISMATCH,
            {item.code for item in report.errors},
        )

    def test_duplicate_instance_identity_is_rejected(self):
        graph = self._resolve("duplicate/root.perdsl")
        duplicate_id = graph.instances[0].identity
        forged_instances = (
            graph.instances[0],
            replace(graph.instances[1], identity=duplicate_id),
            *graph.instances[2:],
        )
        forged = replace(graph, instances=forged_instances)
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.DUPLICATE_INSTANCE_ID,
            {item.code for item in report.errors},
        )

    def test_active_edge_without_target_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        target_edge = next(
            edge
            for edge in graph.edges
            if edge.active and edge.target_path is not None
        )
        forged_edges = tuple(
            replace(edge, target=None, child=None)
            if edge is target_edge
            else edge
            for edge in graph.edges
        )
        forged = replace(graph, edges=forged_edges)
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.ACTIVE_UNRESOLVED_EDGE,
            {item.code for item in report.errors},
        )

    def test_missing_child_instance_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        forged = replace(graph, instances=(graph.instances[0],))
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.ACTIVE_EDGE_MISSING_CHILD,
            {item.code for item in report.errors},
        )

    def test_slice_ordinal_gap_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        first = graph.slices[0]
        forged_slices = (
            replace(first, ordinal=1),
            *graph.slices[1:],
        )
        forged = replace(graph, slices=forged_slices)
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.SLICE_ORDINAL_GAP,
            {item.code for item in report.errors},
        )

    def test_cycle_in_instance_load_stack_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        child = graph.instances[1]
        forged_child = replace(
            child,
            ancestry=(*child.ancestry, child.source),
        )
        forged = replace(
            graph,
            instances=(graph.instances[0], forged_child, *graph.instances[2:]),
        )
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.INSTANCE_CYCLE,
            {item.code for item in report.errors},
        )

    def test_missing_conditional_symbol_is_rejected(self):
        graph = self._resolve(
            "conditional-defined/root.perdsl",
            (("TEST", LoadSymbolState.DEFINED),),
        )
        from Compiler.ir.source_graph import ConditionContext, ConditionPredicate

        target = next(
            edge
            for edge in graph.edges
            if edge.target is not None and edge.condition.predicates
        )
        forged = replace(
            graph,
            edges=tuple(
                replace(
                    edge,
                    condition=ConditionContext(
                        (ConditionPredicate("UNKNOWN_SYMBOL", LoadSymbolState.DEFINED),)
                    ),
                )
                if edge is target
                else edge
                for edge in graph.edges
            ),
        )
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.MISSING_CONDITION_SYMBOL,
            {item.code for item in report.errors},
        )

    def test_random_load_requires_materialization(self):
        graph = self._resolve("linear/root.perdsl")
        target = next(
            edge
            for edge in graph.edges
            if edge.target_path is not None and edge.active
        )
        forged = replace(
            graph,
            edges=tuple(
                replace(edge, kind=LoadKind.RANDOM)
                if edge is target
                else edge
                for edge in graph.edges
            ),
        )
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.RANDOM_LOAD_UNMATERIALIZED,
            {item.code for item in report.errors},
        )

    def test_inactive_source_changes_assembly_not_effective_fingerprint(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inactive.perdsl").write_text("first\n", encoding="utf-8")
            (root / "root.perdsl").write_text(
                "#load-if-defined TEST\n"
                '(load "inactive.perdsl")\n'
                "#end-if\n"
                "true\n",
                encoding="utf-8",
            )
            symbols = LoadSymbolEnvironment(
                (("TEST", LoadSymbolState.UNDEFINED),)
            )
            first = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=root / "root.perdsl",
                    load_symbols=symbols,
                )
            )
            (root / "inactive.perdsl").write_text("changed\n", encoding="utf-8")
            second = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=root / "root.perdsl",
                    load_symbols=symbols,
                )
            )
            self.assertNotEqual(first.assembly_fingerprint, second.assembly_fingerprint)
            self.assertEqual(first.effective_fingerprint, second.effective_fingerprint)

    def test_dual_fingerprints_are_distinct_contracts(self):
        graph = self._resolve("linear/root.perdsl")
        self.assertEqual(graph.assembly_fingerprint, graph.fingerprint)
        self.assertTrue(graph.effective_fingerprint)
        self.assertNotEqual(graph.assembly_fingerprint, "")

    def test_forged_effective_fingerprint_is_rejected(self):
        graph = self._resolve("linear/root.perdsl")
        forged = replace(graph, effective_fingerprint="0" * 64)
        report = validate_effective_source_graph(forged)
        self.assertFalse(report.valid)
        self.assertIn(
            SourceGraphDiagnosticCode.EFFECTIVE_FINGERPRINT_MISMATCH,
            {item.code for item in report.errors},
        )

    def test_structural_instance_ids_are_repeatable(self):
        first = self._resolve("duplicate/root.perdsl")
        second = self._resolve("duplicate/root.perdsl")
        self.assertEqual(
            [item.identity for item in first.instances],
            [item.identity for item in second.instances],
        )

    def test_child_edge_and_parent_relationship_are_explicit(self):
        graph = self._resolve("linear/root.perdsl")
        child = next(
            item for item in graph.instances if item.identity != graph.root.identity
        )
        edge = next(item for item in graph.edges if item.child == child.identity)
        self.assertEqual(child.parent, graph.root.identity)
        self.assertEqual(child.via_edge, edge.identity)
        self.assertEqual(edge.source, graph.root.identity)
        self.assertEqual(edge.target, child.source)

    def test_nested_condition_context_preserves_all_predicates(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "child.perdsl").write_text("; child\n", encoding="utf-8")
            (root / "root.perdsl").write_text(
                "#load-if-defined A\n"
                "#load-if-defined B\n"
                '(load "child.perdsl")\n'
                "#end-if\n"
                "#end-if\n",
                encoding="utf-8",
            )
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(
                    entrypoint=root / "root.perdsl",
                    load_symbols=LoadSymbolEnvironment(
                        (
                            ("A", LoadSymbolState.DEFINED),
                            ("B", LoadSymbolState.DEFINED),
                        ),
                    ),
                )
            )
            edge = next(item for item in graph.edges if item.target is not None)
            self.assertEqual(edge.condition.depth, 2)
            self.assertEqual(
                [item.symbol for item in edge.condition.predicates],
                ["A", "B"],
            )

    def test_validation_error_exposes_semantic_diagnostics(self):
        graph = self._resolve("linear/root.perdsl")
        forged = replace(graph, assembly_fingerprint="0" * 64)
        report = validate_effective_source_graph(forged)
        error = SourceGraphValidationError(report)
        self.assertIsInstance(error, CompileError)
        self.assertTrue(error.diagnostics)
        self.assertEqual(
            error.diagnostics[0].code,
            SourceGraphDiagnosticCode.ASSEMBLY_FINGERPRINT_MISMATCH.value,
        )


if __name__ == "__main__":
    unittest.main()
