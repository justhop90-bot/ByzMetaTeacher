import unittest

from Compiler.ast import Expression
from Compiler.ir.native_attack import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
)
from Compiler.primitives import default_de_registry, default_native_contract_catalog
from Compiler.primitives.engine_semantics import EngineSemanticMappingStatus
from Compiler.primitives.native_binder import NativeSemanticBinder, NativeSupportState
from Compiler.primitives.native_schema import load_default_native_schema
from Compiler.semantic.native_controller import (
    NativeControlSurfaceKind,
    default_native_controller_catalog,
)


LIFECYCLE = (
    AttackLifecycleObservation.ADMISSION_REQUIRED,
    AttackLifecycleObservation.ISSUE,
    AttackLifecycleObservation.COMPLETION_UNOBSERVED,
    AttackLifecycleObservation.REASSESS_REQUIRED,
)


def _expr(source, head, *args):
    return Expression(source, head, tuple(args))


def _attack_rule(identity="attack", order=1, *, facts=(), actions=None, lifecycle=LIFECYCLE):
    return NativeAttackRule(
        identity=identity,
        order=order,
        facts=tuple(facts),
        actions=(
            _expr("(attack-now)", "attack-now")
            if actions is None
            else tuple(actions)
        ),
        lifecycle=tuple(lifecycle),
    )


