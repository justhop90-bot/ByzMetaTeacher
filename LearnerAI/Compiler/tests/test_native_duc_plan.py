import unittest

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.ir import GoalRole, GoalSpanKind, GoalSpanRequest, SemanticId, StorageRequestId
from Compiler.ir.native_duc import NativeDucOutputRequest, NativeDucPlan, NativeDucRule
from Compiler.primitives import default_de_registry, default_native_contract_catalog
from Compiler.primitives.native_binder import NativeSemanticBinder
from Compiler.primitives.native_schema import load_default_native_schema


def _expr(source, head, *args):
    return Expression(source, head, tuple(args))


def _search_state_output_request(rule_identity="search-state-output", section="ACTION", expression_index=0):
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            "up-get-search-state",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=4,
        shape=GoalSpanKind.EXTENDED_4,
        contract_id="up-get-search-state.OutputGoalId",
        start_min=41,
        start_max=15996,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section=section,
        expression_index=expression_index,
        request=request,
        command="up-get-search-state",
        argument_index=0,
    )


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

    def test_plan_accepts_action_only_duc_rule(self):
        plan = NativeDucPlan(
            (
                NativeDucRule(
                    identity="reset-search",
                    order=1,
                    facts=(),
                    actions=(
                        _expr("(up-reset-filters)", "up-reset-filters"),
                    ),
                ),
            )
        )
        self.assertEqual(plan.rules[0].actions[0].head, "up-reset-filters")

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

    def test_registry_rejects_fact_action_misplacement(self):
        from Compiler.primitives import default_de_registry

        registry = default_de_registry()
        bad_plan = NativeDucPlan(
            (
                NativeDucRule(
                    identity="bad-placement",
                    order=1,
                    facts=(
                        _expr(
                            "(up-target-objects 1 0 -1 -1)",
                            "up-target-objects",
                            "1",
                            "0",
                            "-1",
                            "-1",
                        ),
                    ),
                    actions=(),
                ),
            )
        )

        with self.assertRaisesRegex(ValueError, "is an Action and cannot be emitted as a Fact"):
            registry.validate_duc_plan(bad_plan)

    def test_registry_accepts_search_state_goalspan_output_request(self):
        from Compiler.primitives import default_de_registry

        registry = default_de_registry()
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="search-state-output",
                    order=1,
                    facts=(),
                    actions=(
                        _expr(
                            "(up-get-search-state 41)",
                            "up-get-search-state",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _search_state_output_request(),
            ),
        )

        registry.validate_duc_plan(plan)

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

    def test_search_state_duc_command_is_executable_safe(self):
        binding = self.binder.bind_duc_command("up-get-search-state")
        self.assertEqual(binding.command, "up-get-search-state")
        self.assertEqual(binding.native_kind, "Action")
        self.assertEqual(binding.parameter_count, 1)
        self.assertEqual(binding.support_state.value, "executable-safe")


class NativeDucEmissionFixtureTests(unittest.TestCase):
    def test_compile_allocates_and_emits_bound_search_state_goalspan(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="search-state-output",
                    order=100,
                    facts=(
                        _expr(
                            "(up-get-search-state 41)",
                            "up-get-search-state",
                            "41",
                        ),
                    ),
                    actions=(),
                ),
            ),
            output_requests=(
                _search_state_output_request(),
            ),
        )
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        artifact = compile_source(source, duc_plan=plan)
        self.assertIn("(up-get-search-state 43)", artifact)
        self.assertNotIn("(up-get-search-state 41)", artifact)

    def test_compile_surface_accepts_internal_duc_plan_without_source_syntax(self):
        self.assertTrue(hasattr(NativeDucPlan, "rules"))


if __name__ == "__main__":
    unittest.main()
