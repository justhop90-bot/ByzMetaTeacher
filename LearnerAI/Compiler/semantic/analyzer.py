"""Semantic validation and AST -> Basilisk IR lowering."""
from __future__ import annotations
import re
from ..ast import DemandNode, Expression
from ..errors import CompileError
from ..ir import PendingDiagnostic, SemanticAction, SemanticDemand, SemanticRequirement
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
        for child in expr.args:
            if not isinstance(child, Expression):
                raise CompileError(f"logical operator '{expr.head}' requires nested expressions")
            _validate_expression(child, registry)
        return None
    primitive = registry.get(expr.head)
    if primitive is None:
        raise CompileError(f"unknown AoE2 primitive '{expr.head}'")
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


def _stored_role(expr: Expression, registry: PrimitiveRegistry) -> str:
    roles = _context_roles(expr, registry)
    return next(iter(roles)) if len(roles) == 1 else "COMPOSITE"


def _pending_diagnostics(demand: DemandNode, goal: int, pending_goal: int, completed_goal: int):
    action = parse_expression(demand.action)
    witness = parse_expression(demand.witness)
    release = parse_expression(demand.release)
    return (
        PendingDiagnostic(
            "PENDING-ACTION-GUARD",
            "INFO",
            f"action is gated by active goal {goal} and cannot reissue from pending goal {pending_goal}",
        ),
        PendingDiagnostic(
            "PENDING-WITNESS-GUARD",
            "INFO",
            f"completion witness is evaluated only while pending goal {pending_goal} is active",
        ),
        PendingDiagnostic(
            "PENDING-RELEASE-GUARD",
            "INFO",
            f"release is evaluated only after completion goal {completed_goal} is reached",
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


def analyze(demands: list[DemandNode], registry: PrimitiveRegistry, base_goal: int = 1000) -> list[SemanticDemand]:
    if base_goal < 0:
        raise CompileError("base goal must be non-negative")
    result = []
    for offset, demand in enumerate(demands):
        requirements = []
        for raw in demand.requirements:
            expr = parse_expression(raw)
            _validate_context(
                expr,
                registry,
                {"OBSERVATION", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION"},
                f"demand '{demand.name}' requirement",
            )
            requirements.append(SemanticRequirement(expr, _stored_role(expr, registry)))
        action = parse_expression(demand.action)
        _validate_context(action, registry, {"ACTION"}, f"demand '{demand.name}' action")
        if not demand.witness.strip() or demand.witness.strip() == "()":
            raise CompileError(f"PENDING-WITNESS-MISSING: demand '{demand.name}' has no completion witness")
        witness = parse_expression(demand.witness)
        _validate_context(witness, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' witness")
        _validate_completion_witness(witness, registry)
        release = parse_expression(demand.release)
        if release.head == action.head:
            raise CompileError(
                f"PENDING-RELEASE-PREMATURE: demand '{demand.name}' release cannot reuse action '{action.head}'"
            )
        _validate_context(release, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' release")
        goal = base_goal + (offset * 3)
        pending_goal = goal + 1
        completed_goal = goal + 2
        result.append(
            SemanticDemand(
                demand.name,
                goal,
                tuple(requirements),
                SemanticAction(action, "ACTION"),
                witness,
                release,
                pending_goal,
                completed_goal,
                _pending_diagnostics(demand, goal, pending_goal, completed_goal),
            )
        )
    return result
