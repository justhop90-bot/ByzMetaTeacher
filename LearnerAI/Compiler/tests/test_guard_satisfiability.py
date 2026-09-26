import unittest

from Compiler.semantic.fact_registry import FactSemanticAdapter, NativeFactRegistry
from Compiler.semantic.fact_values import (
    CanonicalEnum,
    StaticTruth,
    CanonicalizationContext,
)
from Compiler.semantic.guard_satisfiability import (
    GuardSatisfiability,
    analyze_guard,
)
from Compiler.semantic.analyzer import parse_expression
from Compiler.primitives.native_hygiene import (
    AIRefProvenance,
    ConfidenceBasis,
    ConfidenceLevel,
    EvidenceKind,
)


class GuardSatisfiabilityTests(unittest.TestCase):
    def _prov(self, name):
        return (
            AIRefProvenance(
                evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                confidence=ConfidenceLevel.HIGH,
                confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                citation_id=f"test://guard/{name}",
            ),
        )

    def _registry(self, *, truth=StaticTruth.UNKNOWN):
        adapter = FactSemanticAdapter(
            native_command="fixture-fact",
            semantic_id="fixture.fact",
            role="OBSERVATION",
            parameter_contexts=(
                CanonicalizationContext.enum(
                    parameter_name="State",
                    domain="STATE",
                    members=("TRUE", "FALSE"),
                ),
            ),
            provenance=self._prov("adapter"),
            static_truth_evaluator=lambda fact: truth,
        )
        return NativeFactRegistry(
            adapters=(adapter,),
            source_blob_sha="test://guard-registry",
        )

    def test_literal_true_and_false_are_classified(self):
        registry = self._registry()
        self.assertIs(
            analyze_guard(parse_expression("(true)"), registry),
            GuardSatisfiability.SATISFIABLE,
        )
        self.assertIs(
            analyze_guard(parse_expression("(false)"), registry),
            GuardSatisfiability.UNSATISFIABLE,
        )

    def test_unknown_native_fact_is_runtime_dependent(self):
        expr = parse_expression("(fixture-fact TRUE)")
        registry = self._registry(truth=StaticTruth.UNKNOWN)
        self.assertIs(
            analyze_guard(expr, registry),
            GuardSatisfiability.UNKNOWN,
        )

    def test_native_fact_static_truth_is_observed_through_adapter(self):
        expr = parse_expression("(fixture-fact TRUE)")
        self.assertIs(
            analyze_guard(expr, self._registry(truth=StaticTruth.TRUE)),
            GuardSatisfiability.SATISFIABLE,
        )
        self.assertIs(
            analyze_guard(expr, self._registry(truth=StaticTruth.FALSE)),
            GuardSatisfiability.UNSATISFIABLE,
        )

    def test_not_inverts_static_status(self):
        registry = self._registry(truth=StaticTruth.TRUE)
        self.assertIs(
            analyze_guard(parse_expression("(not (fixture-fact TRUE))"), registry),
            GuardSatisfiability.UNSATISFIABLE,
        )
        registry = self._registry(truth=StaticTruth.FALSE)
        self.assertIs(
            analyze_guard(parse_expression("(not (fixture-fact TRUE))"), registry),
            GuardSatisfiability.SATISFIABLE,
        )

    def test_and_short_circuits_provable_contradiction(self):
        registry = self._registry(truth=StaticTruth.UNKNOWN)
        self.assertIs(
            analyze_guard(
                parse_expression("(and (false) (fixture-fact TRUE))"),
                registry,
            ),
            GuardSatisfiability.UNSATISFIABLE,
        )

    def test_or_short_circuits_provable_satisfaction(self):
        registry = self._registry(truth=StaticTruth.UNKNOWN)
        self.assertIs(
            analyze_guard(
                parse_expression("(or (true) (fixture-fact TRUE))"),
                registry,
            ),
            GuardSatisfiability.SATISFIABLE,
        )

    def test_unknown_is_preserved_when_no_static_proof_exists(self):
        registry = self._registry(truth=StaticTruth.UNKNOWN)
        for operator in ("and", "or", "xor", "xnor", "nand", "nor"):
            with self.subTest(operator=operator):
                expr = parse_expression(
                    f"({operator} (fixture-fact TRUE) (fixture-fact FALSE))"
                )
                self.assertIs(
                    analyze_guard(expr, registry),
                    GuardSatisfiability.UNKNOWN,
                )

    def test_static_boolean_algebra_handles_xor_xnor_nand_nor(self):
        registry_true = self._registry(truth=StaticTruth.TRUE)
        registry_false = self._registry(truth=StaticTruth.FALSE)

        self.assertIs(
            analyze_guard(
                parse_expression("(xor (true) (fixture-fact TRUE))"),
                registry_true,
            ),
            GuardSatisfiability.UNSATISFIABLE,
        )
        self.assertIs(
            analyze_guard(
                parse_expression("(xnor (true) (fixture-fact TRUE))"),
                registry_false,
            ),
            GuardSatisfiability.UNSATISFIABLE,
        )
        self.assertIs(
            analyze_guard(
                parse_expression("(nand (true) (fixture-fact TRUE))"),
                registry_true,
            ),
            GuardSatisfiability.UNSATISFIABLE,
        )
        self.assertIs(
            analyze_guard(
                parse_expression("(nor (false) (fixture-fact TRUE))"),
                registry_true,
            ),
            GuardSatisfiability.UNSATISFIABLE,
        )

    def test_unresolved_native_arguments_fail_to_unknown_not_false(self):
        registry = self._registry(truth=StaticTruth.TRUE)
        expr = parse_expression("(fixture-fact MAYBE)")
        self.assertIs(
            analyze_guard(expr, registry),
            GuardSatisfiability.UNKNOWN,
        )

    def test_exact_structural_negation_is_provable_without_runtime_state(self):
        registry = self._registry()
        expr = parse_expression(
            "(and (fixture-fact TRUE) (not (fixture-fact TRUE)))"
        )
        self.assertIs(
            analyze_guard(expr, registry),
            GuardSatisfiability.UNSATISFIABLE,
        )


if __name__ == "__main__":
    unittest.main()
