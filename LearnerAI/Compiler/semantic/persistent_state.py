"""Persistent native Goal/SN/Timer state and rule-source-order analysis.

The AoE2 rule engine evaluates a rule's facts before executing its action list.
Persistent-state analysis therefore treats guard reads as preceding all action
writes in the same emitted rule, while preserving action order for writes within
one rule and rule order across passes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from ..diagnostics import DiagnosticSeverity
from .rule_execution import (
    EffectiveRule,
    RuleExecutionReport,
    RulePassBehavior,
    StaticControlTransfer,
    analyze_rule_reachability,
)


class PersistentStateKind(str, Enum):
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"


class PersistentStateAccessKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class PersistentStateVisibility(str, Enum):
    SAME_RULE_ACTION_SEQUENCE = "SAME_RULE_ACTION_SEQUENCE"
    CROSS_RULE_PERSISTED = "CROSS_RULE_PERSISTED"
    CONSUMER_BEFORE_WRITER = "CONSUMER_BEFORE_WRITER"
    MISSING_WRITER = "MISSING_WRITER"
    UNCONSUMED = "UNCONSUMED"


class PersistentStateDiagnosticCode(str, Enum):
    CONSUMER_BEFORE_WRITER = "PSTATE-001"
    LATER_OVERWRITE = "PSTATE-002"
    CONSUMER_SHADOWED_BY_WRITER = "PSTATE-003"
    CONSUMER_STARVED_BY_RECURRENT_WRITER = "PSTATE-004"
    OPEN_LOOP_WRITE_WITHOUT_CONSUMER = "PSTATE-005"
    SAME_PASS_CONSUMER_PATH_BLOCKED = "PSTATE-006"


@dataclass(frozen=True)
class PersistentStateRef:
    kind: PersistentStateKind
    identifier: str


@dataclass(frozen=True)
class PersistentStateAccess:
    state: PersistentStateRef
    effect: PersistentStateAccessKind
    rule_order: int
    within_rule_order: int
    section: str
    command: str
    expression: Expression
    pass_behavior: RulePassBehavior
    location: SourceLocation | None

    @property
    def sort_key(self) -> tuple[int, int, int]:
        section_order = 0 if self.section == "GUARD" else 1
        return self.rule_order, section_order, self.within_rule_order


@dataclass(frozen=True)
class PersistentStateBoundary:
    state: PersistentStateRef
    writers: tuple[PersistentStateAccess, ...]
    readers: tuple[PersistentStateAccess, ...]
    first_writer: PersistentStateAccess | None
    first_consumer: PersistentStateAccess | None
    later_writers: tuple[PersistentStateAccess, ...]
    visibility: PersistentStateVisibility


@dataclass(frozen=True)
class PersistentStateDiagnostic:
    code: PersistentStateDiagnosticCode
    severity: DiagnosticSeverity
    message: str
    rule_order: int
    access: PersistentStateAccess
    related_access: PersistentStateAccess | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PersistentStateReport:
    accesses: tuple[PersistentStateAccess, ...]
    boundaries: tuple[PersistentStateBoundary, ...]
    diagnostics: tuple[PersistentStateDiagnostic, ...]

    @property
    def errors(self) -> tuple[PersistentStateDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[PersistentStateDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.WARNING
        )


# These command identities and operand positions are taken from the checked-in
# AIRef command inventory. They are deliberately narrow: this tranche does not
# infer persistent state from arbitrary command names.
_STATE_SPECS = {
    "set-goal": (PersistentStateKind.GOAL, PersistentStateAccessKind.WRITE, 0, None),
    "goal": (PersistentStateKind.GOAL, PersistentStateAccessKind.READ, 0, "="),
    "up-compare-goal": (PersistentStateKind.GOAL, PersistentStateAccessKind.READ, 0, None),
    "set-strategic-number": (
        PersistentStateKind.STRATEGIC_NUMBER,
        PersistentStateAccessKind.WRITE,
        0,
        None,
    ),
    "up-modify-sn": (
        PersistentStateKind.STRATEGIC_NUMBER,
        PersistentStateAccessKind.WRITE,
        0,
        None,
    ),
    "strategic-number": (
        PersistentStateKind.STRATEGIC_NUMBER,
        PersistentStateAccessKind.READ,
        0,
        None,
    ),
    "up-compare-sn": (
        PersistentStateKind.STRATEGIC_NUMBER,
        PersistentStateAccessKind.READ,
        0,
        None,
    ),
    "enable-timer": (
        PersistentStateKind.TIMER,
        PersistentStateAccessKind.WRITE,
        0,
        None,
    ),
    "disable-timer": (
        PersistentStateKind.TIMER,
        PersistentStateAccessKind.WRITE,
        0,
        None,
    ),
    "timer-triggered": (
        PersistentStateKind.TIMER,
        PersistentStateAccessKind.READ,
        0,
        None,
    ),
    "up-set-timer": (
        PersistentStateKind.TIMER,
        PersistentStateAccessKind.WRITE,
        1,
        None,
    ),
    "up-timer-status": (
        PersistentStateKind.TIMER,
        PersistentStateAccessKind.READ,
        0,
        None,
    ),
}


def _walk(expressions: tuple[Expression, ...] | list[Expression]):
    for expression in expressions:
        yield expression
        for argument in expression.args:
            if isinstance(argument, Expression):
                yield from _walk((argument,))


def _state_access(
    expression: Expression,
    *,
    rule: EffectiveRule,
    section: str,
    within_rule_order: int,
) -> PersistentStateAccess | None:
    spec = _STATE_SPECS.get(expression.head)
    if spec is None:
        return None

    kind, effect, identifier_index, _default_operator = spec
    if len(expression.args) <= identifier_index:
        return None

    identifier = expression.args[identifier_index]
    if not isinstance(identifier, str) or not identifier:
        return None

    return PersistentStateAccess(
        state=PersistentStateRef(kind=kind, identifier=identifier),
        effect=effect,
        rule_order=rule.rule_order,
        within_rule_order=within_rule_order,
        section=section,
        command=expression.head,
        expression=expression,
        pass_behavior=rule.pass_behavior,
        location=expression.location or rule.source_location,
    )


def _operand_state_accesses(
    expression: Expression,
    *,
    rule: EffectiveRule,
    section: str,
    within_rule_order: int,
) -> tuple[PersistentStateAccess, ...]:
    if expression.head not in {"up-modify-sn", "up-compare-sn"}:
        return ()
    if len(expression.args) != 3:
        return ()
    operator = str(expression.args[1])
    value = str(expression.args[2])
    if len(operator) < 3 or operator[1] != ":":
        return ()
    prefix = operator[:2].lower()
    if prefix == "g:":
        kind = PersistentStateKind.GOAL
    elif prefix == "s:":
        kind = PersistentStateKind.STRATEGIC_NUMBER
    else:
        return ()
    identifier = value
    if not identifier:
        return ()
    return (
        PersistentStateAccess(
            state=PersistentStateRef(kind=kind, identifier=identifier),
            effect=PersistentStateAccessKind.READ,
            rule_order=rule.rule_order,
            within_rule_order=within_rule_order,
            section=section,
            command=expression.head,
            expression=expression,
            pass_behavior=rule.pass_behavior,
            location=expression.location or rule.source_location,
        ),
    )


def _guard_accesses(rule: EffectiveRule) -> tuple[PersistentStateAccess, ...]:
    accesses: list[PersistentStateAccess] = []
    for index, expression in enumerate(_walk(rule.facts)):
        access = _state_access(
            expression,
            rule=rule,
            section="GUARD",
            within_rule_order=index,
        )
        if access is not None:
            accesses.append(access)
        accesses.extend(
            _operand_state_accesses(
                expression,
                rule=rule,
                section="GUARD",
                within_rule_order=index,
            )
        )
    return tuple(accesses)


def _action_accesses(rule: EffectiveRule) -> tuple[PersistentStateAccess, ...]:
    accesses: list[PersistentStateAccess] = []
    for action in rule.actions:
        expression = action.expression
        access = _state_access(
            expression,
            rule=rule,
            section="ACTION",
            within_rule_order=action.within_rule_order,
        )
        if access is not None:
            accesses.append(access)
        accesses.extend(
            _operand_state_accesses(
                expression,
                rule=rule,
                section="ACTION",
                within_rule_order=action.within_rule_order,
            )
        )
    return tuple(accesses)


def _numeric(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 10)
    except ValueError:
        return None


def _reader_predicate(
    access: PersistentStateAccess,
) -> tuple[str, str] | None:
    args = access.expression.args
    if access.command == "goal" and len(args) >= 2:
        return "=", str(args[1])
    if access.command in {"up-compare-goal", "strategic-number", "up-compare-sn"} and len(args) >= 3:
        return str(args[1]), str(args[2])
    if access.command == "up-timer-status" and len(args) >= 3:
        return str(args[1]), str(args[2])
    return None


def _writer_value(access: PersistentStateAccess) -> str | None:
    args = access.expression.args
    if access.command in {"set-goal", "set-strategic-number"} and len(args) >= 2:
        return str(args[1])
    return None


def _predicate_is_false_after_write(
    reader: PersistentStateAccess,
    writer: PersistentStateAccess,
) -> bool:
    reader_predicate = _reader_predicate(reader)
    writer_value = _writer_value(writer)
    if reader_predicate is None or writer_value is None:
        return False

    operator, expected = reader_predicate
    if operator == "=":
        return writer_value != expected
    if operator == "!=":
        return writer_value == expected

    actual_number = _numeric(writer_value)
    expected_number = _numeric(expected)
    if actual_number is None or expected_number is None:
        return False

    return {
        "<": actual_number >= expected_number,
        "<=": actual_number > expected_number,
        ">": actual_number <= expected_number,
        ">=": actual_number < expected_number,
    }.get(operator, False)


def _guard_is_guaranteed(rule: EffectiveRule) -> bool:
    return len(rule.facts) == 1 and rule.facts[0].head == "true"


def _control_transfer_by_rule(
    report: RuleExecutionReport,
) -> dict[int, StaticControlTransfer]:
    transfers: dict[int, StaticControlTransfer] = {}
    for transfer in report.control_transfers:
        current = transfers.get(transfer.rule_order)
        if current is None or transfer.within_rule_order > current.within_rule_order:
            transfers[transfer.rule_order] = transfer
    return transfers


def _same_pass_consumer_reachable(
    report: RuleExecutionReport,
    writer: PersistentStateAccess,
    reader: PersistentStateAccess,
) -> bool:
    if writer.rule_order == reader.rule_order:
        return (
            reader.section == "ACTION"
            and writer.section == "ACTION"
            and reader.within_rule_order > writer.within_rule_order
        )

    if report.reachability is None:
        reachability = analyze_rule_reachability(
            report.rules,
            report.control_transfers,
        )
    else:
        reachability = report.reachability

    outgoing = dict(reachability.outgoing_rule_orders)
    transfers = _control_transfer_by_rule(report)
    final_transfer = transfers.get(writer.rule_order)

    if final_transfer is not None and final_transfer.target_rule_order is not None:
        initial_successors = (final_transfer.target_rule_order,)
    elif writer.rule_order < len(report.rules):
        initial_successors = (writer.rule_order + 1,)
    else:
        initial_successors = ()

    seen: set[int] = set()
    worklist = list(initial_successors)
    while worklist:
        rule_order = worklist.pop()
        if rule_order in seen:
            continue
        seen.add(rule_order)
        if rule_order == reader.rule_order:
            return True
        for target in outgoing.get(rule_order, ()):
            if target not in seen:
                worklist.append(target)

    return False


def _diagnostic_key(item: PersistentStateDiagnostic) -> tuple[object, ...]:
    related = item.related_access
    return (
        item.code.value,
        item.rule_order,
        item.access.rule_order,
        item.access.within_rule_order,
        item.access.command,
        related.rule_order if related is not None else -1,
        related.within_rule_order if related is not None else -1,
        item.message,
    )


def analyze_persistent_state(
    report: RuleExecutionReport,
    *,
    ignored_state_identifiers: set[str] | frozenset[str] = frozenset(),
) -> PersistentStateReport:
    """Analyze native persistent Goal/SN/Timer state across effective rules."""
    if not isinstance(report, RuleExecutionReport):
        raise TypeError("report must be a RuleExecutionReport")
    if not isinstance(ignored_state_identifiers, (set, frozenset)):
        raise TypeError(
            "ignored_state_identifiers must be a set or frozenset of strings"
        )
    if any(
        not isinstance(identifier, str) or not identifier
        for identifier in ignored_state_identifiers
    ):
        raise TypeError(
            "ignored_state_identifiers must contain only non-empty strings"
        )

    accesses: list[PersistentStateAccess] = []
    rules_by_order = {rule.rule_order: rule for rule in report.rules}
    for rule in report.rules:
        accesses.extend(_guard_accesses(rule))
        accesses.extend(_action_accesses(rule))

    ordered_accesses = tuple(sorted(accesses, key=lambda item: item.sort_key))
    grouped: dict[PersistentStateRef, list[PersistentStateAccess]] = {}
    for access in ordered_accesses:
        if access.state.identifier in ignored_state_identifiers:
            continue
        grouped.setdefault(access.state, []).append(access)

    boundaries: list[PersistentStateBoundary] = []
    diagnostics: list[PersistentStateDiagnostic] = []

    for state in sorted(
        grouped,
        key=lambda item: (item.kind.value, item.identifier),
    ):
        state_accesses = tuple(grouped[state])
        writers = tuple(
            access
            for access in state_accesses
            if access.effect is PersistentStateAccessKind.WRITE
        )
        readers = tuple(
            access
            for access in state_accesses
            if access.effect is PersistentStateAccessKind.READ
        )
        first_writer = writers[0] if writers else None
        first_consumer = readers[0] if readers else None
        later_writers = writers[1:]

        if first_writer is None:
            visibility = PersistentStateVisibility.MISSING_WRITER
        elif first_consumer is None:
            visibility = PersistentStateVisibility.UNCONSUMED
        elif first_consumer.sort_key < first_writer.sort_key:
            visibility = PersistentStateVisibility.CONSUMER_BEFORE_WRITER
            diagnostics.append(
                PersistentStateDiagnostic(
                    code=PersistentStateDiagnosticCode.CONSUMER_BEFORE_WRITER,
                    severity=DiagnosticSeverity.ERROR,
                    message=(
                        f"{state.kind.value.lower()} state '{state.identifier}' is read "
                        f"before its first writer in effective rule order"
                    ),
                    rule_order=first_consumer.rule_order,
                    access=first_consumer,
                    related_access=first_writer,
                    location=first_consumer.location,
                )
            )
        elif first_consumer.rule_order == first_writer.rule_order:
            visibility = PersistentStateVisibility.SAME_RULE_ACTION_SEQUENCE
        else:
            visibility = PersistentStateVisibility.CROSS_RULE_PERSISTED

        if (
            first_writer is not None
            and first_consumer is None
            and len(writers) > 1
            and len({writer.rule_order for writer in writers}) == 1
        ):
            visibility = PersistentStateVisibility.SAME_RULE_ACTION_SEQUENCE

        for previous, later in zip(writers, writers[1:]):
            if later.sort_key == previous.sort_key:
                continue
            diagnostics.append(
                PersistentStateDiagnostic(
                    code=PersistentStateDiagnosticCode.LATER_OVERWRITE,
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        f"{state.kind.value.lower()} state '{state.identifier}' has a later "
                        f"writer in rule {later.rule_order} after writer in rule {previous.rule_order}"
                    ),
                    rule_order=later.rule_order,
                    access=later,
                    related_access=previous,
                    location=later.location,
                )
            )

        if readers:
            for reader in readers:
                prior_writers = tuple(
                    writer
                    for writer in writers
                    if writer.sort_key < reader.sort_key
                )
                if not prior_writers:
                    continue
                candidate = prior_writers[-1]
                source_rule = rules_by_order.get(candidate.rule_order)
                if source_rule is None or not _guard_is_guaranteed(source_rule):
                    continue
                if not _predicate_is_false_after_write(reader, candidate):
                    continue
                if source_rule.pass_behavior is RulePassBehavior.RECURRENT:
                    diagnostics.append(
                        PersistentStateDiagnostic(
                            code=PersistentStateDiagnosticCode.CONSUMER_STARVED_BY_RECURRENT_WRITER,
                            severity=DiagnosticSeverity.ERROR,
                            message=(
                                f"rule {reader.rule_order} reads {state.kind.value.lower()} "
                                f"state '{state.identifier}', but recurrent guaranteed writer "
                                f"rule {candidate.rule_order} establishes a value that "
                                "contradicts the consumer before every subsequent pass"
                            ),
                            rule_order=reader.rule_order,
                            access=reader,
                            related_access=candidate,
                            location=reader.location,
                        )
                    )
                else:
                    diagnostics.append(
                        PersistentStateDiagnostic(
                            code=PersistentStateDiagnosticCode.CONSUMER_SHADOWED_BY_WRITER,
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                f"rule {reader.rule_order} reads {state.kind.value.lower()} "
                                f"state '{state.identifier}' with a predicate contradicted by "
                                f"the preceding guaranteed one-shot writer in rule "
                                f"{candidate.rule_order}; the consumer may be shadowed "
                                "for the current pass but is not statically starved"
                            ),
                            rule_order=reader.rule_order,
                            access=reader,
                            related_access=candidate,
                            location=reader.location,
                        )
                    )

        if any(
            transfer.target_rule_order is None
            for transfer in report.control_transfers
        ):
            downstream_readers_by_writer = {}
        else:
            downstream_readers_by_writer = {
                writer: tuple(
                    reader
                    for reader in readers
                    if reader.sort_key > writer.sort_key
                    and (
                        writer.rule_order != reader.rule_order
                        or (
                            writer.section == "ACTION"
                            and reader.section == "ACTION"
                            and reader.within_rule_order > writer.within_rule_order
                        )
                    )
                )
                for writer in writers
            }
            for writer, downstream_readers in downstream_readers_by_writer.items():
                if (
                    writer.pass_behavior is not RulePassBehavior.RECURRENT
                    or not downstream_readers
                ):
                    continue
                if any(
                    _same_pass_consumer_reachable(report, writer, reader)
                    for reader in downstream_readers
                ):
                    continue
                diagnostics.append(
                    PersistentStateDiagnostic(
                        code=PersistentStateDiagnosticCode.SAME_PASS_CONSUMER_PATH_BLOCKED,
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"rule {writer.rule_order} writes "
                            f"{state.kind.value.lower()} state '{state.identifier}', "
                            "but no same-pass control-flow path from that firing "
                            "reaches any downstream consumer; later-pass consumption "
                            "is not ruled out"
                        ),
                        rule_order=writer.rule_order,
                        access=writer,
                        related_access=downstream_readers[0],
                        location=writer.location,
                    )
                )
        reachable_orders = (
            set(report.reachability.reachable_rule_orders)
            if report.reachability is not None
            else {rule.rule_order for rule in report.rules}
        )
        reachable_writers = tuple(
            writer
            for writer in writers
            if writer.rule_order in reachable_orders
        )
        if reachable_writers:
            terminal_writer = reachable_writers[-1]
            downstream_consumers = tuple(
                reader
                for reader in readers
                if reader.rule_order in reachable_orders
                and reader.sort_key > terminal_writer.sort_key
            )
            if not downstream_consumers:
                diagnostics.append(
                    PersistentStateDiagnostic(
                        code=PersistentStateDiagnosticCode.OPEN_LOOP_WRITE_WITHOUT_CONSUMER,
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"rule {terminal_writer.rule_order} writes "
                            f"{state.kind.value.lower()} state '{state.identifier}', "
                            "but no downstream reachable consumer reads that state; "
                            "the persistent mutation is behaviorally open-loop"
                        ),
                        rule_order=terminal_writer.rule_order,
                        access=terminal_writer,
                        related_access=None,
                        location=terminal_writer.location,
                    )
                )
        boundaries.append(
            PersistentStateBoundary(
                state=state,
                writers=writers,
                readers=readers,
                first_writer=first_writer,
                first_consumer=first_consumer,
                later_writers=later_writers,
                visibility=visibility,
            )
        )

    return PersistentStateReport(
        accesses=ordered_accesses,
        boundaries=tuple(boundaries),
        diagnostics=tuple(sorted(diagnostics, key=_diagnostic_key)),
    )


__all__ = [
    "PersistentStateAccess",
    "PersistentStateAccessKind",
    "PersistentStateBoundary",
    "PersistentStateDiagnostic",
    "PersistentStateDiagnosticCode",
    "PersistentStateKind",
    "PersistentStateRef",
    "PersistentStateReport",
    "PersistentStateVisibility",
    "analyze_persistent_state",
]
