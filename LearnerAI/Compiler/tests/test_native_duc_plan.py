import unittest

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.ir import GoalRole, GoalSlotRequest, GoalSpanKind, GoalSpanRequest, SemanticId, StorageRequestId
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


def _group_size_output_request(rule_identity="group-size-output", section="ACTION", expression_index=0):
    request = GoalSlotRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            "up-get-group-size",
        ),
        role=GoalRole.NATIVE_OUTPUT,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section=section,
        expression_index=expression_index,
        request=request,
        command="up-get-group-size",
        argument_index=2,
    )


def _cost_delta_output_request(rule_identity="cost-delta-output", section="ACTION", expression_index=0):
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            "up-get-cost-delta",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=4,
        shape=GoalSpanKind.EXTENDED_4,
        contract_id="up-get-cost-delta.OutputGoalId",
        start_min=41,
        start_max=15996,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section=section,
        expression_index=expression_index,
        request=request,
        command="up-get-cost-delta",
        argument_index=0,
    )


def _point_output_request(rule_identity="point-output", section="ACTION", expression_index=0):
    request = GoalSpanRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            "up-get-point",
        ),
        role=GoalRole.NATIVE_OUTPUT,
        width=2,
        shape=GoalSpanKind.POINT_PAIR,
        contract_id="up-get-point.Point",
        start_min=41,
        start_max=15998,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section=section,
        expression_index=expression_index,
        request=request,
        command="up-get-point",
        argument_index=1,
    )


