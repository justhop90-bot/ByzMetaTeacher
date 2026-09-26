"""Rule-level diagnostics compiled from static firing eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from ..ast import Expression, SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..primitives import PrimitiveRegistry, default_de_registry
from ..primitives.native_hygiene import NativeFactRegistry
from .firing_eligibility import FiringEligibility, analyze_firing_eligibility
from .guard_satisfiability import analyze_guard
from .rule_execution import EffectiveRule, RuleExecutionReport


class RuleDiagnosticCode(str, Enum):
    NEVER_ELIGIBLE = "RULE-FIRE-001"
    RUNTIME_DEPENDENT = "RULE-FIRE-002"
    FIRST_PASS_ELIGIBLE = "RULE-FIRE-003"
    RECURRENTLY_ELIGIBLE = "RULE-FIRE-004"


@dataclass(frozen=True)
class RuleDiagnostic:
    rule_order: int
    code: RuleDiagnosticCode
    severity: DiagnosticSeverity
    eligibility: FiringEligibility
    message: str
    location: SourceLocation


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
    )


def analyze_rule_diagnostics(
    report: RuleExecutionReport,
    registry: PrimitiveRegistry | None = None,
    *,
    runtime_demand_states: Mapping[int, object] | None = None,
    completion_witnesses: Mapping[int, object] | None = None,
) -> RuleDiagnosticReport:
    """Compile firing eligibility into deterministic diagnostics by rule order."""
    if not isinstance(report, RuleExecutionReport):
        raise TypeError("report must be a RuleExecutionReport")

    registry = registry or default_de_registry()
    fact_registry = registry.fact_registry
    runtime_demand_states = runtime_demand_states or {}
    completion_witnesses = completion_witnesses or {}

    diagnostics: list[RuleDiagnostic] = []
    for rule in report.rules:
        guard = analyze_guard(
            _guard_expression(rule),
            fact_registry,
        )
        eligibility = analyze_firing_eligibility(
            rule,
            guard,
            runtime_demand_state=runtime_demand_states.get(rule.rule_order),
            completion_witness=completion_witnesses.get(rule.rule_order),
        )
        diagnostics.append(_diagnostic_for(rule, eligibility))

    return RuleDiagnosticReport(tuple(diagnostics))


__all__ = [
    "RuleDiagnostic",
    "RuleDiagnosticCode",
    "RuleDiagnosticReport",
    "analyze_rule_diagnostics",
]
