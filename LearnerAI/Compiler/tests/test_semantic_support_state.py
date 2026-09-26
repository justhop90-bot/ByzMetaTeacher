import unittest

from Compiler.primitives.native_schema import (
    NativeCommandRegistry,
    NativeCommandSpec,
    NativeParameterSpec,
)
from Compiler.primitives.registry import (
    NativeSupportState,
    Primitive,
    PrimitiveRegistry,
    default_de_registry,
)


class SemanticSupportStateTests(unittest.TestCase):
    def test_default_registry_maps_every_semantic_adapter(self):
        registry = default_de_registry()
        mappings = [
            registry.require(name).engine_semantics_id
            for name in registry.names()
        ]
        self.assertEqual(len(mappings), len(set(mappings)))
        self.assertTrue(all(mappings))
        self.assertTrue(
            all(
                registry.assess_support(name).state
                is NativeSupportState.EXECUTABLE_SAFE
                for name in registry.names()
            )
        )

    def test_semantic_adapter_without_engine_mapping_is_blocked(self):
        native = NativeCommandRegistry(
            (
                NativeCommandSpec(
                    "synthetic",
                    "DE",
                    "Fact",
                    (
                        NativeParameterSpec(
                            "Value",
                            "Const",
                            "in",
                            "fixture",
                            "fixture",
                        ),
                    ),
                ),
            ),
            source_blob_sha="test",
            command_count=1,
        )
        registry = PrimitiveRegistry(
            (Primitive("synthetic", "FACT", "OBSERVATION", 1, 1),),
            native,
        )
        assessment = registry.assess_support("synthetic")
        self.assertEqual(assessment.state, NativeSupportState.UNSUPPORTED)
        self.assertEqual(
            [item.state for item in assessment.diagnostics],
            [
                NativeSupportState.NATIVE_KNOWN,
                NativeSupportState.NATIVE_TYPED,
                NativeSupportState.SEMANTICALLY_ADAPTED,
                NativeSupportState.UNSUPPORTED,
            ],
        )
        self.assertEqual(
            assessment.diagnostics[-1].code,
            "NATIVE-SUPPORT-006",
        )
        self.assertIn("engine semantic mapping", assessment.message)

    def test_evidence_only_practices_are_not_native_support_mappings(self):
        from Compiler.semantic.community_engine import (
            default_community_engine_registry,
        )

        engine = default_community_engine_registry()
        evidence_only = {
            item.identity
            for item in engine.practices
            if item.status.value == "EVIDENCE_ONLY"
        }
        mappings = {
            item.engine_semantics_id
            for item in default_de_registry()._items.values()
        }
        self.assertIn("duc.search-state-retained", evidence_only)
        self.assertIn("attack.group-state-control", evidence_only)
        self.assertNotIn("duc.search-state-retained", mappings)
        self.assertNotIn("attack.group-state-control", mappings)


if __name__ == "__main__":
    unittest.main()
