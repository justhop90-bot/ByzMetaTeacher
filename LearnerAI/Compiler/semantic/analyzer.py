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
    ProductionLifecycle,
    ResearchLifecycle,
    ResearchState,
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
    PersistentControlId,
    PersistentControlKind,
    PersistentControlRef,
    StrategicNumberState,
    StrategicNumberStorageRequest,
    TimerRequest,
    TimerState,
)
from ..primitives import NativeSupportState, PrimitiveRegistry
from .construction import canonical_build_completion_witness
from .native_building_catalog import NativeBuildingIdError, resolve_building_id
from .native_unit_catalog import NativeUnitIdError, resolve_unit_id
from .native_tech_catalog import NativeTechIdError, resolve_tech_id

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
    if _is_open_production_queue_capacity_control(expr):
        return
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


def _render_expression(expr: Expression) -> str:
    parts = [expr.head]
    for argument in expr.args:
        if isinstance(argument, Expression):
            parts.append(_render_expression(argument))
        else:
            parts.append(str(argument))
    return "(" + " ".join(parts) + ")"


def _populate_expression_sources(
    expr: Expression,
    *,
    root_source: str | None = None,
    location=None,
) -> Expression:
    nested_args = tuple(
        _populate_expression_sources(argument)
        if isinstance(argument, Expression)
        else argument
        for argument in expr.args
    )
    return Expression(
        source=root_source if root_source is not None else _render_expression(
            Expression(source="", head=expr.head, args=nested_args)
        ),
        head=expr.head,
        args=nested_args,
        location=location if location is not None else expr.location,
    )



def parse_expression(source: str, location=None) -> Expression:
    tokens = _tokens(source)
    try:
        expr, end = _parse(tokens)
    except CompileError as exc:
        if str(exc) in {
            "unbalanced .per expression",
            "logical operator 'or' requires 2 operands",
            "logical operator 'and' requires 2 operands",
        }:
            raise CompileError(
                f"{exc}: {source}"
            ) from exc
        raise
    if end != len(tokens):
        raise CompileError(
            f"trailing tokens after .per expression: {source}"
        )
    if expr.head in _LOGICAL_ARITY and len(expr.args) != _LOGICAL_ARITY[expr.head]:
        raise CompileError(
            f"logical operator '{expr.head}' requires "
            f"{_LOGICAL_ARITY[expr.head]} operands: {source}"
        )
    return _populate_expression_sources(
        expr,
        root_source=source,
        location=location,
    )


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


def _is_open_production_queue_capacity_control(expr: Expression) -> bool:
    if expr.head != "up-compare-sn" or len(expr.args) != 3:
        return False
    if str(expr.args[0]) not in {"264", "sn-enable-training-queue"}:
        return False
    if str(expr.args[1]) != "==":
        return False
    try:
        value = int(str(expr.args[2]), 10)
    except (TypeError, ValueError):
        return False
    return 0 <= value <= 15


def _persistent_goal_read(expr: Expression, registry: PrimitiveRegistry) -> bool:
    # Goal reads are persistent-state observations. The generic native-support
    # registry intentionally keeps them engine-semantics-mapped, but demand
    # requirements are explicitly allowed to consume persistent state. Writes
    # remain on the native control plane and witness contexts still reject the
    # PERSISTENT_STATE role below.
    if expr.head not in {"goal", "up-compare-goal"}:
        return False
    native = registry.require_native(expr.head)
    registry.validate_native_signature(expr.head, len(expr.args))
    if native.command_type != "Fact":
        raise ValueError(
            f"persistent goal read '{expr.head}' is not registered as a native fact"
        )
    return True


