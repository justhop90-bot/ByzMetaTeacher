"""Domain adapters for the compiler operational-semantics IR."""
from __future__ import annotations

from ..ast import Expression
from ..ir import (
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
    attack_plan: NativeAttackLifecyclePlan | None = None,
    duc_plan: NativeDucPlan | None = None,
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None,
) -> OperationalSemanticsPlan:
    contracts = list(base.contracts)

    if attack_plan is not None:
        contracts.extend(operational_contracts_for_attack_plan(attack_plan))
    if duc_plan is not None:
        contracts.extend(operational_contracts_for_duc_plan(duc_plan))
    if escrow_plan is not None:
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
