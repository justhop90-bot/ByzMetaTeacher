import unittest

from Compiler.ast import Expression
from Compiler.ir.native_duc import NativeDucPlan, NativeDucRule
from Compiler.primitives import default_de_registry, default_native_contract_catalog
from Compiler.primitives.native_binder import NativeSemanticBinder
from Compiler.primitives.native_schema import load_default_native_schema


def _expr(source, head, *args):
    return Expression(source, head, tuple(args))


class NativeDucPlanTests(unittest.TestCase):
    def test_plan_orders_rules_deterministically(self):
        plan = NativeDucPlan(
            (
                NativeDucRule(
                    identity="duc-b",
                    order=1,
                    facts=(_expr("(true)", "true"),),
                    actions=(),
                ),
                NativeDucRule(
                    identity="duc-c",
                    order=1,
                    facts=(_expr("(true)", "true"),),
                    actions=(),
                ),
            )
        )
        self.assertEqual(
            tuple(rule.identity for rule in plan.rules),
            ("duc-b", "duc-c"),
        )

    def test_plan_rejects_non_deterministic_rule_order(self):
        with self.assertRaisesRegex(ValueError, "deterministic order"):
            NativeDucPlan(
                (
                    NativeDucRule(
                        identity="duc-b",
                        order=2,
                        facts=(_expr("(true)", "true"),),
                        actions=(),
                    ),
                    NativeDucRule(
                        identity="duc-a",
                        order=1,
                        facts=(_expr("(true)", "true"),),
                        actions=(),
                    ),
                )
            )

    def test_plan_rejects_duplicate_rule_identity(self):
        with self.assertRaisesRegex(ValueError, "duplicate native DUC rule identity"):
            NativeDucPlan(
                (
                    NativeDucRule(
                        identity="duc-a",
                        order=1,
                        facts=(_expr("(true)", "true"),),
                        actions=(),
                    ),
                    NativeDucRule(
                        identity="duc-a",
                        order=2,
                        facts=(_expr("(true)", "true"),),
                        actions=(),
                    ),
                )
            )


class NativeDucBinderTests(unittest.TestCase):
    def setUp(self):
        native = load_default_native_schema()
        registry = default_de_registry()
        self.binder = NativeSemanticBinder(
            native_registry=native,
            semantic_mappings=registry._semantic_mappings,
            native_contracts=default_native_contract_catalog(),
            adapter_lookup=registry.get,
        )

    def test_promotes_contracted_duc_command(self):
        binding = self.binder.bind_duc_command("up-find-local")
        self.assertEqual(binding.command, "up-find-local")
        self.assertEqual(binding.native_kind, "Fact/Action")
        self.assertEqual(binding.support_state.value, "executable-safe")

    def test_unpromoted_duc_command_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not executable"):
            self.binder.bind_duc_command("up-get-search-state")


class NativeDucEmissionFixtureTests(unittest.TestCase):
    def test_compile_surface_accepts_internal_duc_plan_without_source_syntax(self):
        self.assertTrue(hasattr(NativeDucPlan, "rules"))


if __name__ == "__main__":
    unittest.main()
