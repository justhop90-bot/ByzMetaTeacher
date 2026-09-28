import unittest

from Compiler.ast import Expression
from Compiler.ir import (
    GoalRole,
    GoalSlotRequest,
    ProductionLifecycle,
    SemanticId,
    StorageRequestId,
)


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


def _lifecycle(*, witness=None, retry_purpose="production-retry-barrier"):
    owner = SemanticId("test", "spears")
    return ProductionLifecycle(
        unit="spearman",
        native_unit_id=93,
        pending_fact=_expression(
            "(up-pending-objects c: 93 >= 1)",
            "up-pending-objects",
            "c:",
            "93",
            ">=",
            "1",
        ),
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
    )


class ProductionLifecycleContractTests(unittest.TestCase):
    def test_production_lifecycle_owns_canonical_completion_and_retry_contract(self):
        lifecycle = _lifecycle()

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


if __name__ == "__main__":
    unittest.main()
