import unittest

from Compiler.ast import Expression
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    ProductionFactDisposition,
    ProductionLifecycle,
    ProductionProviderStateObservation,
    ProductionQueueProtection,
    ProductionTargetAdmission,
    SemanticId,
    StorageRequestId,
    evaluate_production_runtime,
    ProductionBoundaryStatus,
    ProductionProviderTransition,
    ProductionRuntimeStatus,
)
from Compiler.ir.strategy_runtime import (
    EvidenceTruth,
    RuntimeObservationSnapshot,
)


def expr(source, head, *args):
    return Expression(source, head, tuple(args))


def lifecycle_with_runtime_evidence():
    registry = __import__(
        "Compiler.primitives",
        fromlist=["default_de_registry"],
    ).default_de_registry()

    pending = expr(
        "(up-pending-objects c: 93 >= 1)",
        "up-pending-objects",
        "c:",
        "93",
        ">=",
        "1",
    )
    target = ProductionTargetAdmission(
        disposition=ProductionFactDisposition.SUPPORTED,
        primitive="can-train",
        expression=expr("(can-train 93)", "can-train", "93"),
        native_unit_id=93,
        semantic_id="execution.train.feasibility",
    )
    lifecycle = ProductionLifecycle(
        unit="spearman",
        native_unit_id=93,
        target_admission=target,
        completion_witness=expr(
            "(unit-type-count spearman >= 1)",
            "unit-type-count",
            "spearman",
            ">=",
            "1",
        ),
        retry_barrier=GoalSlotRequest(
            request_id=StorageRequestId(
                owner=SemanticId("test", "spears"),
                purpose="production-retry-barrier",
            ),
            role=GoalRole.EXECUTION_MEMORY,
        ),
        queue_protection=ProductionQueueProtection(
            disposition=ProductionFactDisposition.SUPPORTED,
            pending_fact=pending,
            native_unit_id=93,
        ),
        queue_state=registry.resolve_production_queue_state(
            expr(
                "(unit-type-count-total 93 >= 1)",
                "unit-type-count-total",
                "93",
                ">=",
                "1",
            ),
            native_unit_id=93,
        ),
        provider_state=registry.resolve_production_provider_state(
            expr(
                "(building-type-count 12 >= 1)",
                "building-type-count",
                "12",
                ">=",
                "1",
            ),
            native_building_id=12,
        ),
        queue_capacity_control=registry.resolve_production_queue_capacity_control_evidence(
            expr(
                "(up-compare-sn 264 == 3)",
                "up-compare-sn",
                "264",
                "==",
                "3",
            ),
        ),
        provider_readiness_evidence=registry.resolve_production_provider_readiness(
            expr(
                "(up-train-site-ready c: 93)",
                "up-train-site-ready",
                "c:",
                "93",
            ),
            native_unit_id=93,
        ),
        provider_availability_evidence=registry.resolve_production_provider_availability_evidence(
            expr(
                "(building-type-count 12 >= 1)",
                "building-type-count",
                "12",
                ">=",
                "1",
            ),
            native_building_id=12,
        ),
        birth_timing_evidence=registry.resolve_production_birth_timing(
            expr("(game-time >= 100)", "game-time", ">=", "100"),
            expr(
                "(unit-type-count 93 >= 1)",
                "unit-type-count",
                "93",
                ">=",
                "1",
            ),
            native_unit_id=93,
        ),
        queue_exit_timing_evidence=registry.resolve_production_queue_exit_timing(
            expr("(game-time >= 110)", "game-time", ">=", "110"),
            expr(
                "(unit-type-count-total 93 >= 1)",
                "unit-type-count-total",
                "93",
                ">=",
                "1",
            ),
            expr(
                "(up-pending-objects c: 93 == 0)",
                "up-pending-objects",
                "c:",
                "93",
                "==",
                "0",
            ),
            native_unit_id=93,
        ),
    )
    return lifecycle


