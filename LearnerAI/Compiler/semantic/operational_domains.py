"""Domain adapters for the compiler operational-semantics IR."""
from __future__ import annotations

from ..ast import Expression
from ..ir import (
    AttackExecution,
    AttackExecutionMode,
    AttackExecutionState,
    NativeAttackLifecyclePlan,
    NativeDucPlan,
    NativeEscrowPolicyPlan,
    NativeEscrowReleasePlan,
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
    SemanticId,
)

from .community_engine import PracticeStatus
from .native_controller import (
    NativeControlSurfaceKind,
    default_native_controller_catalog,
)


def _policy_observation(
    identity: str,
    *,
    expression: Expression | None = None,
    reference: str | None = None,
    role: OperationalObservationRole,
) -> OperationalObservation:
    return OperationalObservation(
        identity=identity,
        role=role,
        evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
        expression=expression,
        reference=reference,
    )


def _guard(identity: str, observation_ids: tuple[str, ...]) -> OperationalGuard:
    return OperationalGuard(
        identity=identity,
        conditions=tuple(OperationalCondition(item) for item in observation_ids),
        combination=OperationalCombination.ALL,
    )


def operational_contracts_for_attack_plan(
    plan: NativeAttackLifecyclePlan,
) -> tuple[OperationalLoopContract, ...]:
    contracts: list[OperationalLoopContract] = []

    for rule in plan.rules:
        facts = tuple(
            _policy_observation(
                f"attack:{rule.identity}:fact:{index}",
                expression=expression,
                role=OperationalObservationRole.ADMISSION,
            )
            for index, expression in enumerate(rule.facts)
        )
        if not facts:
            facts = (
                _policy_observation(
                    f"attack:{rule.identity}:control",
                    reference=f"attack-control:{rule.identity}",
                    role=OperationalObservationRole.CONTROL_STATE,
                ),
            )

        observation_ids = tuple(item.identity for item in facts)
        admission = _guard(f"attack:{rule.identity}:admission", observation_ids)
        retry = _guard(f"attack:{rule.identity}:retry-admission", observation_ids)

        contracts.append(
            OperationalLoopContract(
                identity=f"attack:{rule.identity}:operational",
                domain=OperationalDomain.ATTACK,
                demand=SemanticId("<native-attack-plan>", rule.identity),
                observations=facts,
                observe=OperationalStage(
                    identity=f"attack:{rule.identity}:observe",
                    observation_ids=observation_ids,
                ),
                admission=admission,
                request=OperationalRequest(
                    identity=f"attack:{rule.identity}:request",
                    kind=OperationalRequestKind.ATTACK_CONTROLLER,
                    commands=rule.actions,
                    execution_ref=rule.identity,
                    location=rule.location,
                ),
                debounce=OperationalGuard(
                    identity=f"attack:{rule.identity}:debounce",
                    conditions=(),
                ),
                reobserve=OperationalStage(
                    identity=f"attack:{rule.identity}:reobserve",
                    observation_ids=observation_ids,
                ),
                recovery=OperationalRecovery(
                    identity=f"attack:{rule.identity}:recovery",
                    strategies=(
                        OperationalRecoveryStrategy.REISSUE_REQUEST,
                        OperationalRecoveryStrategy.REASSESS,
                    ),
                    preserves_demand=True,
                    retry_guard=retry,
                    location=rule.location,
                ),
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                location=rule.location,
            )
        )

    return tuple(contracts)