class NativeAttackIrTests(unittest.TestCase):
    def test_lifecycle_observation_is_closed(self):
        self.assertEqual(
            tuple(item.value for item in AttackLifecycleObservation),
            (
                "ADMISSION_REQUIRED",
                "ISSUE",
                "COMPLETION_UNOBSERVED",
                "REASSESS_REQUIRED",
            ),
        )

    def test_rule_requires_exact_lifecycle_contract(self):
        rule = _attack_rule()
        self.assertEqual(rule.lifecycle, LIFECYCLE)

        for bad in (
            (AttackLifecycleObservation.ISSUE,),
            (
                AttackLifecycleObservation.ADMISSION_REQUIRED,
                AttackLifecycleObservation.ISSUE,
                AttackLifecycleObservation.REASSESS_REQUIRED,
            ),
            (
                AttackLifecycleObservation.ADMISSION_REQUIRED,
                AttackLifecycleObservation.ISSUE,
                AttackLifecycleObservation.COMPLETION_UNOBSERVED,
                AttackLifecycleObservation.REASSESS_REQUIRED,
                AttackLifecycleObservation.ISSUE,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "requires lifecycle"):
                _attack_rule(lifecycle=bad)

    def test_rule_rejects_invalid_shape(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            _attack_rule(identity="")

        with self.assertRaisesRegex(ValueError, "non-negative"):
            _attack_rule(order=-1)

        with self.assertRaisesRegex(TypeError, "facts/actions"):
            NativeAttackRule(
                identity="bad",
                order=1,
                facts=[],
                actions=(),
                lifecycle=LIFECYCLE,
            )

        with self.assertRaisesRegex(TypeError, "lifecycle"):
            NativeAttackRule(
                identity="bad",
                order=1,
                facts=(),
                actions=(_expr("(attack-now)", "attack-now"),),
                lifecycle=list(LIFECYCLE),
            )

        with self.assertRaisesRegex(ValueError, "requires a fact or action"):
            NativeAttackRule(
                identity="empty",
                order=1,
                facts=(),
                actions=(),
                lifecycle=LIFECYCLE,
            )

    def test_plan_requires_deterministic_order_and_unique_identities(self):
        first = _attack_rule("a", 1)
        second = _attack_rule("b", 1)
        plan = NativeAttackLifecyclePlan((first, second))
        self.assertEqual(tuple(rule.identity for rule in plan.rules), ("a", "b"))
        self.assertFalse(plan.empty)
        self.assertEqual(plan.commands, ("attack-now",))

        with self.assertRaisesRegex(ValueError, "deterministic order"):
            NativeAttackLifecyclePlan((second, first))

        with self.assertRaisesRegex(ValueError, "duplicate native attack rule identity"):
            NativeAttackLifecyclePlan((first, _attack_rule("a", 2)))

    def test_empty_plan_is_valid(self):
        plan = NativeAttackLifecyclePlan()
        self.assertTrue(plan.empty)
        self.assertEqual(plan.expressions, ())
        self.assertEqual(plan.commands, ())

    def test_mapping_is_narrow_issue_only_contract(self):
        registry = default_de_registry()
        mapping = registry._semantic_mappings.for_command("attack-now")
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(mapping.identity, "attack.execution.issue")
        self.assertIs(mapping.status, EngineSemanticMappingStatus.CONTRACTED)
        self.assertEqual(mapping.native_command, "attack-now")
        self.assertEqual(mapping.native_kind, "Action")
        self.assertIn("unobserved", mapping.completion)
        self.assertIn("no contracted native attack completion witness", mapping.completion)
        self.assertEqual(
            tuple(
                item.native_command
                for item in registry._semantic_mappings.mappings
                if item.status is EngineSemanticMappingStatus.CONTRACTED
                and item.native_command == "attack-now"
            ),
            ("attack-now",),
        )

    def test_attack_controller_remains_descriptive_ownership(self):
        catalog = default_native_controller_catalog()
        surface = catalog.resolve_surface(
            NativeControlSurfaceKind.COMMAND,
            "attack-now",
        )
        self.assertEqual(surface.controller_id, "attack-group-control")
        self.assertNotEqual(surface.status.value, "contracted")


class NativeAttackBinderTests(unittest.TestCase):
    def setUp(self):
        registry = default_de_registry()
        self.registry = registry
        self.binder = NativeSemanticBinder(
            native_registry=load_default_native_schema(),
            semantic_mappings=registry._semantic_mappings,
            native_contracts=default_native_contract_catalog(),
            adapter_lookup=registry.get,
        )

    def test_attack_now_binds_through_dedicated_path(self):
        binding = self.binder.bind_attack_command("attack-now")
        self.assertEqual(binding.command, "attack-now")
        self.assertEqual(binding.native_kind, "Action")
        self.assertEqual(binding.parameter_count, 0)
        self.assertEqual(binding.controller_id, "attack-group-control")
        self.assertIn("attack-group-control", binding.surface_identity)
        self.assertIs(
            binding.completion_state,
            AttackLifecycleObservation.COMPLETION_UNOBSERVED,
        )
        self.assertIs(binding.support_state, NativeSupportState.EXECUTABLE_SAFE)

    def test_generic_action_path_does_not_promote_attack_now(self):
        with self.assertRaises(ValueError):
            self.binder.bind("attack-now")

    def test_unknown_attack_command_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not supported by the native attack lifecycle slice"):
            self.binder.bind_attack_command("up-reset-attack-now")

    def test_nonzero_attack_now_arity_fails_closed(self):
        plan = NativeAttackLifecyclePlan(
            (
                _attack_rule(
                    actions=(
                        _expr("(attack-now 1)", "attack-now", "1"),
                    ),
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "expects exactly 0 argument"):
            self.registry.validate_attack_plan(plan)

    def test_attack_now_cannot_be_a_fact(self):
        plan = NativeAttackLifecyclePlan(
            (
                _attack_rule(
                    facts=(_expr("(attack-now)", "attack-now"),),
                    actions=(
                        _expr("(true)", "true"),
                    ),
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "Action and cannot be emitted as a Fact"):
            self.registry.validate_attack_plan(plan)

    def test_attack_plan_requires_lifecycle_before_binding(self):
        with self.assertRaisesRegex(ValueError, "requires lifecycle"):
            NativeAttackLifecyclePlan(
                (
                    NativeAttackRule(
                        identity="missing-completion",
                        order=1,
                        facts=(),
                        actions=(_expr("(attack-now)", "attack-now"),),
                        lifecycle=(
                            AttackLifecycleObservation.ADMISSION_REQUIRED,
                            AttackLifecycleObservation.ISSUE,
                        ),
                    ),
                )
            )

    def test_evidence_only_interaction_does_not_add_attack_facts(self):
        plan = NativeAttackLifecyclePlan((_attack_rule(),))
        bindings = self.binder.bind_attack_plan(plan)
        self.assertEqual(
            tuple(binding.command for binding in bindings),
            ("attack-now",),
        )
        self.assertEqual(plan.rules[0].facts, ())


class NativeAttackRegistryTests(unittest.TestCase):
    def test_plan_validation_accepts_only_contract_slice(self):
        plan = NativeAttackLifecyclePlan((_attack_rule(),))
        registry = default_de_registry()
        bindings = registry.bind_attack_plan(plan)
        self.assertEqual(tuple(item.command for item in bindings), ("attack-now",))
        registry.validate_attack_plan(plan)

    def test_attack_controller_strategic_number_is_not_promoted(self):
        plan = NativeAttackLifecyclePlan(
            (
                _attack_rule(
                    actions=(
                        _expr(
                            "(set-strategic-number sn-number-attack-groups 1)",
                            "set-strategic-number",
                            "sn-number-attack-groups",
                            "1",
                        ),
                    ),
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "not supported by the native attack lifecycle slice"):
            default_de_registry().validate_attack_plan(plan)


if __name__ == "__main__":
    unittest.main()