class ProductionRuntimePathTests(unittest.TestCase):
    def setUp(self):
        self.lifecycle = lifecycle_with_runtime_evidence()

    def test_queue_capacity_is_observed_but_never_authorizes_train(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(can-train 93)", True),
                ("(building-type-count 12 >= 1)", True),
                ("(up-train-site-ready c: 93)", True),
                ("(up-compare-sn 264 == 3)", True),
                ("(unit-type-count-total 93 >= 1)", False),
                ("(up-pending-objects c: 93 >= 1)", False),
                ("(unit-type-count spearman >= 1)", False),
            ),
        )
        state = evaluate_production_runtime("spears", self.lifecycle, snapshot)

        self.assertEqual(state.queue_capacity_control, EvidenceTruth.TRUE)
        self.assertEqual(state.provider_usability, EvidenceTruth.TRUE)
        self.assertEqual(state.status, ProductionRuntimeStatus.READY)
        self.assertFalse(state.can_authorize_train)

    def test_provider_loss_and_recovery_are_detected_from_previous_pass(self):
        lost = evaluate_production_runtime(
            "spears",
            self.lifecycle,
            RuntimeObservationSnapshot(
                fact_results=(
                    ("(can-train 93)", True),
                    ("(building-type-count 12 >= 1)", False),
                    ("(up-train-site-ready c: 93)", True),
                ),
                previous_fact_results=(
                    ("(building-type-count 12 >= 1)", True),
                ),
            ),
        )
        self.assertEqual(
            lost.provider_transition,
            ProductionProviderTransition.LOST,
        )
        self.assertEqual(
            lost.status,
            ProductionRuntimeStatus.BLOCKED,
        )

        recovered = evaluate_production_runtime(
            "spears",
            self.lifecycle,
            RuntimeObservationSnapshot(
                fact_results=(
                    ("(can-train 93)", True),
                    ("(building-type-count 12 >= 1)", True),
                    ("(up-train-site-ready c: 93)", True),
                ),
                previous_fact_results=(
                    ("(building-type-count 12 >= 1)", False),
                ),
            ),
        )
        self.assertEqual(
            recovered.provider_transition,
            ProductionProviderTransition.RECOVERED,
        )

    def test_birth_and_queue_exit_boundaries_remain_observational(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(game-time >= 100)", True),
                ("(unit-type-count 93 >= 1)", True),
                ("(game-time >= 110)", True),
                ("(unit-type-count-total 93 >= 1)", True),
                ("(up-pending-objects c: 93 == 0)", True),
            ),
        )
        state = evaluate_production_runtime("spears", self.lifecycle, snapshot)
        self.assertEqual(state.birth_boundary, ProductionBoundaryStatus.OBSERVED)
        self.assertEqual(
            state.queue_exit_boundary,
            ProductionBoundaryStatus.OBSERVED,
        )

    def test_next_pass_visibility_requires_a_cross_pass_transition(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(unit-type-count spearman >= 1)", True),
                ("(up-pending-objects c: 93 >= 1)", False),
            ),
            previous_fact_results=(
                ("(unit-type-count spearman >= 1)", False),
                ("(up-pending-objects c: 93 >= 1)", True),
            ),
        )
        state = evaluate_production_runtime("spears", self.lifecycle, snapshot)
        self.assertEqual(
            state.next_pass_visibility,
            ProductionBoundaryStatus.OBSERVED,
        )

    def test_missing_open_runtime_evidence_fails_closed(self):
        snapshot = RuntimeObservationSnapshot(
            fact_results=(
                ("(can-train 93)", True),
            ),
        )
        state = evaluate_production_runtime("spears", self.lifecycle, snapshot)
        self.assertEqual(state.queue_capacity_control, EvidenceTruth.UNKNOWN)
        self.assertEqual(state.provider_usability, EvidenceTruth.UNKNOWN)
        self.assertEqual(state.status, ProductionRuntimeStatus.UNKNOWN)
        self.assertTrue(state.runtime_open)


if __name__ == "__main__":
    unittest.main()
