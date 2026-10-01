"""Phase 3 (ROADMAP): attack target proof revalidation on promotion.

Slice: a DUC_TARGETED promotion (advance to PREPARE/ASSEMBLE/ATTACK/
PRESS/REINFORCE) revalidates the stored target proof when the caller
holds live search generations. Attack target references are frozen
snapshots: the DUC layer mints new state per mutation/reset/filter
change, so a stored VALID ref can outlive its proof. The pinned
source_list_generation / source_filter_generation exist to catch that
drift; nothing read them until now.

Hard invariants pinned here:
- drift or an unaccepted snapshot status fails promotion fail-closed;
- neither failure claims target death (liveness stays RUNTIME_DEPENDENT;
  death needs an independent world witness);
- RETARGET stays open despite drift (it exists to fix drift), as do
  REASSESS (recovery routing), READY (resting), and RETREAT;
- targetless PREPARE still constructs (identity-recovery staging);
- ATTACK_NOW never consults DUC lineage (target-optional by design).
"""
import unittest

from Compiler.ir.attack import (
    AttackExecution,
    AttackExecutionMode,
    AttackExecutionState,
    AttackReassessment,
    AttackTargetRef,
    revalidate_attack_target_proof,
)
from Compiler.ir.duc import (
    DucObjectLiveness,
    DucTargetKind,
    DucTargetProof,
    DucTargetState,
    DucTargetStatus,
)
from Compiler.ir.model import SemanticId
from Compiler.ir.strategy_runtime import ReassessmentReason


def _target(
    *,
    validity=DucTargetStatus.VALID,
    list_generation=5,
    filter_generation=2,
):
    return DucTargetState(
        kind=DucTargetKind.OBJECT,
        generation=1,
        validity=validity,
        proof=DucTargetProof.CURRENT_PASS_PROOF,
        source_list_generation=list_generation,
        source_filter_generation=filter_generation,
    )


def _execution(*, state=AttackExecutionState.READY, target=None):
    return AttackExecution(
        identity=SemanticId("test", "duc-attempt"),
        objective=SemanticId("test", "war-objective"),
        state=state,
        mode=AttackExecutionMode.DUC_TARGETED,
        target=(
            AttackTargetRef.from_duc(target)
            if target is not None
            else None
        ),
    )


def _reassessment():
    return AttackReassessment(
        reasons=(ReassessmentReason.CAPABILITY_LOSS,),
    )


