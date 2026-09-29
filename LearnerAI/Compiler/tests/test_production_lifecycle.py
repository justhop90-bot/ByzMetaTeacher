import unittest

from Compiler.ast import Expression
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    ProductionFactDisposition,
    ProductionLifecycle,
    ProductionQueueProtection,
    ProductionTargetAdmission,
    SemanticId,
    StorageRequestId,
)


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


def _lifecycle(*, witness=None, retry_purpose="production-retry-barrier"):
    owner = SemanticId("test", "spears")
    pending = _expression(
        "(up-pending-objects c: 93 >= 1)",
        "up-pending-objects",
        "c:",
        "93",
        ">=",
        "1",
    )
    target_admission = ProductionTargetAdmission(
        disposition=ProductionFactDisposition.SUPPORTED,
        primitive="can-train",
        expression=_expression(
            "(can-train 93)",
            "can-train",
            "93",
        ),
        native_unit_id=93,
        semantic_id="execution.train.feasibility",
    )
    queue_protection = ProductionQueueProtection(
        disposition=ProductionFactDisposition.SUPPORTED,
        pending_fact=pending,
        native_unit_id=93,
    )
    return ProductionLifecycle(
        unit="spearman",
        native_unit_id=93,
        target_admission=target_admission,
        completion_witness=witness
        or _expression(
            "(unit-type-count spearman >= 1)",
            "unit-type-count",
            "spearman",
            ">=",
            "1",
        ),
        retry_barrier=GoalSlotRequest(
            request_id=StorageRequestId(
                owner=owner,
                purpose=retry_purpose,
            ),
            role=GoalRole.EXECUTION_MEMORY,
        ),
        queue_protection=queue_protection,
    )


class ProductionLifecycleContractTests(unittest.TestCase):
    def test_production_lifecycle_owns_canonical_completion_and_retry_contract(self):
        lifecycle = _lifecycle()

        self.assertEqual(lifecycle.target_admission.primitive, "can-train")
        self.assertEqual(lifecycle.target_admission.native_unit_id, 93)
        self.assertEqual(lifecycle.queue_protection.pending_fact.head, "up-pending-objects")
        self.assertEqual(lifecycle.completion_witness.head, "unit-type-count")
        self.assertEqual(lifecycle.completion_witness.args[0], "spearman")
        self.assertEqual(
            lifecycle.retry_barrier.request_id.purpose,
            "production-retry-barrier",
        )
        self.assertEqual(
            lifecycle.retry_barrier.role,
            GoalRole.EXECUTION_MEMORY,
        )

    def test_total_count_witness_is_rejected_as_production_completion(self):
        with self.assertRaisesRegex(
            ValueError,
            "production completion witness must use unit-type-count",
        ):
            _lifecycle(
                witness=_expression(
                    "(unit-type-count-total spearman >= 1)",
                    "unit-type-count-total",
                    "spearman",
                    ">=",
                    "1",
                )
            )

    def test_completion_witness_must_target_the_production_unit(self):
        with self.assertRaisesRegex(
            ValueError,
            "production completion witness must target unit 'spearman'",
        ):
            _lifecycle(
                witness=_expression(
                    "(unit-type-count skirmisher >= 1)",
                    "unit-type-count",
                    "skirmisher",
                    ">=",
                    "1",
                )
            )

    def test_retry_barrier_must_be_execution_memory_for_production(self):
        with self.assertRaisesRegex(
            ValueError,
            "production retry barrier must use the 'production-retry-barrier' purpose",
        ):
            _lifecycle(retry_purpose="research-retry-barrier")

    def test_analyzer_connects_canonical_witness_and_retry_barrier(self):
        source = """
        demand spears {
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

        self.assertIsNotNone(demand.production_lifecycle)
        self.assertEqual(
            demand.production_lifecycle.completion_witness,
            demand.completion_witness.expression,
        )
        self.assertEqual(
            demand.production_lifecycle.retry_barrier,
            demand.production_retry_barrier,
        )


if __name__ == "__main__":
    unittest.main()
