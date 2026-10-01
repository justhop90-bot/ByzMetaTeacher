"""Typed semantic IR for strategic attack execution.

This layer composes existing strategy, capability, DUC, recovery, and native
attack IR. It does not replace ownership of those subsystems or simulate combat.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from .capability import CapabilityId
from .duc import DucProvenance, DucTargetState, DucTargetStatus
from .model import CompletionWitnessContract, SemanticId, StateAccess
from .native_attack import NativeAttackLifecyclePlan
from . import strategy as _strategy
from . import strategy_runtime as _strategy_runtime


class AttackExecutionState(str, Enum):
    READY = "READY"
    PREPARE = "PREPARE"
    ASSEMBLE = "ASSEMBLE"
    ATTACK = "ATTACK"
    PRESS = "PRESS"
    RETREAT = "RETREAT"
    REINFORCE = "REINFORCE"
    RETARGET = "RETARGET"
    COMPLETE = "COMPLETE"
    REASSESS = "REASSESS"


class AttackExecutionMode(str, Enum):
    ATTACK_NOW = "ATTACK_NOW"
    ATTACK_GROUPS = "ATTACK_GROUPS"
    TOWN_SIZE_ATTACK = "TOWN_SIZE_ATTACK"
    DUC_TARGETED = "DUC_TARGETED"

    @property
    def requires_duc_target(self) -> bool:
        return self is AttackExecutionMode.DUC_TARGETED


class AttackCapabilityRole(str, Enum):
    PRIMARY_FORCE = "PRIMARY_FORCE"
    SIEGE = "SIEGE"
    REINFORCEMENT = "REINFORCEMENT"
    TARGET_ACCESS = "TARGET_ACCESS"
    DEFENSIVE_RESERVE = "DEFENSIVE_RESERVE"
    POSITIONAL_ACCESS = "POSITIONAL_ACCESS"


class AttackResultDisposition(str, Enum):
    UNKNOWN = "UNKNOWN"
    DAMAGED = "DAMAGED"
    STALLED = "STALLED"
    REASSESS = "REASSESS"
    SEVERE_COLLAPSE = "SEVERE_COLLAPSE"


@dataclass(frozen=True)
class AttackCapabilityRef:
    capability: CapabilityId
    role: AttackCapabilityRole
    required: bool = True

    def __post_init__(self) -> None:
        if not self.capability.local_name.strip():
            raise ValueError("attack capability reference requires a non-empty capability")
        if not isinstance(self.role, AttackCapabilityRole):
            raise TypeError("attack capability role must be AttackCapabilityRole")


@dataclass(frozen=True)
class AttackTargetRef:
    target: DucTargetState
    required_validity: tuple[DucTargetStatus, ...] = (DucTargetStatus.VALID,)
    source_list_generation: int | None = None
    source_filter_generation: int | None = None
    provenance: DucProvenance | None = None

    @classmethod
    def from_duc(
        cls,
        target: DucTargetState,
        *,
        required_validity: tuple[DucTargetStatus, ...] = (DucTargetStatus.VALID,),
    ) -> "AttackTargetRef":
        return cls(
            target=target,
            required_validity=required_validity,
            source_list_generation=target.source_list_generation,
            source_filter_generation=target.source_filter_generation,
            provenance=target.provenance,
        )

    def __post_init__(self) -> None:
        if not self.required_validity:
            raise ValueError("attack target reference requires at least one accepted target status")
        if any(not isinstance(status, DucTargetStatus) for status in self.required_validity):
            raise TypeError("attack target validity requirements must use DucTargetStatus")
        if self.source_list_generation is not None and self.source_list_generation < 0:
            raise ValueError("attack target source list generation must be non-negative")
        if self.source_filter_generation is not None and self.source_filter_generation < 0:
            raise ValueError("attack target source filter generation must be non-negative")
        if self.target.source_list_generation is not None and (
            self.source_list_generation is not None
            and self.target.source_list_generation != self.source_list_generation
        ):
            raise ValueError("attack target list generation conflicts with DUC target state")
        if self.target.source_filter_generation is not None and (
            self.source_filter_generation is not None
            and self.target.source_filter_generation != self.source_filter_generation
        ):
            raise ValueError("attack target filter generation conflicts with DUC target state")

    @property
    def validity(self) -> DucTargetStatus:
        return self.target.validity

    @property
    def generation(self) -> int:
        return self.target.generation

    @property
    def valid_for_execution(self) -> bool:
        return self.validity in self.required_validity


#: Execution states whose promotion revalidates DUC target proof against
#: live search generations when the caller provides them. RETARGET stays
#: open by design (it exists to fix drift), as do REASSESS (recovery
#: routing), READY (resting), RETREAT (withdrawal), and COMPLETE (which
#: requires its own explicit witness).
_REVALIDATED_PROMOTION_STATES = frozenset(
    {
        AttackExecutionState.PREPARE,
        AttackExecutionState.ASSEMBLE,
        AttackExecutionState.ATTACK,
        AttackExecutionState.PRESS,
        AttackExecutionState.REINFORCE,
    }
)


def revalidate_attack_target_proof(
    ref: AttackTargetRef | None,
    *,
    current_list_generation: int | None = None,
    current_filter_generation: int | None = None,
) -> None:
    """Revalidate attack target proof for promotion.

    Checks both the snapshot status accepted by the ref and the pinned
    DUC generations against live search state.

    Attack target references are frozen snapshots: the DUC layer mints new
    state objects on every mutation, reset, or filter change, so a stored
    ref can read VALID while the live list has moved on. The pinned
    `source_list_generation` / `source_filter_generation` exist to catch
    exactly that drift.

    Fail-closed ValueError on an unaccepted snapshot status or on drift.
    Passes silently when the ref carries no lineage on an axis
    (direct-ID targets), when the caller provides no live state on an
    axis, or when the ref is absent. Never claims target death: an
    invalid proof ends promotion, while liveness stays unknown (death
    needs an independent world witness).
    """
    if ref is None:
        return
    if not ref.valid_for_execution:
        accepted = ", ".join(status.value for status in ref.required_validity)
        raise ValueError(
            f"attack target proof is invalid: target status "
            f"{ref.validity.value} is not accepted for promotion "
            f"(accepted: {accepted}); invalidation ends the proof — "
            "target liveness remains unknown"
        )
    for pin, current, axis in (
        (ref.source_list_generation, current_list_generation, "list"),
        (ref.source_filter_generation, current_filter_generation, "filter"),
    ):
        if pin is None or current is None:
            continue
        if pin != current:
            raise ValueError(
                f"attack target proof is stale: pinned source {axis} generation "
                f"{pin} != current {axis} generation {current}; the target may have "
                "been invalidated by list mutation, reset, or filter change — "
                "target liveness remains unknown"
            )


@dataclass(frozen=True)
class AttackCompletionContract:
    witness: CompletionWitnessContract
    objective: SemanticId

    def __post_init__(self) -> None:
        if self.witness.establishes != self.objective:
            raise ValueError(
                "attack completion witness must establish the declared attack objective"
            )


@dataclass(frozen=True)
class AttackReassessment:
    reasons: tuple[_strategy_runtime.ReassessmentReason, ...]
    preserve_objective: bool = True
    allow_retarget: bool = False
    allow_reinforce: bool = False
    allow_reprepare: bool = True
    allow_complete: bool = False

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("attack reassessment requires at least one reason")
        if any(not isinstance(reason, _strategy_runtime.ReassessmentReason) for reason in self.reasons):
            raise TypeError("attack reassessment reasons must use ReassessmentReason")
        if self.allow_complete and not self.preserve_objective:
            raise ValueError(
                "an attack cannot complete while discarding its strategic objective"
            )


@dataclass(frozen=True)
class AttackExecutionTransition:
    from_state: AttackExecutionState
    to_state: AttackExecutionState
    reason: str
    reassessment_reasons: tuple[_strategy_runtime.ReassessmentReason, ...] = ()

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("attack transition reason must not be empty")


_ALLOWED_TRANSITIONS: dict[AttackExecutionState, frozenset[AttackExecutionState]] = {
    AttackExecutionState.READY: frozenset(
        {
            AttackExecutionState.PREPARE,
            AttackExecutionState.RETARGET,
            AttackExecutionState.COMPLETE,
        }
    ),
    AttackExecutionState.PREPARE: frozenset(
        {
            AttackExecutionState.ASSEMBLE,
            AttackExecutionState.RETARGET,
            AttackExecutionState.RETREAT,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.ASSEMBLE: frozenset(
        {
            AttackExecutionState.ATTACK,
            AttackExecutionState.PREPARE,
            AttackExecutionState.RETARGET,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.ATTACK: frozenset(
        {
            AttackExecutionState.PRESS,
            AttackExecutionState.RETREAT,
            AttackExecutionState.RETARGET,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.PRESS: frozenset(
        {
            AttackExecutionState.REINFORCE,
            AttackExecutionState.RETREAT,
            AttackExecutionState.RETARGET,
            AttackExecutionState.COMPLETE,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.REINFORCE: frozenset(
        {
            AttackExecutionState.PRESS,
            AttackExecutionState.PREPARE,
            AttackExecutionState.RETREAT,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.RETREAT: frozenset(
        {
            AttackExecutionState.PREPARE,
            AttackExecutionState.RETARGET,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.RETARGET: frozenset(
        {
            AttackExecutionState.ASSEMBLE,
            AttackExecutionState.ATTACK,
            AttackExecutionState.PREPARE,
            AttackExecutionState.REASSESS,
        }
    ),
    AttackExecutionState.REASSESS: frozenset(
        {
            AttackExecutionState.PREPARE,
            AttackExecutionState.RETARGET,
            AttackExecutionState.REINFORCE,
            AttackExecutionState.COMPLETE,
            AttackExecutionState.READY,
        }
    ),
    AttackExecutionState.COMPLETE: frozenset(),
}


@dataclass(frozen=True)
class AttackExecution:
    identity: SemanticId
    objective: SemanticId
    state: AttackExecutionState
    mode: AttackExecutionMode
    target: AttackTargetRef | None = None
    capabilities: tuple[AttackCapabilityRef, ...] = ()
    strategic_binding: _strategy.StrategicBinding | None = None
    completion: AttackCompletionContract | None = None
    reassessment: AttackReassessment | None = None
    result: AttackResultDisposition = AttackResultDisposition.UNKNOWN
    attack_attempt_generation: int = 0
    native_plan: NativeAttackLifecyclePlan | None = None
    recovery: _strategy.CapabilityRecoveryContract | None = None
    state_accesses: tuple[StateAccess, ...] = ()
    previous_state: AttackExecutionState | None = None
    transition: AttackExecutionTransition | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.local_name.strip():
            raise ValueError("attack execution identity must not be empty")
        if not self.objective.local_name.strip():
            raise ValueError("attack execution objective must not be empty")
        if self.attack_attempt_generation < 0:
            raise ValueError("attack attempt generation must be non-negative")

        capability_ids = tuple(ref.capability for ref in self.capabilities)
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("attack execution cannot reference a capability more than once")

        roles = tuple(ref.role for ref in self.capabilities)
        if len(roles) != len(set(roles)):
            raise ValueError("attack execution cannot assign multiple capabilities to one role")

        target_dependent_states = {
            AttackExecutionState.ASSEMBLE,
            AttackExecutionState.ATTACK,
            AttackExecutionState.PRESS,
            AttackExecutionState.REINFORCE,
        }

        if self.mode.requires_duc_target and self.state in target_dependent_states:
            if self.target is None:
                raise ValueError(
                    f"{self.state.value} for {self.mode.value} requires a DUC target"
                )
            if not self.target.valid_for_execution:
                raise ValueError(
                    f"{self.state.value} for {self.mode.value} requires a valid DUC target"
                )

        if self.state in {
            AttackExecutionState.ATTACK,
            AttackExecutionState.PRESS,
        }:
            if self.native_plan is None:
                raise ValueError(f"{self.state.value} requires a native attack plan")

        if self.state is AttackExecutionState.REINFORCE:
            if not any(
                ref.role is AttackCapabilityRole.REINFORCEMENT and ref.required
                for ref in self.capabilities
            ):
                raise ValueError("REINFORCE requires a reinforcement capability")

        if self.state is AttackExecutionState.COMPLETE:
            if self.completion is None:
                raise ValueError("COMPLETE requires an explicit completion witness")

        if self.state is AttackExecutionState.REASSESS:
            if self.reassessment is None:
                raise ValueError("REASSESS requires an explicit reassessment contract")

        if self.previous_state is not None:
            self.validate_transition(self.previous_state, self.state)

        if self.transition is not None:
            if self.transition.from_state is not self.previous_state:
                raise ValueError("attack transition source must match previous_state")
            if self.transition.to_state is not self.state:
                raise ValueError("attack transition target must match execution state")

        if self.state is AttackExecutionState.COMPLETE and self.result is AttackResultDisposition.SEVERE_COLLAPSE:
            raise ValueError("severe collapse cannot be represented as successful attack completion")

    @staticmethod
    def validate_transition(
        from_state: AttackExecutionState,
        to_state: AttackExecutionState,
    ) -> None:
        if to_state not in _ALLOWED_TRANSITIONS[from_state]:
            raise ValueError(
                f"illegal attack execution transition "
                f"{from_state.value} -> {to_state.value}"
            )

    @property
    def objective_identity(self) -> SemanticId:
        return self.objective

    @property
    def target_valid(self) -> bool:
        return self.target is not None and self.target.valid_for_execution

    @property
    def is_terminal(self) -> bool:
        return self.state is AttackExecutionState.COMPLETE

    @property
    def native_executable(self) -> bool:
        return (
            self.native_plan is not None
            and not self.native_plan.empty
            and self.mode is AttackExecutionMode.ATTACK_NOW
        )

    def advance(
        self,
        state: AttackExecutionState,
        *,
        reason: str,
        reassessment: AttackReassessment | None = None,
        target: AttackTargetRef | None = None,
        result: AttackResultDisposition | None = None,
        native_plan: NativeAttackLifecyclePlan | None = None,
        completion: AttackCompletionContract | None = None,
        capabilities: tuple[AttackCapabilityRef, ...] | None = None,
        current_list_generation: int | None = None,
        current_filter_generation: int | None = None,
    ) -> "AttackExecution":
        self.validate_transition(self.state, state)
        selected_target = self.target if target is None else target
        if (
            self.mode.requires_duc_target
            and state in _REVALIDATED_PROMOTION_STATES
        ):
            if current_list_generation is not None and current_list_generation < 0:
                raise ValueError("current list generation must be non-negative")
            if current_filter_generation is not None and current_filter_generation < 0:
                raise ValueError("current filter generation must be non-negative")
            revalidate_attack_target_proof(
                selected_target,
                current_list_generation=current_list_generation,
                current_filter_generation=current_filter_generation,
            )
        selected_plan = self.native_plan if native_plan is None else native_plan
        selected_completion = self.completion if completion is None else completion
        selected_reassessment = (
            self.reassessment if reassessment is None else reassessment
        )
        selected_capabilities = (
            self.capabilities if capabilities is None else capabilities
        )
        transition = AttackExecutionTransition(
            from_state=self.state,
            to_state=state,
            reason=reason,
            reassessment_reasons=(
                selected_reassessment.reasons
                if selected_reassessment is not None
                else ()
            ),
        )
        return AttackExecution(
            identity=self.identity,
            objective=self.objective,
            state=state,
            mode=self.mode,
            target=selected_target,
            capabilities=selected_capabilities,
            strategic_binding=self.strategic_binding,
            completion=selected_completion,
            reassessment=selected_reassessment,
            result=self.result if result is None else result,
            attack_attempt_generation=self.attack_attempt_generation,
            native_plan=selected_plan,
            recovery=self.recovery,
            state_accesses=self.state_accesses,
            previous_state=self.state,
            transition=transition,
            location=self.location,
        )


__all__ = [
    "AttackCapabilityRef",
    "AttackCapabilityRole",
    "AttackCompletionContract",
    "AttackExecution",
    "AttackExecutionMode",
    "AttackExecutionState",
    "AttackExecutionTransition",
    "AttackReassessment",
    "AttackResultDisposition",
    "revalidate_attack_target_proof",
]
