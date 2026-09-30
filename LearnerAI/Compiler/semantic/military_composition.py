"""Cross-domain validation for the first military composition proof path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..diagnostics import DiagnosticSeverity
from ..ir.attack import AttackCapabilityRole, AttackExecutionMode, AttackExecutionState
from ..ir.capability import CapabilityRecoveryContract, CapabilityRecoveryEvent, CapabilityRecoveryState, CapabilityRecoveryStateKind, DemandId
from ..ir.model import CompletionWitnessContract
from ..ir.resource import ResourceClaim, ResourceClaimId, ResourceKind, ResourceScope
from ..ir.program import CompilerSemanticProgram
from ..ir.military_composition import MilitaryCompositionProofPath
from ..ir.model import SemanticId
if TYPE_CHECKING:
    from ..ir.attack import AttackExecution
    from ..ir.strategy import StrategyCompilation


@dataclass(frozen=True)
class MilitaryProofDiagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity is DiagnosticSeverity.ERROR


@dataclass(frozen=True)
class MilitaryProofReport:
    diagnostics: tuple[MilitaryProofDiagnostic, ...]

    @property
    def errors(self) -> tuple[MilitaryProofDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.is_error)

    @property
    def valid(self) -> bool:
        return not self.errors


def _error(code: str, message: str) -> MilitaryProofDiagnostic:
    return MilitaryProofDiagnostic(code, DiagnosticSeverity.ERROR, message)


def build_military_composition_proof(
    compilation: "StrategyCompilation",
    composition,
    *,
    attack: "AttackExecution",
) -> MilitaryCompositionProofPath:
    """Assemble a proof path from lowered strategy state plus runtime attack evidence."""
    if composition not in compilation.military_compositions:
        raise ValueError(
            "military composition must originate from the StrategyCompilation"
        )
    if attack.objective != composition.attack_objective:
        raise ValueError(
            "attack objective does not match the compiled military composition"
        )
    if attack.target is None:
        raise ValueError("military proof assembly requires an attack target")
    if attack.completion is None:
        raise ValueError(
            "military proof assembly requires an attack completion witness"
        )

    claims = tuple(
        ResourceClaim(
            identity=ResourceClaimId(
                composition.identity.source_unit,
                f"{target.demand.local_name}-military-composition-resource",
            ),
            kind=ResourceKind.ACTION_EXCLUSION,
            scope=ResourceScope.TRANSIENT,
            claimant=target.demand,
            conflict_class=(
                f"military-composition:{composition.identity.local_name}"
            ),
            arbitration_owner=composition.identity,
        )
        for target in composition.targets
    )
    recovery_contract = CapabilityRecoveryContract()
    recovery_demand = SemanticId(
        composition.identity.source_unit,
        composition.identity.local_name,
    )
    recovery_state = CapabilityRecoveryState(
        demand=DemandId(
            recovery_demand.source_unit,
            recovery_demand.local_name,
        ),
        kind=CapabilityRecoveryStateKind.ACTIVE,
    )
    return MilitaryCompositionProofPath(
        composition=composition,
        resource_claims=claims,
        target=attack.target.target,
        attack_target=attack.target,
        attack=attack,
        witness=attack.completion.witness,
        recovery_demand=composition.identity,
        recovery_contract=recovery_contract,
        recovery_state=recovery_state,
    )


def validate_military_composition_proof(
    proof: MilitaryCompositionProofPath,
    program: CompilerSemanticProgram,
) -> MilitaryProofReport:
    diagnostics: list[MilitaryProofDiagnostic] = []
    demand_by_id = {demand.identity: demand for demand in program.demands}
    composition = proof.composition

    # A strategy composition is a strategy-level proof identity, not itself an
    # execution demand. Its concrete production targets must resolve to actual
    # SemanticDemand instances below.
    for target in composition.targets:
        demand = demand_by_id.get(target.demand)
        if demand is None:
            diagnostics.append(_error(
                "MIL-PROOF-002",
                f"production demand '{target.demand.local_name}' is missing",
            ))
            continue

        lifecycle = demand.production_lifecycle
        if lifecycle is None:
            diagnostics.append(_error(
                "MIL-PROOF-003",
                f"production demand '{target.demand.local_name}' has no ProductionLifecycle",
            ))
            continue

        if lifecycle.native_unit_id != target.native_unit_id:
            diagnostics.append(_error(
                "MIL-PROOF-004",
                f"production UnitId mismatch for '{target.unit}': "
                f"target={target.native_unit_id}, lifecycle={lifecycle.native_unit_id}",
            ))

        claims = tuple(
            claim for claim in proof.resource_claims if claim.claimant == target.demand
        )
        if not claims:
            diagnostics.append(_error(
                "MIL-PROOF-005",
                f"production demand '{target.demand.local_name}' has no resource arbitration claim",
            ))
        elif any(
            claim.arbitration_owner != composition.identity
            for claim in claims
        ):
            diagnostics.append(_error(
                "MIL-PROOF-006",
                f"resource arbitration for '{target.demand.local_name}' is not owned by "
                f"composition '{composition.identity.local_name}'",
            ))

    attack = proof.attack
    if attack.objective != composition.attack_objective:
        diagnostics.append(_error(
            "MIL-PROOF-007",
            "attack objective does not match the composition attack objective",
        ))
    if attack.state not in {AttackExecutionState.ATTACK, AttackExecutionState.PRESS}:
        diagnostics.append(_error(
            "MIL-PROOF-008",
            "military proof requires ATTACK or PRESS execution state",
        ))
    if attack.mode is not AttackExecutionMode.DUC_TARGETED:
        diagnostics.append(_error(
            "MIL-PROOF-009",
            "military proof requires DUC_TARGETED mode so the DUC target is causal",
        ))
    if attack.target is None:
        diagnostics.append(_error(
            "MIL-PROOF-010",
            "DUC_TARGETED attack requires an attack target reference",
        ))
    elif attack.target is not proof.attack_target:
        diagnostics.append(_error(
            "MIL-PROOF-011",
            "attack target reference must be the exact reference carried by the proof",
        ))
    if proof.attack_target.target is not proof.target:
        diagnostics.append(_error(
            "MIL-PROOF-012",
            "attack target reference must point to the exact proof DUC target",
        ))
    if not any(
        capability.role is AttackCapabilityRole.PRIMARY_FORCE and capability.required
        for capability in attack.capabilities
    ):
        diagnostics.append(_error(
            "MIL-PROOF-013",
            "attack proof requires a PRIMARY_FORCE capability",
        ))

    witness = proof.witness
    if not isinstance(witness, CompletionWitnessContract):
        diagnostics.append(_error(
            "MIL-PROOF-014",
            "proof witness must be a CompletionWitnessContract",
        ))
    elif witness.establishes != attack.objective:
        diagnostics.append(_error(
            "MIL-PROOF-015",
            "completion witness must establish the attack objective",
        ))
    if attack.completion is None:
        diagnostics.append(_error(
            "MIL-PROOF-017",
            "attack execution must carry the proof completion witness",
        ))
    elif attack.completion.witness is not witness:
        diagnostics.append(_error(
            "MIL-PROOF-018",
            "attack completion must carry the exact proof completion witness",
        ))

    recovered = (
        proof.recovery_state
        .transition(CapabilityRecoveryEvent.LOST, proof.recovery_contract)
        .transition(CapabilityRecoveryEvent.RECOVERED, proof.recovery_contract)
    )
    if recovered.kind is not CapabilityRecoveryStateKind.ACTIVE:
        diagnostics.append(_error(
            "MIL-PROOF-016",
            "recovery path must return the original demand to ACTIVE",
        ))

    return MilitaryProofReport(tuple(diagnostics))


__all__ = [
    "build_military_composition_proof",
    "MilitaryProofDiagnostic",
    "MilitaryProofReport",
    "validate_military_composition_proof",
]
