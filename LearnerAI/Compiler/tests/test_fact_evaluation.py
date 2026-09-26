import unittest

from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)
from Compiler.semantic.fact_evaluation import evaluate_static_truth
from Compiler.semantic.fact_values import (
    CanonicalEnum,
    FactDomain,
    FactDomainKind,
    NormalizedFact,
    StaticTruth,
)


class StaticFactEvaluationTests(unittest.TestCase):
    def _provenance(self, suffix="domain"):
        return (
            AIRefProvenance(
                evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                confidence=ConfidenceLevel.HIGH,
                confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                citation_id=f"test://evaluation/{suffix}",
            ),
        )

    def _fact(self):
        return NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=(CanonicalEnum("AGE", "CASTLE"),),
            provenance=self._provenance("fact"),
        )

    def test_explicit_invariant_true_evaluates_true(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            invariant_truth=StaticTruth.TRUE,
            provenance=self._provenance(),
        )

        self.assertIs(
            evaluate_static_truth(self._fact(), domain),
            StaticTruth.TRUE,
        )

    def test_explicit_invariant_false_evaluates_false(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            invariant_truth=StaticTruth.FALSE,
            provenance=self._provenance("false"),
        )

        self.assertIs(
            evaluate_static_truth(self._fact(), domain),
            StaticTruth.FALSE,
        )

    def test_unproven_domain_evaluates_unknown(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=self._provenance("unknown"),
        )

        self.assertIs(
            evaluate_static_truth(self._fact(), domain),
            StaticTruth.UNKNOWN,
        )

    def test_evaluation_does_not_use_canonical_argument_as_runtime_truth(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=self._provenance("argument-boundary"),
        )
        fact = NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=(CanonicalEnum("AGE", "IMPERIAL"),),
            provenance=self._provenance("argument-fact"),
        )

        self.assertIs(
            evaluate_static_truth(fact, domain),
            StaticTruth.UNKNOWN,
        )

    def test_fact_domain_mismatch_is_rejected(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=self._provenance("mismatch"),
        )

        fact = NormalizedFact(
            semantic_id="observation.resource.food",
            canonical_args=(),
            provenance=self._provenance("mismatch-fact"),
        )

        with self.assertRaisesRegex(ValueError, "does not describe fact"):
            evaluate_static_truth(fact, domain)


if __name__ == "__main__":
    unittest.main()
