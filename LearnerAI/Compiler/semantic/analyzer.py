"""Semantic validation and AST -> Basilisk IR lowering."""
from __future__ import annotations
import re
from ..ast import DemandNode, Expression
from ..errors import CompileError
from ..ir import (
    AccessKind,
    ActionIssuance,
    ActionIssuanceFailure,
    ActionIssuancePhase,
    CompletionWitnessContract,
    ReleaseStateContract,
    ReleaseEvidenceKind,
    InvalidationContract,
    InvalidationEvidenceKind,
    CancellationStateContract,
    ConstructionLifecycle,
    WitnessEvidenceKind,
    DemandOwnership,
    GoalRole,
    GoalSlotRequest,
    LifecycleState,
    LifecycleStorage,
    PendingDiagnostic,
    SemanticAction,
    LifecycleAccessPhase,
    StateAccess,
    SemanticDemand,
    SemanticId,
    SemanticRequirement,
    StorageRequestId,
    StrategicNumberState,
    StrategicNumberStorageRequest,
    TimerRequest,
    TimerState,
)
from ..primitives import NativeSupportState, PrimitiveRegistry
from .construction import canonical_build_completion_witness
from .native_building_catalog import NativeBuildingIdError, resolve_building_id

_LOGICAL_ARITY = {
    "and": 2, "or": 2, "nand": 2, "nor": 2,
    "xor": 2, "xnor": 2, "not": 1,
}
_SN_STATE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_SN_RESERVED_PREFIXES = (
    "demand-",
    "issued-",
    "pending-",
    "complete-",
    "cancelled-",
    "action-claim-",
    "sn-",
)

_SN_WHY_NOT_GOAL = (
    "Strategic Number is explicitly compiler-owned native control state; "
    "Goal storage would not preserve the declared native SN control surface."
)
_SN_STABILITY_PREFIX = "sn-state:v1"


def _validate_compiler_owned_sn_reference(
    expr: Expression,
    declared_state_names: set[str],
    *,
    demand_name: str,
) -> None:
    if expr.head in {"up-compare-sn", "strategic-number", "up-modify-sn", "set-strategic-number"}:
        if expr.args:
            target = str(expr.args[0])
            try:
                int(target, 10)
            except ValueError:
                if target not in declared_state_names:
                    raise CompileError(
                        f"demand '{demand_name}' references undeclared compiler-owned "
                        f"Strategic Number '{target}'"
                    )
    for child in expr.args:
        if isinstance(child, Expression):
            _validate_compiler_owned_sn_reference(
                child,
                declared_state_names,
                demand_name=demand_name,
            )


def _tokens(expr: str) -> list[str]:
    if not expr.startswith("(") or not expr.endswith(")"):
        raise CompileError("expression must be a parenthesized native .per expression")
    if "=>" in expr or "\n" in expr or "\r" in expr:
        raise CompileError("expression contains an invalid rule separator")
    tokens = re.findall(r"\(|\)|[^\s()]+", expr)
    if not tokens or tokens[0] != "(":
        raise CompileError("expression must start with '('")
    return tokens


def _parse(tokens: list[str], index: int = 0):
    if index >= len(tokens) or tokens[index] != "(":
        raise CompileError("malformed .per expression")
    index += 1
    if index >= len(tokens) or tokens[index] in (")", "("):
        raise CompileError("expression is missing its command")
    head = tokens[index]
    index += 1
    args = []
    while index < len(tokens) and tokens[index] != ")":
        if tokens[index] == "(":
            value, index = _parse(tokens, index)
            args.append(value)
        else:
            args.append(tokens[index])
            index += 1
    if index >= len(tokens):
        raise CompileError("unbalanced .per expression")
    return Expression(source="", head=head, args=tuple(args)), index + 1


def parse_expression(source: str, location=None) -> Expression:
    tokens = _tokens(source)
    expr, end = _parse(tokens)
    if end != len(tokens):
        raise CompileError("trailing tokens after .per expression")
    if expr.head in _LOGICAL_ARITY and len(expr.args) != _LOGICAL_ARITY[expr.head]:
        raise CompileError(
            f"logical operator '{expr.head}' requires {_LOGICAL_ARITY[expr.head]} operands"
        )
    return Expression(source=source, head=expr.head, args=expr.args, location=location)