def _target_data_output_request(
    command,
    rule_identity,
    *,
    section="ACTION",
    expression_index=0,
):
    request = GoalSlotRequest(
        StorageRequestId(
            SemanticId("native.duc", rule_identity),
            command,
        ),
        role=GoalRole.NATIVE_OUTPUT,
    )
    return NativeDucOutputRequest(
        rule_identity=rule_identity,
        section=section,
        expression_index=expression_index,
        request=request,
        command=command,
        argument_index=1,
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

    def test_registry_accepts_group_size_goal_slot_output_request(self):
        from Compiler.primitives import default_de_registry

        registry = default_de_registry()
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="group-size-output",
                    order=1,
                    facts=(_expr("(true)", "true"),),
                    actions=(
                        _expr(
                            "(up-get-group-size c: 3 41)",
                            "up-get-group-size",
                            "c:",
                            "3",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _group_size_output_request(),
            ),
        )

        registry.validate_duc_plan(plan)

    def test_registry_accepts_target_data_goal_outputs(self):
        registry = default_de_registry()
        for command, rule_identity, source in (
            (
                "up-get-object-data",
                "object-data-output",
                "(up-get-object-data 38 41)",
            ),
            (
                "up-get-object-target-data",
                "object-target-data-output",
                "(up-get-object-target-data 38 41)",
            ),
        ):
            plan = NativeDucPlan(
                rules=(
                    NativeDucRule(
                        identity=rule_identity,
                        order=1,
                        facts=(_expr("(true)", "true"),),
                        actions=(
                            _expr(source, command, "38", "41"),
                        ),
                    ),
                ),
                output_requests=(
                    _target_data_output_request(command, rule_identity),
                ),
            )
            registry.validate_duc_plan(plan)

    def test_registry_accepts_point_goalspan_output_request(self):
        registry = default_de_registry()
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="point-output",
                    order=1,
                    facts=(_expr("(true)", "true"),),
                    actions=(
                        _expr(
                            "(up-get-point position-center 41)",
                            "up-get-point",
                            "position-center",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _point_output_request(),
            ),
        )

        registry.validate_duc_plan(plan)

    def test_registry_accepts_cost_delta_goalspan_output_request(self):
        registry = default_de_registry()
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="cost-delta-output",
                    order=1,
                    facts=(_expr("(true)", "true"),),
                    actions=(
                        _expr(
                            "(up-get-cost-delta 41)",
                            "up-get-cost-delta",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _cost_delta_output_request(),
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

    def test_group_size_duc_command_is_executable_safe(self):
        binding = self.binder.bind_duc_command("up-get-group-size")
        self.assertEqual(binding.command, "up-get-group-size")
        self.assertEqual(binding.native_kind, "Action")
        self.assertEqual(binding.parameter_count, 3)
        self.assertEqual(binding.support_state.value, "executable-safe")

    def test_cost_delta_duc_command_is_executable_safe(self):
        binding = self.binder.bind_duc_command("up-get-cost-delta")
        self.assertEqual(binding.command, "up-get-cost-delta")
        self.assertEqual(binding.native_kind, "Action")
        self.assertEqual(binding.parameter_count, 1)
        self.assertEqual(binding.support_state.value, "executable-safe")

    def test_point_duc_command_is_executable_safe(self):
        binding = self.binder.bind_duc_command("up-get-point")
        self.assertEqual(binding.command, "up-get-point")
        self.assertEqual(binding.native_kind, "Action")
        self.assertEqual(binding.parameter_count, 2)
        self.assertEqual(binding.support_state.value, "executable-safe")

    def test_target_data_output_commands_are_executable_safe(self):
        for command in ("up-get-object-data", "up-get-object-target-data"):
            binding = self.binder.bind_duc_command(command)
            self.assertEqual(binding.command, command)
            self.assertEqual(binding.native_kind, "Fact/Action")
            self.assertEqual(binding.parameter_count, 2)
            self.assertEqual(binding.support_state.value, "executable-safe")


class NativeDucEmissionFixtureTests(unittest.TestCase):
    def test_compile_allocates_and_emits_target_data_goal_outputs(self):
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        for command, rule_identity, source_text in (
            (
                "up-get-object-data",
                "object-data-output",
                "(up-get-object-data 38 41)",
            ),
            (
                "up-get-object-target-data",
                "object-target-data-output",
                "(up-get-object-target-data 38 41)",
            ),
        ):
            plan = NativeDucPlan(
                rules=(
                    NativeDucRule(
                        identity=rule_identity,
                        order=100,
                        facts=(_expr("(true)", "true"),),
                        actions=(
                            _expr(source_text, command, "38", "41"),
                        ),
                    ),
                ),
                output_requests=(
                    _target_data_output_request(command, rule_identity),
                ),
            )
            artifact = compile_source(source, duc_plan=plan)
            self.assertIn(
                f"({command} 38 42)",
                artifact,
            )
            self.assertNotIn(
                f"({command} 38 41)",
                artifact,
            )

    def test_compile_allocates_and_emits_bound_point_goalspan(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="point-output",
                    order=100,
                    facts=(_expr("(true)", "true"),),
                    actions=(
                        _expr(
                            "(up-get-point position-center 41)",
                            "up-get-point",
                            "position-center",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _point_output_request(),
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
        self.assertIn("(up-get-point position-center 43)", artifact)
        self.assertNotIn("(up-get-point position-center 41)", artifact)

    def test_compile_allocates_and_emits_bound_cost_delta_goalspan(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="cost-delta-output",
                    order=100,
                    facts=(_expr("(true)", "true"),),
                    actions=(
                        _expr(
                            "(up-get-cost-delta 41)",
                            "up-get-cost-delta",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _cost_delta_output_request(),
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
        self.assertIn("(up-get-cost-delta 43)", artifact)
        self.assertNotIn("(up-get-cost-delta 41)", artifact)

    def test_compile_allocates_and_emits_bound_group_size_goal_slot(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="group-size-output",
                    order=100,
                    facts=(
                        _expr("(true)", "true"),
                    ),
                    actions=(
                        _expr(
                            "(up-get-group-size c: 3 41)",
                            "up-get-group-size",
                            "c:",
                            "3",
                            "41",
                        ),
                    ),
                ),
            ),
            output_requests=(
                _group_size_output_request(),
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
        self.assertIn("(up-get-group-size c: 3 42)", artifact)
        self.assertNotIn("(up-get-group-size c: 3 41)", artifact)

    def test_compile_allocates_and_emits_bound_search_state_goalspan(self):
        plan = NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="search-state-output",
                    order=100,
                    facts=(
                        _expr("(true)", "true"),
                    ),
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
