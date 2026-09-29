import unittest

from Compiler.ir import (
    EscrowOperation,
    EscrowOperationKind,
    NativeEscrowPolicyPlan,
    NativeEscrowReleasePlan,
    SemanticId,
)
from Compiler.primitives import default_de_registry
from Compiler.primitives.engine_semantics import (
    EngineSemanticMappingStatus,
    default_escrow_executable_commands,
    default_engine_semantic_mapping_registry,
)
from Compiler.primitives.native_binder import NativeSemanticBinder
from Compiler.primitives.native_schema import load_default_native_schema


class NativeEscrowReleaseTests(unittest.TestCase):
    def setUp(self):
        self.native = load_default_native_schema()
        self.registry = default_de_registry()
        self.mappings = default_engine_semantic_mapping_registry()
        self.contracts = self.registry.native_contracts
        self.binder = NativeSemanticBinder(
            native_registry=self.native,
            semantic_mappings=self.mappings,
            native_contracts=self.contracts,
            adapter_lookup=self.registry.get,
        )

    def test_set_escrow_percentage_plan_is_typed(self):
        from Compiler.ir import EscrowOperation, EscrowOperationKind

        operation = EscrowOperation(
            contract_identity="research-food-policy",
            owner=SemanticId("test", "research"),
            kind=EscrowOperationKind.POLICY_RESET,
            resource="food",
            command="set-escrow-percentage",
            percentage=50,
            rule_order=10,
        )
        plan = NativeEscrowPolicyPlan((operation,))

        self.registry.validate_escrow_policy_plan(plan)
        bindings = self.binder.bind_escrow_plan(plan)
        self.assertEqual(
            tuple(binding.command for binding in bindings),
            ("set-escrow-percentage",),
        )

    def test_percentage_mapping_is_contracted(self):
        mapping = self.mappings.for_command("set-escrow-percentage")
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(
            mapping.identity,
            "escrow.execution.set-percentage",
        )
        self.assertIs(
            mapping.status,
            EngineSemanticMappingStatus.CONTRACTED,
        )
        self.assertEqual(mapping.native_kind, "Action")

    def test_release_mapping_is_contracted(self):
        mapping = self.mappings.for_command("release-escrow")
        self.assertIsNotNone(mapping)
        assert mapping is not None
        self.assertEqual(mapping.identity, "escrow.execution.release")
        self.assertIs(mapping.status, EngineSemanticMappingStatus.CONTRACTED)
        self.assertEqual(mapping.native_kind, "Action")
        self.assertGreaterEqual(len(mapping.evidence_sources), 3)

    def test_executable_inventory_includes_release_only_once(self):
        self.assertEqual(
            default_escrow_executable_commands(),
            ("release-escrow",),
        )
        self.assertEqual(
            self.mappings.for_command("release-escrow").native_command,
            "release-escrow",
        )

    def test_percentage_policy_binds_all_resources_and_range(self):
        from Compiler.ir import EscrowOperation, EscrowOperationKind

        operations = tuple(
            EscrowOperation(
                contract_identity=f"policy-{resource}",
                owner=SemanticId("test", "research"),
                kind=EscrowOperationKind.POLICY_RESET,
                resource=resource,
                command="set-escrow-percentage",
                percentage=50,
                rule_order=index,
            )
            for index, resource in enumerate(("food", "wood", "stone", "gold"))
        )
        plan = NativeEscrowPolicyPlan(operations)
        bindings = self.binder.bind_escrow_plan(plan)
        self.assertEqual(
            tuple(binding.command for binding in bindings),
            ("set-escrow-percentage",),
        )
        binding = bindings[0]
        self.assertEqual(binding.parameter_count, 2)
        self.assertEqual(binding.integer_range, (0, 100))
        self.registry.validate_escrow_policy_plan(plan)

    def test_percentage_policy_rejects_out_of_range(self):
        from Compiler.ir import EscrowOperation, EscrowOperationKind

        with self.assertRaisesRegex(ValueError, "0..100"):
            NativeEscrowPolicyPlan(
                (
                    EscrowOperation(
                        contract_identity="bad-percentage",
                        owner=SemanticId("test", "research"),
                        kind=EscrowOperationKind.POLICY_RESET,
                        resource="food",
                        command="set-escrow-percentage",
                        percentage=101,
                        rule_order=1,
                    ),
                )
            )

    def test_release_plan_binds_all_resources_deterministically(self):
        plan = NativeEscrowReleasePlan(
            (
                EscrowOperation(
                    contract_identity="escrow-food",
                    owner=SemanticId("test", "research"),
                    kind=EscrowOperationKind.RELEASE,
                    resource="food",
                    command="release-escrow",
                    rule_order=10,
                    within_rule_order=0,
                ),
                EscrowOperation(
                    contract_identity="escrow-gold",
                    owner=SemanticId("test", "research"),
                    kind=EscrowOperationKind.RELEASE,
                    resource="gold",
                    command="release-escrow",
                    rule_order=10,
                    within_rule_order=1,
                ),
                EscrowOperation(
                    contract_identity="escrow-wood",
                    owner=SemanticId("test", "research"),
                    kind=EscrowOperationKind.RELEASE,
                    resource="wood",
                    command="release-escrow",
                    rule_order=20,
                    within_rule_order=0,
                ),
            )
        )
        bindings = self.binder.bind_escrow_plan(plan)
        self.assertEqual(
            tuple(binding.command for binding in bindings),
            ("release-escrow",),
        )
        self.registry.validate_escrow_release_plan(plan)

    def test_percentage_policy_emits_deterministically(self):
        from Compiler.compiler import compile_source

        plan = NativeEscrowPolicyPlan(
            (
                EscrowOperation(
                    contract_identity="policy-food",
                    owner=SemanticId("test", "research"),
                    kind=EscrowOperationKind.POLICY_RESET,
                    resource="food",
                    command="set-escrow-percentage",
                    percentage=50,
                    rule_order=10,
                ),
                EscrowOperation(
                    contract_identity="policy-gold",
                    owner=SemanticId("test", "research"),
                    kind=EscrowOperationKind.POLICY_RESET,
                    resource="gold",
                    command="set-escrow-percentage",
                    percentage=25,
                    rule_order=11,
                ),
            )
        )
        source = """
        demand marker {
            require (can-train spearman)
            action (train spearman)
            witness (unit-type-count spearman >= 1)
            release (unit-type-count spearman >= 1)
        }
        """
        artifact = compile_source(source, escrow_plan=plan)
        self.assertIn("(set-escrow-percentage food 50)", artifact)
        self.assertIn("(set-escrow-percentage gold 25)", artifact)
        self.assertNotIn("(release-escrow", artifact)

    def test_release_plan_rejects_non_resource_domains_at_construction(self):
        with self.assertRaisesRegex(ValueError, "unsupported native escrow release resource"):
            NativeEscrowReleasePlan(
                (
                    EscrowOperation(
                        contract_identity="bad",
                        owner=SemanticId("test", "research"),
                        kind=EscrowOperationKind.RELEASE,
                        resource="food-amount",
                        command="release-escrow",
                        rule_order=10,
                    ),
                )
            )

    def test_release_plan_rejects_wrong_native_command(self):
        with self.assertRaisesRegex(ValueError, "must use release-escrow"):
            NativeEscrowReleasePlan(
                (
                    EscrowOperation(
                        contract_identity="bad",
                        owner=SemanticId("test", "research"),
                        kind=EscrowOperationKind.RELEASE,
                        resource="food",
                        command="set-escrow-percentage",
                        rule_order=10,
                    ),
                )
            )


if __name__ == "__main__":
    unittest.main()
