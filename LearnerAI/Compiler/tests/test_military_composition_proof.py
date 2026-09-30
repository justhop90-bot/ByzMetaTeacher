import unittest
from dataclasses import replace

from Compiler.ast import Expression
from Compiler.diagnostics import DiagnosticSeverity
from Compiler.ir import (
    AttackCapabilityRef,
    AttackCompletionContract,
    AttackCapabilityRole,
    AttackExecution,
    AttackExecutionMode,
    AttackExecutionState,
    AttackTargetRef,
    CapabilityId,
    CapabilityRecoveryContract,
    CapabilityRecoveryState,
    CapabilityRecoveryStateKind,
    CompletionWitnessContract,
    GoalRole,
    GoalSlotRequest,
    LifecycleState,
    LifecycleStorage,
    MilitaryCompositionPlan,
    MilitaryCompositionProofPath,
    MilitaryCompositionUnitTarget,
    NativeAttackLifecyclePlan,
    NativeAttackRule,
    AttackLifecycleObservation,
    ProductionLifecycle,
    ProductionQueueProtection,
    ProductionTargetAdmission,
    ProductionFactDisposition,
    ResourceClaim,
    ResourceClaimId,
    ResourceKind,
    ResourceScope,
    SemanticAction,
    SemanticDemand,
    SemanticId,
    StateStorageKind,
    StorageRequestId,
)
from Compiler.ir.capability import DemandId
from Compiler.ir.duc import DucTargetKind, DucTargetProof, DucTargetState, DucTargetStatus
from Compiler.ir.model import CompletionWitnessContract
from Compiler.ir.native_attack import _REQUIRED_LIFECYCLE
from Compiler.semantic.military_composition import validate_military_composition_proof
from Compiler.ir.program import CompilerSemanticProgram


def _expr(source, head, *args):
    return Expression(source=source, head=head, args=args)


def _demand(identity, *, production=None):
    lifecycle = LifecycleStorage(
        slot=GoalSlotRequest(
            StorageRequestId(identity, "lifecycle"),
            role=GoalRole.LIFECYCLE_STATE,
        ),
        initial_state=LifecycleState.ACTIVE,
    )
    return SemanticDemand(
        identity=identity,
        lifecycle=lifecycle,
        requirements=(),
        action=SemanticAction(
            _expr("(train spearman)", "train", "spearman"),
            "military-production",
        ),
        witness=_expr("(unit-type-count spearman >= 1)", "unit-type-count", "spearman", ">=", "1"),
        release=_expr("(unit-type-count spearman >= 1)", "unit-type-count", "spearman", ">=", "1"),
        production_lifecycle=production,
        production_retry_barrier=production.retry_barrier if production else None,
    )


def _production(demand):
    barrier = GoalSlotRequest(
        StorageRequestId(demand, "production-retry-barrier"),
        role=GoalRole.EXECUTION_MEMORY,
    )
    admission = ProductionTargetAdmission(
        disposition=ProductionFactDisposition.SUPPORTED,
        primitive="can-train",
        expression=_expr("(can-train 93)", "can-train", "93"),
        native_unit_id=93,
        semantic_id="execution.train.feasibility",
    )
    queue = ProductionQueueProtection(
        disposition=ProductionFactDisposition.SUPPORTED,
        pending_fact=_expr(
            "(up-pending-objects c: 93 > 0)",
            "up-pending-objects",
            "c:",
            "93",
            ">",
            "0",
        ),
        native_unit_id=93,
    )
    return ProductionLifecycle(
        unit="spearman",
        native_unit_id=93,
        target_admission=admission,
        completion_witness=_expr(
            "(unit-type-count spearman >= 1)",
            "unit-type-count",
            "spearman",
            ">=",
            "1",
        ),
        retry_barrier=barrier,
        queue_protection=queue,
    )


