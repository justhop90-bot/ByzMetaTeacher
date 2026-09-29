import unittest

from Compiler.ast import Expression
from Compiler.ir.production import (
    ProductionFactDisposition,
    ProductionLifecycle,
    ProductionProviderAvailabilityEvidence,
    ProductionProviderStateObservation,
    ProductionQueueCapacityEvidence,
    ProductionQueueProtection,
    ProductionQueueStateObservation,
    ProductionTargetAdmission,
)
from Compiler.ir.model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from Compiler.primitives import default_de_registry


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


class ProductionObservationTests(unittest.TestCase):
    def test_production_lifecycle_accepts_optional_typed_observations(self):
        registry = default_de_registry()
        queue = registry.resolve_production_queue_state(
            _expression(
                "(unit-type-count-total 93 >= 2)",
                "unit-type-count-total",
                "93",
                ">=",
                "2",
            ),
            native_unit_id=93,
        )
        provider = registry.resolve_production_provider_state(
            _expression(
                "(building-type-count 87 >= 1)",
                "building-type-count",
                "87",
                ">=",
                "1",
            ),
            native_building_id=87,
        )

        pending = _expression(
            "(up-pending-objects c: 93 >= 1)",
            "up-pending-objects",
            "c:",
            "93",
            ">=",
            "1",
        )
        lifecycle = ProductionLifecycle(
            unit="spearman",
            native_unit_id=93,
            target_admission=ProductionTargetAdmission(
                disposition=ProductionFactDisposition.SUPPORTED,
                primitive="can-train",
                expression=_expression(
                    "(can-train 93)",
                    "can-train",
                    "93",
                ),
                native_unit_id=93,
                semantic_id="execution.train.feasibility",
            ),
            completion_witness=_expression(
                "(unit-type-count spearman >= 1)",
                "unit-type-count",
                "spearman",
                ">=",
                "1",
            ),
            retry_barrier=_retry_barrier(),
            queue_protection=ProductionQueueProtection(
                disposition=ProductionFactDisposition.SUPPORTED,
                pending_fact=pending,
                native_unit_id=93,
            ),
            queue_state=queue,
            provider_state=provider,
        )

        self.assertIsInstance(lifecycle.queue_state, ProductionQueueStateObservation)
        self.assertIsInstance(lifecycle.provider_state, ProductionProviderStateObservation)
        self.assertEqual(lifecycle.queue_state.native_unit_id, 93)
        self.assertEqual(lifecycle.provider_state.native_building_id, 87)

    def test_queue_resolution_fails_closed_on_unknown_fact(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production queue-state observation 'unknown-queue-fact' is not a registered native fact",
        ):
            registry.resolve_production_queue_state(
                _expression(
                    "(unknown-queue-fact 93 >= 1)",
                    "unknown-queue-fact",
                    "93",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

    def test_queue_resolution_rejects_non_queue_observation(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production queue-state observation must use unit-type-count-total",
        ):
            registry.resolve_production_queue_state(
                _expression(
                    "(unit-type-count 93 >= 1)",
                    "unit-type-count",
                    "93",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

    def test_queue_resolution_rejects_wrong_unit_target(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production queue-state observation does not target UnitId 93",
        ):
            registry.resolve_production_queue_state(
                _expression(
                    "(unit-type-count-total 38 >= 1)",
                    "unit-type-count-total",
                    "38",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

    def test_provider_resolution_fails_closed_on_unknown_fact(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production provider-state observation 'provider-ready' is not a registered native fact",
        ):
            registry.resolve_production_provider_state(
                _expression(
                    "(provider-ready 87)",
                    "provider-ready",
                    "87",
                ),
                native_building_id=87,
            )

    def test_provider_resolution_rejects_non_provider_world_state(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production provider-state observation must use building-type-count",
        ):
            registry.resolve_production_provider_state(
                _expression(
                    "(unit-type-count-total 87 >= 1)",
                    "unit-type-count-total",
                    "87",
                    ">=",
                    "1",
                ),
                native_building_id=87,
            )

    def test_provider_resolution_rejects_wrong_provider_building(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "production provider-state observation does not target BuildingId 87",
        ):
            registry.resolve_production_provider_state(
                _expression(
                    "(building-type-count 82 >= 1)",
                    "building-type-count",
                    "82",
                    ">=",
                    "1",
                ),
                native_building_id=87,
            )


    def test_queue_capacity_evidence_is_explicitly_open(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_queue_capacity_evidence(
            _expression(
                "(unit-type-count-total 93 >= 2)",
                "unit-type-count-total",
                "93",
                ">=",
                "2",
            ),
            native_unit_id=93,
        )

        self.assertIsInstance(evidence, ProductionQueueCapacityEvidence)
        self.assertEqual(evidence.disposition, ProductionFactDisposition.OPEN)
        self.assertEqual(evidence.native_unit_id, 93)
        self.assertEqual(evidence.expression.head, "unit-type-count-total")

    def test_queue_capacity_evidence_rejects_pending_and_unknown_sources(self):
        registry = default_de_registry()
        for expression in (
            _expression(
                "(up-pending-objects c: 93 >= 1)",
                "up-pending-objects",
                "c:",
                "93",
                ">=",
                "1",
            ),
            _expression(
                "(unknown-queue-capacity 93 >= 1)",
                "unknown-queue-capacity",
                "93",
                ">=",
                "1",
            ),
        ):
            with self.subTest(primitive=expression.head):
                with self.assertRaisesRegex(
                    ValueError,
                    "queue-capacity evidence.*(REJECTED|registered native fact)",
                ):
                    registry.resolve_production_queue_capacity_evidence(
                        expression,
                        native_unit_id=93,
                    )

    def test_provider_availability_evidence_is_explicitly_open(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_provider_availability_evidence(
            _expression(
                "(building-type-count 87 >= 1)",
                "building-type-count",
                "87",
                ">=",
                "1",
            ),
            native_building_id=87,
        )

        self.assertIsInstance(evidence, ProductionProviderAvailabilityEvidence)
        self.assertEqual(evidence.disposition, ProductionFactDisposition.OPEN)
        self.assertEqual(evidence.native_building_id, 87)
        self.assertEqual(evidence.expression.head, "building-type-count")

    def test_provider_availability_evidence_rejects_queue_observation(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(
            ValueError,
            "provider-availability evidence.*REJECTED",
        ):
            registry.resolve_production_provider_availability_evidence(
                _expression(
                    "(unit-type-count-total 93 >= 1)",
                    "unit-type-count-total",
                    "93",
                    ">=",
                    "1",
                ),
                native_building_id=87,
            )

    def test_lifecycle_carries_open_capacity_and_provider_availability_evidence(self):
        registry = default_de_registry()
        queue_capacity = registry.resolve_production_queue_capacity_evidence(
            _expression(
                "(unit-type-count-total 93 >= 2)",
                "unit-type-count-total",
                "93",
                ">=",
                "2",
            ),
            native_unit_id=93,
        )
        provider_availability = registry.resolve_production_provider_availability_evidence(
            _expression(
                "(building-type-count 87 >= 1)",
                "building-type-count",
                "87",
                ">=",
                "1",
            ),
            native_building_id=87,
        )

        pending = _expression(
            "(up-pending-objects c: 93 >= 1)",
            "up-pending-objects",
            "c:",
            "93",
            ">=",
            "1",
        )
        lifecycle = ProductionLifecycle(
            unit="spearman",
            native_unit_id=93,
            target_admission=ProductionTargetAdmission(
                disposition=ProductionFactDisposition.SUPPORTED,
                primitive="can-train",
                expression=_expression("(can-train 93)", "can-train", "93"),
                native_unit_id=93,
                semantic_id="execution.train.feasibility",
            ),
            completion_witness=_expression(
                "(unit-type-count spearman >= 1)",
                "unit-type-count",
                "spearman",
                ">=",
                "1",
            ),
            retry_barrier=_retry_barrier(),
            queue_protection=ProductionQueueProtection(
                disposition=ProductionFactDisposition.SUPPORTED,
                pending_fact=pending,
                native_unit_id=93,
            ),
            queue_state=registry.resolve_production_queue_state(
                _expression(
                    "(unit-type-count-total 93 >= 2)",
                    "unit-type-count-total",
                    "93",
                    ">=",
                    "2",
                ),
                native_unit_id=93,
            ),
            provider_state=registry.resolve_production_provider_state(
                _expression(
                    "(building-type-count 87 >= 1)",
                    "building-type-count",
                    "87",
                    ">=",
                    "1",
                ),
                native_building_id=87,
            ),
            queue_capacity_evidence=queue_capacity,
            provider_availability_evidence=provider_availability,
        )

        self.assertEqual(
            lifecycle.queue_capacity_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(
            lifecycle.provider_availability_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )


if __name__ == "__main__":
    unittest.main()
