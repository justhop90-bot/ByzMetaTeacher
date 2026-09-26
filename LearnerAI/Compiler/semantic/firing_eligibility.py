"""Static firing-eligibility analysis for effective .per rules.

This layer combines guard proof with already-modeled demand state and completion
contracts. It does not simulate the engine and never claims that a rule fired.
"""

from __future__ import annotations

from enum import Enum

from ..ast import Expression
from ..ir import CompletionWitnessContract, WitnessEvidenceKind
from ..ir.strategy_runtime import StrategicDemandRuntimeState
from .guard_satisfiability import GuardSatisfiability
from .rule_execution import EffectiveRule, RulePassBehavior


class FiringEligibility(str, Enum):
    NEVER_ELIGIBLE = "NEVER_ELIGIBLE"
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    FIRST_PASS_ELIGIBLE = "FIRST_PASS_ELIGIBLE"
    RECURRENTLY_ELIGIBLE = "RECURRENTLY_ELIGIBLE"


def _completion_witness_is_valid(
    witness: CompletionWitnessContract | None,
) -> bool:
    if not isinstance(witness, CompletionWitnessContract):
        return False
    if witness.evidence_kind is not WitnessEvidenceKind.WORLD_STATE:
        return False
    if not isinstance(witness.primitive, str) or not witness.primitive:
        return False
    if not isinstance(witness.expression, Expression):
        return False
    if witness.source_order < 0 or witness.issuance_source_order < 0:
        return False
    if witness.source_order >= witness.issuance_source_order:
        return False
    return True


def analyze_firing_eligibility(
    rule: EffectiveRule,
    guard_satisfiability: GuardSatisfiability,
    *,
    runtime_demand_state: StrategicDemandRuntimeState | None = None,
    completion_witness: CompletionWitnessContract | None = None,
) -> FiringEligibility:
    """Classify whether a rule is statically eligible to fire.

    Guard proof remains the first gate. A demand-bound rule must also be
    strategically live and have a structurally valid world-state completion
    witness. The witness establishes a completion path; it does not establish
    that completion has already occurred.
    """
    if not isinstance(rule, EffectiveRule):
        raise TypeError("rule must be an EffectiveRule")
    if not isinstance(guard_satisfiability, GuardSatisfiability):
        raise TypeError(
            "guard_satisfiability must be a GuardSatisfiability"
        )
    if runtime_demand_state is not None and not isinstance(
        runtime_demand_state,
        StrategicDemandRuntimeState,
    ):
        raise TypeError(
            "runtime_demand_state must be a StrategicDemandRuntimeState or None"
        )

    if guard_satisfiability is GuardSatisfiability.UNSATISFIABLE:
        return FiringEligibility.NEVER_ELIGIBLE

    if runtime_demand_state in {
        StrategicDemandRuntimeState.STRATEGIC_INACTIVE,
        StrategicDemandRuntimeState.STRATEGIC_INVALIDATED,
        StrategicDemandRuntimeState.STRATEGIC_COMPLETE,
    }:
        return FiringEligibility.NEVER_ELIGIBLE

    demand_bound = runtime_demand_state is not None
    if demand_bound and not _completion_witness_is_valid(completion_witness):
        return FiringEligibility.NEVER_ELIGIBLE

    if guard_satisfiability is GuardSatisfiability.UNKNOWN:
        return FiringEligibility.RUNTIME_DEPENDENT

    if runtime_demand_state is StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED:
        return FiringEligibility.RUNTIME_DEPENDENT

    if rule.pass_behavior is RulePassBehavior.ONE_SHOT:
        return FiringEligibility.FIRST_PASS_ELIGIBLE

    if rule.pass_behavior is RulePassBehavior.RECURRENT:
        return FiringEligibility.RECURRENTLY_ELIGIBLE

    raise ValueError(
        f"unsupported rule pass behavior '{rule.pass_behavior}'"
    )


__all__ = [
    "FiringEligibility",
    "analyze_firing_eligibility",
]
