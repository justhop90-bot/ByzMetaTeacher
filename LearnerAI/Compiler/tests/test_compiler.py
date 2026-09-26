import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from compiler import CompileError, compile_source, parse


EXAMPLES = (Path(__file__).parents[1] / "examples" / "basics.basilisk").read_text(encoding="utf-8")


class CompilerTests(unittest.TestCase):
    def test_three_examples_parse(self):
        self.assertEqual(
            [d.name for d in parse(EXAMPLES)],
            ["castle", "defensive-spearmen", "wheelbarrow"],
        )

    def test_output_is_deterministic_and_contains_lifecycle(self):
        a = compile_source(EXAMPLES)
        self.assertEqual(a, compile_source(EXAMPLES))
        self.assertIn("(set-goal demand-castle 1)", a)
        self.assertIn("(build castle)", a)
        self.assertIn("(building-type-count castle > 0)", a)
        self.assertIn("(train spearman)", a)
        self.assertIn("(research ri-wheelbarrow)", a)
        self.assertEqual(a.count("(defrule"), 7)

    def test_missing_witness_rejected(self):
        source = """
        demand bad {
            require (can-build castle)
            action (build castle)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_native_per_expression_is_required(self):
        source = """
        demand bad {
            require can-build castle
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)


if __name__ == "__main__":
    unittest.main()
