"""Semantic validation and AST -> Basilisk IR lowering."""
from __future__ import annotations
import re
from ..ast import DemandNode, Expression
from ..errors import CompileError
from ..ir import SemanticAction, SemanticDemand, SemanticRequirement
from ..primitives import PrimitiveRegistry

_LOGICAL_ARITY = {"and": 2, "or": 2, "nand": 2, "nor": 2, "xor": 2, "xnor": 2, "not": 1}

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
    return head, tuple(args), index + 1

def parse_expression(source: str) -> Expression:
    tokens = _tokens(source)
    head, args, end = _parse(tokens)
    if end != len(tokens):
        raise CompileError("trailing tokens after .per expression")
    if head in _LOGICAL_ARITY and len(args) != _LOGICAL_ARITY[head]:
        raise CompileError(f"logical operator '{head}' requires {_LOGICAL_ARITY[head]} operands")
    return Expression(source=source, head=head, args=args)

def _validate_primitive(expr: Expression, registry: PrimitiveRegistry):
    primitive = registry.get(expr.head)
    if primitive is None:
        raise CompileError(f"unknown AoE2 primitive '{expr.head}'")
    if not (primitive.min_args <= len(expr.args) <= primitive.max_args):
        raise CompileError(
            f"primitive '{expr.head}' expects {primitive.min_args} argument(s), "
            f"got {len(expr.args)}"
        )
    if primitive.kind == "FACT" and any(hasattr(a, "head") for a in expr.args):
        # Nested expressions are valid for logical operators, not ordinary first-slice facts.
        raise CompileError(f"nested expression is not supported in primitive '{expr.head}'")
    return primitive

def _validate_role(expr: Expression, registry: PrimitiveRegistry, allowed: set[str], context: str):
    primitive = _validate_primitive(expr, registry)
    if primitive.role not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise CompileError(
            f"{context}: '{expr.head}' has role {primitive.role}; expected one of {allowed_text}"
        )
    return primitive

def analyze(demands: list[DemandNode], registry: PrimitiveRegistry, base_goal: int = 1000) -> list[SemanticDemand]:
    if base_goal < 0:
        raise CompileError("base goal must be non-negative")
    result = []
    for offset, demand in enumerate(demands):
        requirements = []
        for raw in demand.requirements:
            expr = parse_expression(raw)
            role = _validate_primitive(expr, registry).role
            if role not in {"OBSERVATION", "ADMISSIBILITY", "FEASIBILITY", "RESOURCE_ARBITRATION"}:
                raise CompileError(f"demand '{demand.name}': requirement '{expr.head}' is not a valid requirement")
            requirements.append(SemanticRequirement(expr, role))
        action = parse_expression(demand.action)
        action_primitive = _validate_role(action, registry, {"ACTION"}, f"demand '{demand.name}' action")
        witness = parse_expression(demand.witness)
        _validate_role(witness, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' witness")
        release = parse_expression(demand.release)
        _validate_role(release, registry, {"OBSERVATION", "WITNESS"}, f"demand '{demand.name}' release")
        result.append(SemanticDemand(
            demand.name,
            base_goal + offset,
            tuple(requirements),
            SemanticAction(action, action_primitive.role),
            witness,
            release,
        ))
    return result
