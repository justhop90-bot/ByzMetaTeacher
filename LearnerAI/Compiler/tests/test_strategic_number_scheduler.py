import tempfile
import unittest
from pathlib import Path

from Compiler.semantic.pass_scheduler import PassScheduler
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.semantic.strategic_number_semantics import (
    analyze_strategic_number_expressions,
)
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class StrategicNumberSchedulerTests(unittest.TestCase):
    def _rules(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(source, encoding="utf-8")
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            return analyze_effective_rules(graph)

    def test_same_pass_write_is_visible_to_later_rule(self):
        report = self._rules(
            "(defrule (true) => (set-strategic-number 510 7) (disable-self))
"
            "(defrule (strategic-number 510 >= 7) => (disable-self))
"
        )
        scheduler = PassScheduler(report.rules)
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1, 2))
        self.assertEqual(scheduler.strategic_numbers["510"], 7)

    def test_same_rule_goal_dependency_is_explicitly_tracked(self):
        report = self._rules(
            "(defrule (true) => "
            "(set-goal goal-x 4) "
            "(up-modify-sn 510 g:+ goal-x) "
            "(disable-self))
"
        )
        semantic = analyze_strategic_number_expressions(report)

        self.assertEqual(len(semantic.dependencies), 1)
        dependency = semantic.dependencies[0]
        self.assertEqual(dependency.kind.value, "GOAL")
        self.assertEqual(dependency.identifier, "goal-x")
        self.assertEqual(dependency.rule_order, 1)
        self.assertEqual(dependency.within_rule_order, 1)
        self.assertFalse(semantic.errors)

    def test_forward_same_rule_dependency_is_rejected(self):
        report = self._rules(
            "(defrule (true) => "
            "(up-modify-sn 510 s:+ 511) "
            "(set-strategic-number 511 4))
"
        )
        semantic = analyze_strategic_number_expressions(report)

        self.assertTrue(semantic.errors)
        self.assertEqual(semantic.errors[0].code.value, "SNSEM-009")

    def test_same_pass_operator_semantics_reuse_typed_evaluator(self):
        report = self._rules(
            "(defrule (true) => "
            "(set-strategic-number 510 8) "
            "(up-modify-sn 510 c:/ 3) "
            "(disable-self))
"
        )
        scheduler = PassScheduler(report.rules)
        scheduler.run_pass()

        self.assertEqual(scheduler.strategic_numbers["510"], 3)


if __name__ == "__main__":
    unittest.main()
