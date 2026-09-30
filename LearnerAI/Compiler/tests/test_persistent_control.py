import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from Compiler.diagnostics import DiagnosticSeverity
from Compiler.ir import (
    CleanupStatus,
    PersistentControlKind,
    PersistentControlLifetime,
    PersistentControlRef,
    SemanticId,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.persistent_control import (
    PersistentControlDiagnosticCode,
    PersistentControlStatus,
    analyze_persistent_control_lifetimes,
)
from Compiler.semantic.persistent_state import analyze_persistent_state
from Compiler.semantic.rule_execution import analyze_effective_rules
from Compiler.source_graph import SourceGraphRequest, SourceGraphResolver


_SOURCE = """
demand timer_gate {
    timer cooldown
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


class PersistentControlTests(unittest.TestCase):
    def _demand(self):
        return analyze(
            parse(_SOURCE, source_unit="timer-control-test"),
            default_de_registry(),
            source_unit="timer-control-test",
        )[0]

    def _report(self, per_source: str, *, demand=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(per_source, encoding="utf-8")
            graph = SourceGraphResolver().resolve(
                SourceGraphRequest(entrypoint=entry)
            )
            execution = analyze_effective_rules(graph)
            persistent_state = analyze_persistent_state(execution)
            return analyze_persistent_control_lifetimes(
                (demand or self._demand(),),
                persistent_state,
                execution,
            )

    def test_timer_projection_is_owner_scoped(self):
        demand = self._demand()
        control = demand.persistent_controls[0]

        self.assertEqual(control.kind, PersistentControlKind.TIMER)
        self.assertEqual(control.owner, demand.identity)
        self.assertEqual(
            control.lifetime,
            PersistentControlLifetime.UNTIL_OWNER_RELEASE,
        )
        self.assertIsNone(control.native_binding)

    def test_owner_mismatch_is_blocked(self):
        demand = self._demand()
        control = demand.persistent_controls[0]
        bad_control = replace(
            control,
            owner=SemanticId("other", "demand"),
        )
        bad_demand = replace(demand, persistent_controls=(bad_control,))

        report = self._report(
            "(defrule (true) => (enable-timer cooldown 30))\n",
            demand=bad_demand,
        )

        self.assertEqual(len(report.errors), 1)
        self.assertEqual(
            report.errors[0].code,
            PersistentControlDiagnosticCode.OWNER_MISMATCH,
        )
        self.assertEqual(
            report.errors[0].status,
            PersistentControlStatus.BLOCKED,
        )

    def test_direct_cleanup_after_owner_release_is_satisfied(self):
        demand = self._demand()
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
    (disable-timer cooldown)
)
"""
        )

        obligation = report.obligations[0]
        self.assertEqual(obligation.status, CleanupStatus.SATISFIED)
        self.assertEqual(obligation.release_rule_order, 2)
        self.assertEqual(obligation.cleanup_rule_orders, (2,))
        self.assertEqual(obligation.cleanup_commands, ("disable-timer",))
        self.assertFalse(report.warnings)

    def test_later_reachable_cleanup_is_satisfied(self):
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (true) => (disable-timer cooldown) (disable-self))
"""
        )

        obligation = report.obligations[0]
        self.assertEqual(obligation.status, CleanupStatus.SATISFIED)
        self.assertEqual(obligation.cleanup_rule_orders, (3,))

    def test_cleanup_only_before_owner_release_is_not_satisfied(self):
        report = self._report(
            """
(defrule (true) => (disable-timer cooldown) (disable-self))
(defrule (true) => (enable-timer cooldown 30) (disable-self))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
"""
        )

        obligation = report.obligations[0]
        self.assertEqual(obligation.status, CleanupStatus.REQUIRED)
        self.assertEqual(
            report.warnings[0].code,
            PersistentControlDiagnosticCode.CLEANUP_PRE_RELEASE,
        )

    def test_unreachable_cleanup_is_not_satisfied(self):
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30) (disable-self))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (true) => (up-jump-rule 1))
(defrule (true) => (disable-timer cooldown) (disable-self))
(defrule (true) => (disable-self))
"""
        )

        obligation = report.obligations[0]
        self.assertEqual(obligation.status, CleanupStatus.REQUIRED)
        self.assertEqual(
            report.warnings[0].code,
            PersistentControlDiagnosticCode.CLEANUP_UNREACHABLE,
        )

    def test_dynamic_timer_write_keeps_cleanup_unknown(self):
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (true) => (up-set-timer c: cooldown g: duration))
"""
        )

        obligation = report.obligations[0]
        self.assertEqual(obligation.status, CleanupStatus.UNKNOWN)
        self.assertEqual(
            report.warnings[0].code,
            PersistentControlDiagnosticCode.RELEASE_PATH_UNKNOWN,
        )

    def test_timer_triggered_does_not_count_as_cleanup(self):
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (timer-triggered cooldown) => (set-goal observed 1))
"""
        )

        self.assertEqual(
            report.obligations[0].status,
            CleanupStatus.REQUIRED,
        )
        self.assertEqual(
            report.warnings[0].code,
            PersistentControlDiagnosticCode.RELEASE_MISSING,
        )

    def test_initialization_disable_is_not_owner_release_cleanup(self):
        report = self._report(
            """
(defrule (true) => (disable-timer cooldown) (disable-self))
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
"""
        )

        self.assertEqual(
            report.obligations[0].status,
            CleanupStatus.REQUIRED,
        )
        self.assertEqual(
            report.warnings[0].code,
            PersistentControlDiagnosticCode.CLEANUP_PRE_RELEASE,
        )

    def test_negative_up_set_timer_is_explicit_cleanup(self):
        report = self._report(
            """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (true) => (up-set-timer c: cooldown c: -1))
"""
        )

        self.assertEqual(
            report.obligations[0].status,
            CleanupStatus.SATISFIED,
        )
        self.assertEqual(
            report.obligations[0].cleanup_commands,
            ("up-set-timer",),
        )

    def test_multiple_timers_have_independent_cleanup_obligations(self):
        source = """
demand timer_gate {
    timer cooldown
    timer rearm
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""
        demand = analyze(
            parse(source, source_unit="timer-control-test"),
            default_de_registry(),
            source_unit="timer-control-test",
        )[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "root.per"
            entry.write_text(
                """
(defrule (true) => (enable-timer cooldown 30) (enable-timer rearm 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
    (disable-timer cooldown)
    (disable-timer rearm)
)
""",
                encoding="utf-8",
            )
            execution = analyze_effective_rules(
                SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=entry))
            )
            report = analyze_persistent_control_lifetimes(
                (demand,),
                analyze_persistent_state(execution),
                execution,
            )

        self.assertEqual(
            [item.status for item in report.obligations],
            [CleanupStatus.SATISFIED, CleanupStatus.SATISFIED],
        )
        self.assertEqual(
            [item.control.local_name for item in report.obligations],
            ["timer:cooldown", "timer:rearm"],
        )

    def test_analysis_is_deterministic(self):
        per_source = """
(defrule (true) => (enable-timer cooldown 30))
(defrule
    (goal demand-timer_gate 999)
    (building-type-count castle > 0)
=>
    (set-goal demand-timer_gate 0)
)
(defrule (true) => (disable-timer cooldown))
"""
        first = self._report(per_source)
        second = self._report(per_source)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