def _validate_expression(expr: Expression, registry: PrimitiveRegistry):
    if expr.head in _LOGICAL_ARITY:
        expected = _LOGICAL_ARITY[expr.head]
        if len(expr.args) != expected:
            raise CompileError(
                f"logical operator '{expr.head}' requires {expected} operands"
            )
        for child in expr.args:
            if not isinstance(child, Expression):
                raise CompileError(f"logical operator '{expr.head}' requires nested expressions")
            _validate_expression(child, registry)
        return None
    assessment = registry.assess_support(expr.head)
    if assessment.state is not NativeSupportState.EXECUTABLE_SAFE:
        raise CompileError(
            f"{assessment.diagnostics[-1].code}: native command '{expr.head}' "
            f"is {assessment.state.value}: {assessment.message}"
        )
    primitive = registry.get(expr.head)
    if primitive is None:
        raise CompileError(
            f"NATIVE-SUPPORT-005: native command '{expr.head}' has no semantic adapter"
        )
    try:
        registry.validate_native_signature(expr.head, len(expr.args))
        registry.validate_adapter_contract(primitive)
    except ValueError as exc:
        raise CompileError(str(exc)) from exc
    if not (primitive.min_args <= len(expr.args) <= primitive.max_args):
        raise CompileError(
            f"primitive '{expr.head}' expects {primitive.min_args} argument(s), "
            f"got {len(expr.args)}"
        )
    if any(isinstance(a, Expression) for a in expr.args):
        raise CompileError(f"nested expression is not supported in primitive '{expr.head}'")
    return primitive


def _root_roles(expr: Expression, registry: PrimitiveRegistry) -> set[str]:
    # Validate the logical node itself before descending. Otherwise a nested
    # malformed logical expression can bypass _validate_expression entirely.
    if expr.head in _LOGICAL_ARITY:
        expected = _LOGICAL_ARITY[expr.head]
        if len(expr.args) != expected:
            raise CompileError(
                f"logical operator '{expr.head}' requires {expected} operands"
            )
        roles = set()
        for child in expr.args:
            roles.update(_root_roles(child, registry))
        return roles
    primitive = _validate_expression(expr, registry)
    return {primitive.role}


def _context_roles(expr: Expression, registry: PrimitiveRegistry) -> set[str]:
    roles = _root_roles(expr, registry)
    if not roles:
        raise CompileError("expression has no semantic role")
    return roles


def _validate_completion_witness(expr: Expression, registry: PrimitiveRegistry):
    if expr.head in _LOGICAL_ARITY:
        expected = _LOGICAL_ARITY[expr.head]
        if len(expr.args) != expected:
            raise CompileError(
                f"logical operator '{expr.head}' requires {expected} operands"
            )
        for child in expr.args:
            _validate_completion_witness(child, registry)
        return
    primitive = registry.require(expr.head)
    if not primitive.completion_witness:
        raise CompileError(
            f"completion witness '{expr.head}' does not prove completed world state"
        )


def _validate_context(expr: Expression, registry: PrimitiveRegistry, allowed: set[str], context: str):
    roles = _context_roles(expr, registry)
    if not roles.issubset(allowed):
        actual = ", ".join(sorted(roles))
        expected = ", ".join(sorted(allowed))
        raise CompileError(f"{context}: expression has role {actual}; expected only {expected}")


def _validate_action(expr: Expression, registry: PrimitiveRegistry, context: str):
    if expr.head in _LOGICAL_ARITY:
        raise CompileError(
            f"{context}: action must be one native action command, not logical "
            f"operator '{expr.head}'"
        )
    primitive = _validate_expression(expr, registry)
    if primitive.kind != "ACTION":
        raise CompileError(f"{context}: command '{expr.head}' is not an action primitive")
    _validate_context(expr, registry, {"ACTION"}, context)
    return primitive


def _stored_role(expr: Expression, registry: PrimitiveRegistry) -> str:
    roles = _context_roles(expr, registry)
    return next(iter(roles)) if len(roles) == 1 else "COMPOSITE"


