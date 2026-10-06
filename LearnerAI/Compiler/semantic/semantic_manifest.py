"""Deterministic semantic shadow for effective AoE2 .per artifacts.

The semantic shadow is deliberately observational. It indexes what the existing
native .per parser already sees and what generated comments already declare,
without inventing runtime behavior or introducing a second scripting language.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from ..ast import Expression
from ..source_graph import SourceGraphRequest, SourceGraphResolver
from .rule_execution import EffectiveRule, RulePassBehavior, analyze_effective_rules


_ANNOTATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "NATIVE_CONTROL",
        re.compile(r"^\s*;\s*Native control rule:\s*(?P<identity>[^\s]+)"),
    ),
    (
        "ACTION_ISSUANCE",
        re.compile(r"^\s*;\s*Action issuance:\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "COMPLETION_WITNESS",
        re.compile(r"^\s*;\s*Completion witness:\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "PENDING_ADMISSION",
        re.compile(r"^\s*;\s*Pending admission:\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "RETRY",
        re.compile(r"^\s*;\s*RETRY\s*\|\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "RELEASE",
        re.compile(r"^\s*;\s*Release:\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "NATIVE_DUC",
        re.compile(r"^\s*;\s*Native DUC rule:\s*(?P<identity>[^\s|]+)"),
    ),
    (
        "NATIVE_ATTACK",
        re.compile(r"^\s*;\s*Native attack rule:\s*(?P<identity>[^\s|]+)"),
    ),
)

_GOAL_READ_HEADS = frozenset({"goal", "up-compare-goal"})
_GOAL_WRITE_HEADS = frozenset({"set-goal", "up-modify-goal"})
_SN_READ_HEADS = frozenset({"up-compare-sn"})
_SN_WRITE_HEADS = frozenset({"set-strategic-number", "up-modify-sn"})
_TIMER_READ_HEADS = frozenset({"timer-triggered", "up-timer-status"})
_TIMER_WRITE_HEADS = frozenset(
    {"enable-timer", "disable-timer", "set-timer", "reset-timer"}
)


@dataclass(frozen=True)
class SemanticRuleRecord:
    rule_order: int
    identity: str
    annotation_kind: str
    annotation_text: str | None
    source_path: str
    line: int
    column: int
    pass_behavior: str
    facts: tuple[str, ...]
    actions: tuple[str, ...]
    fact_heads: tuple[str, ...]
    action_heads: tuple[str, ...]
    goal_reads: tuple[str, ...]
    goal_writes: tuple[str, ...]
    strategic_number_reads: tuple[str, ...]
    strategic_number_writes: tuple[str, ...]
    timer_reads: tuple[str, ...]
    timer_writes: tuple[str, ...]
    element_count: int

    @property
    def state_writes(self) -> tuple[str, ...]:
        return tuple(sorted((*self.goal_writes, *self.strategic_number_writes, *self.timer_writes)))

    @property
    def state_reads(self) -> tuple[str, ...]:
        return tuple(sorted((*self.goal_reads, *self.strategic_number_reads, *self.timer_reads)))


@dataclass(frozen=True)
class SemanticManifest:
    schema_version: int
    source_path: str
    artifact_sha256: str
    rule_count: int
    annotated_rule_count: int
    max_element_count: int
    over_32_element_rules: tuple[int, ...]
    annotation_counts: tuple[tuple[str, int], ...]
    writers_by_state: tuple[tuple[str, tuple[int, ...]], ...]
    readers_by_state: tuple[tuple[str, tuple[int, ...]], ...]
    rules: tuple[SemanticRuleRecord, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source_path": self.source_path,
            "artifact_sha256": self.artifact_sha256,
            "summary": {
                "rule_count": self.rule_count,
                "annotated_rule_count": self.annotated_rule_count,
                "max_element_count": self.max_element_count,
                "over_32_element_rules": list(self.over_32_element_rules),
                "annotation_counts": dict(self.annotation_counts),
            },
            "writers_by_state": {
                key: list(orders)
                for key, orders in self.writers_by_state
            },
            "readers_by_state": {
                key: list(orders)
                for key, orders in self.readers_by_state
            },
            "rules": [asdict(rule) for rule in self.rules],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def write_json(self, path: Path) -> None:
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        staged = path.with_name("." + path.name + ".stage")
        staged.write_text(self.to_json(), encoding="utf-8")
        staged.replace(path)


def _walk(expressions: Iterable[Expression]) -> Iterable[Expression]:
    for expression in expressions:
        yield expression
        for arg in expression.args:
            if isinstance(arg, Expression):
                yield from _walk((arg,))


def _elements(rule: EffectiveRule) -> int:
    return sum(1 for _ in _walk((*rule.facts, *(action.expression for action in rule.actions))))


def _first_symbol(expression: Expression) -> str | None:
    if not expression.args:
        return None
    value = expression.args[0]
    if isinstance(value, Expression):
        return None
    return str(value)


def _collect_state_accesses(rule: EffectiveRule) -> tuple[set[str], set[str], set[str], set[str], set[str], set[str]]:
    goal_reads: set[str] = set()
    goal_writes: set[str] = set()
    sn_reads: set[str] = set()
    sn_writes: set[str] = set()
    timer_reads: set[str] = set()
    timer_writes: set[str] = set()

    for expression in _walk((*rule.facts, *(action.expression for action in rule.actions))):
        head = expression.head
        symbol = _first_symbol(expression)
        if symbol is None:
            continue
        if head in _GOAL_READ_HEADS:
            goal_reads.add(f"goal:{symbol}")
        if head in _GOAL_WRITE_HEADS:
            goal_writes.add(f"goal:{symbol}")
        if head in _SN_READ_HEADS:
            sn_reads.add(f"sn:{symbol}")
        if head in _SN_WRITE_HEADS:
            sn_writes.add(f"sn:{symbol}")
        if head in _TIMER_READ_HEADS:
            timer_reads.add(f"timer:{symbol}")
        if head in _TIMER_WRITE_HEADS:
            timer_writes.add(f"timer:{symbol}")

    return (
        goal_reads,
        goal_writes,
        sn_reads,
        sn_writes,
        timer_reads,
        timer_writes,
    )


def _annotation_for_rule(
    *,
    rule: EffectiveRule,
    source_text: str,
    slice_start_line: int,
    lookback: int = 16,
) -> tuple[str, str | None, str]:
    lines = source_text.splitlines()
    index = rule.source_location.line - slice_start_line
    if index < 0 or index >= len(lines):
        return "UNANNOTATED", None, f"rule-{rule.rule_order}"

    lower_bound = max(0, index - lookback)
    for candidate in reversed(lines[lower_bound:index]):
        stripped = candidate.strip()
        if not stripped.startswith(";"):
            continue
        for kind, pattern in _ANNOTATION_PATTERNS:
            match = pattern.match(stripped)
            if match:
                identity = match.group("identity").strip()
                return kind, stripped, identity
    return "UNANNOTATED", None, f"rule-{rule.rule_order}"


def _slice_for_rule(graph, rule: EffectiveRule):
    return next(
        slice_
        for slice_ in graph.slices
        if slice_.ordinal == rule.source_slice_ordinal
    )


def build_semantic_manifest(path: Path) -> SemanticManifest:
    """Build an observational semantic index for one effective .per entrypoint."""
    path = path.resolve()
    graph = SourceGraphResolver().resolve(SourceGraphRequest(entrypoint=path))
    report = analyze_effective_rules(graph)

    sources = {
        source.path: source
        for source in graph.files
    }
    records: list[SemanticRuleRecord] = []
    annotation_counts: dict[str, int] = {}
    writers: dict[str, list[int]] = {}
    readers: dict[str, list[int]] = {}

    for rule in report.rules:
        source = sources[Path(rule.source_location.source_unit).resolve()]
        source_slice = _slice_for_rule(graph, rule)
        kind, annotation_text, identity = _annotation_for_rule(
            rule=rule,
            source_text=source_slice.text,
            slice_start_line=source_slice.physical_range.start_line,
        )
        (
            goal_reads,
            goal_writes,
            sn_reads,
            sn_writes,
            timer_reads,
            timer_writes,
        ) = _collect_state_accesses(rule)
        record = SemanticRuleRecord(
            rule_order=rule.rule_order,
            identity=identity,
            annotation_kind=kind,
            annotation_text=annotation_text,
            source_path=source.path.as_posix(),
            line=rule.source_location.line,
            column=rule.source_location.column,
            pass_behavior=rule.pass_behavior.value,
            facts=tuple(expression.source for expression in rule.facts),
            actions=tuple(action.expression.source for action in rule.actions),
            fact_heads=tuple(expression.head for expression in rule.facts),
            action_heads=tuple(action.expression.head for action in rule.actions),
            goal_reads=tuple(sorted(goal_reads)),
            goal_writes=tuple(sorted(goal_writes)),
            strategic_number_reads=tuple(sorted(sn_reads)),
            strategic_number_writes=tuple(sorted(sn_writes)),
            timer_reads=tuple(sorted(timer_reads)),
            timer_writes=tuple(sorted(timer_writes)),
            element_count=_elements(rule),
        )
        records.append(record)
        annotation_counts[kind] = annotation_counts.get(kind, 0) + 1
        for state in record.state_writes:
            writers.setdefault(state, []).append(record.rule_order)
        for state in record.state_reads:
            readers.setdefault(state, []).append(record.rule_order)

    artifact_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    ordered_records = tuple(records)
    return SemanticManifest(
        schema_version=1,
        source_path=path.as_posix(),
        artifact_sha256=artifact_sha256,
        rule_count=len(ordered_records),
        annotated_rule_count=sum(
            count for kind, count in annotation_counts.items()
            if kind != "UNANNOTATED"
        ),
        max_element_count=max((rule.element_count for rule in ordered_records), default=0),
        over_32_element_rules=tuple(
            rule.rule_order
            for rule in ordered_records
            if rule.element_count > 32
        ),
        annotation_counts=tuple(sorted(annotation_counts.items())),
        writers_by_state=tuple(
            (state, tuple(sorted(orders)))
            for state, orders in sorted(writers.items())
        ),
        readers_by_state=tuple(
            (state, tuple(sorted(orders)))
            for state, orders in sorted(readers.items())
        ),
        rules=ordered_records,
    )


__all__ = [
    "SemanticManifest",
    "SemanticRuleRecord",
    "build_semantic_manifest",
]
