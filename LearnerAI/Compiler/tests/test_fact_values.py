import unittest
from enum import Enum

from Compiler.ast import SourceLocation
from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)
from Compiler.semantic.fact_values import (
    CanonicalEnum,
    CanonicalIdentifier,
    CanonicalInteger,
    CanonicalKind,
    CanonicalSymbol,
    CanonicalizationContext,
    FactDomain,
    FactDomainKind,
    NormalizedFact,
    StaticTruth,
    IdentifierForm,
    canonicalize_value,
)


class ExampleAge(str, Enum):
    DARK = "DARK"
    CASTLE = "CASTLE"


class CanonicalFactValueTests(unittest.TestCase):
    def test_integer_normalization_rejects_bool_and_normalizes_decimal_text(self):
        context = CanonicalizationContext.integer(parameter_name="Value")

        self.assertEqual(
            canonicalize_value(42, context),
            CanonicalInteger(42),
        )
        self.assertEqual(
            canonicalize_value("0042", context),
            CanonicalInteger(42),
        )

        with self.assertRaisesRegex(ValueError, "boolean"):
            canonicalize_value(True, context)

    def test_enum_normalization_is_domain_scoped_and_accepts_enum_instances(self):
        context = CanonicalizationContext.enum(
            parameter_name="Age",
            domain="AGE",
            members=("DARK", "CASTLE"),
        )

        self.assertEqual(
            canonicalize_value("castle", context),
            CanonicalEnum("AGE", "CASTLE"),
        )
        self.assertEqual(
            canonicalize_value(ExampleAge.CASTLE, context),
            CanonicalEnum("AGE", "CASTLE"),
        )

        with self.assertRaisesRegex(ValueError, "not a member"):
            canonicalize_value("IMPERIAL", context)

    def test_identifier_normalization_preserves_namespace_and_reference_form(self):
        context = CanonicalizationContext.identifier(
            parameter_name="BuildingId",
            namespace="BUILDING",
            accepted_forms=(
                IdentifierForm.NAME,
                IdentifierForm.NUMERIC_ID,
                IdentifierForm.CLASS,
            ),
            names=("castle",),
            classes=("building-class",),
        )

        self.assertEqual(
            canonicalize_value(109, context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.NUMERIC_ID,
                value=109,
            ),
        )
        self.assertEqual(
            canonicalize_value("castle", context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.NAME,
                value="castle",
            ),
        )
        self.assertEqual(
            canonicalize_value("building-class", context),
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.CLASS,
                value="building-class",
            ),
        )

        self.assertNotEqual(
            CanonicalIdentifier("BUILDING", IdentifierForm.NUMERIC_ID, 7),
            CanonicalIdentifier("UNIT", IdentifierForm.NUMERIC_ID, 7),
        )

    def test_symbol_normalization_preserves_symbol_namespace(self):
        context = CanonicalizationContext.symbol(
            parameter_name="Goal",
            namespace="GOAL",
        )

        self.assertEqual(
            canonicalize_value("strategy-goal", context),
            CanonicalSymbol(
                namespace="GOAL",
                name="strategy-goal",
            ),
        )

        self.assertNotEqual(
            CanonicalSymbol("GOAL", "strategy-goal"),
            CanonicalSymbol("STRATEGIC_NUMBER", "strategy-goal"),
        )


    def test_repeated_atoms_share_identity_key_but_keep_occurrence_provenance(self):
        args = (
            CanonicalIdentifier(
                namespace="BUILDING",
                form=IdentifierForm.NUMERIC_ID,
                value=109,
            ),
            CanonicalInteger(1),
        )
        first = NormalizedFact(
            semantic_id="observation.world.building-count",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://fact/building-count",
                ),
            ),
        )
        repeated = NormalizedFact(
            semantic_id="observation.world.building-count",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://fact/building-count-repeated",
                ),
            ),
        )

        self.assertEqual(first.identity_key, repeated.identity_key)
        self.assertEqual(
            first.identity_key,
            (
                "observation.world.building-count",
                args,
            ),
        )
        self.assertNotEqual(first, repeated)
        self.assertNotEqual(first.provenance, repeated.provenance)

    def test_identity_key_is_independent_of_provenance(self):
        args = (
            CanonicalEnum("AGE", "CASTLE"),
            CanonicalInteger(1),
        )
        first = NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://fact/age/root",
                ),
            ),
        )
        loaded = NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.MEDIUM,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TABLE,
                    citation_id="test://fact/age/loaded",
                ),
            ),
        )

        self.assertEqual(first.identity_key, loaded.identity_key)
        self.assertEqual(hash(first.identity_key), hash(loaded.identity_key))
        self.assertEqual(first.canonical_args, loaded.canonical_args)



    def test_fact_domain_is_an_invariant_value_space_not_runtime_truth(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://domain/age",
                ),
            ),
        )

        self.assertTrue(
            domain.contains(CanonicalEnum("AGE", "CASTLE"))
        )
        self.assertFalse(
            domain.contains(CanonicalEnum("AGE", "MYTHIC"))
        )
        self.assertEqual(StaticTruth.UNKNOWN, StaticTruth.UNKNOWN)
        self.assertNotEqual(StaticTruth.UNKNOWN, True)
        self.assertNotEqual(StaticTruth.UNKNOWN, False)

    def test_integer_fact_domain_enforces_invariant_bounds_only(self):
        domain = FactDomain(
            identity="RESOURCE_AMOUNT",
            kind=FactDomainKind.RESOURCE_AMOUNT,
            value_type="int",
            ordered=True,
            non_negative=True,
            minimum=0,
            maximum=20000,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://domain/resource",
                ),
            ),
        )

        self.assertTrue(domain.contains(CanonicalInteger(0)))
        self.assertTrue(domain.contains(CanonicalInteger(20000)))
        self.assertFalse(domain.contains(CanonicalInteger(-1)))
        self.assertFalse(domain.contains(CanonicalInteger(20001)))
        self.assertFalse(
            domain.contains(CanonicalIdentifier("UNIT", IdentifierForm.NUMERIC_ID, 7))
        )

    def test_normalized_fact_domain_does_not_change_identity_or_claim_static_truth(self):
        args = (CanonicalEnum("AGE", "CASTLE"),)
        domain_a = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://domain/age/a",
                ),
            ),
        )
        domain_b = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.MEDIUM,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TABLE,
                    citation_id="test://domain/age/b",
                ),
            ),
        )

        first = NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="test://fact/age/a",
                ),
            ),
            domain=domain_a,
        )
        second = NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=args,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.MEDIUM,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TABLE,
                    citation_id="test://fact/age/b",
                ),
            ),
            domain=domain_b,
        )

        self.assertEqual(first.identity_key, second.identity_key)
        self.assertEqual(first.domain.identity, "AGE")
        self.assertEqual(second.domain.identity, "AGE")
        self.assertEqual(StaticTruth.UNKNOWN, StaticTruth.UNKNOWN)


    def test_canonical_kind_is_explicit_for_union_members(self):
        self.assertEqual(
            CanonicalInteger(1).kind,
            CanonicalKind.INTEGER,
        )
        self.assertEqual(
            CanonicalEnum("AGE", "CASTLE").kind,
            CanonicalKind.ENUM,
        )
        self.assertEqual(
            CanonicalIdentifier("UNIT", IdentifierForm.NUMERIC_ID, 7).kind,
            CanonicalKind.IDENTIFIER,
        )
        self.assertEqual(
            CanonicalSymbol("GOAL", "x").kind,
            CanonicalKind.SYMBOL,
        )


if __name__ == "__main__":
    unittest.main()
