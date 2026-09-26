"""Recurrent native .per rule semantics over the effective source graph.

This module models rule structure and lifetime only. It deliberately does not
claim that a recurrent rule fires, that a guard is satisfiable, or that one
rule preempts another. Those are later semantic analyses.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..ast import Expression, SourceLocation
from ..errors import CompileError
from ..source_graph import EffectiveSourceGraph, EffectiveSourceSlice


class RulePassBehavior(str, Enum):
    RECURRENT = "RECURRENT"
    ONE_SHOT = "ONE_SHOT"


@dataclass(frozen=True)
class RuleAction:
    expression: Expression
    within_rule_order: int


@dataclass(frozen=True)
class EffectiveRule:
    rule_order: int
    source_location: SourceLocation
    source_slice_ordinal: int
    instance_id: str
    facts: tuple[Expression, ...]
    actions: tuple[RuleAction, ...]
    pass_behavior: RulePassBehavior
    disable_self_action_index: int | None
    fires_guaranteed: bool = False


@dataclass(frozen=True)
class RuleExecutionReport:
    rules: tuple[EffectiveRule, ...]


def _line_column(slice_: EffectiveSourceSlice, offset: int) -> SourceLocation:
    prefix = slice_.text[:offset]
    line = slice_.start_line + prefix.count("\n")
    last_newline = prefix.rfind("\n")
    if last_newline < 0:
        column = slice_.start_column + offset
    else:
        column = offset - last_newline
    return SourceLocation(line, column, str(slice_.path))


def _scan_balanced(text: str, start: int) -> int:
    if text[start] != "(":
        raise ValueError("balanced form must start with '('")
    depth = 0
    in_string = False
    escape = False
    in_comment = False
    for index in range(start, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == ";":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
            if depth < 0:
                break
    raise CompileError("RULE-PARSE-002: unterminated parenthesized expression")


def _lex_expression(source: str) -> tuple[str, ...]:
    tokens: list[str] = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = source.find("\n", index)
            index = len(source) if newline < 0 else newline + 1
            continue
        if char in "()":
            tokens.append(char)
            index += 1
            continue
        if char == '"':
            start = index
            index += 1
            escape = False
            while index < len(source):
                current = source[index]
                if escape:
                    escape = False
                elif current == "\\":
                    escape = True
                elif current == '"':
                    index += 1
                    break
                index += 1
            else:
                raise CompileError("RULE-PARSE-003: unterminated string literal")
            tokens.append(source[start:index])
            continue
        start = index
        while index < len(source) and not source[index].isspace() and source[index] not in "();":
            index += 1
        tokens.append(source[start:index])
    return tuple(tokens)


def _parse_expression(source: str, location: SourceLocation) -> Expression:
    tokens = _lex_expression(source)
    if not tokens or tokens[0] != "(":
        raise CompileError("RULE-PARSE-004: expression must start with '('")

    def parse_at(index: int) -> tuple[Expression | str, int]:
        if index >= len(tokens) or tokens[index] != "(":
            raise CompileError("RULE-PARSE-004: malformed parenthesized expression")
        index += 1
        if index >= len(tokens) or tokens[index] in {")", "("}:
            raise CompileError("RULE-PARSE-004: expression is missing its command")
        head = tokens[index]
        index += 1
        args: list[object] = []
        while index < len(tokens) and tokens[index] != ")":
            if tokens[index] == "(":
                value, index = parse_at(index)
                args.append(value)
            else:
                args.append(tokens[index])
                index += 1
        if index >= len(tokens):
            raise CompileError("RULE-PARSE-004: unterminated expression")
        return Expression(source=source.strip(), head=head, args=tuple(args), location=location), index + 1

    expression, end = parse_at(0)
    if not isinstance(expression, Expression) or end != len(tokens):
        raise CompileError("RULE-PARSE-004: trailing tokens after expression")
    return expression


def _top_level_forms(text: str) -> tuple[tuple[int, int], ...]:
    forms: list[tuple[int, int]] = []
    index = 0
    while index < body_end:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if char == "(":
            end = _scan_balanced(text, index)
            forms.append((index, end))
            index = end
            continue
        index += 1
    return tuple(forms)


def _split_rule_body(
    text: str,
    slice_: EffectiveSourceSlice,
    body_start: int,
    body_end: int,
    source_offset: int,
) -> tuple[tuple[Expression, ...], tuple[RuleAction, ...]]:
    facts: list[Expression] = []
    actions: list[RuleAction] = []
    arrow_start: int | None = None
    index = body_start

    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = text.find("\n", index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("=>", index):
            if arrow_start is not None:
                location = _line_column(slice_, source_offset + index)
                raise CompileError(
                    f"RULE-PARSE-001: multiple '=>' separators at "
                    f"{location.source_unit}:{location.line}:{location.column}"
                )
            arrow_start = index
            index += 2
            continue
        if char != "(":
            location = _line_column(slice_, index)
            raise CompileError(
                f"RULE-PARSE-005: unexpected token in defrule at "
                f"{location.source_unit}:{location.line}:{location.column}"
            )
        end = _scan_balanced(text, index)
        location = _line_column(slice_, index)
        expression = _parse_expression(text[index:end], location)
        if arrow_start is None:
            facts.append(expression)
        else:
            actions.append(
                RuleAction(
                    expression=expression,
                    within_rule_order=len(actions),
                )
            )
        index = end

    if arrow_start is None:
        location = _line_column(slice_, source_offset + body_start)
        raise CompileError(
            f"RULE-PARSE-001: defrule is missing '=>' at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )
    if not facts:
        location = _line_column(slice_, body_start)
        raise CompileError(
            f"RULE-PARSE-006: defrule has no facts at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )
    if not actions:
        location = _line_column(slice_, source_offset + arrow_start + 2)
        raise CompileError(
            f"RULE-PARSE-007: defrule has no actions at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )
    return tuple(facts), tuple(actions)


def _parse_rule(slice_: EffectiveSourceSlice, start: int, end: int) -> EffectiveRule:
    source = slice_.text[start:end]
    location = _line_column(slice_, start)

    outer_end = _scan_balanced(source, 0)
    if outer_end != len(source):
        raise CompileError(
            f"RULE-PARSE-008: defrule form boundary is malformed at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )

    index = 1
    while index < len(source) and source[index].isspace():
        index += 1
    command_start = index
    while index < len(source) and not source[index].isspace() and source[index] not in "()":
        index += 1
    if source[command_start:index] != "defrule":
        raise CompileError(
            f"RULE-PARSE-008: top-level form is not defrule at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )

    while index < len(source) and source[index].isspace():
        index += 1
    name_start = index
    while index < len(source) and not source[index].isspace() and source[index] not in "()":
        index += 1
    rule_name = source[name_start:index]
    if not rule_name or rule_name == "=>":
        raise CompileError(
            f"RULE-PARSE-009: defrule is missing its rule name at "
            f"{location.source_unit}:{location.line}:{location.column}"
        )

    body_start = index
    facts, actions = _split_rule_body(
        source,
        slice_,
        body_start,
        outer_end - 1,
        start,
    )
    disable_self_indices = [
        index
        for index, action in enumerate(actions)
        if action.expression.head == "disable-self"
    ]
    disable_self_index = disable_self_indices[0] if disable_self_indices else None
    pass_behavior = (
        RulePassBehavior.ONE_SHOT
        if disable_self_index is not None
        else RulePassBehavior.RECURRENT
    )
    return EffectiveRule(
        rule_order=0,
        source_location=location,
        source_slice_ordinal=slice_.ordinal,
        instance_id=slice_.instance_id,
        facts=facts,
        actions=actions,
        pass_behavior=pass_behavior,
        disable_self_action_index=disable_self_index,
        fires_guaranteed=False,
    )


def analyze_effective_rules(graph: EffectiveSourceGraph) -> RuleExecutionReport:
    rules: list[EffectiveRule] = []
    for slice_ in sorted(graph.slices, key=lambda item: item.ordinal):
        for start, end in _top_level_forms(slice_.text):
            form = slice_.text[start:end]
            tokens = _lex_expression(form)
            if len(tokens) >= 2 and tokens[0] == "(" and tokens[1] == "defrule":
                rule = _parse_rule(slice_, start, end)
                rule = EffectiveRule(
                    rule_order=len(rules) + 1,
                    source_location=rule.source_location,
                    source_slice_ordinal=rule.source_slice_ordinal,
                    instance_id=rule.instance_id,
                    facts=rule.facts,
                    actions=rule.actions,
                    pass_behavior=rule.pass_behavior,
                    disable_self_action_index=rule.disable_self_action_index,
                    fires_guaranteed=False,
                )
                rules.append(rule)
    return RuleExecutionReport(tuple(rules))


__all__ = [
    "EffectiveRule",
    "RuleAction",
    "RuleExecutionReport",
    "RulePassBehavior",
    "analyze_effective_rules",
]
