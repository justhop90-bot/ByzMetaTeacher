import unittest

from Compiler.ast import Expression
from Compiler.ir import (
    OperationalCombination,
    OperationalCondition,
    OperationalControlKind,
    OperationalControlRef,
    OperationalControlUse,
    OperationalDomain,
    OperationalEvidenceClass,
    OperationalGuard,
    OperationalLoopContract,
    OperationalObservation,
    OperationalObservationRole,
    OperationalRecovery,
    OperationalRecoveryStrategy,
    OperationalRequest,
    OperationalRequestKind,
    OperationalSemanticsPlan,
    OperationalStage,
)
from Compiler.semantic.operational_semantics import (
    OperationalDiagnosticCode,
    OperationalStatus,
    validate_operational_semantics,
)


class OperationalSemanticsIRTests(unittest.TestCase):
    def _expression(self, head: str) -> Expression:
        return Expression(source=f"({head})", head=head, args=())

    def _contract(self, *, domain=OperationalDomain.GENERIC, request_kind=OperationalRequestKind.ACTION):
        observation = OperationalObservation(
            identity="obs-admit",
            role=OperationalObservationRole.ADMISSION,
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            expression=self._expression("can-act"),
        )
        witness = OperationalObservation(
            identity="obs-witness",
            role=OperationalObservationRole.WORLD_STATE,
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            expression=self._expression("world-state"),
        )
        admission = OperationalGuard(
            identity="admit",
            conditions=(OperationalCondition("obs-admit"),),
        )
        debounce = OperationalGuard(identity="debounce", conditions=())
        retry = OperationalGuard(
            identity="retry",
            conditions=(OperationalCondition("obs-admit"),),
        )
        return OperationalLoopContract(
            identity="contract",
            domain=domain,
            demand=__import__("Compiler.ir", fromlist=["SemanticId"]).SemanticId("test", "demand"),
            observations=(observation, witness),
            observe=OperationalStage(
                identity="observe",
                observation_ids=("obs-admit",),
            ),
            admission=admission,
            request=OperationalRequest(
                identity="request",
                kind=request_kind,
                commands=(self._expression("act"),),
            ),
            debounce=debounce,
            reobserve=OperationalStage(
                identity="reobserve",
                observation_ids=("obs-witness",),
            ),
            recovery=OperationalRecovery(
                identity="recovery",
                strategies=(OperationalRecoveryStrategy.REISSUE_REQUEST,),
                retry_guard=retry,
            ),
        )

    def test_valid_contract_is_accepted(self):
        report = validate_operational_semantics(
            OperationalSemanticsPlan(contracts=(self._contract(),))
        )
        self.assertTrue(report.valid)
        self.assertFalse(report.errors)

    def test_retry_without_admission_is_rejected(self):
        contract = self._contract()
        contract = OperationalLoopContract(
            **{
                **contract.__dict__,
                "recovery": OperationalRecovery(
                    identity="recovery",
                    strategies=(OperationalRecoveryStrategy.REISSUE_REQUEST,),
                    retry_guard=None,
                ),
            }
        )
        report = validate_operational_semantics(
            OperationalSemanticsPlan(contracts=(contract,))
        )
        self.assertIn(
            OperationalDiagnosticCode.RETRY_WITHOUT_ADMISSION,
            {item.code for item in report.errors},
        )

    def test_timer_only_reobserve_is_rejected(self):
        timer = OperationalObservation(
            identity="obs-timer",
            role=OperationalObservationRole.TIMING,
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            expression=self._expression("timer-triggered"),
        )
        contract = self._contract()
        contract = OperationalLoopContract(
            **{
                **contract.__dict__,
                "observations": tuple(
                    item for item in contract.observations if item.identity != "obs-witness"
                )
                + (timer,),
                "reobserve": OperationalStage(
                    identity="reobserve",
                    observation_ids=("obs-timer",),
                ),
            }
        )
        report = validate_operational_semantics(
            OperationalSemanticsPlan(contracts=(contract,))
        )
        self.assertIn(
            OperationalDiagnosticCode.TIMER_ONLY_REOBSERVATION,
            {item.code for item in report.errors},
        )

    def test_pending_is_not_completion(self):
        pending = OperationalObservation(
            identity="obs-pending",
            role=OperationalObservationRole.DEBOUNCE,
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            expression=self._expression("up-pending-objects"),
        )
        contract = self._contract()
        contract = OperationalLoopContract(
            **{
                **contract.__dict__,
                "observations": contract.observations + (pending,),
                "debounce": OperationalGuard(
                    identity="debounce",
                    conditions=(OperationalCondition("obs-pending"),),
                ),
            }
        )
        report = validate_operational_semantics(
            OperationalSemanticsPlan(contracts=(contract,))
        )
        self.assertTrue(report.valid)

    def test_domain_request_mismatch_is_rejected(self):
        contract = self._contract(
            domain=OperationalDomain.STRATEGIC_NUMBER,
            request_kind=OperationalRequestKind.ACTION,
        )
        report = validate_operational_semantics(
            OperationalSemanticsPlan(contracts=(contract,))
        )
        self.assertIn(
            OperationalDiagnosticCode.DOMAIN_REQUEST_MISMATCH,
            {item.code for item in report.errors},
        )


if __name__ == "__main__":
    unittest.main()
