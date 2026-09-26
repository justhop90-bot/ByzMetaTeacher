from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from Compiler.source_graph import (
    LoadKind,
    LoadSymbolEnvironment,
    LoadSymbolState,
    SourceGraphRequest,
    SourceGraphResolver,
    parse_source_directives,
)
from Compiler.errors import CompileError


ROOT = Path(__file__).parent / "fixtures" / "source_graph"


class SourceGraphSyntaxTests(unittest.TestCase):
    def test_native_file_load_is_recognized(self):
        directives = parse_source_directives('(load "child.perdsl")\n')
        self.assertEqual(len(directives), 1)
        self.assertEqual(directives[0].kind, LoadKind.FILE)
        self.assertEqual(directives[0].target, "child.perdsl")
        self.assertEqual(directives[0].location.line, 1)

    def test_raw_load_directive_is_recognized(self):
        directives = parse_source_directives('#load "child.perdsl"\n')
        self.assertEqual(len(directives), 1)
        self.assertEqual(directives[0].kind, LoadKind.RAW_LOAD)
        self.assertEqual(directives[0].target, "child.perdsl")

    def test_conditional_directives_are_distinct(self):
        directives = parse_source_directives(
            '#load-if-defined TEST\n'
            '#else\n'
            '#end-if\n'
        )
        self.assertEqual(
            [item.kind for item in directives],
            [
                LoadKind.CONDITIONAL_DEFINED,
                LoadKind.CONDITIONAL_ELSE,
                LoadKind.CONDITIONAL_END,
            ],
        )
        self.assertEqual(directives[0].symbol, "TEST")

    def test_load_inside_string_does_not_create_edge(self):
        directives = parse_source_directives(
            'demand x {\n'
            'require (current-age >= dark-age)\n'
            'action (chat-local-to-self "(load \\"child.perdsl\\")")\n'
            'witness (building-type-count house > 0)\n'
            'release (building-type-count house > 0)\n'
            '}\n'
        )
        self.assertEqual(directives, ())

    def test_load_inside_nested_expression_is_not_top_level_source_load(self):
        directives = parse_source_directives(
            '(foo (load "child.perdsl"))\n'
        )
        self.assertEqual(directives, ())

    def test_malformed_load_is_rejected(self):
        cases = (
            '(load)',
            '(load child.perdsl)',
            '(load "child.perdsl" "other.perdsl")',
            '(load "unterminated',
            '#load child.perdsl',
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(CompileError):
                    parse_source_directives(source)

    def test_conditional_structure_errors(self):
        cases = (
            '#else\n',
            '#end-if\n',
            '#load-if-defined TEST\n#else\n#else\n#end-if\n',
            '#load-if-defined TEST\n',
        )
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(CompileError):
                    parse_source_directives(source)


class SourceGraphResolverTests(unittest.TestCase):
    def _request(
        self,
        root: Path,
        *,
        symbols=None,
    ) -> SourceGraphRequest:
        return SourceGraphRequest(
            entrypoint=root,
            search_roots=(root.parent,),
            load_symbols=symbols,
        )

    def test_load_position_is_effective_program_order(self):
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "load-position" / "root.perdsl")
        )
        self.assertEqual(
            [slice_.path.name for slice_ in graph.slices],
            ["root.perdsl", "child.perdsl", "root.perdsl"],
        )
        self.assertIn("before", graph.slices[0].text)
        self.assertIn("child", graph.slices[1].text)
        self.assertIn("after", graph.slices[2].text)

    def test_nested_loads_are_depth_first(self):
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "nested" / "root.perdsl")
        )
        self.assertEqual(
            [slice_.path.name for slice_ in graph.slices],
            ["root.perdsl", "child-a.perdsl", "child-b.perdsl"],
        )

    def test_duplicate_loads_preserve_two_source_instances(self):
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "duplicate" / "root.perdsl")
        )
        shared = [item for item in graph.instances if item.physical.path.name == "shared.perdsl"]
        self.assertEqual(len(shared), 2)
        self.assertEqual(
            [slice_.path.name for slice_ in graph.slices],
            ["root.perdsl", "shared.perdsl", "shared.perdsl"],
        )
        self.assertNotEqual(shared[0].instance_id, shared[1].instance_id)

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-002"):
            SourceGraphResolver().resolve(
                self._request(ROOT / "cycle" / "a.perdsl")
            )

    def test_missing_target_is_rejected(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-001"):
            SourceGraphResolver().resolve(
                self._request(ROOT / "missing" / "root.perdsl")
            )

    def test_defined_conditional_selects_only_defined_branch(self):
        symbols = LoadSymbolEnvironment.from_mapping({"TEST": LoadSymbolState.DEFINED})
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "conditional-defined" / "root.perdsl", symbols=symbols)
        )
        names = [item.path.name for item in graph.slices]
        self.assertIn("selected.perdsl", names)
        self.assertNotIn("rejected.perdsl", names)

    def test_undefined_conditional_selects_not_defined_branch(self):
        symbols = LoadSymbolEnvironment.from_mapping({"TEST": LoadSymbolState.UNDEFINED})
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "conditional-not-defined" / "root.perdsl", symbols=symbols)
        )
        names = [item.path.name for item in graph.slices]
        self.assertIn("selected.perdsl", names)
        self.assertNotIn("rejected.perdsl", names)

    def test_unresolved_conditional_symbol_fails_closed(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-006"):
            SourceGraphResolver().resolve(
                self._request(ROOT / "conditional-defined" / "root.perdsl")
            )

    def test_random_load_is_rejected_for_deterministic_resolution(self):
        with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-007"):
            SourceGraphResolver().resolve(
                self._request(ROOT / "random" / "root.perdsl")
            )

    def test_file_load_depth_limit(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for depth in range(10):
                path = root / f"level-{depth}.perdsl"
                target = f"level-{depth + 1}.perdsl"
                path.write_text(
                    f'(load "{target}")\n',
                    encoding="utf-8",
                )
            (root / "level-10.perdsl").write_text("", encoding="utf-8")
            SourceGraphResolver().resolve(
                self._request(root / "level-0.perdsl")
            )

            (root / "level-10.perdsl").write_text(
                '(load "level-11.perdsl")\n',
                encoding="utf-8",
            )
            (root / "level-11.perdsl").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-003"):
                SourceGraphResolver().resolve(
                    self._request(root / "level-0.perdsl")
                )

    def test_conditional_depth_limit(self):
        symbols = LoadSymbolEnvironment.from_mapping(
            {f"S{i}": LoadSymbolState.DEFINED for i in range(50)}
        )
        source = "".join(
            f"#load-if-defined S{i}\n"
            for i in range(50)
        ) + "".join("#end-if\n" for _ in range(50))

        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "root.perdsl"
            root.write_text(source, encoding="utf-8")
            SourceGraphResolver().resolve(
                self._request(root, symbols=symbols)
            )

            root.write_text(
                "#load-if-defined OVERFLOW\n" + source + "#end-if\n",
                encoding="utf-8",
            )
            symbols = LoadSymbolEnvironment.from_mapping(
                {
                    "OVERFLOW": LoadSymbolState.DEFINED,
                    **{f"S{i}": LoadSymbolState.DEFINED for i in range(50)},
                }
            )
            with self.assertRaisesRegex(CompileError, "SOURCE-GRAPH-005"):
                SourceGraphResolver().resolve(
                    self._request(root, symbols=symbols)
                )

    def test_physical_provenance_survives_into_slices(self):
        graph = SourceGraphResolver().resolve(
            self._request(ROOT / "provenance" / "root.perdsl")
        )
        child = next(item for item in graph.slices if item.path.name == "child.perdsl")
        self.assertGreaterEqual(child.start_line, 1)
        self.assertEqual(child.path.name, "child.perdsl")

    def test_graph_fingerprint_is_deterministic(self):
        request = self._request(ROOT / "nested" / "root.perdsl")
        first = SourceGraphResolver().resolve(request)
        second = SourceGraphResolver().resolve(request)
        self.assertEqual(first, second)
        self.assertEqual(first.fingerprint, second.fingerprint)


if __name__ == "__main__":
    unittest.main()
