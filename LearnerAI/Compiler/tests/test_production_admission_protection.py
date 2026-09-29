import unittest

from Compiler.ast import Expression
from Compiler.ir.production import ProductionFactDisposition
from Compiler.parser import parse
from Compiler.primitives import default_de_registry
from Compiler.semantic import analyze
from Compiler.errors import CompileError


def _expression(source, head, *args):
    return Expression(source, head, tuple(args))


class ProductionAdmissionProtectionTests(unittest.TestCase):
    def setUp(self):
        self.registry = default_de_registry()

    def test_target_admission_matrix_supported(self):
        for primitive in ("can-train", "can-train-with-escrow"):
            with self.subTest(primitive=primitive):
                resolved = self.registry.resolve_production_target_admission(
                    _expression(
                        f"({primitive} 93)",
                        primitive,
                        "93",
                    ),
                    native_unit_id=93,
                )
                self.assertEqual(
                    resolved.disposition,
                    ProductionFactDisposition.SUPPORTED,
                )
                self.assertEqual(resolved.native_unit_id, 93)

    def test_target_admission_matrix_rejects_queue_and_provider_facts(self):
        for primitive, args in (
            (
                "up-pending-objects",
                ("c:", "93", ">=", "1"),
            ),
            (
                "unit-type-count-total",
                ("93", "<", "2"),
            ),
            (
                "building-type-count",
                ("87", ">=", "1"),
            ),
        ):
            with self.subTest(primitive=primitive):
                with self.assertRaisesRegex(
                    ValueError,
                    "production target-admission fact",
                ):
                    self.registry.resolve_production_target_admission(
                        _expression(
                            f"({primitive} {' '.join(args)})",
                            primitive,
                            *args,
                        ),
                        native_unit_id=93,
                    )

    def test_queue_protection_matrix_supported(self):
        resolved = self.registry.resolve_production_queue_protection(
            _expression(
                "(up-pending-objects c: 93 >= 1)",
                "up-pending-objects",
                "c:",
                "93",
                ">=",
                "1",
            ),
            native_unit_id=93,
        )
        self.assertEqual(resolved.disposition, ProductionFactDisposition.SUPPORTED)
        self.assertEqual(resolved.pending_fact.args[1], "93")

    def test_queue_protection_matrix_marks_total_and_provider_state_open(self):
        for primitive, args, message in (
            (
                "unit-type-count-total",
                ("93", "<", "2"),
                "queue-state",
            ),
            (
                "building-type-count",
                ("87", ">=", "1"),
                "provider-state",
            ),
        ):
            with self.subTest(primitive=primitive):
                with self.assertRaisesRegex(
                    ValueError,
                    f"production queue-protection {message} observation is OPEN",
                ):
                    self.registry.resolve_production_queue_protection(
                        _expression(
                            f"({primitive} {' '.join(args)})",
                            primitive,
                            *args,
                        ),
                        native_unit_id=93,
                    )

    def test_queue_protection_matrix_rejects_target_admission_fact(self):
        with self.assertRaisesRegex(
            ValueError,
            "production queue-protection fact 'can-train' is REJECTED",
        ):
            self.registry.resolve_production_queue_protection(
                _expression(
                    "(can-train 93)",
                    "can-train",
                    "93",
                ),
                native_unit_id=93,
            )

    def test_unknown_queue_fact_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "production queue-protection fact 'unknown-queue-fact' is REJECTED",
        ):
            self.registry.resolve_production_queue_protection(
                _expression(
                    "(unknown-queue-fact 93)",
                    "unknown-queue-fact",
                    "93",
                ),
                native_unit_id=93,
            )

    def test_unknown_provider_fact_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "production queue-protection provider-state fact 'provider-ready' is REJECTED",
        ):
            self.registry.resolve_production_queue_protection(
                _expression(
                    "(provider-ready 87)",
                    "provider-ready",
                    "87",
                ),
                native_unit_id=93,
                provider_state=_expression(
                    "(provider-ready 87)",
                    "provider-ready",
                    "87",
                ),
            )

    def test_analyzer_populates_separate_target_admission_and_queue_protection(self):
        source = """
        demand spears {
            require (unit-type-count-total spearman < 2)
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        demand = analyze(
            parse(source),
            self.registry,
            source_unit="test",
        )[0]

        self.assertIsNotNone(demand.production_lifecycle)
        lifecycle = demand.production_lifecycle
        self.assertEqual(
            lifecycle.target_admission.primitive,
            "can-train",
        )
        self.assertEqual(
            lifecycle.queue_protection.pending_fact.head,
            "up-pending-objects",
        )
        self.assertEqual(
            lifecycle.pending_fact,
            lifecycle.queue_protection.pending_fact,
        )

    def test_analyzer_rejects_train_without_target_admission(self):
        source = """
        demand spears {
            require (unit-type-count-total spearman < 2)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            "PRODUCTION-TARGET-ADMISSION-MISSING",
        ):
            analyze(
                parse(source),
                self.registry,
                source_unit="test",
            )

    def test_analyzer_rejects_target_admission_for_wrong_unit(self):
        source = """
        demand spears {
            require (can-train skirmisher)
            action (train spearman)
            witness (unit-type-count spearman >= 2)
            release (unit-type-count spearman >= 2)
        }
        """
        with self.assertRaisesRegex(
            CompileError,
            "PRODUCTION-TARGET-ADMISSION",
        ):
            analyze(
                parse(source),
                self.registry,
                source_unit="test",
            )


if __name__ == "__main__":
    unittest.main()
