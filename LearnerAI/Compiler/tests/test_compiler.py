import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))
from Compiler.compiler import CompileError, compile_source
from Compiler.parser import parse
from Compiler.semantic import parse_expression

EXAMPLES = (Path(__file__).parents[1] / "examples" / "basics.basilisk").read_text(encoding="utf-8")

class CompilerTests(unittest.TestCase):
    def test_three_examples_parse(self):
        self.assertEqual([d.name for d in parse(EXAMPLES)], ["castle", "defensive-spearmen", "wheelbarrow"])

    def test_output_is_deterministic_and_has_separate_lifecycle_stages(self):
        a = compile_source(EXAMPLES)
        self.assertEqual(a, compile_source(EXAMPLES))
        self.assertIn("(set-goal demand-castle 1)", a)
        self.assertIn("(build castle)", a)
        self.assertIn("(set-goal demand-castle 2)", a)
        self.assertIn("(set-goal demand-castle 0)", a)
        self.assertEqual(a.count("(defrule"), 10)

    def test_unknown_primitive_rejected(self):
        source = """
        demand bad {
            require (not-a-real-fact castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_action_must_be_action_primitive(self):
        source = """
        demand bad {
            require (can-build castle)
            action (can-build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_witness_cannot_be_feasibility(self):
        source = """
        demand bad {
            require (can-build castle)
            action (build castle)
            witness (can-build castle)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_logical_arity_is_checked(self):
        source = """
        demand bad {
            require (and (can-build castle) (building-available castle) (can-build castle))
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        with self.assertRaises(CompileError):
            compile_source(source)

    def test_nested_logical_expression_is_supported(self):
        source = """
        demand castle {
            require (and (building-available castle) (can-build castle))
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        output = compile_source(source)
        self.assertIn("(and (building-available castle) (can-build castle))", output)

    def test_native_expression_parser_exposes_root_primitive(self):
        expr = parse_expression("(current-age >= castle)")
        self.assertEqual(expr.head, "current-age")
        self.assertEqual(expr.args, (">=", "castle"))

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
