import unittest

from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)
from Compiler.semantic.fact_evaluation import evaluate_static_truth
from Compiler.semantic.fact_registry import FactSemanticAdapter
from Compiler.semantic.fact_values import (
    CanonicalEnum,
    CanonicalizationContext,
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

    def _fact(self, age="CASTLE", domain=None):
        return NormalizedFact(
            semantic_id="observation.age.current",
            canonical_args=(CanonicalEnum("AGE", age),),
            provenance=self._provenance("fact"),
            domain=domain,
        )

    def _adapter(self, result):
        return FactSemanticAdapter(
            native_command="current-age",
            semantic_id="observation.age.current",
            role="OBSERVATION",
            parameter_contexts=(
                CanonicalizationContext.enum(
                    parameter_name="Age",
                    domain="AGE",
                    members=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
                ),
            ),
            provenance=self._provenance("adapter"),
            static_truth_evaluator=lambda fact: result,
        )

    def test_static_truth_is_supplied_by_fact_adapter(self):
        fact = self._fact()
        adapter = self._adapter(StaticTruth.TRUE)

        self.assertIs(
            evaluate_static_truth(fact, adapter),
            StaticTruth.TRUE,
        )

    def test_adapter_can_prove_false_without_domain_claiming_truth(self):
        fact = self._fact()
        adapter = self._adapter(StaticTruth.FALSE)

        self.assertIs(
            evaluate_static_truth(fact, adapter),
            StaticTruth.FALSE,
        )

    def test_missing_static_truth_proof_is_unknown(self):
        adapter = FactSemanticAdapter(
            native_command="current-age",
            semantic_id="observation.age.current",
            role="OBSERVATION",
            parameter_contexts=(
                CanonicalizationContext.enum(
                    parameter_name="Age",
                    domain="AGE",
                    members=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
                ),
            ),
            provenance=self._provenance("unknown-adapter"),
        )

        self.assertIs(
            evaluate_static_truth(self._fact(), adapter),
            StaticTruth.UNKNOWN,
        )

    def test_static_evaluator_receives_the_normalized_fact(self):
        seen = []

        def evaluator(fact):
            seen.append(fact)
            self.assertEqual(fact.identity_key[0], "observation.age.current")
            self.assertEqual(fact.canonical_args[0], CanonicalEnum("AGE", "CASTLE"))
            return StaticTruth.TRUE

        adapter = self._adapter(StaticTruth.TRUE)
        adapter = type(adapter)(
            native_command=adapter.native_command,
            semantic_id=adapter.semantic_id,
            role=adapter.role,
            parameter_contexts=adapter.parameter_contexts,
            provenance=adapter.provenance,
            static_truth_evaluator=evaluator,
        )

        fact = self._fact()
        self.assertIs(evaluate_static_truth(fact, adapter), StaticTruth.TRUE)
        self.assertEqual(seen, [fact])

    def test_fact_adapter_identity_mismatch_is_rejected(self):
        fact = self._fact()
        adapter = FactSemanticAdapter(
            native_command="current-age",
            semantic_id="observation.age.other",
            role="OBSERVATION",
            parameter_contexts=(
                CanonicalizationContext.enum(
                    parameter_name="Age",
                    domain="AGE",
                    members=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
                ),
            ),
            provenance=self._provenance("mismatch"),
            static_truth_evaluator=lambda fact: StaticTruth.TRUE,
        )

        with self.assertRaisesRegex(ValueError, "semantic adapter 'observation.age.other'.*fact 'observation.age.current'"):
            evaluate_static_truth(fact, adapter)

    def test_fact_domain_legality_is_not_proposition_truth(self):
        domain = FactDomain(
            identity="AGE",
            kind=FactDomainKind.ORDERED_ENUM,
            value_type="Age",
            ordered=True,
            values=("DARK", "FEUDAL", "CASTLE", "IMPERIAL"),
            provenance=self._provenance("domain-legality"),
        )
        fact = self._fact(domain=domain)
        adapter = self._adapter(StaticTruth.UNKNOWN)

        self.assertTrue(domain.contains(fact.canonical_args[0]))
        self.assertIs(
            evaluate_static_truth(fact, adapter),
            StaticTruth.UNKNOWN,
        )

    def test_domain_identity_does_not_select_static_truth_adapter(self):
        domain = FactDomain(
            identity="RESOURCE",
            kind=FactDomainKind.RESOURCE_AMOUNT,
            value_type="int",
            non_negative=True,
            provenance=self._provenance("different-domain"),
        )
        fact = self._fact(domain=domain)
        adapter = self._adapter(StaticTruth.TRUE)

        self.assertIs(
            evaluate_static_truth(fact, adapter),
            StaticTruth.TRUE,
        )


if __name__ == "__main__":
    unittest.main()
