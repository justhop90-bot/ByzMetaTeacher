import unittest
from dataclasses import replace

from Compiler.compiler import compile_source
from Compiler.ir import (
    AccessKind,
    GoalRole,
    SemanticId,
    StateAccess,
    StateStorageKind,
    StorageRequestId,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.semantic.demand_ownership import OwnershipDiagnosticCode, OwnershipStatus
from Compiler.semantic.source_order import (
    StateOrderVisibility,
    validate_non_lifecycle_source_order,
)


SOURCE = """
demand castle {
    require (can-build castle)
    action (build castle)
    witness (building-type-count castle > 0)
    release (building-type-count castle > 0)
}
"""


class NonLifecycleSourceOrderTests(unittest.TestCase):
    def _demand(self):
        return analyze(
            parse(SOURCE),
            default_de_registry(),
            source_unit="source-order",
        )[0]

    def _access(
        self,
        demand,
        *,
        purpose,
        storage_kind,
        kind,
        rule_order,
        within_rule_order,
        source_order,
        operation,
    ):
        state = StorageRequestId(demand.identity, purpose)
        return StateAccess(
            state=state,
            owner=demand.identity,
            demand=demand.identity,
            kind=kind,
            phase=None,
            source_order=source_order,
            operation=operation,
            storage_kind=storage_kind,
            rule_order=rule_order,
            within_rule_order=within_rule_order,
        )

    def test_lifecycle_ownership_ignores_non_lifecycle_accesses(self):
        from Compiler.semantic.demand_ownership import validate_demand_ownership

        demand = self._demand()
        ordinary = self._access(
            demand,
            purpose="timer",
            storage_kind=StateStorageKind.TIMER,
            kind=AccessKind.WRITE,
            rule_order=4,
            within_rule_order=0,
            source_order=100,
            operation="set-timer",
        )
        report = validate_demand_ownership(
            (replace(demand, state_accesses=demand.state_accesses + (ordinary,)),)
        )

        self.assertTrue(report.valid)

    def test_same_rule_write_then_read_is_visible_without_persisted_latch(self):
        demand = self._demand()
        accesses = (
            self._access(
                demand,
                purpose="castle-state",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.WRITE,
                rule_order=4,
                within_rule_order=0,
                source_order=100,
                operation="set-goal",
            ),
            self._access(
                demand,
                purpose="castle-state",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.READ,
                rule_order=4,
                within_rule_order=1,
                source_order=101,
                operation="goal",
            ),
        )

        report = validate_non_lifecycle_source_order((replace(demand, state_accesses=accesses),))

        self.assertTrue(report.valid)
        self.assertEqual(report.diagnostics, ())
        self.assertEqual(
            report.boundaries[0].visibility,
            StateOrderVisibility.SAME_RULE_SEQUENTIAL,
        )

    def test_same_rule_read_before_write_reuses_consumer_before_writer_diagnostic(self):
        demand = self._demand()
        accesses = (
            self._access(
                demand,
                purpose="castle-state",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.READ,
                rule_order=4,
                within_rule_order=0,
                source_order=100,
                operation="goal",
            ),
            self._access(
                demand,
                purpose="castle-state",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.WRITE,
                rule_order=4,
                within_rule_order=1,
                source_order=101,
                operation="set-goal",
            ),
        )

        report = validate_non_lifecycle_source_order((replace(demand, state_accesses=accesses),))

        self.assertEqual(len(report.diagnostics), 1)
        self.assertEqual(
            report.diagnostics[0].code,
            OwnershipDiagnosticCode.CONSUMER_BEFORE_WRITER,
        )
        self.assertEqual(
            report.diagnostics[0].status,
            OwnershipStatus.ORDER_VIOLATION,
        )

    def test_cross_rule_write_then_read_is_persisted_pass_boundary(self):
        demand = self._demand()
        accesses = (
            self._access(
                demand,
                purpose="persistent-sn",
                storage_kind=StateStorageKind.STRATEGIC_NUMBER,
                kind=AccessKind.WRITE,
                rule_order=7,
                within_rule_order=1,
                source_order=200,
                operation="set-sn",
            ),
            self._access(
                demand,
                purpose="persistent-sn",
                storage_kind=StateStorageKind.STRATEGIC_NUMBER,
                kind=AccessKind.READ,
                rule_order=8,
                within_rule_order=0,
                source_order=300,
                operation="sn",
            ),
        )

        report = validate_non_lifecycle_source_order((replace(demand, state_accesses=accesses),))

        self.assertTrue(report.valid)
        self.assertEqual(
            report.boundaries[0].visibility,
            StateOrderVisibility.CROSS_RULE_PERSISTED,
        )

    def test_goal_sn_timer_are_all_checked_as_native_persistent_state(self):
        demand = self._demand()
        for storage_kind in (
            StateStorageKind.GOAL,
            StateStorageKind.STRATEGIC_NUMBER,
            StateStorageKind.TIMER,
        ):
            with self.subTest(storage_kind=storage_kind):
                state = StorageRequestId(
                    demand.identity,
                    f"{storage_kind.value.lower()}-state",
                )
                accesses = (
                    replace(
                        demand.state_accesses[0],
                        state=state,
                        storage_kind=storage_kind,
                        rule_order=1,
                        within_rule_order=0,
                        source_order=10,
                    ),
                    replace(
                        demand.state_accesses[1],
                        state=state,
                        storage_kind=storage_kind,
                        rule_order=2,
                        within_rule_order=0,
                        source_order=20,
                    ),
                )
                report = validate_non_lifecycle_source_order(
                    (replace(demand, state_accesses=accesses),)
                )
                self.assertTrue(report.valid)
                self.assertEqual(
                    report.boundaries[0].visibility,
                    StateOrderVisibility.CROSS_RULE_PERSISTED,
                )

    def test_missing_rule_scope_fails_closed(self):
        demand = self._demand()
        access = self._access(
            demand,
            purpose="timer",
            storage_kind=StateStorageKind.TIMER,
            kind=AccessKind.WRITE,
            rule_order=None,
            within_rule_order=0,
            source_order=10,
            operation="set-timer",
        )
        report = validate_non_lifecycle_source_order(
            (replace(demand, state_accesses=(access,)),)
        )

        self.assertEqual(len(report.diagnostics), 1)
        self.assertEqual(
            report.diagnostics[0].code,
            OwnershipDiagnosticCode.STATE_ACCESS_MISSING_RULE_SCOPE,
        )

    def test_cross_rule_reader_before_writer_is_an_order_violation(self):
        demand = self._demand()
        accesses = (
            self._access(
                demand,
                purpose="timer",
                storage_kind=StateStorageKind.TIMER,
                kind=AccessKind.READ,
                rule_order=2,
                within_rule_order=0,
                source_order=20,
                operation="timer",
            ),
            self._access(
                demand,
                purpose="timer",
                storage_kind=StateStorageKind.TIMER,
                kind=AccessKind.WRITE,
                rule_order=3,
                within_rule_order=0,
                source_order=30,
                operation="set-timer",
            ),
        )
        report = validate_non_lifecycle_source_order((replace(demand, state_accesses=accesses),))

        self.assertEqual(
            report.diagnostics[0].code,
            OwnershipDiagnosticCode.CONSUMER_BEFORE_WRITER,
        )

    def test_analysis_is_deterministic_under_demand_input_order(self):
        first = self._demand()
        second = replace(first, identity=SemanticId("source-order", "other"))
        accesses_first = (
            self._access(
                first,
                purpose="goal",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.WRITE,
                rule_order=1,
                within_rule_order=0,
                source_order=10,
                operation="set-goal",
            ),
        )
        accesses_second = (
            self._access(
                second,
                purpose="goal",
                storage_kind=StateStorageKind.GOAL,
                kind=AccessKind.WRITE,
                rule_order=1,
                within_rule_order=0,
                source_order=10,
                operation="set-goal",
            ),
        )

        report_a = validate_non_lifecycle_source_order(
            (replace(second, state_accesses=accesses_second), replace(first, state_accesses=accesses_first))
        )
        report_b = validate_non_lifecycle_source_order(
            (replace(first, state_accesses=accesses_first), replace(second, state_accesses=accesses_second))
        )

        self.assertEqual(report_a, report_b)

    def test_compiler_pipeline_calls_non_lifecycle_source_order_gate(self):
        from unittest.mock import patch
        from Compiler.semantic.source_order import SourceOrderReport

        empty = SourceOrderReport(diagnostics=(), boundaries=())
        with patch(
            "Compiler.compiler.validate_non_lifecycle_source_order",
            return_value=empty,
        ) as validator:
            compile_source(SOURCE)
            validator.assert_called_once()


if __name__ == "__main__":
    unittest.main()
