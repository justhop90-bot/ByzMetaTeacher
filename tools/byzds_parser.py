#!/usr/bin/env python3
"""Deterministic BYZDS parser, lifecycle validator, and matrix aggregator.

The parser consumes the declarative cross-event constraint specification and the
line-oriented BYZDS protocol. It deliberately keeps wire parsing, lifecycle
state, constraint evaluation, and aggregation separate.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RESULT_PRECEDENCE = {"PASS": 0, "FAIL": 1, "INVALID": 2, "INFRA_ERROR": 3}
RESULTS = tuple(RESULT_PRECEDENCE)

EVENT_FIELDS = {
    "CASE_START": ("case_id", "controller", "scenario", "initial_state", "initial_retry"),
    "CASE_END": ("result", "event_count"),
    "DEMAND_ON": ("source",),
    "DEMAND_OFF": ("source",),
    "ADMITTED": ("attempt",),
    "TARGET_SELECTED": ("target", "attempt"),
    "TARGET_INVALIDATED": ("target", "attempt"),
    "ACTION": ("action", "target", "attempt"),
    "FOUNDATION": ("target", "attempt"),
    "COMPLETION": ("attempt", "building_count"),
    "FAILURE": ("attempt", "reason"),
    "RETRY": ("retry_count", "next_attempt"),
    "BLOCKED": ("retry_count",),
    "RECOVERED": ("previous_state", "new_state", "retry_count"),
    "RELEASE": ("reason",),
    "ERROR": ("code", "reason"),
}

STATES = {
    "UNINITIALIZED", "IDLE", "DEMANDED", "ADMITTED", "ISSUED", "FOUNDATION",
    "FAILED", "RETRY_READY", "BLOCKED", "RECOVERED", "COMPLETED", "RELEASED", "ENDED",
}
ACTIONS = {"BUILD_LUMBER_CAMP", "BUILD_MINING_CAMP", "BUILD_MILL"}
FAILURE_REASONS = {"NO_FOUNDATION", "FOUNDATION_LOST", "PLACEMENT_INVALID",
                    "TARGET_UNAVAILABLE", "ACTION_NOT_OBSERVED"}
RELEASE_REASONS = {"COMPLETED", "DEMAND_REMOVED", "RECOVERED"}
ERROR_CODES = {"MISSING_FOUNDATION", "STALE_TARGET", "UNEXPECTED_ACTION",
               "INVALID_STATE", "ENGINE_TIMEOUT", "LOGGING_FAILURE"}
CONTROLLERS = {
    "lumber-1", "lumber-2", "wood-3", "wood-4", "wood-5", "wood-6",
    "gold-1", "gold-2", "gold-3", "gold-4", "gold-5",
    "stone-1", "stone-2", "stone-3", "stone-4", "stone-5", "mill",
}
SCENARIOS = {"R1_FIRST_FAILURE", "R2_SECOND_FAILURE", "R3_THIRD_FAILURE",
             "R4_BLOCKED_RECOVERY", "R5_STALE_TARGET", "R6_COMPLETION"}

_INT = re.compile(r"^(0|[1-9][0-9]*)$")
_CASE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ESCAPES = re.compile(r"%(?:25|09|0A|0D|3D|3A)")


class BYZDSInvalid(ValueError):
    """Malformed wire/protocol input."""


@dataclass
class Event:
    index: int
    type: str
    fields: dict[str, Any]


@dataclass
class ConstraintResult:
    constraint_id: str
    event_index: int
    case_id: str
    satisfied: bool
    classification: str
    code: str
    terminal: bool
    observed: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "event_index": self.event_index,
            "case_id": self.case_id,
            "satisfied": self.satisfied,
            "classification": self.classification,
            "code": self.code,
            "terminal": self.terminal,
            "observed": self.observed,
        }


@dataclass
class RuntimeState:
    lifecycle_state: str = "IDLE"
    attempt_number: int = 0
    retry_count: int = 0
    active_target: str | None = None
    active_action: str | None = None
    target_invalidated: bool = False
    invalidated_target: str | None = None
    has_fresh_target_selection: bool = False
    target_selected_after_invalidation: bool = False
    failure_seen: bool = False
    last_failure_reason: str | None = None
    foundation_seen: bool = False
    foundation_target: str | None = None
    completion_seen: bool = False
    completion_target: str | None = None
    building_count_before_attempt: int = 0
    building_count_after_completion: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "lifecycle_state": self.lifecycle_state,
            "attempt_number": self.attempt_number,
            "retry_count": self.retry_count,
            "active_target": self.active_target,
            "active_action": self.active_action,
            "target_invalidated": self.target_invalidated,
            "invalidated_target": self.invalidated_target,
            "has_fresh_target_selection": self.has_fresh_target_selection,
            "target_selected_after_invalidation": self.target_selected_after_invalidation,
            "failure_seen": self.failure_seen,
            "last_failure_reason": self.last_failure_reason,
            "foundation_seen": self.foundation_seen,
            "foundation_target": self.foundation_target,
            "completion_seen": self.completion_seen,
            "completion_target": self.completion_target,
            "building_count_before_attempt": self.building_count_before_attempt,
            "building_count_after_completion": self.building_count_after_completion,
        }


@dataclass
class CaseResult:
    case_id: str
    controller: str
    scenario: str
    result: str
    event_count: int
    constraint_results: list[ConstraintResult]
    errors: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "controller": self.controller,
            "scenario": self.scenario,
            "result": self.result,
            "event_count": self.event_count,
            "constraint_results": [x.as_dict() for x in self.constraint_results],
            "errors": self.errors,
        }


def _decode_reason(value: str) -> str:
    if "%" not in value:
        return value
    pos = 0
    out = []
    while pos < len(value):
        if value[pos] != "%":
            if value[pos] in "\t\r\n":
                raise BYZDSInvalid("literal control character in encoded field")
            out.append(value[pos])
            pos += 1
            continue
        match = _ESCAPES.match(value, pos)
        if not match:
            raise BYZDSInvalid("invalid percent escape")
        out.append({"%25": "%", "%09": "\t", "%0A": "\n",
                    "%0D": "\r", "%3D": "=", "%3A": ":"}[match.group()])
        pos = match.end()
    return "".join(out)


def _int(value: str) -> int:
    if not _INT.fullmatch(value):
        raise BYZDSInvalid(f"invalid integer: {value!r}")
    return int(value)


def parse_line(line: str, index: int) -> Event | None:
    if line.endswith("\r"):
        line = line[:-1]
    if not line or line.startswith("#"):
        return None
    parts = line.split("\t")
    if len(parts) < 4 or parts[0] != "BYZDS" or parts[1] != "1":
        raise BYZDSInvalid(f"line {index}: invalid BYZDS header")
    event_type = parts[3]
    if event_type not in EVENT_FIELDS:
        raise BYZDSInvalid(f"line {index}: unknown event type {event_type!r}")
    names = EVENT_FIELDS[event_type]
    values = parts[4:]
    if len(values) != len(names):
        raise BYZDSInvalid(f"line {index}: {event_type} expects {len(names)} fields")
    fields: dict[str, Any] = {}
    for name, raw in zip(names, values):
        if name == "reason" and event_type in {"FAILURE", "ERROR"}:
            fields[name] = _decode_reason(raw)
        elif name in {"attempt", "retry_count", "next_attempt", "event_count", "building_count"}:
            fields[name] = _int(raw)
        else:
            fields[name] = raw
    return Event(index, event_type, fields)


def parse_events(text: str) -> list[Event]:
    events = []
    for index, line in enumerate(text.splitlines(), 1):
        event = parse_line(line, index)
        if event is not None:
            events.append(event)
    return events


class SafeExpression:
    """Small deterministic expression evaluator for the declared constraint DSL."""

    ALLOWED = {
        ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
        ast.Compare, ast.Eq, ast.NotEq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
        ast.Name, ast.Attribute, ast.Constant, ast.Add, ast.Sub, ast.Is,
        ast.IsNot, ast.Load,
    }

    def __init__(self, expression: str):
        self.expression = expression
        self.tree = ast.parse(expression, mode="eval")
        for node in ast.walk(self.tree):
            if type(node) not in self.ALLOWED:
                raise BYZDSInvalid(f"unsupported constraint expression: {expression!r}")

    def evaluate(self, context: dict[str, Any]) -> bool:
        return bool(self._eval(self.tree.body, context))

    def _eval(self, node: ast.AST, ctx: dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return ctx[node.id]
        if isinstance(node, ast.Attribute):
            base = self._eval(node.value, ctx)
            if isinstance(base, dict):
                return base[node.attr]
            return getattr(base, node.attr)
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, ctx) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp):
            return not self._eval(node.operand, ctx)
        if isinstance(node, ast.Compare):
            left = self._eval(node.left, ctx)
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval(comp, ctx)
                if isinstance(op, ast.Eq): ok = left == right
                elif isinstance(op, ast.NotEq): ok = left != right
                elif isinstance(op, ast.Gt): ok = left > right
                elif isinstance(op, ast.GtE): ok = left >= right
                elif isinstance(op, ast.Lt): ok = left < right
                elif isinstance(op, ast.Is): ok = left is right
                elif isinstance(op, ast.IsNot): ok = left is not right
                else: raise BYZDSInvalid("unsupported comparison")
                if not ok: return False
                left = right
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._eval(node.left, ctx) + self._eval(node.right, ctx)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            return self._eval(node.left, ctx) - self._eval(node.right, ctx)
        raise BYZDSInvalid("unsupported constraint expression node")


def _set_state_for_event(state: RuntimeState, event: Event) -> None:
    t, f = event.type, event.fields
    if t == "DEMAND_ON":
        state.lifecycle_state = "DEMANDED"
    elif t == "ADMITTED":
        state.lifecycle_state = "ADMITTED"
        state.attempt_number = f["attempt"]
        state.has_fresh_target_selection = False
        state.target_selected_after_invalidation = False
        state.foundation_seen = False
        state.foundation_target = None
        state.completion_seen = False
        state.completion_target = None
        state.active_action = None
    elif t == "TARGET_SELECTED":
        state.active_target = f["target"]
        state.target_invalidated = False
        state.invalidated_target = None
        state.has_fresh_target_selection = True
        state.target_selected_after_invalidation = False
        state.lifecycle_state = "ISSUED"
    elif t == "ACTION":
        state.active_action = f["action"]
    elif t == "FOUNDATION":
        state.foundation_seen = True
        state.foundation_target = f["target"]
        state.lifecycle_state = "FOUNDATION"
    elif t == "FAILURE":
        state.failure_seen = True
        state.last_failure_reason = f["reason"]
        state.lifecycle_state = "FAILED"
    elif t == "TARGET_INVALIDATED":
        state.target_invalidated = True
        state.invalidated_target = f["target"]
        state.active_target = None
        state.has_fresh_target_selection = False
        state.target_selected_after_invalidation = False
    elif t == "RETRY":
        state.retry_count = f["retry_count"]
        state.attempt_number = f["next_attempt"]
        state.lifecycle_state = "RETRY_READY"
    elif t == "BLOCKED":
        state.retry_count = f["retry_count"]
        state.lifecycle_state = "BLOCKED"
    elif t == "RECOVERED":
        state.lifecycle_state = f["new_state"]
        state.retry_count = f["retry_count"]
        state.attempt_number = 0
        state.active_target = None
        state.active_action = None
        state.target_invalidated = False
        state.invalidated_target = None
    elif t == "COMPLETION":
        state.completion_seen = True
        state.completion_target = state.active_target
        state.building_count_after_completion = f["building_count"]
        state.lifecycle_state = "COMPLETED"
    elif t == "RELEASE":
        if f["reason"] == "COMPLETED":
            state.retry_count = 0
            state.active_target = None
            state.active_action = None
        state.lifecycle_state = "RELEASED"
    elif t == "DEMAND_OFF":
        state.lifecycle_state = "RELEASED"
    elif t == "CASE_END":
        state.lifecycle_state = "ENDED"


def _payload_errors(event: Event) -> list[tuple[str, str]]:
    f, t = event.fields, event.type
    errors: list[tuple[str, str]] = []
    if t == "CASE_START":
        if f["case_id"] == "" or not _CASE.fullmatch(f["case_id"]):
            errors.append(("INVALID_CASE_ID", "invalid case_id"))
        if f["controller"] not in CONTROLLERS:
            errors.append(("INVALID_CONTROLLER", "unknown controller"))
        if f["scenario"] not in SCENARIOS:
            errors.append(("INVALID_SCENARIO", "unknown scenario"))
        if f["initial_state"] != "IDLE" or f["initial_retry"] != 0:
            errors.append(("INVALID_INITIAL_STATE", "CASE_START must begin IDLE with retry 0"))
    elif t == "CASE_END":
        if f["result"] not in RESULTS:
            errors.append(("INVALID_RESULT", "invalid result"))
        if f["event_count"] < 1:
            errors.append(("INVALID_EVENT_COUNT", "event_count must be positive"))
    elif t in {"ADMITTED", "TARGET_SELECTED", "TARGET_INVALIDATED", "ACTION", "FOUNDATION", "COMPLETION", "FAILURE"}:
        if f["attempt"] not in {1, 2, 3}:
            errors.append(("INVALID_ATTEMPT", "attempt must be 1..3"))
    if t in {"TARGET_SELECTED", "TARGET_INVALIDATED", "ACTION", "FOUNDATION"} and not f["target"]:
        errors.append(("EMPTY_TARGET", "target must be non-empty"))
    if t == "ACTION" and f["action"] not in ACTIONS:
        errors.append(("INVALID_ACTION", "unknown action"))
    if t == "FAILURE" and f["reason"] not in FAILURE_REASONS:
        errors.append(("INVALID_FAILURE_REASON", "unknown failure reason"))
    if t == "RELEASE" and f["reason"] not in RELEASE_REASONS:
        errors.append(("INVALID_RELEASE_REASON", "unknown release reason"))
    if t == "ERROR" and f["code"] not in ERROR_CODES:
        errors.append(("INVALID_ERROR_CODE", "unknown error code"))
    if t == "RECOVERED" and (f["previous_state"] not in STATES or f["new_state"] not in STATES):
        errors.append(("INVALID_RECOVERY_STATE", "unknown recovery state"))
    if t == "BLOCKED" and f["retry_count"] not in {1, 2, 3}:
        errors.append(("INVALID_RETRY_COUNT", "retry count must be 1..3"))
    if t == "RETRY" and (f["retry_count"] not in {1, 2} or f["next_attempt"] not in {2, 3}):
        errors.append(("INVALID_RETRY", "retry must be 1->2 or 2->3"))
    return errors


class BYZDSParser:
    def __init__(self, constraint_spec: dict[str, Any]):
        self.spec = constraint_spec
        self.constraints = [
            (c, SafeExpression(c["expression"])) for c in constraint_spec["constraints"]
        ]
        self.precedence = {name: i for i, name in enumerate(
            constraint_spec["evaluation"]["precedence"]
        )}

    @classmethod
    def from_file(cls, path: str | Path) -> "BYZDSParser":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def parse(self, text: str) -> dict[str, Any]:
        try:
            events = parse_events(text)
        except BYZDSInvalid as exc:
            return {"cases": [], "matrix": self._matrix([], "INFRA_ERROR"),
                    "errors": [{"code": "PARSE_ERROR", "reason": str(exc)}]}
        grouped = self._group_cases(events)
        cases = [self._evaluate_case(group) for group in grouped]
        overall = self._overall(cases)
        return {"cases": [c.as_dict() for c in cases],
                "matrix": self._matrix(cases, overall), "errors": []}

    def _group_cases(self, events: list[Event]) -> list[list[Event]]:
        groups: list[list[Event]] = []
        current: list[Event] = []
        for event in events:
            if event.type == "CASE_START":
                if current:
                    groups.append(current)
                current = [event]
            elif current:
                current.append(event)
            else:
                raise BYZDSInvalid("event before CASE_START")
        if current:
            groups.append(current)
        return groups

    def _evaluate_case(self, events: list[Event]) -> CaseResult:
        start = events[0]
        controller = start.fields.get("controller", "")
        scenario = start.fields.get("scenario", "")
        case_id = start.fields.get("case_id", "")
        state = RuntimeState()
        results: list[ConstraintResult] = []
        errors: list[dict[str, Any]] = []

        if start.type != "CASE_START":
            return CaseResult(case_id, controller, scenario, "INVALID", len(events), results,
                              [{"code": "MISSING_CASE_START", "reason": "case does not start with CASE_START"}])

        previous_event: Event | None = None
        for event in events:
            for code, reason in _payload_errors(event):
                errors.append({"event_index": event.index, "code": code, "reason": reason})
            if event.type == "CASE_END":
                continue
            previous = state.snapshot()
            try:
                results.extend(self._evaluate_constraints(event, state, previous, previous_event, case_id, scenario))
            except (KeyError, BYZDSInvalid) as exc:
                errors.append({"event_index": event.index, "code": "CONSTRAINT_EVALUATION_ERROR",
                                "reason": str(exc)})
            _set_state_for_event(state, event)
            previous_event = event

        end_events = [e for e in events if e.type == "CASE_END"]
        if not end_events:
            errors.append({"code": "MISSING_CASE_END", "reason": "case has no CASE_END"})
        if end_events and end_events[-1].fields["event_count"] != len(events):
            errors.append({"code": "EVENT_COUNT_MISMATCH", "reason": "CASE_END event_count does not match parsed event count"})
        result = "PASS"
        if errors:
            result = "INFRA_ERROR" if any(x["code"] == "PARSE_ERROR" for x in errors) else "INVALID"
        for r in results:
            if not r.satisfied:
                if self.precedence.get(r.classification, 0) > self.precedence.get(result, 0):
                    result = r.classification
        return CaseResult(case_id, controller, scenario, result, len(events), results, errors)

    def _evaluate_constraints(self, event: Event, state: RuntimeState,
                              previous: dict[str, Any], previous_event: Event | None,
                              case_id: str, scenario: str) -> list[ConstraintResult]:
        ctx = {
            "event": event.fields,
            "state": state.snapshot(),
            "previous_event": {"type": previous_event.type, **previous_event.fields} if previous_event else None,
            "previous_state": previous,
            "scenario_terminal_state_satisfied": self._scenario_terminal(event, state, scenario),
            "last_failure": {"target_invalidated": state.target_invalidated, "exists": state.failure_seen},
            "current_attempt": state.snapshot(),
        }
        # The declarative DSL uses state.*. Keep completion target derived from
        # active target because COMPLETION has no target field on the wire.
        output = []
        for spec, expression in self.constraints:
            if spec["trigger"]["event"] != event.type:
                continue
            try:
                satisfied = expression.evaluate(ctx)
            except (KeyError, AttributeError, TypeError):
                satisfied = False
                classification = "INFRA_ERROR"
                code = "CONSTRAINT_CONTEXT_MISSING"
                terminal = True
            else:
                classification = "PASS" if satisfied else spec["onViolation"]["classification"]
                code = "PASS" if satisfied else spec["onViolation"]["code"]
                terminal = False if satisfied else spec["onViolation"]["terminal"]
            output.append(ConstraintResult(spec["id"], event.index, case_id, satisfied,
                                           classification, code, terminal,
                                           {"state": state.snapshot(), "event": event.fields}))
        return output

    @staticmethod
    def _scenario_terminal(event: Event, state: RuntimeState, scenario: str) -> bool:
        if event.type != "CASE_END":
            return False
        if scenario in {"R1_FIRST_FAILURE", "R2_SECOND_FAILURE"}:
            return state.lifecycle_state == "RETRY_READY"
        if scenario == "R3_THIRD_FAILURE":
            return state.lifecycle_state == "BLOCKED"
        if scenario == "R4_BLOCKED_RECOVERY":
            return state.lifecycle_state in {"RELEASED", "DEMANDED"}
        if scenario in {"R5_STALE_TARGET", "R6_COMPLETION"}:
            return state.lifecycle_state == "RELEASED"
        return False

    @staticmethod
    def _overall(cases: list[CaseResult]) -> str:
        result = "PASS"
        for case in cases:
            if RESULT_PRECEDENCE[case.result] > RESULT_PRECEDENCE[result]:
                result = case.result
        return result

    @staticmethod
    def _matrix(cases: list[CaseResult], overall: str) -> dict[str, Any]:
        counts = {name: 0 for name in RESULTS}
        for case in cases:
            counts[case.result] += 1
        constraints: dict[str, dict[str, int]] = {}
        for case in cases:
            for result in case.constraint_results:
                bucket = constraints.setdefault(result.constraint_id, {"PASS": 0, "VIOLATION": 0})
                bucket["PASS" if result.satisfied else "VIOLATION"] += 1
        return {
            "result": overall,
            "case_count": len(cases),
            "result_counts": counts,
            "constraint_counts": dict(sorted(constraints.items())),
        }


def load_and_parse(log_text: str, constraint_path: str | Path) -> dict[str, Any]:
    return BYZDSParser.from_file(constraint_path).parse(log_text)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("constraints", type=Path)
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    print(json.dumps(load_and_parse(args.log.read_text(encoding="utf-8"), args.constraints),
                     sort_keys=True, indent=2))
