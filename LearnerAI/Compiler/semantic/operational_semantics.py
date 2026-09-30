"""Validation and projection for recurrent operational .per semantics."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression
from ..ir import (
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
    SemanticDemand,
)


class OperationalStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    CONFLICTING = "CONFLICTING"
    OPEN = "OPEN"


class OperationalDiagnosticCode(str, Enum):
    EMPTY_CONTRACT = "OPS-001"
    MISSING_OBSERVATION = "OPS-002"
    UNKNOWN_STAGE_REFERENCE = "OPS-003"
    EMPTY_ADMISSION = "OPS-004"
    EMPTY_REQUEST = "OPS-005"
    DEBOUNCE_COMPLETION_COLLAPSE = "OPS-006"
    RETRY_WITHOUT_ADMISSION = "OPS-007"
    DEMAND_DROPPED_ON_RECOVERY = "OPS-008"
    TIMER_ONLY_REOBSERVATION = "OPS-009"
    INVALID_CONTROL_REFERENCE = "OPS-011"
    DUPLICATE_CONTRACT = "OPS-012"


@dataclass(frozen=True)
class OperationalDiagnostic:
    code: OperationalDiagnosticCode
    status: OperationalStatus
    message: str
    contract: str
    location: object | None = None


@dataclass(frozen=True)
class OperationalValidationReport:
    diagnostics: tuple[OperationalDiagnostic, ...]

    @property
    def errors(self) -> tuple[OperationalDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.status in {
                OperationalStatus.BLOCKED,
                OperationalStatus.CONFLICTING,
            }
        )

    @property
    def valid(self) -> bool:
        return not self.errors


def _diagnostic(
    code: OperationalDiagnosticCode,
    status: OperationalStatus,
    message: str,
    contract: str,
    *,
    location=None,
) -> OperationalDiagnostic:
    return OperationalDiagnostic(
        code=code,
        status=status,
        message=message,
        contract=contract,
        location=location,
    )


def _condition_ids(guard: OperationalGuard) -> tuple[str, ...]:
    return tuple(condition.observation_id for condition in guard.conditions)


def _validate_contract(contract: OperationalLoopContract) -> list[OperationalDiagnostic]:
    diagnostics: list[OperationalDiagnostic] = []
    subject = contract.identity
    observations = {item.identity: item for item in contract.observations}

    for stage_name, stage in (
        ("observe", contract.observe),
        ("reobserve", contract.reobserve),
    ):
        if not stage.observation_ids:
            diagnostics.append(
                _diagnostic(
                    OperationalDiagnosticCode.EMPTY_CONTRACT,
                    OperationalStatus.BLOCKED,
                    f"{stage_name} stage has no observations",
                    subject,
                    location=contract.location,
                )
            )
        for observation_id in stage.observation_ids:
            if observation_id not in observations:
                diagnostics.append(
                    _diagnostic(
                        OperationalDiagnosticCode.UNKNOWN_STAGE_REFERENCE,
                        OperationalStatus.CONFLICTING,
                        f"{stage_name} stage references unknown observation "
                        f"'{observation_id}'",
                        subject,
                        location=contract.location,
                    )
                )

    admission_ids = _condition_ids(contract.admission)
    if not admission_ids:
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.EMPTY_ADMISSION,
                OperationalStatus.BLOCKED,
                "admission guard has no conditions",
                subject,
                location=contract.location,
            )
        )

    for condition in contract.admission.conditions:
        if condition.observation_id not in observations:
            diagnostics.append(
                _diagnostic(
                    OperationalDiagnosticCode.UNKNOWN_STAGE_REFERENCE,
                    OperationalStatus.CONFLICTING,
                    f"admission references unknown observation "
                    f"'{condition.observation_id}'",
                    subject,
                    location=contract.location,
                )
            )

    for condition in contract.debounce.conditions:
        observation = observations.get(condition.observation_id)
        if observation is None:
            diagnostics.append(
                _diagnostic(
                    OperationalDiagnosticCode.UNKNOWN_STAGE_REFERENCE,
                    OperationalStatus.CONFLICTING,
                    f"debounce references unknown observation "
                    f"'{condition.observation_id}'",
                    subject,
                    location=contract.location,
                )
            )
        elif observation.role is OperationalObservationRole.WORLD_STATE:
            # World-state observations can be debounce signals, but the
            # contract must not independently label them as completion.
            continue

    if not contract.request.commands and contract.request.execution_ref is None:
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.EMPTY_REQUEST,
                OperationalStatus.BLOCKED,
                "request contains neither commands nor an execution reference",
                subject,
                location=contract.request.location or contract.location,
            )
        )

    if (
        contract.reobserve.observation_ids
        and all(
            observations[item].role is OperationalObservationRole.TIMING
            for item in contract.reobserve.observation_ids
            if item in observations
        )
    ):
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.TIMER_ONLY_REOBSERVATION,
                OperationalStatus.CONFLICTING,
                "reobserve stage relies only on timing observations",
                subject,
                location=contract.location,
            )
        )

    if contract.debounce.conditions and any(
        observations.get(condition.observation_id, None)
        and observations[condition.observation_id].role is OperationalObservationRole.TIMING
        and condition.expected
        for condition in contract.debounce.conditions
    ):
        # Timer-triggered/deadline state is valid debounce. This branch is
        # intentionally non-diagnostic to document that timer use here is
        # control state rather than witness state.
        pass

    if contract.recovery.retry_guard is None:
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.RETRY_WITHOUT_ADMISSION,
                OperationalStatus.CONFLICTING,
                "recovery must carry an explicit retry admission guard",
                subject,
                location=contract.recovery.location or contract.location,
            )
        )
    elif not contract.recovery.retry_guard.conditions:
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.RETRY_WITHOUT_ADMISSION,
                OperationalStatus.CONFLICTING,
                "recovery retry guard must contain at least one admission condition",
                subject,
                location=contract.recovery.location or contract.location,
            )
        )

    if not contract.recovery.preserves_demand:
        diagnostics.append(
            _diagnostic(
                OperationalDiagnosticCode.DEMAND_DROPPED_ON_RECOVERY,
                OperationalStatus.CONFLICTING,
                "operational recovery must preserve the owning strategic demand",
                subject,
                location=contract.recovery.location or contract.location,
            )
        )


    for control in contract.controls:
        if not control.reference.strip():
            diagnostics.append(
                _diagnostic(
                    OperationalDiagnosticCode.INVALID_CONTROL_REFERENCE,
                    OperationalStatus.CONFLICTING,
                    "operational control reference must not be empty",
                    subject,
                    location=contract.location,
                )
            )

    return diagnostics


def validate_operational_semantics(
    plan: OperationalSemanticsPlan,
) -> OperationalValidationReport:
    """Validate the structural and semantic boundaries of an operational plan."""
    diagnostics: list[OperationalDiagnostic] = []

    seen: set[str] = set()
    for contract in plan.contracts:
        if contract.identity in seen:
            diagnostics.append(
                _diagnostic(
                    OperationalDiagnosticCode.DUPLICATE_CONTRACT,
                    OperationalStatus.CONFLICTING,
                    f"duplicate operational contract '{contract.identity}'",
                    contract.identity,
                    location=contract.location,
                )
            )
        seen.add(contract.identity)
        diagnostics.extend(_validate_contract(contract))

    return OperationalValidationReport(
        diagnostics=tuple(
            sorted(
                diagnostics,
                key=lambda item: (
                    item.code.value,
                    item.contract,
                    item.message,
                ),
            )
        )
    )


def _observation_role(requirement_role: str) -> OperationalObservationRole:
    normalized = requirement_role.upper()
    if "FEASIBILITY" in normalized or "ADMISSIBILITY" in normalized:
        return OperationalObservationRole.ADMISSION
    if "TIMING" in normalized:
        return OperationalObservationRole.TIMING
    if "WITNESS" in normalized:
        return OperationalObservationRole.WORLD_STATE
    if "CONTROL" in normalized or "STATE" in normalized:
        return OperationalObservationRole.CONTROL_STATE
    return OperationalObservationRole.ADMISSION


def _request_kind(action: Expression) -> OperationalRequestKind:
    if action.head in {"attack-now", "attack-groups"}:
        return OperationalRequestKind.ATTACK_CONTROLLER
    if action.head.startswith("up-"):
        return OperationalRequestKind.DUC_OPERATION
    if action.head in {"release-escrow", "set-escrow-percentage"}:
        return OperationalRequestKind.ESCROW_OPERATION
    if action.head in {
        "set-goal",
        "up-modify-goal",
        "up-compare-goal",
    }:
        return OperationalRequestKind.GOAL_MUTATION
    if action.head in {"set-strategic-number", "up-modify-sn"}:
        return OperationalRequestKind.STRATEGIC_NUMBER_MUTATION
    if action.head in {"enable-timer", "disable-timer", "set-timer"}:
        return OperationalRequestKind.TIMER_MUTATION
    return OperationalRequestKind.ACTION


def _domain(action: Expression, demand: SemanticDemand) -> OperationalDomain:
    if action.head in {"attack-now", "attack-groups", "attack"}:
        return OperationalDomain.ATTACK
    if action.head == "train":
        return OperationalDomain.PRODUCTION
    if action.head == "build":
        return OperationalDomain.CONSTRUCTION
    if action.head == "research":
        return OperationalDomain.RESEARCH
    if action.head.startswith("up-"):
        return OperationalDomain.DUC
    if action.head in {"release-escrow", "set-escrow-percentage"}:
        return OperationalDomain.ESCROW
    if demand.timer_states:
        return OperationalDomain.TIMER
    if demand.strategic_number_states:
        return OperationalDomain.STRATEGIC_NUMBER
    return OperationalDomain.GENERIC


def _control_refs(demand: SemanticDemand) -> tuple[OperationalControlRef, ...]:
    refs: list[OperationalControlRef] = [
        OperationalControlRef(
            kind=OperationalControlKind.GOAL,
            reference=f"{demand.lifecycle.slot.request_id.owner.source_unit}:{demand.lifecycle.slot.request_id.purpose}",
            use=OperationalControlUse.READ,
        )
    ]

    if demand.construction_retry_barrier is not None:
        refs.append(
            OperationalControlRef(
                kind=OperationalControlKind.RETRY_BARRIER,
                reference=demand.construction_retry_barrier.request_id.purpose,
                use=OperationalControlUse.DEBOUNCE,
            )
        )
    if demand.production_retry_barrier is not None:
        refs.append(
            OperationalControlRef(
                kind=OperationalControlKind.RETRY_BARRIER,
                reference=demand.production_retry_barrier.request_id.purpose,
                use=OperationalControlUse.DEBOUNCE,
            )
        )
    if demand.research_retry_barrier is not None:
        refs.append(
            OperationalControlRef(
                kind=OperationalControlKind.RETRY_BARRIER,
                reference=demand.research_retry_barrier.request_id.purpose,
                use=OperationalControlUse.DEBOUNCE,
            )
        )

    for state in demand.strategic_number_states:
        refs.append(
            OperationalControlRef(
                kind=OperationalControlKind.STRATEGIC_NUMBER,
                reference=state.name,
                use=OperationalControlUse.WRITE,
            )
        )
    for state in demand.timer_states:
        refs.append(
            OperationalControlRef(
                kind=OperationalControlKind.TIMER,
                reference=state.name,
                use=OperationalControlUse.WRITE,
            )
        )
    return tuple(
        sorted(
            refs,
            key=lambda item: (item.kind.value, item.reference, item.use.value),
        )
    )


def operational_contract_for_demand(
    demand: SemanticDemand,
) -> OperationalLoopContract:
    """Project an existing SemanticDemand into the common operational model."""
    observations: list[OperationalObservation] = []
    admission_ids: list[str] = []

    for index, requirement in enumerate(demand.requirements):
        identity = (
            f"{demand.identity.source_unit}:{demand.name}:requirement:{index}"
        )
        observations.append(
            OperationalObservation(
                identity=identity,
                role=_observation_role(requirement.role),
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                expression=requirement.expression,
                location=requirement.location,
            )
        )
        admission_ids.append(identity)

    witness = (
        demand.completion_witness.expression
        if demand.completion_witness is not None
        else demand.witness
    )
    witness_id = f"{demand.identity.source_unit}:{demand.name}:witness"
    observations.append(
        OperationalObservation(
            identity=witness_id,
            role=OperationalObservationRole.WORLD_STATE,
            evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
            expression=witness,
            location=witness.location,
        )
    )

    if demand.invalidation is not None:
        invalidation_id = f"{demand.identity.source_unit}:{demand.name}:invalidation"
        observations.append(
            OperationalObservation(
                identity=invalidation_id,
                role=OperationalObservationRole.REASSESSMENT,
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                expression=demand.invalidation.expression,
                location=demand.invalidation.location,
            )
        )

    if not admission_ids:
        admission_ids.append(witness_id)

    debounce_ids: list[str] = []
    if demand.production_lifecycle is not None:
        identity = f"{demand.identity.source_unit}:{demand.name}:pending"
        observations.append(
            OperationalObservation(
                identity=identity,
                role=OperationalObservationRole.DEBOUNCE,
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                expression=demand.production_lifecycle.queue_protection.pending_fact,
                location=demand.location,
            )
        )
        debounce_ids.append(identity)

    if demand.research_lifecycle is not None:
        identity = f"{demand.identity.source_unit}:{demand.name}:research-pending"
        observations.append(
            OperationalObservation(
                identity=identity,
                role=OperationalObservationRole.DEBOUNCE,
                evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                expression=demand.research_lifecycle.pending_fact,
                location=demand.location,
            )
        )
        debounce_ids.append(identity)

    if demand.timer_states:
        for state in demand.timer_states:
            identity = f"{demand.identity.source_unit}:{demand.name}:timer:{state.name}"
            observations.append(
                OperationalObservation(
                    identity=identity,
                    role=OperationalObservationRole.TIMING,
                    evidence_class=OperationalEvidenceClass.COMPILER_POLICY,
                    reference=state.name,
                    location=state.location,
                )
            )
            debounce_ids.append(identity)

    controls = _control_refs(demand)
    domain = _domain(demand.action.expression, demand)
    request_kind = _request_kind(demand.action.expression)

    admission = OperationalGuard(
        identity=f"{demand.identity.source_unit}:{demand.name}:admission",
        conditions=tuple(OperationalCondition(item) for item in admission_ids),
    )
    debounce = OperationalGuard(
        identity=f"{demand.identity.source_unit}:{demand.name}:debounce",
        conditions=tuple(OperationalCondition(item) for item in debounce_ids),
    )
    retry_guard = OperationalGuard(
        identity=f"{demand.identity.source_unit}:{demand.name}:retry-admission",
        conditions=tuple(OperationalCondition(item) for item in admission_ids),
    )
    recovery_strategies = [OperationalRecoveryStrategy.REISSUE_REQUEST]
    if demand.production_lifecycle is not None:
        recovery_strategies.append(OperationalRecoveryStrategy.REASSESS)
    if demand.research_lifecycle is not None:
        recovery_strategies.append(OperationalRecoveryStrategy.REASSESS)
    if demand.timer_states:
        recovery_strategies.append(OperationalRecoveryStrategy.REARM_TIMER)
    if demand.strategic_number_states:
        recovery_strategies.append(
            OperationalRecoveryStrategy.RESTORE_STRATEGIC_NUMBER
        )

    # The projection itself is compiler policy. Community/engine evidence
    # remains authoritative in the existing evidence registry and is not
    # fabricated into executable provenance here.
    evidence_class = OperationalEvidenceClass.COMPILER_POLICY

    return OperationalLoopContract(
        identity=f"{demand.identity.source_unit}:{demand.name}:operational",
        domain=domain,
        demand=demand.identity,
        observations=tuple(
            sorted(observations, key=lambda item: item.identity)
        ),
        observe=OperationalStage(
            identity=f"{demand.identity.source_unit}:{demand.name}:observe",
            observation_ids=tuple(admission_ids),
        ),
        admission=admission,
        request=OperationalRequest(
            identity=f"{demand.identity.source_unit}:{demand.name}:request",
            kind=request_kind,
            commands=(demand.action.expression,),
            execution_ref=f"{demand.identity.source_unit}:{demand.name}:action",
            location=demand.action.location,
        ),
        debounce=debounce,
        reobserve=OperationalStage(
            identity=f"{demand.identity.source_unit}:{demand.name}:reobserve",
            observation_ids=(witness_id,),
        ),
        recovery=OperationalRecovery(
            identity=f"{demand.identity.source_unit}:{demand.name}:recovery",
            strategies=tuple(dict.fromkeys(recovery_strategies)),
            preserves_demand=True,
            retry_guard=retry_guard,
            location=demand.location,
        ),
        controls=controls,
        evidence_class=evidence_class,
        location=demand.location,
    )


def build_operational_plan(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
) -> OperationalSemanticsPlan:
    """Project semantic demands into deterministic operational contracts."""
    contracts = tuple(
        sorted(
            (operational_contract_for_demand(demand) for demand in demands),
            key=lambda contract: (
                contract.domain.value,
                contract.demand,
                contract.identity,
            ),
        )
    )
    return OperationalSemanticsPlan(contracts=contracts)


__all__ = [
    "OperationalDiagnostic",
    "OperationalDiagnosticCode",
    "OperationalStatus",
    "OperationalValidationReport",
    "build_operational_plan",
    "operational_contract_for_demand",
    "validate_operational_semantics",
]
