import tempfile
import unittest
from pathlib import Path

from Compiler.semantic.recurrent_execution import (
    RecurrentExecutionStatus,
    analyze_recurrent_execution,
)
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class RecurrentExecutionSemanticsTests(unittest.TestCase):
    def _graph(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            entry = Path(tmp) / "root.per"
            entry.write_text(source, encoding="utf-8")
            return SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )

    def _analysis(self, source: str):
        report = analyze_effective_rules(self._graph(source))
        return analyze_recurrent_execution(report)

    def test_recurrent_writer_can_permanently_starve_persistent_consumer(self):
        analysis = self._analysis(
            "(defrule (true) => (set-goal gate 2))\n"
            "(defrule (goal gate 1) => (set-goal observed 1))\n"
        )

        self.assertEqual(
            analysis.status_for_rule(2),
            RecurrentExecutionStatus.NEVER_RUNNABLE,
        )
        self.assertTrue(
            any(
                finding.code == "REX-004"
                and finding.rule_order == 2
                and finding.related_rule_order == 1
                for finding in analysis.diagnostics
            )
        )

    def test_recurrent_writer_that_establishes_consumer_value_keeps_consumer_runnable(self):
        analysis = self._analysis(
            "(defrule (true) => (set-goal gate 1))\n"
            "(defrule (goal gate 1) => (set-goal observed 1))\n"
        )

        self.assertEqual(
            analysis.status_for_rule(2),
            RecurrentExecutionStatus.MAY_RUN,
        )
        self.assertFalse(
            any(
                finding.code == "REX-004"
                for finding in analysis.diagnostics
                if finding.rule_order == 2
            )
        )

    def test_disable_self_writer_can_establish_state_for_later_pass(self):
        analysis = self._analysis(
            "(defrule (true) => (set-goal gate 1) (disable-self))\n"
            "(defrule (goal gate 1) => (set-goal observed 1))\n"
        )

        self.assertEqual(
            analysis.status_for_rule(2),
            RecurrentExecutionStatus.MAY_RUN,
        )
        self.assertFalse(
            any(
                finding.code == "REX-005"
                for finding in analysis.diagnostics
            )
        )

    def test_guaranteed_recurrent_jump_can_preempt_downstream_rule(self):
        analysis = self._analysis(
            "(defrule (true) => (up-jump-rule 1))\n"
            "(defrule (true) => (set-goal skipped 1))\n"
            "(defrule (true) => (set-goal tail 1))\n"
        )

        self.assertEqual(
            analysis.status_for_rule(2),
            RecurrentExecutionStatus.NEVER_RUNNABLE,
        )
        self.assertTrue(
            any(
                finding.code == "REX-003"
                and finding.rule_order == 2
                and finding.related_rule_order == 1
                for finding in analysis.diagnostics
            )
        )

    def test_one_shot_jump_does_not_permanently_starve_downstream_rule(self):
        analysis = self._analysis(
            "(defrule (true) => (up-jump-rule 1) (disable-self))\n"
            "(defrule (true) => (set-goal skipped 1))\n"
            "(defrule (true) => (set-goal reached 1))\n"
        )

        self.assertEqual(
            analysis.status_for_rule(2),
            RecurrentExecutionStatus.MAY_RUN,
        )
        self.assertFalse(
            any(
                finding.code == "REX-003"
                for finding in analysis.diagnostics
            )
        )


if __name__ == "__main__":
    unittest.main()