def _resolved_attack_strategic_number_control(
    reference: str,
    *,
    observation_id: str,
    catalog=None,
) -> tuple[OperationalControlRef, OperationalObservation]:
    """Resolve an evidence-only attack SN surface and link it into the loop graph."""
    controller_catalog = catalog or default_native_controller_catalog()
    surface = controller_catalog.resolve_surface(
        NativeControlSurfaceKind.STRATEGIC_NUMBER,
        reference,
    )
    controller = controller_catalog.controller(surface.controller_id)
    if (
        surface.status is not PracticeStatus.EVIDENCE_ONLY
        or controller.status is not PracticeStatus.EVIDENCE_ONLY
    ):
        raise ValueError(
            f"attack Strategic Number control '{reference}' must remain "
            "evidence-only"
        )

    control = OperationalControlRef(
        kind=OperationalControlKind.STRATEGIC_NUMBER,
        reference=reference,
        use=OperationalControlUse.READ,
        controller_id=surface.controller_id,
        surface_identity=surface.identity,
        linked_observation_ids=(observation_id,),
        resolution_required=True,
    )
    observation = _policy_observation(
        observation_id,
        reference=surface.identity,
        role=OperationalObservationRole.CONTROL_STATE,
    )
    return control, observation


def operational_contracts_for_attack_execution(
    execution: AttackExecution,
) -> tuple[OperationalLoopContract, ...]:
    """Project one typed attack lifecycle state into operational control semantics.

    The projection is compiler policy only. It does not infer combat success,
    native acknowledgement, target liveness, or controller causality.
    """
    if execution.is_terminal:
        return ()

    identity = (
        f"attack-execution:{execution.identity.source_unit}:"
        f"{execution.identity.local_name}"
    )
    state_id = f"{identity}:state"
    observations: list[OperationalObservation] = [
        _policy_observation(
            state_id,
            reference=f"{identity}:state:{execution.state.value}",
            role=OperationalObservationRole.CONTROL_STATE,
        )
    ]

    for capability in execution.capabilities:
        if not capability.required:
            continue
        capability_id = (
            f"{identity}:capability:{capability.role.value}:"
            f"{capability.capability.source_unit}:"
            f"{capability.capability.local_name}"
        )
        observations.append(
            _policy_observation(
                capability_id,
                reference=capability_id,
                role=OperationalObservationRole.CAPABILITY,
            )
        )

    if execution.target is not None:
        target_id = f"{identity}:target"
        observations.append(
            _policy_observation(
                target_id,
                reference=(
                    f"{identity}:target:{execution.target.validity.value}:"
                    f"generation:{execution.target.generation}"
                ),
                role=OperationalObservationRole.IDENTITY,
            )
        )

    if execution.reassessment is not None:
        reassess_id = f"{identity}:reassessment"
        observations.append(
            _policy_observation(
                reassess_id,
                reference=reassess_id,
                role=OperationalObservationRole.REASSESSMENT,
            )
        )

    observation_ids = tuple(item.identity for item in observations)
    admission = _guard(f"{identity}:admission", observation_ids)
    retry_guard = _guard(f"{identity}:retry-admission", observation_ids)

    commands: tuple[Expression, ...] = ()
    if execution.native_plan is not None:
        commands = tuple(
            action
            for rule in execution.native_plan.rules
            for action in rule.actions
        )

    recovery_strategies = [OperationalRecoveryStrategy.REASSESS]
    if execution.native_plan is not None and execution.state in {
        AttackExecutionState.ATTACK,
        AttackExecutionState.PRESS,
    }:
        recovery_strategies.insert(0, OperationalRecoveryStrategy.REISSUE_REQUEST)
    if execution.mode is AttackExecutionMode.DUC_TARGETED:
        recovery_strategies.insert(
            0,
            OperationalRecoveryStrategy.REACQUIRE_DUC_IDENTITY,
        )

    controls: list[OperationalControlRef] = []
    control_observation_ids: list[str] = []
    attack_control_references: tuple[str, ...]
    if execution.mode is AttackExecutionMode.ATTACK_GROUPS:
        attack_control_references = (
            "sn-number-attack-groups",
            "sn-percent-attack-soldiers",
        )
    elif execution.mode is AttackExecutionMode.TOWN_SIZE_ATTACK:
        attack_control_references = ("sn-maximum-town-size",)
    else:
        attack_control_references = ()

    for control_reference in attack_control_references:
        observation_id = f"{identity}:control:{control_reference}"
        control, observation = _resolved_attack_strategic_number_control(
            control_reference,
            observation_id=observation_id,
        )
        controls.append(control)
        observations.append(observation)
        control_observation_ids.append(observation_id)

    observation_ids = tuple(item.identity for item in observations)
    admission = _guard(f"{identity}:admission", observation_ids)
    retry_guard = _guard(f"{identity}:retry-admission", observation_ids)

    if execution.mode is AttackExecutionMode.DUC_TARGETED:
        controls.append(
            OperationalControlRef(
                kind=OperationalControlKind.DUC_IDENTITY,
                reference=identity,
                use=OperationalControlUse.REASSERT,
            )
        )

    return (
        OperationalLoopContract(
            identity=f"{identity}:operational",
            domain=OperationalDomain.ATTACK,
            demand=execution.objective,
            observations=tuple(observations),
            observe=OperationalStage(
                identity=f"{identity}:observe",
                observation_ids=observation_ids,
            ),
            admission=admission,
            request=OperationalRequest(
                identity=f"{identity}:request",
                kind=OperationalRequestKind.ATTACK_CONTROLLER,
                commands=commands,
                execution_ref=identity,
                location=execution.location,
            ),
            debounce=OperationalGuard(
                identity=f"{identity}:debounce",
                conditions=(),
            ),
            reobserve=OperationalStage(
                identity=f"{identity}:reobserve",
                observation_ids=observation_ids,
            ),
            recovery=OperationalRecovery(
                identity=f"{identity}:recovery",
                strategies=tuple(recovery_strategies),
                preserves_demand=True,
                retry_guard=retry_guard,
                location=execution.location,
            ),
            controls=tuple(controls),
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            location=execution.location,
        ),
    )

