import tempfile
import unittest
from pathlib import Path

from Compiler.compiler import compile_package
from Compiler.errors import CompileError
from Compiler.source_graph import (
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceGraphRequest,
    SourceGraphResolver,
)


class SourceGraphTests(unittest.TestCase):
    FIXTURES = Path(__file__).parent / "fixtures" / "source_graph"

    def _resolve(self, relative, symbols=()):
        return SourceGraphResolver().resolve(
            SourceGraphRequest(
                entrypoint=self.FIXTURES / relative,
                load_symbols=LoadSymbolEnvironment(tuple(symbols)),
            )
        )

    def test_linear_load_expands_depth_first(self):
        graph = self._resolve("linear/root.perdsl")
        self.assertEqual(
            [item.path.name for item in graph.slices],
            ["root.perdsl", "child.perdsl"],
        )

    def test_load_position_splices_child(self):
        graph = self._resolve("load-position/root.perdsl")
        effective = "\n".join(item.text for item in graph.slices)
        self.assertLess(effective.index("demand before"), effective.index("demand child"))
        self.assertLess(effective.index("demand child"), effective.index("demand after"))

    def test_nested_loads_are_depth_first(self):
        graph = self._resolve("nested/root.perdsl")
        self.assertEqual(
            [item.path.name for item in graph.slices],
            ["root.perdsl", "child-a.perdsl", "child-b.perdsl"],
        )

    def test_duplicate_load_preserves_two_instances(self):
        graph = self._resolve("duplicate/root.perdsl")
        shared = [
            item for item in graph.instances
            if item.physical.path.name == "shared.perdsl"
        ]
        self.assertEqual(len(shared), 2)
        edges = [
            item for item in graph.edges
            if item.active
            and item.target_path is not None
            and item.target_path.name == "shared.perdsl"
        ]
        self.assertEqual(len(edges), 2)

    def test_duplicate_load_is_not_a_cycle(self):
        graph = self._resolve("duplicate/root.perdsl")
        self.assertEqual(
            [item.occurrence for item in graph.instances if item.physical.path.name == "shared.perdsl"],
            [0, 1],
        )

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-002"):
            self._resolve("cycle/a.perdsl")

    def test_missing_target_is_rejected(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-001"):
            self._resolve("missing/root.perdsl")

    def test_defined_branch_is_selected(self):
        graph = self._resolve(
            "conditional-defined/root.perdsl",
            (("TEST", LoadSymbolState.DEFINED),),
        )
        active_targets = [
            edge.target_path.name
            for edge in graph.edges
            if edge.active and edge.target_path is not None
        ]
        self.assertEqual(active_targets, ["selected.perdsl"])
        inactive = [
            edge for edge in graph.edges
            if edge.target_path is not None and not edge.active
        ]
        self.assertEqual([edge.target_path.name for edge in inactive], ["rejected.perdsl"])
        self.assertEqual(
            inactive[0].condition_symbol,
            "TEST",
        )

    def test_not_defined_branch_is_selected(self):
        graph = self._resolve(
            "conditional-not-defined/root.perdsl",
            (("TEST", LoadSymbolState.UNDEFINED),),
        )
        active_targets = [
            edge.target_path.name
            for edge in graph.edges
            if edge.active and edge.target_path is not None
        ]
        self.assertEqual(active_targets, ["selected.perdsl"])

    def test_unknown_conditional_symbol_fails_closed(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-006"):
            self._resolve("conditional-defined/root.perdsl")

    def test_malformed_conditional_directive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = Path(tmp) / "root.perdsl"
            entry.write_text("#load-if-defined\n", encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-012"):
                SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=entry))

    def test_random_load_is_rejected_without_selection_policy(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-007"):
            self._resolve("random/root.perdsl")

    def test_malformed_raw_load_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.perdsl"
            entry.write_text("#load child.perdsl
", encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-009"):
                SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=entry))

    def test_malformed_parenthesized_load_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.perdsl"
            entry.write_text('(load child.perdsl)
', encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-009"):
                SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=entry))

    def test_load_in_string_and_nested_expression_is_not_source_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.perdsl"
            entry.write_text(
                'demand test {\n'
                '    require (current-age >= dark-age)\n'
                '    action (build house)\n'
                '    witness (building-type-count house > 0)\n'
                '    release (building-type-count house > 0)\n'
                '}\n'
                '(and (current-age >= dark-age) (current-age >= dark-age))\n'
                '"(load \\"child.perdsl\\")"\n',
                encoding="utf-8",
            )
            graph = SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=entry))
            self.assertEqual(len(graph.edges), 0)

    def test_conditional_depth_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "deep.perdsl"
            lines = ["#load-if-defined TEST\n"] * 51
            lines += ["true\n"]
            lines += ["#end-if\n"] * 51
            entry.write_text("".join(lines), encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-005"):
                SourceGraphResolver().resolve(
                    SourceGraphRequest(
                        entrypoint=entry,
                        load_symbols=LoadSymbolEnvironment(
                            (("TEST", LoadSymbolState.DEFINED),),
                        ),
                    ),
                )

    def test_load_depth_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(11):
                next_name = f"node-{index + 1}.perdsl"
                (root / f"node-{index}.perdsl").write_text(
                    f'(load "{next_name}")\n',
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-003"):
                SourceGraphResolver().resolve(
                    SourceGraphRequest(entrypoint=root / "node-0.perdsl"),
                )

    def test_fingerprint_is_deterministic(self):
        first = self._resolve("linear/root.perdsl")
        second = self._resolve("linear/root.perdsl")
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.slices, second.slices)

    def test_package_compile_preserves_effective_source_order(self):
        output = compile_package(
            SourceGraphRequest(
                entrypoint=self.FIXTURES / "load-position" / "root.perdsl",
            ),
        )
        self.assertLess(output.index("demand-before"), output.index("demand-child"))
        self.assertLess(output.index("demand-child"), output.index("demand-after"))

    def test_slice_provenance(self):
        graph = self._resolve("linear/root.perdsl")
        child = next(item for item in graph.slices if item.path.name == "child.perdsl")
        self.assertEqual(child.start_line, 1)
        self.assertEqual(child.path.name, "child.perdsl")

    def test_source_edge_kind_for_native_and_conditional_load(self):
        graph = self._resolve(
            "conditional-defined/root.perdsl",
            (("TEST", LoadSymbolState.DEFINED),),
        )
        load_edges = [item for item in graph.edges if item.target_path is not None]
        self.assertEqual(load_edges[0].kind, LoadKind.FILE)
        self.assertEqual(load_edges[0].condition_kind, LoadKind.CONDITIONAL_DEFINED)


if __name__ == "__main__":
    unittest.main()
