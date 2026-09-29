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

    def test_attack_state_requires_valid_target_and_native_plan(self):
        with self.assertRaisesRegex(ValueError, "requires a valid target"):
            _execution(target=_target(validity=DucTargetStatus.STALE))

        with self.assertRaisesRegex(ValueError, "requires a native attack plan"):
            AttackExecution(
                identity=SemanticId("test", "attack-execution"),
                objective=SemanticId("test", "break-production"),
                state=AttackExecutionState.ATTACK,
                mode=AttackExecutionMode.ATTACK_NOW,
                target=AttackTargetRef(_target()),
            )

    def test_illegal_transition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "illegal attack execution transition"):
            AttackExecution.validate_transition(
                AttackExecutionState.ATTACK,
                AttackExecutionState.READY,
            )

    def test_reassess_requires_an_explicit_reason(self):
        with self.assertRaisesRegex(ValueError, "reassessment"):
            _execution(state=AttackExecutionState.REASSESS)

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


if __name__ == "__main__":
    unittest.main()
