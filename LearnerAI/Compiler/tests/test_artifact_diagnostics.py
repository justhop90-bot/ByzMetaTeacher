import unittest
from types import SimpleNamespace

from Compiler.artifact_diagnostics import append_persistent_rule_diagnostics


class ArtifactDiagnosticsTests(unittest.TestCase):
    def _diagnostic(
        self,
        *,
        rule_order=2,
        code="PSTATE-002",
        severity="warning",
        state_kind="GOAL",
        state_identifier="7",
        related_rule_order=1,
        related_operation="set-goal",
        message="goal state '7' has a later writer in rule 2 after writer in rule 1",
    ):
        return SimpleNamespace(
            category=SimpleNamespace(value="PERSISTENT_STATE"),
            rule_order=rule_order,
            code=SimpleNamespace(value=code),
            severity=SimpleNamespace(value=severity),
            state_kind=state_kind,
            state_identifier=state_identifier,
            related_rule_order=related_rule_order,
            related_operation=related_operation,
            message=message,
        )

    def test_appends_persistent_diagnostics_as_deterministic_comments(self):
        source = "(defrule (true) => (set-goal 7 1))\n"
        diagnostic = self._diagnostic()

        first = append_persistent_rule_diagnostics(source, (diagnostic,))
        second = append_persistent_rule_diagnostics(source, (diagnostic,))

        self.assertEqual(first, second)
        self.assertTrue(first.startswith(source))
        self.assertIn("; COMPILER RULE DIAGNOSTICS", first)
        self.assertIn(
            "; PERSISTENT_STATE rule=2 code=PSTATE-002 severity=warning "
            "state=GOAL:7 related-rule=1 related-operation=set-goal",
            first,
        )
        self.assertIn(
            "; message=goal state '7' has a later writer in rule 2 after writer in rule 1",
            first,
        )
        self.assertEqual(first.count("(defrule"), 1)

    def test_ignores_non_persistent_rule_diagnostics(self):
        source = "(defrule (true) => (set-goal 7 1))\n"
        firing = self._diagnostic(
            code="RULE-FIRE-004",
            severity="info",
            state_kind=None,
            state_identifier=None,
            related_rule_order=None,
            related_operation=None,
        )
        firing.category = SimpleNamespace(value="FIRING_ELIGIBILITY")

        result = append_persistent_rule_diagnostics(source, (firing,))

        self.assertEqual(result, source)

    def test_orders_multiple_findings_by_rule_and_code(self):
        source = "(defrule (true) => (set-goal 7 1))\n"
        later = self._diagnostic(rule_order=3, code="PSTATE-003", related_rule_order=2)
        earlier = self._diagnostic(rule_order=2, code="PSTATE-002", related_rule_order=1)

        result = append_persistent_rule_diagnostics(source, (later, earlier))

        first = result.index("rule=2 code=PSTATE-002")
        second = result.index("rule=3 code=PSTATE-003")
        self.assertLess(first, second)


if __name__ == "__main__":
    unittest.main()
