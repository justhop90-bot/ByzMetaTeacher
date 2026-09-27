import tempfile
import unittest
from pathlib import Path

from Compiler.semantic.pass_scheduler import (
    PassScheduler,
    SchedulerSemanticError,
)
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


class PassSchedulerTests(unittest.TestCase):
    def _rules(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(source, encoding="utf-8")
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            return analyze_effective_rules(graph).rules

    def test_same_pass_timer_write_is_visible_to_later_rule(self):
        rules = self._rules(
            '(defrule (true) => (enable-timer 1 60))
'
            '(defrule (up-timer-status 1 = timer-running) => (disable-timer 1))
'
        )

        scheduler = PassScheduler(tuple(rules), timer_ids=("1",))
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1, 2))
        timer = scheduler.timers[0]
        self.assertEqual(timer.status.value, "DISABLED")
        self.assertEqual(timer.generation, 2)

    def test_trigger_created_at_pass_end_is_visible_only_on_next_pass(self):
        rules = self._rules(
            '(defrule (true) => (enable-timer 1 0))
'
            '(defrule (timer-triggered 1) => (disable-timer 1))
'
        )

        scheduler = PassScheduler(tuple(rules), timer_ids=("1",))
        first = scheduler.run_pass()

        self.assertEqual(first.fired_rule_orders, (1,))
        self.assertEqual(first.staged_expiries[0].generation, 1)
        self.assertEqual(scheduler.timers[0].status.value, "RUNNING")

        second = scheduler.run_pass()

        self.assertEqual(second.committed_expiries[0].generation, 1)
        self.assertEqual(second.fired_rule_orders, (2,))
        self.assertEqual(scheduler.timers[0].status.value, "DISABLED")

    def test_disable_self_does_not_abort_remaining_actions_or_later_rules(self):
        rules = self._rules(
            '(defrule (true) => '
            '(enable-timer 1 30) (disable-self) (enable-timer 1 60))
'
            '(defrule (up-timer-status 1 = timer-running) => (disable-self))
'
        )

        scheduler = PassScheduler(tuple(rules), timer_ids=("1",))
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1, 2))
        self.assertEqual(scheduler.timers[0].generation, 2)
        self.assertEqual(scheduler.timers[0].deadline, 60.0)

    def test_up_jump_rule_plus_one_skips_one_rule(self):
        rules = self._rules(
            '(defrule (true) => (up-jump-rule 1))
'
            '(defrule (true) => (disable-self))
'
            '(defrule (true) => (disable-self))
'
        )

        scheduler = PassScheduler(tuple(rules))
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1, 3))
        self.assertEqual(
            trace.control_transfers[0].target_rule_order,
            3,
        )

    def test_up_jump_rule_minus_one_revisits_current_rule(self):
        rules = self._rules(
            '(defrule (true) => (disable-self) (up-jump-rule -1))
'
            '(defrule (true) => (disable-self))
'
        )

        scheduler = PassScheduler(tuple(rules))
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1, 2))
        self.assertEqual(
            trace.control_transfers[0].target_rule_order,
            1,
        )

    def test_out_of_range_jump_is_rejected(self):
        rules = self._rules(
            '(defrule (true) => (up-jump-rule 3))
'
        )

        scheduler = PassScheduler(tuple(rules))

        with self.assertRaisesRegex(SchedulerSemanticError, "outside"):
            scheduler.run_pass()

    def test_negative_up_set_timer_disables_current_generation(self):
        rules = self._rules(
            '(defrule (true) => (up-set-timer c: 1 c: -1))
'
        )

        # up-set-timer is represented by the native four-operand shape in the
        # parser fixture; timer id is the second operand.
        scheduler = PassScheduler(tuple(rules), timer_ids=("1",))
        trace = scheduler.run_pass()

        self.assertEqual(trace.fired_rule_orders, (1,))
        self.assertEqual(scheduler.timers[0].status.value, "DISABLED")
        self.assertEqual(scheduler.timers[0].generation, 1)

    def test_timer_does_not_advance_inside_same_pass(self):
        rules = self._rules(
            '(defrule (true) => (enable-timer 1 10) (up-jump-rule 1))
'
            '(defrule (timer-triggered 1) => (disable-self))
'
            '(defrule (true) => (disable-self))
'
        )

        scheduler = PassScheduler(tuple(rules), timer_ids=("1",))
        scheduler.run_pass(elapsed_seconds=5)

        self.assertEqual(scheduler.timers[0].status.value, "RUNNING")
        self.assertEqual(scheduler.timers[0].deadline, 10.0)


if __name__ == "__main__":
    unittest.main()