def operational_contracts_for_duc_plan(
    plan: NativeDucPlan,
) -> tuple[OperationalLoopContract, ...]:
    contracts: list[OperationalLoopContract] = []

    for rule in plan.rules:
        facts = tuple(
            _policy_observation(
                f"duc:{rule.identity}:fact:{index}",
                expression=expression,
                role=OperationalObservationRole.REASSESSMENT,
            )
            for index, expression in enumerate(rule.facts)
        )
        if not facts:
            facts = (
                _policy_observation(
                    f"duc:{rule.identity}:identity",
                    reference=f"duc-search:{rule.identity}",
                    role=OperationalObservationRole.IDENTITY,
                ),
            )

        observation_ids = tuple(item.identity for item in facts)
        admission = _guard(f"duc:{rule.identity}:admission", observation_ids)
        retry = _guard(f"duc:{rule.identity}:retry-admission", observation_ids)

        contracts.append(
            OperationalLoopContract(
                identity=f"duc:{rule.identity}:operational",
                domain=OperationalDomain.DUC,
                demand=SemanticId("<native-duc-plan>", rule.identity),
                observations=facts,
                observe=OperationalStage(
                    identity=f"duc:{rule.identity}:observe",
                    observation_ids=observation_ids,
                ),
                admission=admission,
                request=OperationalRequest(
                    identity=f"duc:{rule.identity}:request",
                    kind=OperationalRequestKind.DUC_OPERATION,
                    commands=rule.actions,
                    execution_ref=rule.identity,
                    location=rule.location,
                ),
                debounce=OperationalGuard(
                    identity=f"duc:{rule.identity}:debounce",
                    conditions=(),
                ),
                reobserve=OperationalStage(
                    identity=f"duc:{rule.identity}:reobserve",
                    observation_ids=observation_ids,
                ),
                recovery=OperationalRecovery(
                    identity=f"duc:{rule.identity}:recovery",
                    strategies=(
                        OperationalRecoveryStrategy.REACQUIRE_DUC_IDENTITY,
                        OperationalRecoveryStrategy.REISSUE_REQUEST,
                        OperationalRecoveryStrategy.REASSESS,
                    ),
                    preserves_demand=True,
                    retry_guard=retry,
                    location=rule.location,
                ),
                controls=(
                    OperationalControlRef(
                        kind=OperationalControlKind.DUC_IDENTITY,
                        reference=rule.identity,
                        use=OperationalControlUse.REASSERT,
                    ),
                ),
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                location=rule.location,
            )
        )

    return tuple(contracts)


