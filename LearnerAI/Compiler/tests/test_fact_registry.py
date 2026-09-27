import unittest

from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)
from Compiler.primitives.registry import default_de_registry
from Compiler.semantic.fact_registry import NativeFactRegistry
from Compiler.semantic.fact_values import (
    CanonicalEnum,
    CanonicalIdentifier,
    CanonicalInteger,
    IdentifierForm,
)


class NativeFactRegistryTests(unittest.TestCase):
    def test_default_registry_contains_all_registered_fact_primitives(self):
        registry = default_de_registry()
        facts = registry.fact_registry

        primitive_facts = tuple(
            name
            for name in registry.names()
            if registry.require(name).kind == "FACT"
        )
        self.assertEqual(facts.names(), tuple(sorted(primitive_facts)))
        self.assertIsInstance(facts, NativeFactRegistry)

    def test_default_fact_adapter_is_bound_to_engine_semantic_identity(self):
        registry = default_de_registry()
        adapter = registry.fact_registry.require("current-age")

        self.assertEqual(adapter.native_command, "current-age")
        self.assertEqual(adapter.semantic_id, "observation.age.current")
        self.assertEqual(adapter.role, "OBSERVATION")
        self.assertEqual(adapter.native_version, "AoC")
        self.assertEqual(adapter.arity, 2)
        self.assertEqual(
            registry.fact_registry.by_semantic_id(
                "observation.age.current"
            ),
            adapter,
        )

    def test_current_age_normalization_canonicalizes_operator_and_enum(self):
        fact = default_de_registry().normalize_fact(
            "current-age",
            (">=", "castle"),
        )

        self.assertEqual(
            fact.semantic_id,
            "observation.age.current",
        )
        self.assertEqual(
            fact.canonical_args,
            (
                CanonicalEnum("COMPARE_OP", ">="),
                CanonicalEnum("AGE", "CASTLE"),
            ),
        )
        self.assertEqual(
            fact.provenance[0].citation_id,
            "airef:current-age",
        )

    def test_building_fact_preserves_identifier_namespace_and_numeric_form(self):
        fact = default_de_registry().normalize_fact(
            "building-available",
            (109,),
        )

        self.assertEqual(
            fact.canonical_args,
            (
                CanonicalIdentifier(
                    namespace="BUILDING",
                    form=IdentifierForm.NUMERIC_ID,
                    value=109,
                ),
            ),
        )

    def test_unresolved_identifier_names_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "not a declared identifier"):
            default_de_registry().normalize_fact(
                "building-available",
                ("castle",),
            )

    def test_occurrence_provenance_can_override_adapter_provenance(self):
        occurrence = AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.MEDIUM,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TABLE,
            citation_id="test://native-fact/occurrence",
        )
        fact = default_de_registry().normalize_fact(
            "food-amount",
            ("==", 800),
            provenance=(occurrence,),
        )

        self.assertEqual(fact.provenance, (occurrence,))
        self.assertEqual(fact.identity_key[0], "observation.resource.food")

    def test_adapter_rejects_wrong_arity_at_the_bridge(self):
        with self.assertRaisesRegex(ValueError, "expects exactly 2 argument"):
            default_de_registry().normalize_fact(
                "food-amount",
                ("==",),
            )

    def test_two_default_fact_registries_are_structurally_deterministic(self):
        first = default_de_registry().fact_registry
        second = default_de_registry().fact_registry

        self.assertEqual(first, second)
        self.assertEqual(first.names(), tuple(sorted(first.names())))


    def test_up_compare_sn_ai_ref_goalid_parameter_is_normalized_as_sn(self):
        fact = default_de_registry().normalize_fact(
            "up-compare-sn",
            ("511", "g:>=", "1"),
        )
        self.assertEqual(
            fact.canonical_args[0],
            CanonicalIdentifier(
                namespace="STRATEGIC_NUMBER",
                form=IdentifierForm.NUMERIC_ID,
                value=511,
            ),
        )
        self.assertEqual(
            fact.canonical_args[1],
            CanonicalEnum("SN_COMPARE_OP", "g:>="),
        )
        self.assertEqual(
            fact.canonical_args[2].namespace,
            "STRATEGIC_NUMBER_COMPARE_VALUE",
        )

if __name__ == "__main__":
    unittest.main()
