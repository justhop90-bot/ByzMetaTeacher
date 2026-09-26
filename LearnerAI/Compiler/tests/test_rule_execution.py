import tempfile
import unittest
from pathlib import Path

from Compiler.errors import CompileError
from Compiler.semantic.rule_execution import (
    RulePassBehavior,
    analyze_effective_rules,
)
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class RuleExecutionSemanticsTests(unittest.TestCase):
    def _graph(self, source: str, child: str | None = None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(source, encoding="utf-8")
            if child is not None:
                (root / "child.per").write_text(child, encoding="utf-8")
            return SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )

    def test_rules_are_numbered_in_effective_source_order(self):
        graph = self._graph(
            '(defrule (true) => (set-goal root-before 1))\n'
            '(load "child.per")\n'
            '(defrule (true) => (set-goal root-after 1))\n',
            '(defrule (true) => (set-goal child 1))\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual([rule.rule_order for rule in report.rules], [1, 2, 3])
        self.assertEqual(
            [rule.actions[0].head for rule in report.rules],
            ["set-goal", "set-goal", "set-goal"],
        )
        self.assertEqual(
            [rule.actions[0].args[0] for rule in report.rules],
            ["root-before", "child", "root-after"],
        )

    def test_rule_order_is_effective_order_not_physical_file_order(self):
        graph = self._graph(
            '(defrule (true) => (set-goal before 1))\n'
            '(load "child.per")\n'
            '(defrule (true) => (set-goal after 1))\n',
            '(defrule (true) => (set-goal child 1))\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual(
            [rule.source_location.source_unit for rule in report.rules],
            [
                str(graph.slices[0].path),
                str(graph.slices[1].path),
                str(graph.slices[2].path),
            ],
        )


    def test_nested_rule_body_preserves_nested_parentheses(self):
        graph = self._graph(
            '(defrule nested '
            '(and (true) (not (false))) '
            '=> '
            '(set-goal nested 1) '
            '(if (true) (set-goal nested-2 2) (set-goal nested-2 3))'
            ')\\n',
        )

        report = analyze_effective_rules(graph)

        rule = report.rules[0]
        self.assertEqual(len(rule.facts), 1)
        self.assertEqual(rule.facts[0].head, "and")
        self.assertEqual(len(rule.facts[0].args), 2)
        self.assertEqual(len(rule.actions), 2)
        self.assertEqual(rule.actions[1].expression.head, "if")

    def test_outer_defrule_closing_parenthesis_is_consumed_by_rule_parser(self):
        graph = self._graph(
            '(defrule closes-cleanly (true) => (set-goal closed 1))\\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual(len(report.rules), 1)
        self.assertEqual(report.rules[0].actions[0].expression.head, "set-goal")
        self.assertEqual(report.rules[0].actions[0].expression.args[0], "closed")

    def test_plain_rule_is_recurrent_across_passes(self):
        graph = self._graph(
            '(defrule (true) => (set-goal recurring 1))\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual(
            report.rules[0].pass_behavior,
            RulePassBehavior.RECURRENT,
        )
        self.assertIsNone(report.rules[0].disable_self_action_index)

    def test_disable_self_makes_rule_one_shot(self):
        graph = self._graph(
            '(defrule (true) => (set-goal once 1) (disable-self))\n',
        )

        report = analyze_effective_rules(graph)

        rule = report.rules[0]
        self.assertEqual(rule.pass_behavior, RulePassBehavior.ONE_SHOT)
        self.assertEqual(rule.disable_self_action_index, 1)

    def test_actions_preserve_within_rule_order(self):
        graph = self._graph(
            '(defrule (true) => (set-goal first 1) (set-goal second 2) (disable-self))\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual(
            [action.within_rule_order for action in report.rules[0].actions],
            [0, 1, 2],
        )

    def test_source_order_does_not_claim_firing(self):
        graph = self._graph(
            '(defrule (current-age >= castle-age) => (set-goal castle-ready 1))\n',
        )

        report = analyze_effective_rules(graph)

        self.assertEqual(report.rules[0].pass_behavior, RulePassBehavior.RECURRENT)
        self.assertEqual(report.rules[0].facts[0].head, "current-age")
        self.assertEqual(report.rules[0].actions[0].head, "set-goal")
        self.assertFalse(report.rules[0].fires_guaranteed)

    def test_malformed_rule_is_rejected_before_semantic_analysis(self):
        graph = self._graph(
            '(defrule (true) (set-goal broken 1))\n',
        )

        with self.assertRaisesRegex(CompileError, "RULE-PARSE-001"):
            analyze_effective_rules(graph)


if __name__ == "__main__":
    unittest.main()