def _has_non_timing_evidence(expr: Expression, registry: PrimitiveRegistry) -> bool:
    roles = _context_roles(expr, registry)
    return bool(roles & {"OBSERVATION", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION", "PERSISTENT_STATE"})


def _is_timing_only(expr: Expression, registry: PrimitiveRegistry) -> bool:
    return _context_roles(expr, registry) == {"TIMING"}


def _pending_diagnostics(demand: DemandNode):
    action = parse_expression(demand.action)
    witness = parse_expression(demand.witness)
    release = parse_expression(demand.release)
    return (
        PendingDiagnostic(
            "PENDING-ACTION-GUARD",
            "INFO",
            "action is gated by active goal {active_goal} and cannot reissue from pending goal {pending_goal}",
        ),
        PendingDiagnostic(
            "PENDING-WITNESS-GUARD",
            "INFO",
            "completion witness is evaluated only while pending goal {pending_goal} is active",
        ),
        PendingDiagnostic(
            "PENDING-RELEASE-GUARD",
            "INFO",
            "release is evaluated only after completion goal {completed_goal} is reached",
        ),
        PendingDiagnostic(
            "PENDING-ACTION-WITNESS-SEPARATE",
            "INFO",
            f"action '{action.head}' is not treated as completion evidence; witness '{witness.head}' owns completion",
        ),
        PendingDiagnostic(
            "PENDING-RELEASE-SEPARATE",
            "INFO",
            f"release remains separate from witness '{witness.head}' and may clear the demand only from complete state",
        ),
    )


def analyze(
    demands: list[DemandNode],
    registry: PrimitiveRegistry,
    source_unit: str | None = None,
    *,
    building_id_resolver=resolve_building_id,
) -> list[SemanticDemand]:
    result = []
    seen_strategic_number_names: set[str] = set()
    seen_timer_names: set[str] = set()
    for demand in demands:
        demand_source_unit = source_unit or demand.location.source_unit
        requirements = []
        for requirement_index, raw in enumerate(demand.requirements):
            location = (
                demand.requirement_locations[requirement_index]
                if requirement_index < len(demand.requirement_locations)
                else demand.location
            )
            expr = parse_expression(raw, location)
            _validate_context(
                expr,
                registry,
                {"OBSERVATION", "TIMING", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION", "PERSISTENT_STATE"},
                f"demand '{demand.name}' requirement",
            )
            requirements.append(
                SemanticRequirement(
                    expr,
                    _stored_role(expr, registry),
                    location=location,
                )
            )
        if any(_context_roles(req.expression, registry) == {"TIMING"} for req in requirements):
            if not any(_has_non_timing_evidence(req.expression, registry) for req in requirements):
                raise CompileError("TIMING-WITHOUT-WORLD-EVIDENCE: demand " + demand.name + " uses timing as its only evidence")
        action = parse_expression(demand.action, demand.action_location or demand.location)
        action_primitive = _validate_action(
            action,
            registry,
            f"demand '{demand.name}' action",
        )
        arbitration_request = None
        if action_primitive.conflict_class:
            owner = SemanticId(source_unit=demand_source_unit, local_name="__execution_memory__")
            arbitration_request = GoalSlotRequest(
                request_id=StorageRequestId(
                    owner=owner,
                    purpose=f"action-claim:{action_primitive.conflict_class}",
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
        if not demand.witness.strip() or demand.witness.strip() == "()":
            raise CompileError(f"PENDING-WITNESS-MISSING: demand '{demand.name}' has no completion witness")
        witness = parse_expression(
            demand.witness,
            demand.witness_location or demand.location,
        )
        _validate_context(
            witness,
            registry,
            {"OBSERVATION", "WITNESS", "TIMING", "ACTION"},
            f"demand '{demand.name}' witness",
        )

        semantic_id = SemanticId(source_unit=demand_source_unit, local_name=demand.name)
        construction_lifecycle = None
        construction_retry_barrier = None
        if action.head == "build":
            if len(action.args) != 1 or not isinstance(action.args[0], str):
                raise CompileError(
                    f"CONSTRUCTION-BUILD-TARGET: demand '{demand.name}' build action "
                    "must have one literal BuildingId argument"
                )
            building = action.args[0]
            try:
                native_building_id = building_id_resolver(building)
            except (NativeBuildingIdError, KeyError, TypeError, ValueError) as exc:
                raise CompileError(
                    f"CONSTRUCTION-BUILD-ID: demand '{demand.name}' cannot resolve "
                    f"BuildingId '{building}'"
                ) from exc
            native_token = str(native_building_id)
            construction_retry_barrier = GoalSlotRequest(
                request_id=StorageRequestId(
                    owner=semantic_id,
                    purpose="construction-retry-barrier",
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
            construction_lifecycle = ConstructionLifecycle(
                building=building,
                native_building_id=native_building_id,
                completion_witness=witness,
                pending_foundation_fact=Expression(
                    source=f"(up-pending-objects c: {native_token} >= 1)",
                    head="up-pending-objects",
                    args=("c:", native_token, ">=", "1"),
                    location=action.location,
                ),
                pending_placement_fact=Expression(
                    source=f"(up-pending-placement c: {native_token})",
                    head="up-pending-placement",
                    args=("c:", native_token),
                    location=action.location,
                ),
            )

        release = parse_expression(
            demand.release,
            demand.release_location or demand.location,
        )
        _validate_context(
            release,
            registry,
            {"OBSERVATION", "WITNESS", "TIMING", "ACTION"},
            f"demand '{demand.name}' release",
        )
        invalidation = None
        if demand.invalidate and demand.invalidate.strip():
            invalidation = parse_expression(
                demand.invalidate,
                demand.invalidate_location or demand.location,
            )
            _validate_context(
                invalidation,
                registry,
                {"OBSERVATION", "ADMISSIBILITY", "WITNESS", "TIMING", "ACTION"},
                f"demand '{demand.name}' invalidation",
            )
        strategic_number_states = []
        for state_name, initial_value, state_location in demand.strategic_number_states:
        timer_states = []
        for timer_name, timer_location in demand.timer_states:
            if timer_name in seen_timer_names:
                raise CompileError(
                    f"duplicate compiler-owned Timer state '{timer_name}'"
                )
            seen_timer_names.add(timer_name)
            timer_request_id = StorageRequestId(
                owner=semantic_id,
                purpose=f"timer:{timer_name}",
            )
            timer_request = TimerRequest(
                request_id=timer_request_id,
                initialization_policy="DISABLE_BEFORE_FIRST_USE",
                stability_key=(
                    f"timer-state:v1:"
                    f"{demand_source_unit}:{demand.name}:{timer_name}"
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
            timer_states.append(
                TimerState(
                    name=timer_name,
                    request=timer_request,
                    location=timer_location,
                )
            )

            if not _SN_STATE_NAME_RE.fullmatch(state_name):
                raise CompileError(
                    f"demand '{demand.name}' has invalid Strategic Number state name '{state_name}'"
                )
            if state_name.startswith(_SN_RESERVED_PREFIXES):
                raise CompileError(
                    f"demand '{demand.name}' Strategic Number state '{state_name}' "
                    "uses a reserved compiler/native prefix"
                )
            if state_name in seen_strategic_number_names:
                raise CompileError(
                    f"duplicate compiler-owned Strategic Number state name '{state_name}'"
                )
            seen_strategic_number_names.add(state_name)
            request_id = StorageRequestId(
                owner=semantic_id,
                purpose=f"strategic-number:{state_name}",
            )
            request = StrategicNumberStorageRequest(
                request_id=request_id,
                why_not_goal=_SN_WHY_NOT_GOAL,
                stability_key=(
                    f"{_SN_STABILITY_PREFIX}:"
                    f"{demand_source_unit}:{demand.name}:{state_name}"
                ),
                role=GoalRole.PERSISTENT_STATE,
                native_contract_id="set-strategic-number",
            )
            strategic_number_states.append(
                StrategicNumberState(
                    name=state_name,
                    initial_value=initial_value,
                    request=request,
                    location=state_location,
                )
            )

        declared_state_names = {state.name for state in strategic_number_states}
        for requirement in requirements:
            _validate_compiler_owned_sn_reference(
                requirement.expression,
                declared_state_names,
                demand_name=demand.name,
            )
        _validate_compiler_owned_sn_reference(
            witness,
            declared_state_names,
            demand_name=demand.name,
        )
        _validate_compiler_owned_sn_reference(
            release,
            declared_state_names,
            demand_name=demand.name,
        )
        if invalidation is not None:
            _validate_compiler_owned_sn_reference(
                invalidation,
                declared_state_names,
                demand_name=demand.name,
            )

        request_id = StorageRequestId(owner=semantic_id, purpose="lifecycle")
        lifecycle = LifecycleStorage(
            slot=GoalSlotRequest(request_id=request_id, role=GoalRole.LIFECYCLE_STATE),
            initial_state=LifecycleState.ACTIVE,
        )
        lifecycle_base = len(demands) + (len(result) * 8)
        completion_witness = CompletionWitnessContract(
            identity=SemanticId(
                source_unit=demand_source_unit,
                local_name=f"{demand.name}-witness",
            ),
            evidence_kind=WitnessEvidenceKind.WORLD_STATE,
            primitive=witness.head,
            expression=witness,
            establishes=semantic_id,
            source_order=lifecycle_base + 2,
            issuance_source_order=lifecycle_base + 6,
            location=witness.location,
        )
        ownership = DemandOwnership(
            demand=semantic_id,
            owner=semantic_id,
            state=request_id,
        )
        release_state = ReleaseStateContract(
            identity=SemanticId(
                source_unit=demand_source_unit,
                local_name=f"{demand.name}-release",
            ),
            evidence_kind=ReleaseEvidenceKind.WORLD_STATE,
            primitive=release.head,
            expression=release,
            establishes=semantic_id,
            from_state=LifecycleState.COMPLETE,
            to_state=LifecycleState.RELEASED,
            source_order=lifecycle_base,
            witness_source_order=lifecycle_base + 2,
            location=release.location,
        )
        cancellation = None
        if invalidation is not None:
            invalidation_contract = InvalidationContract(
                identity=SemanticId(
                    source_unit=demand_source_unit,
                    local_name=f"{demand.name}-invalidation",
                ),
                evidence_kind=InvalidationEvidenceKind.WORLD_STATE,
                primitive=invalidation.head,
                expression=invalidation,
                invalidates=semantic_id,
                source_order=max(0, lifecycle_base - 1),
                action_source_order=lifecycle_base + 6,
                location=invalidation.location,
            )
            cancellation = CancellationStateContract(
                identity=SemanticId(
                    source_unit=demand_source_unit,
                    local_name=f"{demand.name}-cancellation",
                ),
                trigger=invalidation_contract.identity,
                from_states=(
                    LifecycleState.ACTIVE,
                    LifecycleState.ISSUED,
                    LifecycleState.PENDING,
                ),
                to_state=LifecycleState.CANCELLED,
                source_order=invalidation_contract.source_order,
                invalidation_source_order=invalidation_contract.source_order,
                release_source_order=lifecycle_base,
            )
        else:
            invalidation_contract = None
        action_issuance = ActionIssuance(
            demand=semantic_id,
            primitive=action.head,
            phase=ActionIssuancePhase.ATTEMPT,
            issued_state=LifecycleState.ISSUED,
            pending_state=LifecycleState.PENDING,
            failure=ActionIssuanceFailure.RETAIN_ACTIVE,
            retryable=True,
            source_order=lifecycle_base + 6,
            location=action.location,
        )
        state_accesses = (
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.WRITE,
                phase=LifecycleAccessPhase.INITIALIZATION,
                source_order=len(result),
                operation="initialize",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.READ,
                phase=LifecycleAccessPhase.RELEASE,
                source_order=lifecycle_base,
                operation="release",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.WRITE,
                phase=LifecycleAccessPhase.RELEASE,
                source_order=lifecycle_base + 1,
                operation="release",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.READ,
                phase=LifecycleAccessPhase.COMPLETION_WITNESS,
                source_order=lifecycle_base + 2,
                operation="completion-witness",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.WRITE,
                phase=LifecycleAccessPhase.COMPLETION_WITNESS,
                source_order=lifecycle_base + 3,
                operation="completion-witness",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.READ,
                phase=LifecycleAccessPhase.PENDING_ADMISSION,
                source_order=lifecycle_base + 4,
                operation="pending-admission",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.WRITE,
                phase=LifecycleAccessPhase.PENDING_ADMISSION,
                source_order=lifecycle_base + 5,
                operation="pending-admission",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.READ,
                phase=LifecycleAccessPhase.ISSUANCE,
                source_order=lifecycle_base + 6,
                operation="action-issuance",
            ),
            StateAccess(
                state=request_id,
                owner=semantic_id,
                demand=semantic_id,
                kind=AccessKind.WRITE,
                phase=LifecycleAccessPhase.ISSUANCE,
                source_order=lifecycle_base + 7,
                operation="action-issuance",
            ),
        )
        result.append(
            SemanticDemand(
                identity=semantic_id,
                lifecycle=lifecycle,
                requirements=tuple(requirements),
                action=SemanticAction(
                    action,
                    "ACTION",
                    arbitration_request,
                    location=action.location,
                ),
                action_issuance=action_issuance,
                witness=witness,
                completion_witness=completion_witness,
                release=release,
                release_state=release_state,
                invalidation=invalidation_contract,
                cancellation=cancellation,
                ownership=ownership,
                state_accesses=state_accesses,
                pending_diagnostics=_pending_diagnostics(demand),
                construction_lifecycle=construction_lifecycle,
                construction_retry_barrier=construction_retry_barrier,
                strategic_number_states=tuple(strategic_number_states),
                timer_states=tuple(timer_states),
                location=demand.location,
            )
        )
    return result
