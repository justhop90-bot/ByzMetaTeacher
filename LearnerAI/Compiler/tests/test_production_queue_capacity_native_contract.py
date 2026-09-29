import unittest

from Compiler.ast import Expression
from Compiler.ir import ProductionFactDisposition, ProductionQueueCapacityControlEvidence
from Compiler.primitives import default_de_registry


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


class ProductionQueueCapacityNativeContractTests(unittest.TestCase):
    def test_exact_training_queue_sn_is_typed_open_capacity_evidence(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_queue_capacity_control_evidence(
            _expression(
                "(strategic-number sn-enable-training-queue == 3)",
                "strategic-number",
                "sn-enable-training-queue",
                "==",
                "3",
            ),
            native_unit_id=93,
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

    def test_capacity_evidence_rejects_non_exact_comparisons(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "must use exact equality",
        ):
            registry.resolve_production_queue_capacity_control_evidence(
                _expression(
                    "(strategic-number sn-enable-training-queue >= 3)",
                    "strategic-number",
                    "sn-enable-training-queue",
                    ">=",
                    "3",
                ),
                native_unit_id=93,
            )

    def test_capacity_evidence_rejects_out_of_range_additional_slots(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "additional queue slots must be in 0..15",
        ):
            registry.resolve_production_queue_capacity_control_evidence(
                _expression(
                    "(strategic-number sn-enable-training-queue == 16)",
                    "strategic-number",
                    "sn-enable-training-queue",
                    "==",
                    "16",
                ),
                native_unit_id=93,
            )


if __name__ == "__main__":
    unittest.main()
