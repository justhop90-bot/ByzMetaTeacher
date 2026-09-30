"""Rule-level diagnostics compiled from static firing eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ..ast import Expression, SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..primitives import PrimitiveRegistry, default_de_registry
from .firing_eligibility import FiringEligibility, analyze_firing_eligibility
from .guard_satisfiability import GuardSatisfiability, analyze_guard
from .persistent_state import (
    PersistentStateDiagnostic,
    PersistentStateDiagnosticCode,
    PersistentStateReport,
)
from .duc import DucAnalysisReport, DucDiagnostic
from .strategic_number_semantics import (
    StrategicNumberDiagnosticCode,
    StrategicNumberSemanticReport,
)
from .rule_execution import EffectiveRule, RuleExecutionReport, analyze_rule_reachability
from .recurrent_execution import RecurrentExecutionReport


class RuleDiagnosticCategory(str, Enum):
    FIRING_ELIGIBILITY = "FIRING_ELIGIBILITY"
    PERSISTENT_STATE = "PERSISTENT_STATE"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    CONTROL_FLOW = "CONTROL_FLOW"
    RECURRENT_EXECUTION = "RECURRENT_EXECUTION"
    DUC = "DUC"


class RuleDiagnosticCode(str, Enum):
    NEVER_ELIGIBLE = "RULE-FIRE-001"
    RUNTIME_DEPENDENT = "RULE-FIRE-002"
    FIRST_PASS_ELIGIBLE = "RULE-FIRE-003"
    RECURRENTLY_ELIGIBLE = "RULE-FIRE-004"
    PERSISTENT_CONSUMER_BEFORE_WRITER = "PSTATE-001"
    PERSISTENT_LATER_OVERWRITE = "PSTATE-002"
    PERSISTENT_CONSUMER_SHADOWED_BY_WRITER = "PSTATE-003"
    PERSISTENT_CONSUMER_STARVED_BY_RECURRENT_WRITER = "PSTATE-004"
    PERSISTENT_OPEN_LOOP_WRITE_WITHOUT_CONSUMER = "PSTATE-005"
    PERSISTENT_SAME_PASS_CONSUMER_PATH_BLOCKED = "PSTATE-006"
    STRATEGIC_NUMBER_INVALID_ARITY = "SNSEM-001"
    STRATEGIC_NUMBER_INVALID_OPERATOR = "SNSEM-002"
    STRATEGIC_NUMBER_INVALID_OPERAND_PREFIX = "SNSEM-003"
    STRATEGIC_NUMBER_INVALID_LITERAL = "SNSEM-004"
    STRATEGIC_NUMBER_OUT_OF_RANGE_LITERAL = "SNSEM-005"
    STRATEGIC_NUMBER_CONSTANT_ZERO_DIVISOR = "SNSEM-006"
    STRATEGIC_NUMBER_MISSING_DEPENDENCY = "SNSEM-007"
    STRATEGIC_NUMBER_INVALID_TARGET = "SNSEM-008"
    STRATEGIC_NUMBER_FUTURE_SAME_RULE_DEPENDENCY = "SNSEM-009"
    CONTROL_TRANSFER_OUT_OF_RANGE = "RULE-CF-001"
    CONTROL_TRANSFER_BYPASSES_RULE = "RULE-CF-002"
    CONTROL_TRANSFER_PREEMPTS_RULE = "RULE-CF-003"
    CONTROL_TRANSFER_UNREACHABLE_RULE = "RULE-CF-004"
    CONTROL_TRANSFER_INTO_DISABLED_RULE = "RULE-CF-005"
    RECURRENT_NEVER_RUNNABLE = "REX-001"
    RECURRENT_RUNTIME_DEPENDENT = "REX-002"
    RECURRENT_GUARANTEED_PREEMPTION = "REX-003"
    RECURRENT_STATE_STARVATION = "REX-004"
    DUC_LIST_UNINITIALIZED = "DUC-001"
    DUC_FILTER_UNINITIALIZED = "DUC-002"
    DUC_FILTER_RETAINED = "DUC-003"
    DUC_FILTER_STALE = "DUC-004"
    DUC_TARGET_UNSCOPED = "DUC-005"
    DUC_TARGET_STALE = "DUC-006"
    DUC_TARGET_UNKNOWN = "DUC-007"
    DUC_SEARCH_ACCUMULATION = "DUC-008"
    DUC_SEARCH_STARVED = "DUC-009"
    DUC_RESET_INVALIDATION = "DUC-010"
    DUC_OUTPUT_STALE = "DUC-011"
    DUC_FILTER_PATH_DEPENDENCY = "DUC-012"
    DUC_RECURRENT_TARGET_REUSE = "DUC-013"
    DUC_CARDINALITY = "DUC-014"
    DUC_COST = "DUC-015"
    DUC_LOOP_WIDENING = "DUC-016"
    DUC_GROUP_INVALID_STATE = "DUC-017"


@dataclass(frozen=True)
class RuleDiagnostic:
    rule_order: int
    code: RuleDiagnosticCode
    severity: DiagnosticSeverity
    eligibility: FiringEligibility | None
    message: str
    location: SourceLocation
    category: RuleDiagnosticCategory
    source_code: str
    state_kind: str | None = None
    state_identifier: str | None = None
    related_rule_order: int | None = None
    related_operation: str | None = None


@dataclass(frozen=True)
class RuleDiagnosticReport:
    diagnostics: tuple[RuleDiagnostic, ...]

    @property
    def errors(self) -> tuple[RuleDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[RuleDiagnostic, ...]:
        return tuple(
            item
            for item in self.diagnostics
            if item.severity is DiagnosticSeverity.WARNING
        )

    @property
    def by_rule(self) -> tuple[tuple[int, RuleDiagnostic], ...]:
        return tuple((item.rule_order, item) for item in self.diagnostics)


def _guard_expression(rule: EffectiveRule) -> Expression:
    if len(rule.facts) == 1:
        return rule.facts[0]
    return Expression(
        source="(and " + " ".join(fact.source for fact in rule.facts) + ")",
        head="and",
        args=rule.facts,
        location=rule.facts[0].location,
    )


def _diagnostic_for(
    rule: EffectiveRule,
    eligibility: FiringEligibility,
) -> RuleDiagnostic:
    if eligibility is FiringEligibility.NEVER_ELIGIBLE:
        code = RuleDiagnosticCode.NEVER_ELIGIBLE
        severity = DiagnosticSeverity.ERROR
        message = (
            f"rule {rule.rule_order} is statically never eligible to fire"
        )
    elif eligibility is FiringEligibility.RUNTIME_DEPENDENT:
        code = RuleDiagnosticCode.RUNTIME_DEPENDENT
        severity = DiagnosticSeverity.INFO
        message = (
            f"rule {rule.rule_order} requires runtime state before firing "
            "eligibility can be established"
        )
    elif eligibility is FiringEligibility.FIRST_PASS_ELIGIBLE:
        code = RuleDiagnosticCode.FIRST_PASS_ELIGIBLE
        severity = DiagnosticSeverity.INFO
        message = (
            f"rule {rule.rule_order} is eligible on its first available pass"
        )
    else:
        code = RuleDiagnosticCode.RECURRENTLY_ELIGIBLE
        severity = DiagnosticSeverity.INFO
        message = (
            f"rule {rule.rule_order} is recurrently eligible while its guard "
            "and lifecycle admission remain satisfied"
        )

    return RuleDiagnostic(
        rule_order=rule.rule_order,
        code=code,
        severity=severity,
        eligibility=eligibility,
        message=message,
        location=rule.source_location,
        category=RuleDiagnosticCategory.FIRING_ELIGIBILITY,
        source_code=code.value,
    )


_PERSISTENT_RULE_CODES = {
    PersistentStateDiagnosticCode.CONSUMER_BEFORE_WRITER:
        RuleDiagnosticCode.PERSISTENT_CONSUMER_BEFORE_WRITER,
    PersistentStateDiagnosticCode.LATER_OVERWRITE:
        RuleDiagnosticCode.PERSISTENT_LATER_OVERWRITE,
    PersistentStateDiagnosticCode.CONSUMER_SHADOWED_BY_WRITER:
        RuleDiagnosticCode.PERSISTENT_CONSUMER_SHADOWED_BY_WRITER,
    PersistentStateDiagnosticCode.CONSUMER_STARVED_BY_RECURRENT_WRITER:
        RuleDiagnosticCode.PERSISTENT_CONSUMER_STARVED_BY_RECURRENT_WRITER,
    PersistentStateDiagnosticCode.OPEN_LOOP_WRITE_WITHOUT_CONSUMER:
        RuleDiagnosticCode.PERSISTENT_OPEN_LOOP_WRITE_WITHOUT_CONSUMER,
    PersistentStateDiagnosticCode.SAME_PASS_CONSUMER_PATH_BLOCKED:
        RuleDiagnosticCode.PERSISTENT_SAME_PASS_CONSUMER_PATH_BLOCKED,
}


def _persistent_diagnostic_for(
    item: PersistentStateDiagnostic,
) -> RuleDiagnostic:
    try:
        code = _PERSISTENT_RULE_CODES[item.code]
    except KeyError as exc:
        raise ValueError(
            f"unsupported persistent-state diagnostic code '{item.code}'"
        ) from exc

    access = item.access
    state_kind = access.state.kind.value
    state_identifier = access.state.identifier
    related_rule_order = (
        item.related_access.rule_order
        if item.related_access is not None
        else None
    )
    related_operation = (
        item.related_access.command
        if item.related_access is not None
        else None
    )
    return RuleDiagnostic(
        rule_order=item.rule_order,
        code=code,
        severity=item.severity,
        eligibility=None,
        message=item.message,
        location=item.location or access.location,
        category=RuleDiagnosticCategory.PERSISTENT_STATE,
        source_code=item.code.value,
        state_kind=state_kind,
        state_identifier=state_identifier,
        related_rule_order=related_rule_order,
        related_operation=related_operation,
    )


def _recurrent_diagnostic_for(item) -> RuleDiagnostic:
    code_map = {
        "REX-001": RuleDiagnosticCode.RECURRENT_NEVER_RUNNABLE,
        "REX-002": RuleDiagnosticCode.RECURRENT_RUNTIME_DEPENDENT,
        "REX-003": RuleDiagnosticCode.RECURRENT_GUARANTEED_PREEMPTION,
        "REX-004": RuleDiagnosticCode.RECURRENT_STATE_STARVATION,
    }
    severity = (
        DiagnosticSeverity.INFO
        if item.code == "REX-002"
        else DiagnosticSeverity.ERROR
    )
    return RuleDiagnostic(
        rule_order=item.rule_order,
        code=code_map[item.code],
        severity=severity,
        eligibility=None,
        message=item.message,
        location=item.location,
        category=RuleDiagnosticCategory.RECURRENT_EXECUTION,
        source_code=item.code,
        state_kind=item.state_kind,
        state_identifier=item.state_identifier,
        related_rule_order=item.related_rule_order,
        related_operation="recurrent-execution",
    )


def _diagnostic_sort_key(item: RuleDiagnostic) -> tuple[object, ...]:
    related_rule = item.related_rule_order if item.related_rule_order is not None else -1
    category_order = {
        RuleDiagnosticCategory.FIRING_ELIGIBILITY: 0,
        RuleDiagnosticCategory.PERSISTENT_STATE: 1,
        RuleDiagnosticCategory.STRATEGIC_NUMBER: 1,
        RuleDiagnosticCategory.CONTROL_FLOW: 2,
        RuleDiagnosticCategory.DUC: 3,
        RuleDiagnosticCategory.RECURRENT_EXECUTION: 4,
    }
    return (
        item.rule_order,
        category_order[item.category],
        item.code.value,
        item.state_kind or "",
        item.state_identifier or "",
        related_rule,
        item.related_operation or "",
        item.message,
    )


def _unreachable_rule_diagnostics(
    report: RuleExecutionReport,
) -> tuple[RuleDiagnostic, ...]:
    reachability = report.reachability
    if reachability is None:
        reachability = analyze_rule_reachability(
            report.rules,
            report.control_transfers,
        )

    diagnostics: list[RuleDiagnostic] = []
    for rule_order in reachability.unreachable_rule_orders:
        rule = report.rules[rule_order - 1]
        diagnostics.append(
            RuleDiagnostic(
                rule_order=rule_order,
                code=RuleDiagnosticCode.CONTROL_TRANSFER_UNREACHABLE_RULE,
                severity=DiagnosticSeverity.ERROR,
                eligibility=None,
                message=(
                    f"rule {rule_order} has no reachable control-flow path "
                    "from the start of a pass across recurrent rule execution"
                ),
                location=rule.source_location,
                category=RuleDiagnosticCategory.CONTROL_FLOW,
                source_code=RuleDiagnosticCode.CONTROL_TRANSFER_UNREACHABLE_RULE.value,
                related_rule_order=None,
                related_operation="control-flow",
            )
        )
    return tuple(diagnostics)


def _control_flow_diagnostics(
    report: RuleExecutionReport,
) -> tuple[RuleDiagnostic, ...]:
    diagnostics: list[RuleDiagnostic] = []
    rules_by_order = {rule.rule_order: rule for rule in report.rules}
    for transfer in report.control_transfers:
        if transfer.target_rule_order is None:
            diagnostics.append(
                RuleDiagnostic(
                    rule_order=transfer.rule_order,
                    code=RuleDiagnosticCode.CONTROL_TRANSFER_OUT_OF_RANGE,
                    severity=DiagnosticSeverity.ERROR,
                    eligibility=None,
                    message=(
                        "up-jump-rule in rule "
                        + str(transfer.rule_order)
                        + " with delta "
                        + str(transfer.delta)
                        + " resolves outside the effective rule set"
                    ),
                    location=transfer.location,
                    category=RuleDiagnosticCategory.CONTROL_FLOW,
                    source_code=RuleDiagnosticCode.CONTROL_TRANSFER_OUT_OF_RANGE.value,
                    related_rule_order=None,
                    related_operation="up-jump-rule",
                )
            )
            continue

        source_rule = rules_by_order[transfer.rule_order]
        if (
            transfer.target_rule_order == transfer.rule_order
            and source_rule.disable_self_action_index is not None
            and source_rule.disable_self_action_index < transfer.within_rule_order
        ):
            diagnostics.append(
                RuleDiagnostic(
                    rule_order=transfer.rule_order,
                    code=RuleDiagnosticCode.CONTROL_TRANSFER_INTO_DISABLED_RULE,
                    severity=DiagnosticSeverity.WARNING,
                    eligibility=None,
                    message=(
                        "up-jump-rule in rule "
                        + str(transfer.rule_order)
                        + " targets the same rule after disable-self; "
                        "the target is disabled on re-entry and control falls through"
                    ),
                    location=transfer.location,
                    category=RuleDiagnosticCategory.CONTROL_FLOW,
                    source_code=RuleDiagnosticCode.CONTROL_TRANSFER_INTO_DISABLED_RULE.value,
                    related_rule_order=transfer.target_rule_order,
                    related_operation="up-jump-rule",
                )
            )

        if transfer.target_rule_order > transfer.rule_order + 1:
            diagnostics.append(
                RuleDiagnostic(
                    rule_order=transfer.rule_order,
                    code=RuleDiagnosticCode.CONTROL_TRANSFER_BYPASSES_RULE,
                    severity=DiagnosticSeverity.INFO,
                    eligibility=None,
                    message=(
                        "up-jump-rule in rule "
                        + str(transfer.rule_order)
                        + " can bypass rules "
                        + str(transfer.rule_order + 1)
                        + " through "
                        + str(transfer.target_rule_order - 1)
                        + " in the current pass"
                    ),
                    location=transfer.location,
                    category=RuleDiagnosticCategory.CONTROL_FLOW,
                    source_code=RuleDiagnosticCode.CONTROL_TRANSFER_BYPASSES_RULE.value,
                    related_rule_order=transfer.target_rule_order,
                    related_operation="up-jump-rule",
                )
            )
            skipped = range(
                transfer.rule_order + 1,
                transfer.target_rule_order,
            )
            source_rule = rules_by_order[transfer.rule_order]
            source_guard_guaranteed = (
                len(source_rule.facts) == 1
                and source_rule.facts[0].head == "true"
            )
            for skipped_rule_order in skipped:
                severity = (
                    DiagnosticSeverity.WARNING
                    if source_rule.pass_behavior.value == "RECURRENT"
                    and source_guard_guaranteed
                    else DiagnosticSeverity.INFO
                )
                code = (
                    RuleDiagnosticCode.CONTROL_TRANSFER_PREEMPTS_RULE
                    if severity is DiagnosticSeverity.WARNING
                    else RuleDiagnosticCode.CONTROL_TRANSFER_BYPASSES_RULE
                )
                diagnostics.append(
                    RuleDiagnostic(
                        rule_order=transfer.rule_order,
                        code=code,
                        severity=severity,
                        eligibility=None,
                        message=(
                            "recurrent guaranteed up-jump-rule in rule "
                            + str(transfer.rule_order)
                            + " preempts rule "
                            + str(skipped_rule_order)
                            + " on each firing of the source rule; "
                            + "alternate control paths are not ruled out"
                            if severity is DiagnosticSeverity.WARNING
                            else
                            "up-jump-rule in rule "
                            + str(transfer.rule_order)
                            + " can bypass rule "
                            + str(skipped_rule_order)
                            + " in the current pass"
                        ),
                        location=transfer.location,
                        category=RuleDiagnosticCategory.CONTROL_FLOW,
                        source_code=code.value,
                        related_rule_order=skipped_rule_order,
                        related_operation="up-jump-rule",
                    )
                )

    return tuple(diagnostics)

def _duc_diagnostic_for(item: DucDiagnostic) -> RuleDiagnostic:
    try:
        code = RuleDiagnosticCode(item.code)
    except ValueError as exc:
        raise ValueError(f"unknown DUC diagnostic code '{item.code}'") from exc
    try:
        severity = DiagnosticSeverity(item.severity)
    except ValueError as exc:
        raise ValueError(f"unknown DUC diagnostic severity '{item.severity}'") from exc
    return RuleDiagnostic(
        rule_order=item.rule_order,
        code=code,
        severity=severity,
        eligibility=None,
        message=item.message,
        location=item.location,
        category=RuleDiagnosticCategory.DUC,
        source_code=item.code,
        state_kind=item.state_kind,
        state_identifier=item.state_identifier,
        related_rule_order=item.related_rule_order,
        related_operation=item.related_operation,
    )


def _strategic_number_diagnostic_for(
    item,
    report: RuleExecutionReport,
) -> RuleDiagnostic:
    rule = report.rules[item.rule_order - 1]
    code_map = {
        StrategicNumberDiagnosticCode.INVALID_ARITY: RuleDiagnosticCode.STRATEGIC_NUMBER_INVALID_ARITY,
        StrategicNumberDiagnosticCode.INVALID_OPERATOR: RuleDiagnosticCode.STRATEGIC_NUMBER_INVALID_OPERATOR,
        StrategicNumberDiagnosticCode.INVALID_OPERAND_PREFIX: RuleDiagnosticCode.STRATEGIC_NUMBER_INVALID_OPERAND_PREFIX,
        StrategicNumberDiagnosticCode.INVALID_LITERAL: RuleDiagnosticCode.STRATEGIC_NUMBER_INVALID_LITERAL,
        StrategicNumberDiagnosticCode.OUT_OF_RANGE_LITERAL: RuleDiagnosticCode.STRATEGIC_NUMBER_OUT_OF_RANGE_LITERAL,
        StrategicNumberDiagnosticCode.CONSTANT_ZERO_DIVISOR: RuleDiagnosticCode.STRATEGIC_NUMBER_CONSTANT_ZERO_DIVISOR,
        StrategicNumberDiagnosticCode.MISSING_DEPENDENCY: RuleDiagnosticCode.STRATEGIC_NUMBER_MISSING_DEPENDENCY,
        StrategicNumberDiagnosticCode.INVALID_TARGET: RuleDiagnosticCode.STRATEGIC_NUMBER_INVALID_TARGET,
        StrategicNumberDiagnosticCode.FUTURE_SAME_RULE_DEPENDENCY: RuleDiagnosticCode.STRATEGIC_NUMBER_FUTURE_SAME_RULE_DEPENDENCY,
    }
    return RuleDiagnostic(
        rule_order=item.rule_order,
        code=code_map[item.code],
        severity=item.severity,
        eligibility=None,
        message=item.message,
        location=item.location or rule.source_location,
        category=RuleDiagnosticCategory.STRATEGIC_NUMBER,
        source_code=item.code.value,
    )


def analyze_rule_diagnostics(
    report: RuleExecutionReport,
    registry: PrimitiveRegistry | None = None,
    *,
    runtime_demand_states: Mapping[int, object] | None = None,
    completion_witnesses: Mapping[int, object] | None = None,
    persistent_state_report: PersistentStateReport | None = None,
    strategic_number_report: StrategicNumberSemanticReport | None = None,
    recurrent_execution_report: RecurrentExecutionReport | None = None,
    duc_report: DucAnalysisReport | None = None,
) -> RuleDiagnosticReport:
    """Compile firing eligibility into deterministic diagnostics by rule order."""
    if not isinstance(report, RuleExecutionReport):
        raise TypeError("report must be a RuleExecutionReport")

    registry = registry or default_de_registry()
    try:
        fact_registry = registry.fact_registry
    except ValueError:
        # Some compiler fixtures deliberately exercise native support without
        # a semantic fact bridge. Public rule diagnostics fail closed.
        fact_registry = None
    runtime_demand_states = runtime_demand_states or {}
    completion_witnesses = completion_witnesses or {}
    if persistent_state_report is not None and not isinstance(
        persistent_state_report, PersistentStateReport
    ):
        raise TypeError(
            "persistent_state_report must be a PersistentStateReport"
        )
    if strategic_number_report is not None and not isinstance(
        strategic_number_report, StrategicNumberSemanticReport
    ):
        raise TypeError(
            "strategic_number_report must be a StrategicNumberSemanticReport"
        )

    if recurrent_execution_report is not None and not isinstance(
        recurrent_execution_report, RecurrentExecutionReport
    ):
        raise TypeError(
            "recurrent_execution_report must be a RecurrentExecutionReport"
        )

    diagnostics: list[RuleDiagnostic] = []
    for rule in report.rules:
        if fact_registry is None:
            guard = GuardSatisfiability.UNKNOWN
        else:
            try:
                guard = analyze_guard(
                    _guard_expression(rule),
                    fact_registry,
                )
            except ValueError:
                # Rule diagnostics are advisory. A guard shape outside the
                # current static-proof domain is runtime-dependent, not a
                # compiler crash.
                guard = GuardSatisfiability.UNKNOWN
        eligibility = analyze_firing_eligibility(
            rule,
            guard,
            runtime_demand_state=runtime_demand_states.get(rule.rule_order),
            completion_witness=completion_witnesses.get(rule.rule_order),
        )
        diagnostics.append(_diagnostic_for(rule, eligibility))

    if persistent_state_report is not None:
        diagnostics.extend(
            _persistent_diagnostic_for(item)
            for item in persistent_state_report.diagnostics
        )

    if strategic_number_report is not None:
        diagnostics.extend(
            _strategic_number_diagnostic_for(item, report)
            for item in strategic_number_report.diagnostics
        )

    if duc_report is not None:
        if not isinstance(duc_report, DucAnalysisReport):
            raise TypeError("duc_report must be a DucAnalysisReport")
        diagnostics.extend(
            _duc_diagnostic_for(item)
            for item in duc_report.diagnostics
        )

    diagnostics.extend(_unreachable_rule_diagnostics(report))

    diagnostics.extend(_control_flow_diagnostics(report))

    if recurrent_execution_report is not None:
        diagnostics.extend(
            _recurrent_diagnostic_for(item)
            for item in recurrent_execution_report.diagnostics
        )

    return RuleDiagnosticReport(
        tuple(sorted(diagnostics, key=_diagnostic_sort_key))
    )


__all__ = [
    "RuleDiagnostic",
    "RuleDiagnosticCategory",
    "RuleDiagnosticCode",
    "RuleDiagnosticReport",
    "analyze_rule_diagnostics",
]
