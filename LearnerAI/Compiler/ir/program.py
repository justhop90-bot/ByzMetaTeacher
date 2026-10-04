"""Unified semantic-program envelope for the generic compiler.

The envelope composes existing typed IRs without creating a second semantic
language. It is the compiler's internal ownership boundary for cross-domain
plans; domain-specific IRs retain their own contracts and validation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .attack import AttackExecution
from .capability import CapabilityGraph
from .native_duc import NativeDucPlan
from .model import SemanticDemand
from .military_composition import MilitaryCompositionProofPath
from .native_attack import NativeAttackLifecyclePlan
from .native_control import NativeControlPlan
from .role_separation import NativeRoleSeparationPlan
from .operational import OperationalSemanticsPlan
from .persistent_control import PersistentControlRef
from .resource_control import NativeEscrowPolicyPlan, NativeEscrowReleasePlan


@dataclass(frozen=True)
class CompilerSemanticProgram:
    """One immutable semantic assembly for one compiler invocation."""

    demands: tuple[SemanticDemand, ...] = ()
    capability_graph: CapabilityGraph | None = None
    operational_plan: OperationalSemanticsPlan = OperationalSemanticsPlan()
    control_plan: NativeControlPlan | None = None
    duc_plan: NativeDucPlan | None = None
    attack_plan: NativeAttackLifecyclePlan | AttackExecution | None = None
    role_separation_plan: NativeRoleSeparationPlan | None = None
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None
    military_proof_path: MilitaryCompositionProofPath | None = None
    persistent_controls: tuple[PersistentControlRef, ...] = ()

    def __post_init__(self) -> None:
        # Domain-specific plan validators run at their existing compiler
        # boundaries. This envelope owns only cross-domain assembly invariants.
        if not isinstance(self.demands, tuple):
            raise TypeError("compiler semantic program demands must be a tuple")
        if self.military_proof_path is not None and not isinstance(
            self.military_proof_path, MilitaryCompositionProofPath
        ):
            raise TypeError("compiler semantic program military proof path is invalid")

        identities = tuple(demand.identity for demand in self.demands)
        if len(identities) != len(set(identities)):
            raise ValueError(
                "compiler semantic program contains duplicate demand identities"
            )

        demand_ids = set(identities)
        for control in self.persistent_controls:
            if control.owner not in demand_ids:
                raise ValueError(
                    "compiler semantic program persistent control has unknown owner"
                )

    @property
    def empty(self) -> bool:
        return not (
            self.demands
            or self.capability_graph is not None
            or not self.operational_plan.empty
            or self.control_plan is not None
            or self.duc_plan is not None
            or self.attack_plan is not None
            or self.role_separation_plan is not None
            or self.escrow_plan is not None
            or self.military_proof_path is not None
            or self.persistent_controls
        )

    def with_operational_plan(
        self,
        plan: OperationalSemanticsPlan,
    ) -> "CompilerSemanticProgram":
        """Return the same semantic assembly with a validated operational plan."""
        return replace(self, operational_plan=plan)


__all__ = ["CompilerSemanticProgram"]