def _root_roles(expr: Expression, registry: PrimitiveRegistry) -> set[str]:
    # SN 264 is accepted here only as OPEN production-capacity evidence. It
    # remains forbidden in all other contexts because ordinary Strategic
    # Number state is an engine-control effect, not a generic observation.
    if _is_open_production_queue_capacity_control(expr):
        return {"PERSISTENT_STATE"}
    if _persistent_goal_read(expr, registry):
        return {"PERSISTENT_STATE"}
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
        production_lifecycle = None
        production_retry_barrier = None
        research_lifecycle = None
        research_retry_barrier = None
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

        elif action.head == "train":
            if len(action.args) != 1 or not isinstance(action.args[0], str):
                raise CompileError(
                    f"PRODUCTION-TRAIN-TARGET: demand '{demand.name}' train action "
                    "must have one literal unit target"
                )
            unit = action.args[0]
            if witness.head != "unit-type-count":
                raise CompileError(
                    f"PRODUCTION-COMPLETION-WITNESS: demand '{demand.name}' "
                    "production completion witness must use unit-type-count"
                )
            if (
                not witness.args
                or str(witness.args[0]) != unit
            ):
                raise CompileError(
                    f"PRODUCTION-COMPLETION-WITNESS: demand '{demand.name}' "
                    f"production completion witness must target unit '{unit}'"
                )
            try:
                native_unit_id = resolve_unit_id(unit)
            except (NativeUnitIdError, KeyError, TypeError, ValueError) as exc:
                raise CompileError(
                    f"PRODUCTION-TRAIN-ID: demand '{demand.name}' cannot resolve "
                    f"UnitId '{unit}'"
                ) from exc

            canonical_pending_requirements = []
            for requirement in requirements:
                expression = requirement.expression
                if (
                    expression.head == "up-pending-objects"
                    and len(expression.args) >= 2
                    and str(expression.args[0]) == "c:"
                    and str(expression.args[1]) == unit
                ):
                    canonical_expression = Expression(
                        source=(
                            f"(up-pending-objects c: {native_unit_id} "
                            f"{' '.join(str(arg) for arg in expression.args[2:])})"
                        ),
                        head="up-pending-objects",
                        args=(
                            "c:",
                            str(native_unit_id),
                            *tuple(str(arg) for arg in expression.args[2:]),
                        ),
                        location=expression.location,
                    )
                    requirement = SemanticRequirement(
                        canonical_expression,
                        _stored_role(canonical_expression, registry),
                        location=requirement.location,
                    )
                canonical_pending_requirements.append(requirement)
            requirements = canonical_pending_requirements

            admission_requirements = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head
                in {"can-train", "can-train-with-escrow"}
            ]
            matching_admissions = [
                expression
                for expression in admission_requirements
                if expression.args and str(expression.args[0]) == unit
            ]
            target_admission = None
            provider_state_requirements = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head == "building-type-count"
            ]
            provider_state = None
            provider_availability_evidence = None
            if len(provider_state_requirements) > 1:
                raise CompileError(
                    f"PRODUCTION-PROVIDER-STATE: demand '{demand.name}' "
                    "has multiple provider-state observations; provider selection "
                    "must be unambiguous"
                )
            if provider_state_requirements:
                provider_expression = provider_state_requirements[0]
                if not provider_expression.args:
                    raise CompileError(
                        f"PRODUCTION-PROVIDER-STATE: demand '{demand.name}' "
                        "provider-state observation has no BuildingId"
                    )
                try:
                    native_building_id = resolve_building_id(
                        str(provider_expression.args[0])
                    )
                except (NativeBuildingIdError, KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-PROVIDER-STATE-ID: demand '{demand.name}' "
                        f"cannot resolve provider BuildingId "
                        f"'{provider_expression.args[0]}'"
                    ) from exc
                canonical_provider_state = Expression(
                    source=(
                        f"(building-type-count {native_building_id} "
                        f"{' '.join(str(arg) for arg in provider_expression.args[1:])})"
                    ),
                    head="building-type-count",
                    args=(
                        str(native_building_id),
                        *tuple(str(arg) for arg in provider_expression.args[1:]),
                    ),
                    location=provider_expression.location,
                )
                try:
                    provider_state = registry.resolve_production_provider_state(
                        canonical_provider_state,
                        native_building_id=native_building_id,
                    )
                    provider_availability_evidence = (
                        registry.resolve_production_provider_availability_evidence(
                            canonical_provider_state,
                            native_building_id=native_building_id,
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-PROVIDER-STATE: demand '{demand.name}' "
                        f"cannot resolve provider-state observation: {exc}"
                    ) from exc

            provider_readiness_requirements = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head == "up-train-site-ready"
            ]
            provider_readiness_evidence = None
            if len(provider_readiness_requirements) > 1:
                raise CompileError(
                    f"PRODUCTION-PROVIDER-READINESS: demand '{demand.name}' "
                    "has multiple training-site readiness facts; provider "
                    "readiness must be unambiguous"
                )
            if provider_readiness_requirements:
                readiness_expression = provider_readiness_requirements[0]
                try:
                    provider_readiness_evidence = (
                        registry.resolve_production_provider_readiness(
                            readiness_expression,
                            native_unit_id=native_unit_id,
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-PROVIDER-READINESS: demand '{demand.name}' "
                        f"cannot resolve training-site readiness: {exc}"
                    ) from exc

                canonical_readiness = provider_readiness_evidence.expression
                requirements = [
                    (
                        SemanticRequirement(
                            canonical_readiness,
                            _stored_role(canonical_readiness, registry),
                            location=requirement.location,
                        )
                        if requirement.expression is readiness_expression
                        else requirement
                    )
                    for requirement in requirements
                ]


            production_time_requirements = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head == "game-time"
            ]
            birth_timing_evidence = None
            queue_exit_timing_evidence = None
            if len(production_time_requirements) == 1:
                time_expression = production_time_requirements[0]
                birth_requirements = [
                    requirement.expression
                    for requirement in requirements
                    if requirement.expression.head == "unit-type-count"
                    and requirement.expression.args
                    and str(requirement.expression.args[0]) == unit
                ]
                queue_total_requirements = [
                    requirement.expression
                    for requirement in requirements
                    if requirement.expression.head == "unit-type-count-total"
                    and requirement.expression.args
                    and str(requirement.expression.args[0]) in {unit, str(native_unit_id)}
                ]
                pending_requirements = [
                    requirement.expression
                    for requirement in requirements
                    if requirement.expression.head == "up-pending-objects"
                    and len(requirement.expression.args) >= 2
                    and str(requirement.expression.args[1]) in {unit, str(native_unit_id)}
                ]
                canonical_time = Expression(
                    source=f"(game-time {' '.join(str(arg) for arg in time_expression.args)})",
                    head="game-time",
                    args=tuple(str(arg) for arg in time_expression.args),
                    location=time_expression.location,
                )

                if len(birth_requirements) == 1:
                    birth_expression = birth_requirements[0]
                    canonical_birth = Expression(
                        source=(
                            f"(unit-type-count {native_unit_id} "
                            f"{' '.join(str(arg) for arg in birth_expression.args[1:])})"
                        ),
                        head="unit-type-count",
                        args=(
                            str(native_unit_id),
                            *tuple(str(arg) for arg in birth_expression.args[1:]),
                        ),
                        location=birth_expression.location,
                    )
                    try:
                        birth_timing_evidence = registry.resolve_production_birth_timing(
                            canonical_time,
                            canonical_birth,
                            native_unit_id=native_unit_id,
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        raise CompileError(
                            f"PRODUCTION-BIRTH-TIMING: demand '{demand.name}' "
                            f"cannot resolve birth timing evidence: {exc}"
                        ) from exc

                if len(queue_total_requirements) == 1 and len(pending_requirements) == 1:
                    queue_total_expression = queue_total_requirements[0]
                    pending_expression = pending_requirements[0]
                    canonical_queue_total = Expression(
                        source=(
                            f"(unit-type-count-total {native_unit_id} "
                            f"{' '.join(str(arg) for arg in queue_total_expression.args[1:])})"
                        ),
                        head="unit-type-count-total",
                        args=(
                            str(native_unit_id),
                            *tuple(str(arg) for arg in queue_total_expression.args[1:]),
                        ),
                        location=queue_total_expression.location,
                    )
                    canonical_pending = Expression(
                        source=(
                            f"(up-pending-objects c: {native_unit_id} "
                            f"{' '.join(str(arg) for arg in pending_expression.args[2:])})"
                        ),
                        head="up-pending-objects",
                        args=(
                            "c:",
                            str(native_unit_id),
                            *tuple(str(arg) for arg in pending_expression.args[2:]),
                        ),
                        location=pending_expression.location,
                    )
                    try:
                        queue_exit_timing_evidence = registry.resolve_production_queue_exit_timing(
                            canonical_time,
                            canonical_queue_total,
                            canonical_pending,
                            native_unit_id=native_unit_id,
                        )
                    except (KeyError, TypeError, ValueError) as exc:
                        raise CompileError(
                            f"PRODUCTION-QUEUE-EXIT-TIMING: demand '{demand.name}' "
                            f"cannot resolve queue-exit timing evidence: {exc}"
                        ) from exc

            matching_queue_states = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head == "unit-type-count-total"
                and requirement.expression.args
                and str(requirement.expression.args[0]) == unit
            ]
            queue_state = None
            queue_capacity_evidence = None
            if matching_queue_states:
                queue_expression = matching_queue_states[0]
                canonical_queue_state = Expression(
                    source=(
                        f"(unit-type-count-total {native_unit_id} "
                        f"{' '.join(str(arg) for arg in queue_expression.args[1:])})"
                    ),
                    head="unit-type-count-total",
                    args=(
                        str(native_unit_id),
                        *tuple(str(arg) for arg in queue_expression.args[1:]),
                    ),
                    location=queue_expression.location,
                )
                try:
                    queue_state = registry.resolve_production_queue_state(
                        canonical_queue_state,
                        native_unit_id=native_unit_id,
                    )
                    queue_capacity_evidence = (
                        registry.resolve_production_queue_capacity_evidence(
                            canonical_queue_state,
                            native_unit_id=native_unit_id,
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-QUEUE-STATE: demand '{demand.name}' "
                        f"cannot resolve queue-state observation for unit '{unit}': {exc}"
                    ) from exc
            capacity_control_requirements = [
                requirement.expression
                for requirement in requirements
                if requirement.expression.head == "up-compare-sn"
                and requirement.expression.args
                and str(requirement.expression.args[0])
                in {"264", "sn-enable-training-queue"}
            ]
            queue_capacity_control = None
            if len(capacity_control_requirements) > 1:
                raise CompileError(
                    f"PRODUCTION-QUEUE-CAPACITY: demand '{demand.name}' "
                    "has multiple SN 264 capacity-control observations; "
                    "capacity configuration must be unambiguous"
                )
            if capacity_control_requirements:
                try:
                    queue_capacity_control = (
                        registry.resolve_production_queue_capacity_control_evidence(
                            capacity_control_requirements[0]
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-QUEUE-CAPACITY: demand '{demand.name}' "
                        f"cannot resolve SN 264 capacity-control evidence: {exc}"
                    ) from exc

                # Emit the canonical numeric SnId. Native validation does not
                # infer a symbolic SN name unless a defconst alias exists.
                capacity_source = capacity_control_requirements[0]
                canonical_capacity = queue_capacity_control.expression
                requirements = [
                    (
                        SemanticRequirement(
                            canonical_capacity,
                            _stored_role(canonical_capacity, registry),
                            location=requirement.location,
                        )
                        if requirement.expression == capacity_source
                        else requirement
                    )
                    for requirement in requirements
                ]

            if matching_admissions:
                admission_expression = matching_admissions[0]
                canonical_admission = Expression(
                    source=f"({admission_expression.head} {native_unit_id})",
                    head=admission_expression.head,
                    args=(str(native_unit_id),),
                    location=admission_expression.location,
                )
                try:
                    target_admission = registry.resolve_production_target_admission(
                        canonical_admission,
                        native_unit_id=native_unit_id,
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise CompileError(
                        f"PRODUCTION-TARGET-ADMISSION: demand '{demand.name}' "
                        f"cannot resolve target admission for unit '{unit}': {exc}"
                    ) from exc

            production_retry_barrier = GoalSlotRequest(
                request_id=StorageRequestId(
                    owner=semantic_id,
                    purpose="production-retry-barrier",
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
            pending_fact = Expression(
                source=f"(up-pending-objects c: {native_unit_id} >= 1)",
                head="up-pending-objects",
                args=("c:", str(native_unit_id), ">=", "1"),
                location=action.location,
            )
            try:
                queue_protection = registry.resolve_production_queue_protection(
                    pending_fact,
                    native_unit_id=native_unit_id,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise CompileError(
                    f"PRODUCTION-QUEUE-PROTECTION: demand '{demand.name}' "
                    f"cannot resolve queue protection: {exc}"
                ) from exc
            if target_admission is not None:
                production_lifecycle = ProductionLifecycle(
                    unit=unit,
                    native_unit_id=native_unit_id,
                    target_admission=target_admission,
                    completion_witness=witness,
                    retry_barrier=production_retry_barrier,
                    queue_protection=queue_protection,
                    queue_state=queue_state,
                    provider_state=provider_state,
                    queue_capacity_evidence=queue_capacity_evidence,
                    provider_availability_evidence=provider_availability_evidence,
                    provider_readiness_evidence=provider_readiness_evidence,
                    birth_timing_evidence=birth_timing_evidence,
                    queue_exit_timing_evidence=queue_exit_timing_evidence,
                    queue_capacity_control=queue_capacity_control,
                )

        elif action.head == "research":
            if len(action.args) != 1 or not isinstance(action.args[0], str):
                raise CompileError(
                    f"RESEARCH-TARGET: demand '{demand.name}' research action "
                    "must have one literal technology target"
                )
            technology = action.args[0]
            try:
                native_tech_id = resolve_tech_id(technology)
            except (NativeTechIdError, KeyError, TypeError, ValueError) as exc:
                raise CompileError(
                    f"RESEARCH-TECH-ID: demand '{demand.name}' cannot resolve "
                    f"TechId '{technology}'"
                ) from exc
            research_retry_barrier = GoalSlotRequest(
                request_id=StorageRequestId(
                    owner=semantic_id,
                    purpose="research-retry-barrier",
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
            research_lifecycle = ResearchLifecycle(
                technology=technology,
                native_tech_id=native_tech_id,
                pending_fact=Expression(
                    source=(
                        f"(up-research-status c: {native_tech_id} >= "
                        f"{int(ResearchState.PENDING)})"
                    ),
                    head="up-research-status",
                    args=(
                        "c:",
                        str(native_tech_id),
                        ">=",
                        str(int(ResearchState.PENDING)),
                    ),
                    location=action.location,
                ),
                pending_state=ResearchState.PENDING,
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

        persistent_controls = tuple(
            PersistentControlRef(
                id=PersistentControlId(
                    source_unit=state.request.request_id.owner.source_unit,
                    local_name=f"timer:{state.name}",
                ),
                kind=PersistentControlKind.TIMER,
                owner=state.owner,
            )
            for state in timer_states
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
                production_lifecycle=production_lifecycle,
                production_retry_barrier=(
                    production_lifecycle.retry_barrier
                    if production_lifecycle is not None
                    else None
                ),
                research_lifecycle=research_lifecycle,
                research_retry_barrier=research_retry_barrier,
                strategic_number_states=tuple(strategic_number_states),
                timer_states=tuple(timer_states),
                persistent_controls=persistent_controls,
                location=demand.location,
            )
        )
    return result
