"""Semantic validation and AST -> Basilisk IR lowering."""
from __future__ import annotations
import re
from ..ast import DemandNode, Expression
from ..errors import CompileError
from ..ir import (
    GoalRole,
    GoalSlotRequest,
    LifecycleState,
    LifecycleStorage,
    PendingDiagnostic,
    SemanticAction,
    SemanticDemand,
    SemanticId,
    SemanticRequirement,
    StorageRequestId,
)
from ..primitives import PrimitiveRegistry

_LOGICAL_ARITY = {
    "and": 2, "or": 2, "nand": 2, "nor": 2,
    "xor": 2, "xnor": 2, "not": 1,
}


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


def parse_expression(source: str) -> Expression:
    tokens = _tokens(source)
    expr, end = _parse(tokens)
    if end != len(tokens):
        raise CompileError("trailing tokens after .per expression")
    if expr.head in _LOGICAL_ARITY and len(expr.args) != _LOGICAL_ARITY[expr.head]:
        raise CompileError(
            f"logical operator '{expr.head}' requires {_LOGICAL_ARITY[expr.head]} operands"
        )
    return Expression(source=source, head=expr.head, args=expr.args)


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
    native = registry.native(expr.head)
    if native is None:
        raise CompileError(f"unknown AoE2 primitive '{expr.head}'")
    primitive = registry.get(expr.head)
    if primitive is None:
        raise CompileError(
            f"no Basilisk semantic adapter for native AoE2 command '{expr.head}'"
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
    if expr.head in _LOGICAL_ARITY:
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
    return bool(roles & {"OBSERVATION", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION"})


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
    source_unit: str = "<source>",
) -> list[SemanticDemand]:
    result = []
    for demand in demands:
        requirements = []
        for raw in demand.requirements:
            expr = parse_expression(raw)
            _validate_context(
                expr,
                registry,
                {"OBSERVATION", "TIMING", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION"},
                f"demand '{demand.name}' requirement",
            )
            requirements.append(SemanticRequirement(expr, _stored_role(expr, registry)))
        if any(_context_roles(req.expression, registry) == {"TIMING"} for req in requirements):
            if not any(_has_non_timing_evidence(req.expression, registry) for req in requirements):
                raise CompileError("TIMING-WITHOUT-WORLD-EVIDENCE: demand " + demand.name + " uses timing as its only evidence")
        action = parse_expression(demand.action)
        action_primitive = _validate_action(
            action,
            registry,
            f"demand '{demand.name}' action",
        )
        arbitration_request = None
        if action_primitive.conflict_class:
            owner = SemanticId(source_unit=source_unit, local_name="__execution_memory__")
            arbitration_request = GoalSlotRequest(
                request_id=StorageRequestId(
                    owner=owner,
                    purpose=f"action-claim:{action_primitive.conflict_class}",
                ),
                role=GoalRole.EXECUTION_MEMORY,
            )
        if not demand.witness.strip() or demand.witness.strip() == "()":
            raise CompileError(f"PENDING-WITNESS-MISSING: demand '{demand.name}' has no completion witness")
        witness = parse_expression(demand.witness)
        if "TIMING" in _context_roles(witness, registry):
            raise CompileError("TIMING-CANNOT-WITNESS: demand " + demand.name + " cannot use timing as completion witness")
        _validate_context(witness, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' witness")
        _validate_completion_witness(witness, registry)
        release = parse_expression(demand.release)
        if "TIMING" in _context_roles(release, registry):
            raise CompileError("TIMING-RELEASE-WITHOUT-WORLD-EVIDENCE: demand " + demand.name + " release cannot depend on timing")
        if release.head == action.head:
            raise CompileError(
                f"PENDING-RELEASE-PREMATURE: demand '{demand.name}' release cannot reuse action '{action.head}'"
            )
        _validate_context(release, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' release")
        semantic_id = SemanticId(source_unit=source_unit, local_name=demand.name)
        request_id = StorageRequestId(owner=semantic_id, purpose="lifecycle")
        lifecycle = LifecycleStorage(
            slot=GoalSlotRequest(request_id=request_id, role=GoalRole.LIFECYCLE_STATE),
            initial_state=LifecycleState.ACTIVE,
        )
        result.append(
            SemanticDemand(
                semantic_id,
                lifecycle,
                tuple(requirements),
                SemanticAction(action, "ACTION", arbitration_request),
                witness,
                release,
                _pending_diagnostics(demand),
            )
        )
    return result