def _proof():
    composition = SemanticId("test", "military-composition")
    spear = SemanticId("test", "train-spearman")
    objective = SemanticId("test", "attack-objective")

    production = _production(spear)
    production_demand = _demand(spear, production=production)
    composition_demand = _demand(composition)

    target = DucTargetState(
        kind=DucTargetKind.OBJECT,
        generation=1,
        validity=DucTargetStatus.VALID,
        proof=DucTargetProof.NATIVE_ID_PROOF,
    )
    attack_target = AttackTargetRef.from_duc(target)

    native_rule = NativeAttackRule(
        identity="military-proof-attack",
        order=10,
        facts=(_expr("(true)", "true"),),
        actions=(_expr("(attack-now)", "attack-now"),),
        lifecycle=_REQUIRED_LIFECYCLE,
    )
    witness = CompletionWitnessContract(
        identity=SemanticId("test", "attack-complete"),
        evidence_kind="WORLD_STATE",
        primitive="building-type-count",
        expression=_expr("(building-type-count castle >= 1)", "building-type-count", "castle", ">=", "1"),
        establishes=objective,
        source_order=20,
        issuance_source_order=10,
    )
    completion = AttackCompletionContract(
        witness=witness,
        objective=objective,
    )
    attack = AttackExecution(
        identity=SemanticId("test", "attack"),
        objective=objective,
        state=AttackExecutionState.ATTACK,
        mode=AttackExecutionMode.DUC_TARGETED,
        target=attack_target,
        capabilities=(
            AttackCapabilityRef(
                CapabilityId("test", "primary-force"),
                AttackCapabilityRole.PRIMARY_FORCE,
            ),
        ),
        completion=completion,
        native_plan=NativeAttackLifecyclePlan((native_rule,)),
    )

    claims = (
        ResourceClaim(
            identity=ResourceClaimId("test", "train-spearman-resource"),
            kind=ResourceKind.ACTION_EXCLUSION,
            scope=ResourceScope.TRANSIENT,
            claimant=spear,
            conflict_class="military-production",
            arbitration_owner=composition,
        ),
    )
    recovery_contract = CapabilityRecoveryContract()
    recovery_state = CapabilityRecoveryState(
        demand=DemandId("test", "military-composition"),
        kind=CapabilityRecoveryStateKind.ACTIVE,
    )

    proof = MilitaryCompositionProofPath(
        composition=MilitaryCompositionPlan(
            identity=composition,
            targets=(
                MilitaryCompositionUnitTarget(
                    demand=spear,
                    unit="spearman",
                    native_unit_id=93,
                    minimum=3,
                ),
            ),
            attack_objective=objective,
        ),
        resource_claims=claims,
        target=target,
        attack_target=attack_target,
        attack=attack,
        witness=witness,
        recovery_demand=composition,
        recovery_contract=recovery_contract,
        recovery_state=recovery_state,
    )
    program = CompilerSemanticProgram(
        demands=(composition_demand, production_demand),
        military_proof_path=proof,
    )
    return program, proof


class MilitaryCompositionProofTests(unittest.TestCase):
    def test_complete_path_is_valid_and_remains_native_open(self):
        program, proof = _proof()
        report = validate_military_composition_proof(proof, program)
        self.assertTrue(report.valid)
        self.assertEqual(proof.status.value, "NATIVE_LOWERING_OPEN")

    def test_unit_id_mismatch_is_rejected(self):
        program, proof = _proof()
        target = replace(
            proof.composition.targets[0],
            native_unit_id=94,
        )
        bad = replace(
            proof,
            composition=replace(proof.composition, targets=(target,)),
        )
        report = validate_military_composition_proof(bad, program)
        self.assertFalse(report.valid)
        self.assertIn("MIL-PROOF-004", {item.code for item in report.errors})

    def test_target_identity_cannot_be_substituted(self):
        program, proof = _proof()
        replacement = DucTargetState(
            kind=DucTargetKind.OBJECT,
            generation=2,
            validity=DucTargetStatus.VALID,
            proof=DucTargetProof.NATIVE_ID_PROOF,
        )
        bad = replace(
            proof,
            target=replacement,
        )
        report = validate_military_composition_proof(bad, program)
        self.assertFalse(report.valid)
        self.assertIn("MIL-PROOF-012", {item.code for item in report.errors})

    def test_missing_resource_arbitration_is_rejected(self):
        program, proof = _proof()
        bad = replace(proof, resource_claims=())
        report = validate_military_composition_proof(bad, program)
        self.assertFalse(report.valid)
        self.assertIn("MIL-PROOF-005", {item.code for item in report.errors})

    def test_attack_completion_must_carry_the_declared_witness(self):
        program, proof = _proof()
        bad_attack = replace(proof.attack, completion=None)
        bad = replace(proof, attack=bad_attack)
        report = validate_military_composition_proof(bad, program)
        self.assertFalse(report.valid)
        self.assertIn("MIL-PROOF-017", {item.code for item in report.errors})

    def test_attack_completion_witness_must_be_the_declared_witness(self):
        program, proof = _proof()
        alternate = CompletionWitnessContract(
            identity=SemanticId("test", "alternate-attack-complete"),
            evidence_kind="WORLD_STATE",
            primitive="unit-type-count",
            expression=_expr(
                "(unit-type-count spearman >= 3)",
                "unit-type-count",
                "spearman",
                ">=",
                "3",
            ),
            establishes=proof.attack.objective,
            source_order=21,
            issuance_source_order=10,
        )
        bad_completion = AttackCompletionContract(
            witness=alternate,
            objective=proof.attack.objective,
        )
        bad_attack = replace(proof.attack, completion=bad_completion)
        bad = replace(proof, attack=bad_attack)
        report = validate_military_composition_proof(bad, program)
        self.assertFalse(report.valid)
        self.assertIn("MIL-PROOF-018", {item.code for item in report.errors})

    def test_recovery_returns_same_demand_to_active(self):
        program, proof = _proof()
        report = validate_military_composition_proof(proof, program)
        self.assertTrue(report.valid)
        self.assertEqual(
            proof.recovery_state.demand,
            DemandId("test", "military-composition"),
        )


if __name__ == "__main__":
    unittest.main()
