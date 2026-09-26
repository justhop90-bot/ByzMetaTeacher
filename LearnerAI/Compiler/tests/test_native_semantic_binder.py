import unittest

from Compiler.primitives import default_de_registry, default_native_contract_catalog
from Compiler.primitives.engine_semantics import (
    EngineSemanticMappingStatus,
    default_engine_semantic_mapping_registry,
)
from Compiler.primitives.native_binder import NativeSemanticBinder
from Compiler.primitives.native_schema import load_default_native_schema


class NativeSemanticBinderTests(unittest.TestCase):
    def setUp(self):
        self.native = load_default_native_schema()
        self.primitives = default_de_registry()
        self.mappings = default_engine_semantic_mapping_registry()
        self.contracts = default_native_contract_catalog()
        self.binder = NativeSemanticBinder(
            native_registry=self.native,
            semantic_mappings=self.mappings,
            native_contracts=self.contracts,
            adapter_lookup=self.primitives.get,
        )

    def test_binds_native_command_to_contracted_semantics(self):
        binding = self.binder.bind("current-age")
        self.assertEqual(binding.command, "current-age")
        self.assertEqual(binding.native_kind, "Fact")
        self.assertEqual(binding.adapter_role, "OBSERVATION")
        self.assertEqual(binding.semantic_mapping_id, "observation.age.current")
        self.assertEqual(
            binding.mapping_status,
            EngineSemanticMappingStatus.CONTRACTED,
        )
        self.assertEqual(binding.support_state.value, "executable-safe")

    def test_binding_carries_engine_contract_provenance(self):
        binding = self.binder.bind("build")
        self.assertIn("build-completion-witness", binding.native_witness_ids)
        self.assertIn("lifecycle-goal-storage", binding.native_storage_use_ids)
        self.assertIn("build-action-claim-storage", binding.native_storage_use_ids)
        self.assertIn("build-pass-singleton", binding.native_pass_constraint_ids)
        self.assertTrue(binding.evidence_sources)

    def test_known_typed_command_without_adapter_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "has no semantic adapter"):
            NativeSemanticBinder(
                native_registry=type(self.native)(
                    tuple(
                        item
                        for item in self.native._items.values()
                        if item.name == "up-find-flare"
                    ),
                    source_blob_sha=self.native.source_blob_sha,
                    command_count=1,
                ),
                semantic_mappings=self.mappings,
                native_contracts=self.contracts,
                adapter_lookup=self.primitives.get,
            ).bind("up-find-flare")

    def test_evidence_only_mapping_cannot_bind(self):
        primitive = self.primitives.require("current-age")
        from dataclasses import replace
        from Compiler.primitives.engine_semantics import EngineSemanticMappingRegistry

        mapping = self.mappings.require("observation.age.current")
        evidence_only = replace(
            mapping,
            native_command=None,
            native_kind=None,
            status=EngineSemanticMappingStatus.EVIDENCE_ONLY,
        )
        registry = EngineSemanticMappingRegistry(
            tuple(
                evidence_only if item.identity == mapping.identity else item
                for item in self.mappings.mappings
            )
        )
        binder = NativeSemanticBinder(
            native_registry=self.native,
            semantic_mappings=registry,
            native_contracts=self.contracts,
            adapter_lookup=lambda name: primitive if name == "current-age" else self.primitives.get(name),
        )
        with self.assertRaisesRegex(ValueError, "evidence-only"):
            binder.bind("current-age")


if __name__ == "__main__":
    unittest.main()
