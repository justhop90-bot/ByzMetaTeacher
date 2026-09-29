"""Behavioral tests for the typed AttackExecution semantic IR."""
from __future__ import annotations

import unittest

from Compiler.ast import Expression
from Compiler.ir.attack import (
    AttackCapabilityRef,
    AttackCapabilityRole,
    AttackExecution,
    AttackExecutionMode,
    AttackExecutionState,
    AttackResultDisposition,
    AttackTargetRef,
)
from Compiler.ir.capability import CapabilityId
from Compiler.ir.duc import (
    DucTargetKind,
    DucTargetProof,
    DucTargetState,
    DucTargetStatus,
)
from Compiler.ir.model import SemanticId
from Compiler.ir.native_attack import (
    AttackLifecycleObservation,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
)


def _native_plan() -> NativeAttackLifecyclePlan:
    lifecycle = (
        AttackLifecycleObservation.ADMISSION_REQUIRED,
        AttackLifecycleObservation.ISSUE,
        AttackLifecycleObservation.COMPLETION_UNOBSERVED,
        AttackLifecycleObservation.REASSESS_REQUIRED,
    )
    return NativeAttackLifecyclePlan(
        (
            NativeAttackRule(
                identity="attack",
                order=10,
                facts=(Expression("(true)", "true", ()),),
                actions=(Expression("(attack-now)", "attack-now", ()),),
                lifecycle=lifecycle,
            ),
        )
    )


def _target(
    *,
    validity: DucTargetStatus = DucTargetStatus.VALID,
    generation: int = 1,
) -> DucTargetState:
    return DucTargetState(
        kind=DucTargetKind.OBJECT,
        generation=generation,
        validity=validity,
        proof=DucTargetProof.NATIVE_ID_PROOF,
    )


def _execution(
    *,
    state: AttackExecutionState = AttackExecutionState.ATTACK,
    target: DucTargetState | None = None,
) -> AttackExecution:
    return AttackExecution(
        identity=SemanticId("test", "attack-execution"),
        objective=SemanticId("test", "break-production"),
        state=state,
        mode=AttackExecutionMode.ATTACK_NOW,
        target=AttackTargetRef(target or _target()),
        capabilities=(
            AttackCapabilityRef(
                CapabilityId("test", "standing-army"),
                AttackCapabilityRole.PRIMARY_FORCE,
            ),
            AttackCapabilityRef(
                CapabilityId("test", "enemy-target-access"),
                AttackCapabilityRole.TARGET_ACCESS,
            ),
        ),
        native_plan=_native_plan(),
    )


class AttackExecutionIRTests(unittest.TestCase):
    def test_attack_execution_binds_existing_native_plan_and_refs(self):
        execution = _execution()

        self.assertIsInstance(execution.native_plan, NativeAttackLifecyclePlan)
        self.assertEqual(execution.objective, SemanticId("test", "break-production"))
        self.assertEqual(execution.mode, AttackExecutionMode.ATTACK_NOW)
        self.assertEqual(execution.target.target.validity, DucTargetStatus.VALID)
        self.assertEqual(
            tuple(ref.role for ref in execution.capabilities),
            (
                AttackCapabilityRole.PRIMARY_FORCE,
                AttackCapabilityRole.TARGET_ACCESS,
            ),
        )

    def test_attack_now_does_not_require_a_duc_target(self):
        execution = AttackExecution(
            identity=SemanticId("test", "attack-now"),
            objective=SemanticId("test", "break-production"),
            state=AttackExecutionState.ATTACK,
            mode=AttackExecutionMode.ATTACK_NOW,
            native_plan=_native_plan(),
        )
        self.assertIsNone(execution.target)
        self.assertTrue(execution.native_executable)

    def test_attack_groups_and_town_size_attack_do_not_require_a_duc_target(self):
        for mode in (
            AttackExecutionMode.ATTACK_GROUPS,
            AttackExecutionMode.TOWN_SIZE_ATTACK,
        ):
            execution = AttackExecution(
                identity=SemanticId("test", mode.value.lower()),
                objective=SemanticId("test", "break-production"),
                state=AttackExecutionState.PREPARE,
                mode=mode,
            )
            self.assertIsNone(execution.target)
            self.assertFalse(execution.native_executable)

    def test_duc_targeted_requires_valid_target_for_execution_states(self):
        with self.assertRaisesRegex(ValueError, "requires a DUC target"):
            AttackExecution(
                identity=SemanticId("test", "duc-attack"),
                objective=SemanticId("test", "break-production"),
                state=AttackExecutionState.ATTACK,
                mode=AttackExecutionMode.DUC_TARGETED,
            )

        with self.assertRaisesRegex(ValueError, "requires a valid DUC target"):
            AttackExecution(
                identity=SemanticId("test", "duc-attack"),
                objective=SemanticId("test", "break-production"),
                state=AttackExecutionState.ATTACK,
                mode=AttackExecutionMode.DUC_TARGETED,
                target=AttackTargetRef(_target(validity=DucTargetStatus.STALE)),
                native_plan=_native_plan(),
            )

    def test_stale_target_is_allowed_while_retargeting(self):
        execution = AttackExecution(
            identity=SemanticId("test", "retarget"),
            objective=SemanticId("test", "break-production"),
            state=AttackExecutionState.RETARGET,
            mode=AttackExecutionMode.DUC_TARGETED,
            target=AttackTargetRef(_target(validity=DucTargetStatus.STALE)),
        )
        self.assertFalse(execution.target_valid)

    def test_attack_target_ref_from_duc_preserves_provenance_and_generations(self):
        target = _target()
        ref = AttackTargetRef.from_duc(target)
        self.assertEqual(ref.target, target)
        self.assertEqual(ref.source_list_generation, target.source_list_generation)
        self.assertEqual(ref.source_filter_generation, target.source_filter_generation)
        self.assertEqual(ref.provenance, target.provenance)

    def test_attack_state_requires_native_plan_for_native_execution(self):
        with self.assertRaisesRegex(ValueError, "requires a native attack plan"):
            AttackExecution(
                identity=SemanticId("test", "attack-execution"),
                objective=SemanticId("test", "break-production"),
                state=AttackExecutionState.ATTACK,
                mode=AttackExecutionMode.ATTACK_NOW,
                target=AttackTargetRef(_target()),
            )

    def test_complete_requires_explicit_completion_contract(self):
        with self.assertRaisesRegex(ValueError, "completion witness"):
            _execution(state=AttackExecutionState.COMPLETE)

    def test_result_never_counts_as_completion(self):
        execution = _execution()
        execution = execution.__class__(
            **{
                **execution.__dict__,
                "state": AttackExecutionState.PRESS,
                "result": AttackResultDisposition.DAMAGED,
            }
        )
        self.assertNotEqual(execution.result, AttackResultDisposition.UNKNOWN)
        self.assertNotEqual(execution.state, AttackExecutionState.COMPLETE)

    def test_illegal_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "illegal attack execution transition"):
            AttackExecution.validate_transition(
                AttackExecutionState.ATTACK,
                AttackExecutionState.READY,
            )

    def test_reassess_requires_an_explicit_reason(self):
        with self.assertRaisesRegex(ValueError, "reassessment"):
            _execution(state=AttackExecutionState.REASSESS)


if __name__ == "__main__":
    unittest.main()
