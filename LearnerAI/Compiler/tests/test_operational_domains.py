import unittest

from Compiler.ast import Expression
from Compiler.ir import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    NativeDucPlan,
    NativeDucRule,
    OperationalDomain,
    OperationalRecoveryStrategy,
)
from Compiler.semantic.operational_domains import (
    merge_operational_plan,
    operational_contracts_for_attack_plan,
    operational_contracts_for_duc_plan,
)
from Compiler.semantic.operational_semantics import validate_operational_semantics


class OperationalDomainAdapterTests(unittest.TestCase):
    def _expr(self, head):
        return Expression(source="(" + head + ")", head=head, args=())

    def _attack_plan(self):
        return NativeAttackLifecyclePlan(
            rules=(
                NativeAttackRule(
                    identity="attack-rule",
                    order=0,
                    facts=(self._expr("can-attack"),),
                    actions=(self._expr("attack-now"),),
                    lifecycle=(
                        AttackLifecycleObservation.ADMISSION_REQUIRED,
                        AttackLifecycleObservation.ISSUE,
                        AttackLifecycleObservation.COMPLETION_UNOBSERVED,
                        AttackLifecycleObservation.REASSESS_REQUIRED,
                    ),
                ),
            )
        )

    def _duc_plan(self):
        return NativeDucPlan(
            rules=(
                NativeDucRule(
                    identity="duc-rule",
                    order=0,
                    facts=(self._expr("up-can-search"),),
                    actions=(self._expr("up-full-reset-search"),),
                ),
            )
        )

    def test_attack_adapter_preserves_reassertion_without_completion_ack(self):
        contract = operational_contracts_for_attack_plan(self._attack_plan())[0]
        report = validate_operational_semantics(
            __import__("Compiler.ir", fromlist=["OperationalSemanticsPlan"]).OperationalSemanticsPlan(
                contracts=(contract,)
            )
        )
        self.assertTrue(report.valid)
        self.assertEqual(contract.domain, OperationalDomain.ATTACK)
        self.assertIn(
            OperationalRecoveryStrategy.REISSUE_REQUEST,
            contract.recovery.strategies,
        )

    def test_duc_adapter_requires_identity_reacquisition(self):
        contract = operational_contracts_for_duc_plan(self._duc_plan())[0]
        self.assertEqual(contract.domain, OperationalDomain.DUC)
        self.assertIn(
            OperationalRecoveryStrategy.REACQUIRE_DUC_IDENTITY,
            contract.recovery.strategies,
        )

    def test_merge_is_deterministic(self):
        plan = merge_operational_plan(
            __import__("Compiler.ir", fromlist=["OperationalSemanticsPlan"]).OperationalSemanticsPlan(),
            attack_plan=self._attack_plan(),
            duc_plan=self._duc_plan(),
        )
        self.assertEqual(
            plan.identities,
            (
                "attack:attack-rule:operational",
                "duc:duc-rule:operational",
            ),
        )


if __name__ == "__main__":
    unittest.main()