def operational_contracts_for_escrow_plan(
    plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan,
) -> tuple[OperationalLoopContract, ...]:
    contracts: list[OperationalLoopContract] = []

    for index, operation in enumerate(plan.operations):
        state_id = (
            f"escrow:{operation.contract_identity}:"
            f"{operation.resource}:{index}"
        )
        observation = _policy_observation(
            state_id,
            reference=state_id,
            role=OperationalObservationRole.CONTROL_STATE,
        )
        guard = _guard(f"{state_id}:guard", (state_id,))
        recovery = (
            OperationalRecoveryStrategy.RELEASE_ESCROW
            if operation.kind.value == "RELEASE"
            else OperationalRecoveryStrategy.REASSESS
        )

        contracts.append(
            OperationalLoopContract(
                identity=f"{state_id}:operational",
                domain=OperationalDomain.ESCROW,
                demand=operation.owner,
                observations=(observation,),
                observe=OperationalStage(
                    identity=f"{state_id}:observe",
                    observation_ids=(state_id,),
                ),
                admission=guard,
                request=OperationalRequest(
                    identity=f"{state_id}:request",
                    kind=OperationalRequestKind.ESCROW_OPERATION,
                    execution_ref=operation.contract_identity,
                    location=operation.location,
                ),
                debounce=OperationalGuard(
                    identity=f"{state_id}:debounce",
                    conditions=(),
                ),
                reobserve=OperationalStage(
                    identity=f"{state_id}:reobserve",
                    observation_ids=(state_id,),
                ),
                recovery=OperationalRecovery(
                    identity=f"{state_id}:recovery",
                    strategies=(recovery, OperationalRecoveryStrategy.REASSESS),
                    preserves_demand=True,
                    retry_guard=guard,
                    location=operation.location,
                ),
                controls=(
                    OperationalControlRef(
                        kind=OperationalControlKind.ESCROW,
                        reference=operation.contract_identity,
                        use=OperationalControlUse.WRITE,
                    ),
                ),
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                location=operation.location,
            )
        )

    return tuple(contracts)


def merge_operational_plan(
    base: OperationalSemanticsPlan,
    *,
    attack_plan: NativeAttackLifecyclePlan | AttackExecution | None = None,
    duc_plan: NativeDucPlan | None = None,
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None,
) -> OperationalSemanticsPlan:
    contracts = list(base.contracts)

    if isinstance(attack_plan, NativeAttackLifecyclePlan):
        contracts.extend(operational_contracts_for_attack_plan(attack_plan))
    elif isinstance(attack_plan, AttackExecution):
        contracts.extend(operational_contracts_for_attack_execution(attack_plan))
    if isinstance(duc_plan, NativeDucPlan):
        contracts.extend(operational_contracts_for_duc_plan(duc_plan))
    if isinstance(
        escrow_plan,
        (NativeEscrowReleasePlan, NativeEscrowPolicyPlan),
    ):
        contracts.extend(operational_contracts_for_escrow_plan(escrow_plan))

    contracts.sort(
        key=lambda contract: (
            contract.domain.value,
            contract.demand,
            contract.identity,
        )
    )
    return OperationalSemanticsPlan(contracts=tuple(contracts))


__all__ = [
    "merge_operational_plan",
    "operational_contracts_for_attack_plan",
    "operational_contracts_for_duc_plan",
    "operational_contracts_for_escrow_plan",
]
