import unittest

from Compiler.ast import Expression
from Compiler.ir.model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from Compiler.ir.production import (
    ProductionFactDisposition,
    ProductionBirthTimingEvidence,
    ProductionLifecycle,
    ProductionQueueExitTimingEvidence,
)
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


def _retry_barrier():
    return GoalSlotRequest(
        request_id=StorageRequestId(
            owner=SemanticId("test", "spears"),
            purpose="production-retry-barrier",
        ),
        role=GoalRole.EXECUTION_MEMORY,
    )


class ProductionBirthQueueExitTimingTests(unittest.TestCase):
    def test_birth_timing_resolves_as_open_sample_boundary(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_birth_timing(
            _expression(
                "(game-time >= 600)",
                "game-time",
                ">=",
                "600",
            ),
            _expression(
                "(unit-type-count 93 >= 1)",
                "unit-type-count",
                "93",
                ">=",
                "1",
            ),
            native_unit_id=93,
        )

        self.assertIsInstance(evidence, ProductionBirthTimingEvidence)
        self.assertIs(evidence.disposition, ProductionFactDisposition.OPEN)
        self.assertEqual(evidence.native_unit_id, 93)
        self.assertEqual(
            evidence.semantic_id,
            "timing.production.birth-boundary",
        )
        self.assertEqual(evidence.time_expression.args, (">=", "600"))
        self.assertEqual(
            evidence.birth_expression.args,
            ("93", ">=", "1"),
        )

    def test_birth_timing_rejects_timing_as_completion_or_wrong_unit(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(ValueError, "must use unit-type-count"):
            registry.resolve_production_birth_timing(
                _expression("(game-time >= 600)", "game-time", ">=", "600"),
                _expression(
                    "(unit-type-count-total spearman >= 1)",
                    "unit-type-count-total",
                    "spearman",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

        with self.assertRaisesRegex(ValueError, "does not target UnitId 93"):
            registry.resolve_production_birth_timing(
                _expression("(game-time >= 600)", "game-time", ">=", "600"),
                _expression(
                    "(unit-type-count 38 >= 1)",
                    "unit-type-count",
                    "38",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

    def test_queue_exit_timing_resolves_as_open_snapshot_boundary(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_queue_exit_timing(
            _expression("(game-time >= 700)", "game-time", ">=", "700"),
            _expression(
                "(unit-type-count-total 93 >= 2)",
                "unit-type-count-total",
                "93",
                ">=",
                "2",
            ),
            _expression(
                "(up-pending-objects c: 93 == 0)",
                "up-pending-objects",
                "c:",
                "93",
                "==",
                "0",
            ),
            native_unit_id=93,
        )

        self.assertIsInstance(evidence, ProductionQueueExitTimingEvidence)
        self.assertIs(evidence.disposition, ProductionFactDisposition.OPEN)
        self.assertEqual(evidence.native_unit_id, 93)
        self.assertEqual(
            evidence.semantic_id,
            "timing.production.queue-exit-boundary",
        )
        self.assertEqual(
            evidence.queue_total_expression.args,
            ("93", ">=", "2"),
        )
        self.assertEqual(
            evidence.pending_expression.args,
            ("c:", "93", "==", "0"),
        )

    def test_queue_exit_timing_rejects_wrong_fact_families(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(ValueError, "must use unit-type-count-total"):
            registry.resolve_production_queue_exit_timing(
                _expression("(game-time >= 700)", "game-time", ">=", "700"),
                _expression(
                    "(unit-type-count spearman >= 2)",
                    "unit-type-count",
                    "spearman",
                    ">=",
                    "2",
                ),
                _expression(
                    "(up-pending-objects c: 93 == 0)",
                    "up-pending-objects",
                    "c:",
                    "93",
                    "==",
                    "0",
                ),
                native_unit_id=93,
            )

        with self.assertRaisesRegex(ValueError, "must use up-pending-objects"):
            registry.resolve_production_queue_exit_timing(
                _expression("(game-time >= 700)", "game-time", ">=", "700"),
                _expression(
                    "(unit-type-count-total spearman >= 2)",
                    "unit-type-count-total",
                    "spearman",
                    ">=",
                    "2",
                ),
                _expression(
                    "(unit-type-count spearman == 2)",
                    "unit-type-count",
                    "spearman",
                    "==",
                    "2",
                ),
                native_unit_id=93,
            )

    def test_lifecycle_carries_open_birth_and_queue_exit_timing_without_authorizing_train(self):
        registry = default_de_registry()
        birth = registry.resolve_production_birth_timing(
            _expression("(game-time >= 600)", "game-time", ">=", "600"),
            _expression(
                "(unit-type-count spearman >= 1)",
                "unit-type-count",
                "spearman",
                ">=",
                "1",
            ),
            native_unit_id=93,
        )
        queue_exit = registry.resolve_production_queue_exit_timing(
            _expression("(game-time >= 700)", "game-time", ">=", "700"),
            _expression(
                "(unit-type-count-total spearman >= 2)",
                "unit-type-count-total",
                "spearman",
                ">=",
                "2",
            ),
            _expression(
                "(up-pending-objects c: 93 == 0)",
                "up-pending-objects",
                "c:",
                "93",
                "==",
                "0",
            ),
            native_unit_id=93,
        )

        lifecycle = ProductionLifecycle(
            unit="spearman",
            native_unit_id=93,
            target_admission=registry.resolve_production_target_admission(
                _expression("(can-train 93)", "can-train", "93"),
                native_unit_id=93,
            ),
            completion_witness=_expression(
                "(unit-type-count spearman >= 1)",
                "unit-type-count",
                "spearman",
                ">=",
                "1",
            ),
            retry_barrier=_retry_barrier(),
            queue_protection=registry.resolve_production_queue_protection(
                _expression(
                    "(up-pending-objects c: 93 >= 1)",
                    "up-pending-objects",
                    "c:",
                    "93",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            ),
            birth_timing_evidence=birth,
            queue_exit_timing_evidence=queue_exit,
        )

        self.assertIs(
            lifecycle.birth_timing_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertIs(
            lifecycle.queue_exit_timing_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(lifecycle.target_admission.primitive, "can-train")

    def test_analyzer_preserves_open_birth_and_queue_exit_timing(self):
        source = """
        demand timed-spears {
            require (game-time >= 600)
            require (unit-type-count spearman >= 1)
            require (unit-type-count-total spearman >= 2)
            require (up-pending-objects c: spearman == 0)
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        demand = analyze(parse(source), default_de_registry(), source_unit="test")[0]
        lifecycle = demand.production_lifecycle

        self.assertIsNotNone(lifecycle)
        self.assertIsNotNone(lifecycle.birth_timing_evidence)
        self.assertIsNotNone(lifecycle.queue_exit_timing_evidence)
        self.assertIs(
            lifecycle.birth_timing_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertIs(
            lifecycle.queue_exit_timing_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(lifecycle.birth_timing_evidence.native_unit_id, 93)
        self.assertEqual(lifecycle.queue_exit_timing_evidence.native_unit_id, 93)


if __name__ == "__main__":
    unittest.main()