class AttackTargetRevalidationTests(unittest.TestCase):
    def test_list_drift_blocks_prepare_promotion(self):
        execution = _execution(target=_target())
        with self.assertRaisesRegex(ValueError, "proof is stale"):
            execution.advance(
                AttackExecutionState.PREPARE,
                reason="prepare assault",
                current_list_generation=6,
                current_filter_generation=2,
            )

    def test_filter_drift_blocks_prepare_promotion(self):
        execution = _execution(target=_target())
        with self.assertRaisesRegex(ValueError, "filter generation 2 != current"):
            execution.advance(
                AttackExecutionState.PREPARE,
                reason="prepare assault",
                current_list_generation=5,
                current_filter_generation=3,
            )

    def test_drift_message_claims_no_death(self):
        execution = _execution(target=_target())
        with self.assertRaisesRegex(ValueError, "liveness remains unknown") as raised:
            execution.advance(
                AttackExecutionState.PREPARE,
                reason="prepare assault",
                current_list_generation=6,
                current_filter_generation=2,
            )
        self.assertNotIn("dead", str(raised.exception).lower())
        self.assertNotIn("death", str(raised.exception).lower())
        self.assertNotIn("destroyed", str(raised.exception).lower())
        # The stored liveness field is untouched by the refusal.
        self.assertIs(
            execution.target.target.liveness,
            DucObjectLiveness.RUNTIME_DEPENDENT,
        )

    def test_stale_snapshot_blocks_prepare_without_live_state(self):
        execution = _execution(
            target=_target(validity=DucTargetStatus.STALE)
        )
        with self.assertRaisesRegex(ValueError, "proof is invalid"):
            execution.advance(
                AttackExecutionState.PREPARE,
                reason="prepare assault",
            )

    def test_matching_generations_promote_through_assemble(self):
        execution = _execution(target=_target())
        prepared = execution.advance(
            AttackExecutionState.PREPARE,
            reason="prepare assault",
            current_list_generation=5,
            current_filter_generation=2,
        )
        self.assertEqual(prepared.state, AttackExecutionState.PREPARE)
        self.assertIs(prepared.previous_state, AttackExecutionState.READY)
        assembled = prepared.advance(
            AttackExecutionState.ASSEMBLE,
            reason="assemble force",
            current_list_generation=5,
            current_filter_generation=2,
        )
        self.assertEqual(assembled.state, AttackExecutionState.ASSEMBLE)

    def test_ref_without_lineage_skips_generation_check(self):
        direct = DucTargetState(
            kind=DucTargetKind.OBJECT,
            generation=1,
            validity=DucTargetStatus.UNKNOWN,
            proof=DucTargetProof.NATIVE_ID_PROOF,
        )
        ref = AttackTargetRef(
            direct, required_validity=(DucTargetStatus.UNKNOWN,)
        )
        execution = _execution(target=None)
        execution = AttackExecution(
            identity=execution.identity,
            objective=execution.objective,
            state=execution.state,
            mode=execution.mode,
            target=ref,
        )
        prepared = execution.advance(
            AttackExecutionState.PREPARE,
            reason="prepare assault",
            current_list_generation=9,
            current_filter_generation=9,
        )
        self.assertEqual(prepared.state, AttackExecutionState.PREPARE)

    def test_missing_live_state_preserves_snapshot_behavior(self):
        execution = _execution(target=_target())
        prepared = execution.advance(
            AttackExecutionState.PREPARE,
            reason="prepare assault",
        )
        self.assertEqual(prepared.state, AttackExecutionState.PREPARE)

    def test_targetless_prepare_still_constructs_for_recovery(self):
        execution = _execution(target=None)
        prepared = execution.advance(
            AttackExecutionState.PREPARE,
            reason="stage reacquisition",
            current_list_generation=7,
            current_filter_generation=1,
        )
        self.assertEqual(prepared.state, AttackExecutionState.PREPARE)
        self.assertIsNone(prepared.target)

    def test_retarget_stays_open_despite_drift(self):
        execution = _execution(
            state=AttackExecutionState.PREPARE, target=_target()
        )
        retargeted = execution.advance(
            AttackExecutionState.RETARGET,
            reason="reacquire drifting target",
            current_list_generation=6,
            current_filter_generation=2,
        )
        self.assertEqual(retargeted.state, AttackExecutionState.RETARGET)

    def test_reassess_and_retreat_stay_open_despite_drift(self):
        execution = _execution(
            state=AttackExecutionState.PREPARE, target=_target()
        )
        reassessed = execution.advance(
            AttackExecutionState.REASSESS,
            reason="reassess drifting target",
            reassessment=_reassessment(),
            current_list_generation=6,
            current_filter_generation=2,
        )
        self.assertEqual(reassessed.state, AttackExecutionState.REASSESS)
        retreated = execution.advance(
            AttackExecutionState.RETREAT,
            reason="withdraw from drifting target",
            current_list_generation=6,
            current_filter_generation=2,
        )
        self.assertEqual(retreated.state, AttackExecutionState.RETREAT)

    def test_attack_now_ignores_generation_drift(self):
        execution = AttackExecution(
            identity=SemanticId("test", "attack-now"),
            objective=SemanticId("test", "break-production"),
            state=AttackExecutionState.PREPARE,
            mode=AttackExecutionMode.ATTACK_NOW,
            target=AttackTargetRef.from_duc(_target()),
        )
        assembled = execution.advance(
            AttackExecutionState.ASSEMBLE,
            reason="assemble now",
            current_list_generation=6,
            current_filter_generation=2,
        )
        self.assertEqual(assembled.state, AttackExecutionState.ASSEMBLE)

    def test_pure_function_accepts_current_proof(self):
        ref = AttackTargetRef.from_duc(_target())
        self.assertIsNone(
            revalidate_attack_target_proof(
                ref,
                current_list_generation=5,
                current_filter_generation=2,
            )
        )
        self.assertIsNone(revalidate_attack_target_proof(None))
        self.assertIsNone(revalidate_attack_target_proof(ref))

    def test_negative_live_generations_rejected(self):
        execution = _execution(target=_target())
        with self.assertRaisesRegex(ValueError, "non-negative"):
            execution.advance(
                AttackExecutionState.PREPARE,
                reason="prepare assault",
                current_list_generation=-1,
            )


if __name__ == "__main__":
    unittest.main()
