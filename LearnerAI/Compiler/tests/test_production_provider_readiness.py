import unittest

from Compiler.ast import Expression
from Compiler.ir.production import (
    ProductionFactDisposition,
    ProductionLifecycle,
    ProductionProviderReadinessEvidence,
)
from Compiler.ir.model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
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


class ProductionProviderReadinessTests(unittest.TestCase):
    def test_up_train_site_ready_resolves_as_open_provider_readiness(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_provider_readiness(
            _expression(
                "(up-train-site-ready c: 93)",
                "up-train-site-ready",
                "c:",
                "93",
            ),
            native_unit_id=93,
        )

        self.assertIsInstance(evidence, ProductionProviderReadinessEvidence)
        self.assertIs(evidence.disposition, ProductionFactDisposition.OPEN)
        self.assertEqual(evidence.native_unit_id, 93)
        self.assertEqual(
            evidence.semantic_id,
            "admissibility.train.site-ready",
        )
        self.assertEqual(evidence.expression.args, ("c:", "93"))

    def test_provider_readiness_canonicalizes_symbolic_unit_to_numeric_id(self):
        registry = default_de_registry()
        evidence = registry.resolve_production_provider_readiness(
            _expression(
                "(up-train-site-ready c: spearman)",
                "up-train-site-ready",
                "c:",
                "spearman",
            ),
            native_unit_id=93,
        )

        self.assertEqual(evidence.native_unit_id, 93)
        self.assertEqual(evidence.expression.args, ("c:", "93"))

    def test_provider_readiness_rejects_dynamic_type_operands(self):
        registry = default_de_registry()
        for type_op in ("g:", "s:"):
            with self.subTest(type_op=type_op):
                with self.assertRaisesRegex(ValueError, "must use literal c:"):
                    registry.resolve_production_provider_readiness(
                        _expression(
                            f"(up-train-site-ready {type_op} 93)",
                            "up-train-site-ready",
                            type_op,
                            "93",
                        ),
                        native_unit_id=93,
                    )

    def test_provider_readiness_rejects_wrong_unit(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(ValueError, "does not target UnitId 93"):
            registry.resolve_production_provider_readiness(
                _expression(
                    "(up-train-site-ready c: 38)",
                    "up-train-site-ready",
                    "c:",
                    "38",
                ),
                native_unit_id=93,
            )

    def test_provider_readiness_rejects_non_readiness_fact(self):
        registry = default_de_registry()
        with self.assertRaisesRegex(ValueError, "must use up-train-site-ready"):
            registry.resolve_production_provider_readiness(
                _expression(
                    "(building-type-count 87 >= 1)",
                    "building-type-count",
                    "87",
                    ">=",
                    "1",
                ),
                native_unit_id=93,
            )

    def test_lifecycle_carries_open_provider_readiness_without_replacing_can_train(self):
        registry = default_de_registry()
        readiness = registry.resolve_production_provider_readiness(
            _expression(
                "(up-train-site-ready c: 93)",
                "up-train-site-ready",
                "c:",
                "93",
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
            provider_readiness_evidence=readiness,
        )

        self.assertIs(
            lifecycle.provider_readiness_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(lifecycle.target_admission.primitive, "can-train")

    def test_analyzer_preserves_readiness_and_train_feasibility_separately(self):
        source = """
        demand spears {
            require (up-train-site-ready c: spearman)
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        demand = analyze(parse(source), default_de_registry(), source_unit="test")[0]
        lifecycle = demand.production_lifecycle

        self.assertIsNotNone(lifecycle)
        self.assertIsNotNone(lifecycle.provider_readiness_evidence)
        self.assertIs(
            lifecycle.provider_readiness_evidence.disposition,
            ProductionFactDisposition.OPEN,
        )
        self.assertEqual(
            lifecycle.provider_readiness_evidence.native_unit_id,
            93,
        )
        self.assertEqual(
            lifecycle.provider_readiness_evidence.expression.args,
            ("c:", "93"),
        )
        self.assertEqual(demand.action.expression.head, "train")
        self.assertEqual(demand.action.expression.args, ("spearman",))


if __name__ == "__main__":
    unittest.main()
