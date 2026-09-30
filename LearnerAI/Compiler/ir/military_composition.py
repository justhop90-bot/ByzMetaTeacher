"""Internal proof IR for the first cross-domain military strategy path."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .attack import AttackExecution, AttackTargetRef
from .capability import CapabilityRecoveryContract, CapabilityRecoveryState
from .duc import DucTargetState
from .model import CompletionWitnessContract, SemanticId
from .resource import ResourceClaim


class MilitaryProofStatus(str, Enum):
    STRUCTURAL_SEMANTIC_COMPLETE = "STRUCTURAL_SEMANTIC_COMPLETE"
    NATIVE_LOWERING_OPEN = "NATIVE_LOWERING_OPEN"


@dataclass(frozen=True)
class MilitaryCompositionUnitTarget:
    demand: SemanticId
    unit: str
    native_unit_id: int
    minimum: int

    def __post_init__(self) -> None:
        if not self.demand.local_name.strip():
            raise ValueError("military composition target demand must not be empty")
        if not self.unit.strip():
            raise ValueError("military composition target unit must not be empty")
        if self.native_unit_id <= 0:
            raise ValueError("military composition target UnitId must be positive")
        if self.minimum < 1:
            raise ValueError("military composition target minimum must be positive")


@dataclass(frozen=True)
class MilitaryCompositionPlan:
    identity: SemanticId
    targets: tuple[MilitaryCompositionUnitTarget, ...]
    attack_objective: SemanticId

    def __post_init__(self) -> None:
        if not self.identity.local_name.strip():
            raise ValueError("military composition identity must not be empty")
        if not self.targets:
            raise ValueError("military composition plan requires at least one unit target")
        demand_ids = tuple(target.demand for target in self.targets)
        if len(demand_ids) != len(set(demand_ids)):
            raise ValueError("military composition plan cannot reuse one production demand")
        if not self.attack_objective.local_name.strip():
            raise ValueError("military composition attack objective must not be empty")


@dataclass(frozen=True)
class MilitaryCompositionProofPath:
    composition: MilitaryCompositionPlan
    resource_claims: tuple[ResourceClaim, ...]
    target: DucTargetState
    attack_target: AttackTargetRef
    attack: AttackExecution
    witness: CompletionWitnessContract
    recovery_demand: SemanticId
    recovery_contract: CapabilityRecoveryContract
    recovery_state: CapabilityRecoveryState

    @property
    def status(self) -> MilitaryProofStatus:
        return MilitaryProofStatus.NATIVE_LOWERING_OPEN

    def __post_init__(self) -> None:
        if self.recovery_demand != self.composition.identity:
            raise ValueError("military proof recovery must preserve the composition demand identity")
        if (
            self.recovery_state.demand.source_unit != self.composition.identity.source_unit
            or self.recovery_state.demand.local_name != self.composition.identity.local_name
        ):
            raise ValueError("military proof recovery state must preserve the composition identity")


__all__ = [
    "MilitaryCompositionPlan",
    "MilitaryCompositionProofPath",
    "MilitaryCompositionUnitTarget",
    "MilitaryProofStatus",
]
