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

    def test_castle_enters_pending_and_cannot_reissue_while_pending(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: castle | ACTIVE -> PENDING"):output.find("; Completion witness: castle")]
        self.assertIn("(build castle)", action_block)
        self.assertIn("(set-goal demand-castle 1001)", action_block)
        pending_block = output[output.find("; Completion witness: castle"):output.find("; Release: castle")]
        self.assertIn("(goal demand-castle 1001)", pending_block)
        self.assertNotIn("(build castle)", pending_block)

    def test_spearmen_pending_state_prevents_repeated_train(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: defensive-spearmen | ACTIVE -> PENDING"):output.find("; Completion witness: defensive-spearmen")]
        self.assertIn("(train spearman)", action_block)
        self.assertIn("(set-goal demand-defensive-spearmen 1004)", action_block)
        pending_block = output[output.find("; Completion witness: defensive-spearmen"):output.find("; Release: defensive-spearmen")]
        self.assertIn("(goal demand-defensive-spearmen 1004)", pending_block)
        self.assertNotIn("(train spearman)", pending_block)

    def test_wheelbarrow_pending_state_prevents_repeated_research(self):
        output = compile_source(EXAMPLES)
        action_block = output[output.find("; Demand: wheelbarrow | ACTIVE -> PENDING"):output.find("; Completion witness: wheelbarrow")]
        self.assertIn("(research ri-wheelbarrow)", action_block)
        self.assertIn("(set-goal demand-wheelbarrow 1007)", action_block)
        pending_block = output[output.find("; Completion witness: wheelbarrow"):output.find("; Release: wheelbarrow")]
        self.assertIn("(goal demand-wheelbarrow 1007)", pending_block)
        self.assertNotIn("(research ri-wheelbarrow)", pending_block)

    def test_release_requires_completed_state(self):
        output = compile_source(EXAMPLES)
        castle_release = output[output.find("; Release: castle"):output.find("; Demand: defensive-spearmen")]
        self.assertIn("(goal demand-castle 1002)", castle_release)
        self.assertIn("(set-goal demand-castle 0)", castle_release)
        self.assertNotIn("(goal demand-castle 1001)", castle_release)

if __name__ == "__main__":
    unittest.main()
