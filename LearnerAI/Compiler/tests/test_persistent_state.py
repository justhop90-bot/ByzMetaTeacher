import tempfile
import unittest
from pathlib import Path

from Compiler.semantic.persistent_state import (
    PersistentStateAccessKind,
    PersistentStateDiagnosticCode,
    PersistentStateKind,
    PersistentStateVisibility,
    analyze_persistent_state,
)
from Compiler.semantic.rule_execution import RulePassBehavior, analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class PersistentStateSemanticsTests(unittest.TestCase):
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

    def test_extracts_goal_strategic_number_and_timer_state_in_effective_order(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1) (set-strategic-number 12 3))\n"
            "(load \"child.per\")\n"
            "(defrule (goal 7 1) (strategic-number 12 >= 3) => (up-set-timer timer-type 2 timer-type 5))\n"
            "(defrule (up-timer-status 2 = timer-running) => (set-goal 7 2))\n",
            "(defrule (true) => (set-goal 7 9))\n",
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        self.assertEqual(
            [(item.state.kind, item.effect, item.rule_order, item.within_rule_order)
             for item in report.accesses],
            [
                (PersistentStateKind.GOAL, PersistentStateAccessKind.WRITE, 1, 0),
                (PersistentStateKind.STRATEGIC_NUMBER, PersistentStateAccessKind.WRITE, 1, 1),
                (PersistentStateKind.GOAL, PersistentStateAccessKind.READ, 2, 0),
                (PersistentStateKind.STRATEGIC_NUMBER, PersistentStateAccessKind.READ, 2, 1),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.WRITE, 2, 0),
                (PersistentStateKind.TIMER, PersistentStateAccessKind.READ, 3, 0),
                (PersistentStateKind.GOAL, PersistentStateAccessKind.WRITE, 3, 0),
                (PersistentStateKind.GOAL, PersistentStateAccessKind.WRITE, 4, 0),
            ],
        )

        self.assertEqual(
            [item.command for item in report.accesses],
            [
                "set-goal",
                "set-strategic-number",
                "goal",
                "strategic-number",
                "up-set-timer",
                "up-timer-status",
                "set-goal",
                "set-goal",
            ],
        )

    def test_guard_read_before_same_rule_action_write_is_an_order_violation(self):
        graph = self._graph(
            "(defrule (goal 7 1) => (set-goal 7 2))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        boundary = report.boundaries[0]
        self.assertEqual(
            boundary.visibility,
            PersistentStateVisibility.CONSUMER_BEFORE_WRITER,
        )
        self.assertEqual(
            report.diagnostics[0].code,
            PersistentStateDiagnosticCode.CONSUMER_BEFORE_WRITER,
        )

    def test_cross_rule_write_then_read_is_persisted(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1))\n"
            "(defrule (goal 7 1) => (set-goal 8 1))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        goal_boundary = next(
            item for item in report.boundaries if item.state.identifier == "7"
        )
        self.assertEqual(
            goal_boundary.visibility,
            PersistentStateVisibility.CROSS_RULE_PERSISTED,
        )
        self.assertEqual(goal_boundary.first_writer.rule_order, 1)
        self.assertEqual(goal_boundary.first_consumer.rule_order, 2)

    def test_later_writer_is_explicitly_reported_as_potential_overwrite(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1))\n"
            "(defrule (true) => (set-goal 7 2))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        self.assertTrue(
            any(
                item.code is PersistentStateDiagnosticCode.LATER_OVERWRITE
                for item in report.diagnostics
            )
        )
        self.assertEqual(
            report.boundaries[0].later_writers[0].rule_order,
            2,
        )

    def test_same_rule_later_action_overwrites_earlier_action_in_source_order(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1) (set-goal 7 2))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        self.assertEqual(
            report.boundaries[0].visibility,
            PersistentStateVisibility.SAME_RULE_ACTION_SEQUENCE,
        )
        self.assertTrue(
            any(
                item.code is PersistentStateDiagnosticCode.LATER_OVERWRITE
                for item in report.diagnostics
            )
        )
        self.assertEqual(
            [item.within_rule_order for item in report.boundaries[0].writers],
            [0, 1],
        )

    def test_incompatible_later_writer_shadows_exact_goal_consumer(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1))\n"
            "(defrule (true) => (set-goal 7 2))\n"
            "(defrule (goal 7 1) => (set-goal 9 1))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        self.assertTrue(
            any(
                item.code is PersistentStateDiagnosticCode.CONSUMER_SHADOWED_BY_WRITER
                for item in report.diagnostics
            )
        )
        diagnostic = next(
            item
            for item in report.diagnostics
            if item.code is PersistentStateDiagnosticCode.CONSUMER_SHADOWED_BY_WRITER
        )
        self.assertEqual(diagnostic.rule_order, 3)
        self.assertEqual(diagnostic.access.rule_order, 3)
        self.assertEqual(diagnostic.related_access.rule_order, 2)

    def test_disable_self_writer_retains_one_shot_lifetime_for_state_analysis(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1) (disable-self))\n"
            "(defrule (goal 7 1) => (set-goal 8 1))\n"
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        writer = next(
            item
            for item in report.accesses
            if item.command == "set-goal"
        )
        self.assertEqual(writer.pass_behavior, RulePassBehavior.ONE_SHOT)
        self.assertEqual(
            report.boundaries[0].visibility,
            PersistentStateVisibility.CROSS_RULE_PERSISTED,
        )

    def test_source_graph_load_order_remains_authoritative_for_persistent_state(self):
        graph = self._graph(
            "(defrule (true) => (set-goal 7 1))\n"
            "(load \"child.per\")\n"
            "(defrule (true) => (set-goal 7 2))\n",
            "(defrule (true) => (set-goal 7 3))\n",
        )

        report = analyze_persistent_state(analyze_effective_rules(graph))

        self.assertEqual(
            [item.rule_order for item in report.boundaries[0].writers],
            [1, 2, 3],
        )
        self.assertEqual(
            [item.expression.args[1] for item in report.boundaries[0].writers],
            ["1", "3", "2"],
        )

    def test_analysis_is_deterministic(self):
        source = (
            "(defrule (true) => (set-goal 7 1) (set-goal 7 2))\n"
            "(defrule (goal 7 1) => (set-goal 7 3))\n"
        )

        graph_a = self._graph(source)
        graph_b = self._graph(source)

        report_a = analyze_persistent_state(analyze_effective_rules(graph_a))
        report_b = analyze_persistent_state(analyze_effective_rules(graph_b))

        self.assertEqual(
            [(item.state.kind, item.state.identifier, item.effect, item.rule_order, item.within_rule_order)
             for item in report_a.accesses],
            [(item.state.kind, item.state.identifier, item.effect, item.rule_order, item.within_rule_order)
             for item in report_b.accesses],
        )
        self.assertEqual(
            [(item.code, item.rule_order, item.access.rule_order, item.related_access.rule_order if item.related_access else None)
             for item in report_a.diagnostics],
            [(item.code, item.rule_order, item.access.rule_order, item.related_access.rule_order if item.related_access else None)
             for item in report_b.diagnostics],
        )


if __name__ == "__main__":
    unittest.main()
