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
from .native_attack import NativeAttackLifecyclePlan
from .native_control import NativeControlPlan
from .operational import OperationalSemanticsPlan
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
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None

    def __post_init__(self) -> None:
        # Domain-specific plan validators run at their existing compiler
        # boundaries. This envelope owns only cross-domain assembly invariants.
        if not isinstance(self.demands, tuple):
            raise TypeError("compiler semantic program demands must be a tuple")

        identities = tuple(demand.identity for demand in self.demands)
        if len(identities) != len(set(identities)):
            raise ValueError(
                "compiler semantic program contains duplicate demand identities"
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
            or self.escrow_plan is not None
        )

    def with_operational_plan(
        self,
        plan: OperationalSemanticsPlan,
    ) -> "CompilerSemanticProgram":
        """Return the same semantic assembly with a validated operational plan."""
        return replace(self, operational_plan=plan)


__all__ = ["CompilerSemanticProgram"]
