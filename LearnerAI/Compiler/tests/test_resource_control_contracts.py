import unittest

from Compiler.ast import Expression
from Compiler.ir.model import SemanticId, StorageRequestId
from Compiler.ir.resource_control import (
    EscrowAdmissionMode,
    EscrowConsumption,
    EscrowConsumptionMode,
    EscrowContract,
    EscrowRelease,
    EscrowReleaseKind,
    EscrowReserve,
    EscrowReserveKind,
    NativeArbitrationContract,
    NativeArbitrationRecovery,
    NativeArbitrationRecoveryKind,
    NativeArbitrationRelease,
    NativeArbitrationReleaseKind,
    NativeArbitrationStarvationPolicy,
    NativeControlStorage,
    ResourceControlErrorCode,
    ResourceControlValidationReport,
    TransientActionExclusionClaim,
    TransientClaimKind,
    TransientClaimScope,
    validate_resource_control_contracts,
)


def expr(source="(true)", head="true"):
    return Expression(source=source, head=head, args=())


def sid(name):
    return SemanticId("test", name)


def arbitration():
    return NativeArbitrationContract(
        identity="castle-resource-control",
        owner=sid("castle"),
        storage=StorageRequestId(sid("__control__"), "native-resource-control"),
        storage_kind=NativeControlStorage.STRATEGIC_NUMBER,
        surface_id="sn-resource-control",
        free_value=0,
        claim_value=1,
        acquisition_guard=expr(),
        release=NativeArbitrationRelease(
            kind=NativeArbitrationReleaseKind.RESET_TO_FREE,
            trigger=expr("(building-type-count castle >= 1)", "building-type-count"),
        ),
        recovery=NativeArbitrationRecovery(
            kind=NativeArbitrationRecoveryKind.RETAIN_DEMAND,
            trigger=expr(),
        ),
    )


def escrow(arbitration_identity=None):
    return EscrowContract(
        identity="castle-escrow",
        owner=sid("castle"),
        resources=("food", "wood", "stone"),
        admission_mode=EscrowAdmissionMode.INCLUDE_ESCROW,
        reserve=EscrowReserve(
            kind=EscrowReserveKind.SET_PERCENTAGE,
            command="set-escrow-percentage",
            percentage=25,
        ),
        release=EscrowRelease(
            kind=EscrowReleaseKind.RELEASE_TO_STOCKPILE,
            command="release-escrow",
            trigger=expr("(building-type-count castle >= 1)", "building-type-count"),
        ),
        consumption=EscrowConsumption(
            mode=EscrowConsumptionMode.ESCROW_AWARE_ACTION,
            action_primitive="build",
        ),
        arbitration_identity=arbitration_identity,
    )


def transient():
    return TransientActionExclusionClaim(
        identity_source_unit="test",
        identity_local_name="castle-build-pass",
        claimant=sid("castle"),
        conflict_class="BUILD_PASS_SINGLETON",
        arbitration_owner=sid("__execution_memory__"),
    )


class ResourceControlContractValidationTests(unittest.TestCase):
    def test_clean_three_domain_contracts_have_no_errors(self):
        report = validate_resource_control_contracts(
            arbitration=arbitration(),
            escrow=escrow("castle-resource-control"),
            transient=transient(),
        )

        self.assertTrue(report.valid)
        self.assertEqual(report.errors, ())

    def test_transient_claim_cannot_alias_native_arbitration_surface(self):
        claim = TransientActionExclusionClaim(
            identity_source_unit="test",
            identity_local_name="castle-build-pass",
            claimant=sid("castle"),
            conflict_class="sn-resource-control",
            arbitration_owner=sid("__execution_memory__"),
        )

        report = validate_resource_control_contracts(
            arbitration=arbitration(),
            transient=claim,
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.TRANSIENT_NATIVE_SURFACE_ALIAS,),
        )

    def test_transient_claim_cannot_alias_escrow_contract(self):
        claim = TransientActionExclusionClaim(
            identity_source_unit="test",
            identity_local_name="castle-build-pass",
            claimant=sid("castle"),
            conflict_class="castle-escrow",
            arbitration_owner=sid("__execution_memory__"),
        )

        report = validate_resource_control_contracts(
            escrow=escrow(),
            transient=claim,
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.TRANSIENT_ESCROW_ALIAS,),
        )

    def test_escrow_reference_must_resolve_to_supplied_arbitration(self):
        report = validate_resource_control_contracts(
            arbitration=arbitration(),
            escrow=escrow("different-resource-control"),
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_ARBITRATION_REFERENCE_MISMATCH,),
        )

    def test_handoff_recovery_requires_handoff_release(self):
        bad = NativeArbitrationContract(
            identity="castle-resource-control",
            owner=sid("castle"),
            storage=StorageRequestId(sid("__control__"), "native-resource-control"),
            storage_kind=NativeControlStorage.STRATEGIC_NUMBER,
            surface_id="sn-resource-control",
            free_value=0,
            claim_value=1,
            acquisition_guard=expr(),
            release=NativeArbitrationRelease(
                kind=NativeArbitrationReleaseKind.RESET_TO_FREE,
                trigger=expr(),
            ),
            recovery=NativeArbitrationRecovery(
                kind=NativeArbitrationRecoveryKind.HANDOFF_AND_RETRY,
                trigger=expr(),
            ),
        )

        report = validate_resource_control_contracts(arbitration=bad)

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ARBITRATION_HANDOFF_RECOVERY_MISMATCH,),
        )

    def test_escrow_inclusion_requires_escrow_aware_consumption(self):
        bad = EscrowContract(
            identity="castle-escrow",
            owner=sid("castle"),
            resources=("stone",),
            admission_mode=EscrowAdmissionMode.INCLUDE_ESCROW,
            reserve=EscrowReserve(
                kind=EscrowReserveKind.SET_PERCENTAGE,
                command="set-escrow-percentage",
                percentage=25,
            ),
            release=EscrowRelease(
                kind=EscrowReleaseKind.RELEASE_TO_STOCKPILE,
                command="release-escrow",
                trigger=expr(),
            ),
            consumption=EscrowConsumption(
                mode=EscrowConsumptionMode.NON_ESCROW_ACTION,
                action_primitive="build",
            ),
        )

        report = validate_resource_control_contracts(escrow=bad)

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (ResourceControlErrorCode.ESCROW_ADMISSION_CONSUMPTION_MISMATCH,),
        )

    def test_error_order_is_deterministic(self):
        claim = TransientActionExclusionClaim(
            identity_source_unit="test",
            identity_local_name="castle-build-pass",
            claimant=sid("castle"),
            conflict_class="castle-escrow",
            arbitration_owner=sid("__execution_memory__"),
        )

        report = validate_resource_control_contracts(
            arbitration=arbitration(),
            escrow=escrow("wrong"),
            transient=claim,
        )

        self.assertEqual(
            tuple(error.code for error in report.errors),
            (
                ResourceControlErrorCode.ESCROW_ARBITRATION_REFERENCE_MISMATCH,
                ResourceControlErrorCode.TRANSIENT_ESCROW_ALIAS,
            ),
        )


if __name__ == "__main__":
    unittest.main()
