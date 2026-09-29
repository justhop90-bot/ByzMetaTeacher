import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from Compiler.ast import Expression
from Compiler.ir import (
    EscrowAdmissionMode,
    EscrowConsumption,
    EscrowConsumptionMode,
    EscrowContract,
    EscrowOperation,
    EscrowOperationKind,
    EscrowRelease,
    EscrowReleaseKind,
    EscrowReserve,
    EscrowReserveKind,
    EscrowRetentionPolicy,
    SemanticId,
)
from Compiler.semantic.resource_control import (
    ResourceControlErrorCode,
    validate_escrow_contract_set,
    validate_escrow_execution,
)


class EscrowResourceControlTests(unittest.TestCase):
    def _contract(
        self,
        identity,
        owner,
        *,
        resources=("food",),
        mode=EscrowConsumptionMode.NON_ESCROW_ACTION,
    ):
        admission = (
            EscrowAdmissionMode.NORMAL_STOCKPILE_ONLY
            if mode is EscrowConsumptionMode.NON_ESCROW_ACTION
            else EscrowAdmissionMode.INCLUDE_ESCROW
        )
        return EscrowContract(
            identity=identity,
            owner=owner,
            resources=resources,
            admission_mode=admission,
            reserve=EscrowReserve(
                kind=EscrowReserveKind.SET_PERCENTAGE,
                command="set-escrow-percentage",
                percentage=50,
            ),
            release=EscrowRelease(
                kind=EscrowReleaseKind.RELEASE_TO_STOCKPILE,
                command="release-escrow",
                trigger=Expression("(always)", "always", ()),
            ),
            consumption=EscrowConsumption(
                mode=mode,
                action_primitive="research",
            ),
            retention_policy=EscrowRetentionPolicy.REQUIRE_RELEASE_OR_CONSUMPTION,
        )

    def _op(
        self,
        contract,
        owner,
        kind,
        *,
        resource="food",
        rule_order=0,
        within_rule_order=0,
        command=None,
    ):
        return EscrowOperation(
            contract_identity=contract.identity,
            owner=owner,
            kind=kind,
            resource=resource,
            command=command or {
                EscrowOperationKind.RELEASE: "release-escrow",
                EscrowOperationKind.CONSUME: "research",
                EscrowOperationKind.POLICY_RESET: "set-escrow-percentage",
            }[kind],
            rule_order=rule_order,
            within_rule_order=within_rule_order,
        )

    def test_targeted_research_release_is_explicit(self):
        demand = SemanticId("test", "research")
        operation = self._op(
            self._contract("research", demand),
            demand,
            EscrowOperationKind.RELEASE,
        )
        operation = replace(operation, target_demand=demand)
        plan = NativeEscrowReleasePlan((operation,))
        self.assertEqual(plan.operations[0].target_demand, demand)

    def test_targeted_research_release_rejects_duplicate_resource_claim(self):
        demand = SemanticId("test", "research")
        contract = self._contract("research", demand)
        first = replace(
            self._op(contract, demand, EscrowOperationKind.RELEASE, within_rule_order=0),
            target_demand=demand,
        )
        second = replace(
            self._op(contract, demand, EscrowOperationKind.RELEASE, within_rule_order=1),
            target_demand=demand,
        )
        with self.assertRaisesRegex(
            ValueError,
            "duplicate targeted native escrow release",
        ):
            NativeEscrowReleasePlan((first, second))

    def test_two_demands_cannot_own_one_escrow_resource(self):
        first = self._contract("research-a", SemanticId("test", "research-a"))
        second = self._contract("research-b", SemanticId("test", "research-b"))

        report = validate_escrow_contract_set((first, second))

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_RESOURCE_OWNER_CONFLICT,),
        )

    def test_non_escrow_consumption_without_release_is_rejected(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.CONSUME),
            ),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_RELEASE_ORDER,),
        )

    def test_policy_reset_alone_does_not_terminate_escrow(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.POLICY_RESET),
            ),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_OPEN_LOOP,),
        )

    def test_canonical_release_policy_reset_then_consume_sequence_is_valid(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.RELEASE, within_rule_order=0),
                self._op(
                    contract,
                    contract.owner,
                    EscrowOperationKind.POLICY_RESET,
                    within_rule_order=1,
                ),
                self._op(
                    contract,
                    contract.owner,
                    EscrowOperationKind.CONSUME,
                    within_rule_order=2,
                ),
            ),
        )

        self.assertTrue(report.valid)

    def test_non_escrow_consumption_requires_release_before_action(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.RELEASE, rule_order=7),
                self._op(contract, contract.owner, EscrowOperationKind.CONSUME, rule_order=7, within_rule_order=1),
            ),
        )

        self.assertTrue(report.valid)

    def test_reversed_release_and_consume_is_rejected(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.CONSUME, rule_order=7),
                self._op(contract, contract.owner, EscrowOperationKind.RELEASE, rule_order=7, within_rule_order=1),
            ),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_RELEASE_AFTER_CONSUMPTION,),
        )

    def test_escrow_aware_consumption_is_terminal_without_release(self):
        contract = self._contract(
            "research",
            SemanticId("test", "research"),
            mode=EscrowConsumptionMode.ESCROW_AWARE_ACTION,
        )

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.CONSUME),
            ),
        )

        self.assertTrue(report.valid)

    def test_consumption_after_release_is_rejected_as_stale_lifecycle(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.RELEASE, rule_order=7),
                self._op(contract, contract.owner, EscrowOperationKind.CONSUME, rule_order=8),
            ),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_POST_RELEASE_OPERATION,),
        )

    def test_policy_reset_after_release_is_cleanup_not_reacquisition(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(contract, contract.owner, EscrowOperationKind.RELEASE, rule_order=7),
                self._op(
                    contract,
                    contract.owner,
                    EscrowOperationKind.POLICY_RESET,
                    rule_order=7,
                    within_rule_order=1,
                ),
            ),
        )

        self.assertTrue(report.valid)

    def test_wrong_operation_owner_is_rejected(self):
        contract = self._contract("research", SemanticId("test", "research"))

        report = validate_escrow_execution(
            contract,
            (
                self._op(
                    contract,
                    SemanticId("test", "other"),
                    EscrowOperationKind.RELEASE,
                ),
            ),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_OPERATION_OWNER_MISMATCH,),
        )


if __name__ == "__main__":
    unittest.main()
