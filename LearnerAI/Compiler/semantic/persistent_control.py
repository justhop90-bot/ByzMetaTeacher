"""Static owner/release analysis for compiler-owned persistent controls."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from ..diagnostics import DiagnosticSeverity
from ..ir import (
    CleanupStatus,
    PersistentControlCleanupObligation,
    PersistentControlId,
    PersistentControlKind,
    PersistentControlRef,
    SemanticDemand,
    SemanticId,
)
from .persistent_state import (
    PersistentStateAccess,
    PersistentStateAccessKind,
    PersistentStateKind,
    PersistentStateReport,
    _timer_lifetime_effect,
)
from .rule_execution import EffectiveRule, RuleExecutionReport, analyze_rule_reachability


class PersistentControlDiagnosticCode(str, Enum):
    OWNER_MISMATCH = "PCONTROL-001"
    RELEASE_MISSING = "PCONTROL-002"
    CLEANUP_UNREACHABLE = "PCONTROL-003"
    CLEANUP_PRE_RELEASE = "PCONTROL-004"
    RELEASE_PATH_UNKNOWN = "PCONTROL-005"
    TIMER_AS_STRATEGIC_STATE = "PCONTROL-006"


class PersistentControlStatus(str, Enum):
    CONNECTED = "CONNECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PersistentControlDiagnostic:
    code: PersistentControlDiagnosticCode
    status: PersistentControlStatus
    severity: DiagnosticSeverity
    message: str
    control: PersistentControlId
    owner: SemanticId
    release_contract: SemanticId | None = None
    cleanup_rule_order: int | None = None
    release_rule_order: int | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class PersistentControlReport:
    controls: tuple[PersistentControlRef, ...]
    obligations: tuple[PersistentControlCleanupObligation, ...]
    diagnostics: tuple[PersistentControlDiagnostic, ...]

    @property
    def errors(self) -> tuple[PersistentControlDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is DiagnosticSeverity.ERROR)

    @property
    def warnings(self) -> tuple[PersistentControlDiagnostic, ...]:
        return tuple(item for item in self.diagnostics if item.severity is DiagnosticSeverity.WARNING)


def _expr_key(expr: Expression) -> tuple[object, ...]:
    return (
        expr.head,
        tuple(
            _expr_key(arg) if isinstance(arg, Expression) else str(arg)
            for arg in expr.args
        ),
    )


def _contains(root: Expression, needle: Expression) -> bool:
    if _expr_key(root) == _expr_key(needle):
        return True
    return any(
        _contains(arg, needle)
        for arg in root.args
        if isinstance(arg, Expression)
    )


def _release_rule(report: RuleExecutionReport, demand: SemanticDemand) -> EffectiveRule | None:
    goal_name = f"demand-{demand.name}"
    for rule in report.rules:
        if not any(_contains(fact, demand.release) for fact in rule.facts):
            continue
        if not any(
            fact.head == "goal"
            and len(fact.args) >= 2
            and str(fact.args[0]) == goal_name
            for fact in rule.facts
        ):
            continue
        if any(
            action.expression.head == "set-goal"
            and len(action.expression.args) == 2
            and str(action.expression.args[0]) == goal_name
            and str(action.expression.args[1]) == "0"
            for action in rule.actions
        ):
            return rule
    return None


def _release_write_index(rule: EffectiveRule, demand: SemanticDemand) -> int | None:
    goal_name = f"demand-{demand.name}"
    for action in rule.actions:
        if (
            action.expression.head == "set-goal"
            and len(action.expression.args) == 2
            and str(action.expression.args[0]) == goal_name
            and str(action.expression.args[1]) == "0"
        ):
            return action.within_rule_order
    return None


def _timer_accesses(
    report: PersistentStateReport,
    control: PersistentControlRef,
) -> tuple[PersistentStateAccess, ...]:
    timer_name = control.id.local_name.removeprefix("timer:")
    return tuple(
        access
        for access in report.accesses
        if (
            access.state.kind is PersistentStateKind.TIMER
            and access.state.identifier == timer_name
            and access.effect is PersistentStateAccessKind.WRITE
        )
    )


def _reachable(
    report: RuleExecutionReport,
    source: int,
    target: int,
) -> bool:
    if source == target:
        return True
    reachability = report.reachability or analyze_rule_reachability(
        report.rules,
        report.control_transfers,
    )
    outgoing = dict(reachability.outgoing_rule_orders)
    seen: set[int] = set()
    worklist = list(outgoing.get(source, ()))
    while worklist:
        current = worklist.pop()
        if current in seen:
            continue
        seen.add(current)
        if current == target:
            return True
        worklist.extend(outgoing.get(current, ()))
    return False


def _unresolved_control_flow(report: RuleExecutionReport) -> bool:
    return any(transfer.target_rule_order is None for transfer in report.control_transfers)


def analyze_persistent_control_lifetimes(
    demands: tuple[SemanticDemand, ...] | list[SemanticDemand],
    persistent_state: PersistentStateReport,
    rule_execution: RuleExecutionReport,
) -> PersistentControlReport:
    if not isinstance(persistent_state, PersistentStateReport):
        raise TypeError("persistent_state must be a PersistentStateReport")
    if not isinstance(rule_execution, RuleExecutionReport):
        raise TypeError("rule_execution must be a RuleExecutionReport")

    controls = tuple(
        control for demand in demands for control in demand.persistent_controls
    )
    demand_by_id = {demand.identity: demand for demand in demands}
    diagnostics: list[PersistentControlDiagnostic] = []
    obligations: list[PersistentControlCleanupObligation] = []

    for control in sorted(
        controls,
        key=lambda item: (
            item.owner.source_unit,
            item.owner.local_name,
            item.id.local_name,
        ),
    ):
        demand = demand_by_id.get(control.owner)
        if demand is None:
            diagnostics.append(
                PersistentControlDiagnostic(
                    PersistentControlDiagnosticCode.OWNER_MISMATCH,
                    PersistentControlStatus.BLOCKED,
                    DiagnosticSeverity.ERROR,
                    "persistent control owner does not identify a demand",
                    control.id,
                    control.owner,
                    location=None,
                )
            )
            continue

        if control.owner != demand.identity:
            diagnostics.append(
                PersistentControlDiagnostic(
                    PersistentControlDiagnosticCode.OWNER_MISMATCH,
                    PersistentControlStatus.BLOCKED,
                    DiagnosticSeverity.ERROR,
                    f"persistent control '{control.id.local_name}' has the wrong owner",
                    control.id,
                    control.owner,
                    demand.release_state.identity if demand.release_state else None,
                    location=demand.location,
                )
            )
            continue

        if control.kind is not PersistentControlKind.TIMER:
            continue

        accesses = _timer_accesses(persistent_state, control)
        starts = tuple(access for access in accesses if _timer_lifetime_effect(access) == "START")
        unknown_writes = tuple(access for access in accesses if _timer_lifetime_effect(access) is None)
        cleanup = tuple(access for access in accesses if _timer_lifetime_effect(access) == "CLEANUP")

        if not starts and not unknown_writes:
            if demand.release_state is not None:
                obligations.append(
                    PersistentControlCleanupObligation(
                        control.id,
                        control.owner,
                        demand.release_state.identity,
                        CleanupStatus.NOT_APPLICABLE,
                    )
                )
            continue

        if demand.release_state is None:
            release_id = SemanticId(control.owner.source_unit, f"{control.owner.local_name}-release")
            obligations.append(
                PersistentControlCleanupObligation(
                    control.id, control.owner, release_id, CleanupStatus.UNKNOWN
                )
            )
            diagnostics.append(
                PersistentControlDiagnostic(
                    PersistentControlDiagnosticCode.RELEASE_MISSING,
                    PersistentControlStatus.UNKNOWN,
                    DiagnosticSeverity.WARNING,
                    f"timer '{control.id.local_name}' has no release-state contract",
                    control.id,
                    control.owner,
                    release_id,
                    location=demand.location,
                )
            )
            continue

        release_rule = _release_rule(rule_execution, demand)
        release_write = _release_write_index(release_rule, demand) if release_rule else None
        if release_rule is None or release_write is None or _unresolved_control_flow(rule_execution):
            obligations.append(
                PersistentControlCleanupObligation(
                    control.id,
                    control.owner,
                    demand.release_state.identity,
                    CleanupStatus.UNKNOWN,
                    release_rule_order=release_rule.rule_order if release_rule else None,
                    cleanup_rule_orders=tuple(access.rule_order for access in cleanup),
                )
            )
            diagnostics.append(
                PersistentControlDiagnostic(
                    PersistentControlDiagnosticCode.RELEASE_PATH_UNKNOWN,
                    PersistentControlStatus.UNKNOWN,
                    DiagnosticSeverity.WARNING,
                    f"timer '{control.id.local_name}' cleanup reachability is not statically closed",
                    control.id,
                    control.owner,
                    demand.release_state.identity,
                    release_rule_order=release_rule.rule_order,
                    location=demand.location,
                )
            )
            continue

        valid_same_rule = tuple(
            access
            for access in cleanup
            if access.rule_order == release_rule.rule_order
            and access.within_rule_order > release_write
        )
        valid_later = tuple(
            access
            for access in cleanup
            if access.rule_order != release_rule.rule_order
            and _reachable(rule_execution, release_rule.rule_order, access.rule_order)
        )
        valid_cleanup = valid_same_rule + valid_later

        if unknown_writes:
            status = CleanupStatus.UNKNOWN
            diagnostic = PersistentControlDiagnostic(
                PersistentControlDiagnosticCode.RELEASE_PATH_UNKNOWN,
                PersistentControlStatus.UNKNOWN,
                DiagnosticSeverity.WARNING,
                f"timer '{control.id.local_name}' has dynamic timer writes with unknown lifetime",
                control.id,
                control.owner,
                demand.release_state.identity,
                location=demand.location,
            )
            diagnostics.append(diagnostic)
        elif valid_cleanup:
            status = CleanupStatus.SATISFIED
        else:
            status = CleanupStatus.REQUIRED
            if cleanup and all(
                access.rule_order < release_rule.rule_order
                or (
                    access.rule_order == release_rule.rule_order
                    and access.within_rule_order < release_write
                )
                for access in cleanup
            ):
                code = PersistentControlDiagnosticCode.CLEANUP_PRE_RELEASE
                message = f"timer '{control.id.local_name}' is cleaned only before owner release"
            elif cleanup:
                code = PersistentControlDiagnosticCode.CLEANUP_UNREACHABLE
                message = f"timer '{control.id.local_name}' cleanup is not reachable after owner release"
            else:
                code = PersistentControlDiagnosticCode.RELEASE_MISSING
                message = f"timer '{control.id.local_name}' has no explicit cleanup after owner release"
            diagnostics.append(
                PersistentControlDiagnostic(
                    code,
                    PersistentControlStatus.BLOCKED,
                    DiagnosticSeverity.WARNING,
                    message,
                    control.id,
                    control.owner,
                    demand.release_state.identity,
                    cleanup_rule_order=cleanup[0].rule_order if cleanup else None,
                    release_rule_order=release_rule.rule_order,
                    location=demand.location,
                )
            )

        obligations.append(
            PersistentControlCleanupObligation(
                control.id,
                control.owner,
                demand.release_state.identity,
                status,
                cleanup_commands=tuple(sorted({access.command for access in cleanup})),
                release_rule_order=release_rule.rule_order,
                cleanup_rule_orders=tuple(access.rule_order for access in cleanup),
            )
        )

    diagnostics.sort(
        key=lambda item: (
            item.owner.source_unit,
            item.owner.local_name,
            item.control.local_name,
            item.code.value,
            item.cleanup_rule_order or -1,
            item.message,
        )
    )
    return PersistentControlReport(controls=controls, obligations=tuple(obligations), diagnostics=tuple(diagnostics))


__all__ = [
    "PersistentControlDiagnostic",
    "PersistentControlDiagnosticCode",
    "PersistentControlReport",
    "PersistentControlStatus",
    "analyze_persistent_control_lifetimes",
]
