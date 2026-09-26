import unittest

from Compiler.ast import SourceLocation
from Compiler.ir import (
    CompletionWitnessContract,
    LifecycleState,
    SemanticId,
    WitnessEvidenceKind,
)
from Compiler.ir.strategy_runtime import StrategicDemandRuntimeState
from Compiler.semantic.analyzer import parse_expression
from Compiler.semantic.firing_eligibility import (
    FiringEligibility,
    analyze_firing_eligibility,
)
from Compiler.semantic.guard_satisfiability import GuardSatisfiability
from Compiler.semantic.rule_execution import (
    EffectiveRule,
    RulePassBehavior,
)


class FiringEligibilityTests(unittest.TestCase):
    def _rule(self, behavior=RulePassBehavior.RECURRENT):
        return EffectiveRule(
            rule_order=1,
            source_location=SourceLocation(1, 1, "<test>"),
            source_slice_ordinal=0,
            instance_id="test",
            facts=(parse_expression("(true)", SourceLocation(1, 1, "<test>")),),
            actions=(),
            pass_behavior=behavior,
            disable_self_action_index=0 if behavior is RulePassBehavior.ONE_SHOT else None,
        )

    def _witness(self, *, evidence_kind=WitnessEvidenceKind.WORLD_STATE,
                 source_order=1, issuance_source_order=3):
        return CompletionWitnessContract(
            identity=SemanticId("<test>", "demand"),
            evidence_kind=evidence_kind,
            primitive="building-type-count-total",
            expression=parse_expression("(true)", SourceLocation(2, 1, "<test>")),
            establishes=SemanticId("<test>", "demand"),
            source_order=source_order,
            issuance_source_order=issuance_source_order,
            location=SourceLocation(2, 1, "<test>"),
        )

    def test_recurrent_rule_with_satisfiable_guard_and_executable_demand_is_recurrently_eligible(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.RECURRENTLY_ELIGIBLE)

    def test_one_shot_rule_with_satisfiable_guard_is_first_pass_eligible(self):
        result = analyze_firing_eligibility(
            self._rule(RulePassBehavior.ONE_SHOT),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.FIRST_PASS_ELIGIBLE)

    def test_unknown_guard_remains_runtime_dependent(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.UNKNOWN,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.RUNTIME_DEPENDENT)

    def test_unsatisfiable_guard_is_never_eligible_even_with_active_demand(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.UNSATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.NEVER_ELIGIBLE)

    def test_inactive_invalidated_and_complete_demands_cannot_make_rule_eligible(self):
        for state in (
            StrategicDemandRuntimeState.STRATEGIC_INACTIVE,
            StrategicDemandRuntimeState.STRATEGIC_INVALIDATED,
            StrategicDemandRuntimeState.STRATEGIC_COMPLETE,
        ):
            with self.subTest(state=state):
                result = analyze_firing_eligibility(
                    self._rule(),
                    GuardSatisfiability.SATISFIABLE,
                    runtime_demand_state=state,
                    completion_witness=self._witness(),
                )
                self.assertIs(result, FiringEligibility.NEVER_ELIGIBLE)

    def test_blocked_demand_is_runtime_dependent_not_static_failure(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.RUNTIME_DEPENDENT)

    def test_missing_completion_witness_blocks_demand_bound_firing(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=None,
        )
        self.assertIs(result, FiringEligibility.NEVER_ELIGIBLE)

    def test_invalid_completion_witness_blocks_demand_bound_firing(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(
                evidence_kind=object(),  # deliberately invalid contract fixture
            ),
        )
        self.assertIs(result, FiringEligibility.NEVER_ELIGIBLE)

    def test_witness_contract_does_not_prove_current_completion(self):
        result = analyze_firing_eligibility(
            self._rule(),
            GuardSatisfiability.SATISFIABLE,
            runtime_demand_state=StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            completion_witness=self._witness(),
        )
        self.assertIs(result, FiringEligibility.RECURRENTLY_ELIGIBLE)

    def test_generic_rule_without_runtime_demand_retains_guard_and_pass_semantics(self):
        self.assertIs(
            analyze_firing_eligibility(
                self._rule(),
                GuardSatisfiability.SATISFIABLE,
            ),
            FiringEligibility.RECURRENTLY_ELIGIBLE,
        )
        self.assertIs(
            analyze_firing_eligibility(
                self._rule(RulePassBehavior.ONE_SHOT),
                GuardSatisfiability.SATISFIABLE,
            ),
            FiringEligibility.FIRST_PASS_ELIGIBLE,
        )


if __name__ == "__main__":
    unittest.main()
