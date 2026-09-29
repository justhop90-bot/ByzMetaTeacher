import unittest

from Compiler.ast import Expression
from Compiler.ir import ProductionFactDisposition, ProductionQueueCapacityControlEvidence
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


class ProductionQueueCapacityNativeContractTests(unittest.TestCase):
    def test_exact_training_queue_sn_is_typed_open_capacity_evidence(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_queue_capacity_control_evidence(
            _expression(
                "(up-compare-sn sn-enable-training-queue == 3)",
                "up-compare-sn",
                "sn-enable-training-queue",
                "==",
                "3",
            ),
        )

        self.assertIsInstance(evidence, ProductionQueueCapacityControlEvidence)
        self.assertIs(
            evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(evidence.native_strategic_number_id, 264)
        self.assertEqual(evidence.configured_additional_queue_slots, 3)
        self.assertEqual(evidence.documented_total_capacity, 4)
        self.assertEqual(
            evidence.semantic_id,
            "controller.production.queue-capacity.sn264",
        )
        self.assertEqual(evidence.expression.args, ("264", "==", "3"))

    def test_numeric_training_queue_sn_alias_is_accepted(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_queue_capacity_control_evidence(
            _expression(
                "(up-compare-sn 264 == 3)",
                "up-compare-sn",
                "264",
                "==",
                "3",
            ),
        )

        self.assertEqual(evidence.native_strategic_number_id, 264)
        self.assertEqual(evidence.documented_total_capacity, 4)
        self.assertIs(evidence.disposition, ProductionFactDisposition.OPEN)

    def test_capacity_evidence_rejects_wrong_sn(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "does not target SN 264",
        ):
            registry.resolve_production_queue_capacity_control_evidence(
                _expression(
                    "(up-compare-sn sn-food-gatherer-percentage == 3)",
                    "up-compare-sn",
                    "sn-food-gatherer-percentage",
                    "==",
                    "3",
                ),
            )

    def test_capacity_evidence_rejects_non_exact_comparisons(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "must use exact equality",
        ):
            registry.resolve_production_queue_capacity_control_evidence(
                _expression(
                    "(up-compare-sn sn-enable-training-queue >= 3)",
                    "up-compare-sn",
                    "sn-enable-training-queue",
                    ">=",
                    "3",
                ),
            )

    def test_capacity_evidence_rejects_out_of_range_additional_slots(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "additional queue slots must be in 0..15",
        ):
            registry.resolve_production_queue_capacity_control_evidence(
                _expression(
                    "(up-compare-sn sn-enable-training-queue == 16)",
                    "up-compare-sn",
                    "sn-enable-training-queue",
                    "==",
                    "16",
                ),
            )

    def test_analyzer_preserves_open_capacity_control_without_authorizing_train(self):
        source = """
        demand queued-spears {
            require (up-compare-sn sn-enable-training-queue == 3)
            require (unit-type-count-total spearman < 4)
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        demand = analyze(
            parse(source),
            default_de_registry(),
            source_unit="test",
        )[0]

        lifecycle = demand.production_lifecycle
        self.assertIsNotNone(lifecycle)
        self.assertIsNotNone(lifecycle.queue_capacity_control)
        self.assertIs(
            lifecycle.queue_capacity_control.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(
            lifecycle.queue_capacity_control.native_strategic_number_id,
            264,
        )
        self.assertEqual(
            lifecycle.queue_capacity_control.documented_total_capacity,
            4,
        )
        self.assertEqual(demand.action.expression.head, "train")
        self.assertEqual(demand.action.expression.args, ("spearman",))


if __name__ == "__main__":
    unittest.main()
