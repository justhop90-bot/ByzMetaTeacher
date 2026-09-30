import unittest

from Compiler.ast import Expression
from Compiler.compiler import compile_source
from Compiler.ir import (
    AttackExecution,
    AttackExecutionMode,
    AttackExecutionState,
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    NativeDucPlan,
    NativeDucRule,
    OperationalDomain,
    OperationalRecoveryStrategy,
    SemanticId,
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
                    facts=(self._expr("true"),),
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

    def _attack_execution(self):
        return AttackExecution(
            identity=SemanticId("test", "attack-attempt"),
            objective=SemanticId("test", "war-objective"),
            state=AttackExecutionState.ATTACK,
            mode=AttackExecutionMode.ATTACK_NOW,
            native_plan=self._attack_plan(),
        )

    def test_attack_execution_projects_into_operational_loop(self):
        execution = self._attack_execution()
        plan = merge_operational_plan(
            __import__("Compiler.ir", fromlist=["OperationalSemanticsPlan"]).OperationalSemanticsPlan(),
            attack_plan=execution,
        )
        contract = plan.contracts[0]
        self.assertEqual(contract.demand, execution.objective)
        self.assertEqual(contract.domain, OperationalDomain.ATTACK)
        self.assertIn(OperationalRecoveryStrategy.REISSUE_REQUEST, contract.recovery.strategies)
        self.assertIn(OperationalRecoveryStrategy.REASSESS, contract.recovery.strategies)
        self.assertEqual(contract.request.commands[0].head, "attack-now")

    def test_duc_targeted_execution_projects_identity_recovery(self):
        execution = AttackExecution(
            identity=SemanticId("test", "duc-attempt"),
            objective=SemanticId("test", "war-objective"),
            state=AttackExecutionState.PREPARE,
            mode=AttackExecutionMode.DUC_TARGETED,
        )
        plan = merge_operational_plan(
            __import__("Compiler.ir", fromlist=["OperationalSemanticsPlan"]).OperationalSemanticsPlan(),
            attack_plan=execution,
        )
        self.assertIn(
            OperationalRecoveryStrategy.REACQUIRE_DUC_IDENTITY,
            plan.contracts[0].recovery.strategies,
        )

    def test_compile_source_accepts_typed_attack_execution_on_existing_channel(self):
        source = """
        demand castle-posture {
            require (can-build castle)
            action (build castle)
            witness (building-type-count castle > 0)
            release (building-type-count castle > 0)
        }
        """
        artifact = compile_source(source, attack_plan=self._attack_execution())
        self.assertIn("; Native attack lifecycle plan", artifact)
        self.assertIn("(attack-now)", artifact)

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
