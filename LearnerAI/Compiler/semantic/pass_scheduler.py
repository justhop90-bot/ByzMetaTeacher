"""Minimal recurrent .per pass scheduler for timer/control-flow semantics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..ast import Expression
from ..ir.recurrent import (
    PendingTimerExpiry,
    TimerRuntimeState,
    TimerStatus,
    create_initialized_timer,
    read_timer_triggered,
)
from .rule_execution import EffectiveRule
from .strategic_number_semantics import (
    StrategicNumberSemanticError,
    evaluate_strategic_number_mutation,
    parse_strategic_number_mutation,
)


class SchedulerSemanticError(ValueError):
    """Raised when a recurrent rule cannot be represented safely."""


@dataclass(frozen=True)
class ControlTransfer:
    rule_order: int
    delta: int
    target_rule_order: int


@dataclass(frozen=True)
class PassTrace:
    pass_id: int
    evaluated_rule_orders: tuple[int, ...]
    fired_rule_orders: tuple[int, ...]
    skipped_rule_orders: tuple[int, ...]
    control_transfers: tuple[ControlTransfer, ...]
    committed_expiries: tuple[PendingTimerExpiry, ...]
    staged_expiries: tuple[PendingTimerExpiry, ...]


ActionHandler = Callable[[Expression], None]


class PassScheduler:
    """Execute the minimum recurrent control/timer subset of .per."""

    def __init__(
        self,
        rules: tuple[EffectiveRule, ...],
        *,
        timer_ids: tuple[str, ...] = (),
        goal_values: dict[str, int] | None = None,
        strategic_number_values: dict[str, int] | None = None,
        action_handler: ActionHandler | None = None,
    ) -> None:
        self.rules = tuple(rules)
        expected_orders = tuple(range(1, len(self.rules) + 1))
        actual_orders = tuple(rule.rule_order for rule in self.rules)
        if actual_orders != expected_orders:
            raise SchedulerSemanticError(
                "effective rules must have contiguous 1-based rule_order values"
            )
        if len(set(timer_ids)) != len(timer_ids):
            raise SchedulerSemanticError("timer_ids must be unique")
        self._enabled = {rule.rule_order: True for rule in self.rules}
        self._timers = {
            timer_id: create_initialized_timer(timer_id)
            for timer_id in timer_ids
        }
        self._goals = {
            str(identifier): int(value)
            for identifier, value in (goal_values or {}).items()
        }
        self._strategic_numbers = {
            str(identifier): int(value)
            for identifier, value in (strategic_number_values or {}).items()
        }
        self._pending_expiries: list[PendingTimerExpiry] = []
        self._pass_id = 0
        self._now_seconds = 0.0
        self._action_handler = action_handler

    @property
    def pass_id(self) -> int:
        return self._pass_id

    @property
    def now_seconds(self) -> float:
        return self._now_seconds

    @property
    def timers(self) -> tuple[TimerRuntimeState, ...]:
        return tuple(
            self._timers[timer_id]
            for timer_id in sorted(self._timers)
        )

    @property
    def pending_expiries(self) -> tuple[PendingTimerExpiry, ...]:
        return tuple(self._pending_expiries)

    @property
    def goals(self) -> dict[str, int]:
        return dict(self._goals)

    @property
    def strategic_numbers(self) -> dict[str, int]:
        return dict(self._strategic_numbers)

    def run_pass(self, *, elapsed_seconds: float = 0.0) -> PassTrace:
        if elapsed_seconds < 0:
            raise SchedulerSemanticError(
                "elapsed_seconds must be non-negative"
            )

        committed = self._commit_pending_expiries()
        evaluated: list[int] = []
        fired: list[int] = []
        skipped: list[int] = []
        transfers: list[ControlTransfer] = []

        pc = 0
        while pc < len(self.rules):
            rule = self.rules[pc]
            evaluated.append(rule.rule_order)

            if not self._enabled[rule.rule_order]:
                skipped.append(rule.rule_order)
                pc += 1
                continue

            if not self._evaluate_facts(rule.facts):
                skipped.append(rule.rule_order)
                pc += 1
                continue

            fired.append(rule.rule_order)
            jump_delta: int | None = None

            for action in rule.actions:
                expression = action.expression
                head = expression.head

                if head == "enable-timer":
                    timer_id, duration = self._enable_args(expression)
                    self._timers[timer_id] = self._timers[timer_id].enable(
                        duration,
                        self._now_seconds,
                    )
                elif head == "set-goal":
                    self._set_goal_action(expression)
                elif head == "set-strategic-number":
                    self._set_strategic_number_action(expression)
                elif head == "up-modify-sn":
                    self._apply_strategic_number_mutation(
                        expression,
                        rule.rule_order,
                        action.within_rule_order,
                    )
                elif head == "disable-timer":
                    timer_id = self._timer_id_arg(expression, 0)
                    self._timers[timer_id] = self._timers[timer_id].disable()
                elif head == "up-set-timer":
                    timer_id, interval = self._up_set_timer_args(expression)
                    if interval < 0:
                        self._timers[timer_id] = self._timers[timer_id].disable()
                    else:
                        self._timers[timer_id] = self._timers[timer_id].enable(
                            interval,
                            self._now_seconds,
                        )
                elif head == "disable-self":
                    self._enabled[rule.rule_order] = False
                elif head == "up-jump-rule":
                    if len(expression.args) != 1:
                        raise SchedulerSemanticError(
                            "up-jump-rule requires exactly one RuleDelta argument"
                        )
                    jump_delta = self._parse_int(
                        expression.args[0],
                        "up-jump-rule RuleDelta",
                    )
                elif head == "true":
                    pass
                elif self._action_handler is not None:
                    self._action_handler(expression)

            if jump_delta is None:
                pc += 1
                continue

            target_index = pc + jump_delta + 1
            if target_index < 0 or target_index >= len(self.rules):
                raise SchedulerSemanticError(
                    f"up-jump-rule from rule {rule.rule_order} resolves outside "
                    f"the effective rule set: delta {jump_delta}"
                )
            target_order = self.rules[target_index].rule_order
            transfers.append(
                ControlTransfer(
                    rule_order=rule.rule_order,
                    delta=jump_delta,
                    target_rule_order=target_order,
                )
            )
            pc = target_index

        self._now_seconds += float(elapsed_seconds)
        staged = self._stage_expiries()

        trace = PassTrace(
            pass_id=self._pass_id,
            evaluated_rule_orders=tuple(evaluated),
            fired_rule_orders=tuple(fired),
            skipped_rule_orders=tuple(skipped),
            control_transfers=tuple(transfers),
            committed_expiries=tuple(committed),
            staged_expiries=tuple(staged),
        )
        self._pass_id += 1
        return trace

    def _commit_pending_expiries(self) -> tuple[PendingTimerExpiry, ...]:
        committed: list[PendingTimerExpiry] = []
        remaining: list[PendingTimerExpiry] = []

        for pending in self._pending_expiries:
            timer = self._timers.get(pending.timer_id)
            if timer is None:
                continue
            if timer.can_commit_pending_expiry(pending):
                self._timers[pending.timer_id] = timer.commit_expiry()
                committed.append(pending)
            # A stale pending expiry is discarded, not requeued.

        self._pending_expiries = remaining
        return committed

    def _stage_expiries(self) -> tuple[PendingTimerExpiry, ...]:
        staged: list[PendingTimerExpiry] = []
        queued = {
            (item.timer_id, item.generation)
            for item in self._pending_expiries
        }
        for timer_id in sorted(self._timers):
            timer = self._timers[timer_id]
            if timer.status is not TimerStatus.RUNNING:
                continue
            if timer.deadline is None or timer.deadline > self._now_seconds:
                continue
            key = (timer.timer_id, timer.generation)
            if key in queued:
                continue
            pending = timer.stage_expiry(self._now_seconds)
            self._pending_expiries.append(pending)
            staged.append(pending)
            queued.add(key)
        return tuple(staged)

    def _evaluate_facts(self, facts: tuple[Expression, ...]) -> bool:
        return all(self._evaluate_fact(fact) for fact in facts)

    def _evaluate_fact(self, expression: Expression) -> bool:
        head = expression.head
        if head == "true":
            return True
        if head == "strategic-number":
            return self._evaluate_strategic_number_fact(expression)
        if head == "up-modify-sn":
            self._apply_strategic_number_mutation(
                expression,
                None,
                -1,
                section="GUARD",
            )
            return True
        if head == "goal":
            if len(expression.args) != 2:
                raise SchedulerSemanticError(
                    "goal requires GoalId and expected value"
                )
            return self._goals.get(str(expression.args[0]), 0) == self._parse_int(
                expression.args[1],
                "goal value",
            )
        if head == "timer-triggered":
            timer_id = self._timer_id_arg(expression, 0)
            return read_timer_triggered(self._timers[timer_id])
        if head == "up-timer-status":
            if len(expression.args) != 3:
                raise SchedulerSemanticError(
                    "up-timer-status requires TimerId, compareOp, and TimerState"
                )
            timer_id = self._timer_id_arg(expression, 0)
            operator = str(expression.args[1]).lstrip("c:")
            expected = str(expression.args[2]).lstrip("c:")
            actual = self._timers[timer_id].status.value.lower()
            expected = expected.replace("timer-", "")
            if operator in {"=", "=="}:
                return actual == expected.upper() or actual == expected
            if operator == "!=":
                return actual != expected.upper() and actual != expected
            raise SchedulerSemanticError(
                f"up-timer-status operator '{operator}' is outside the scheduler's "
                "minimum equality contract"
            )
        if head == "and":
            return all(
                self._evaluate_fact(argument)
                for argument in expression.args
                if isinstance(argument, Expression)
            )
        if head == "or":
            return any(
                self._evaluate_fact(argument)
                for argument in expression.args
                if isinstance(argument, Expression)
            )
        if head == "not":
            if len(expression.args) != 1 or not isinstance(
                expression.args[0], Expression
            ):
                raise SchedulerSemanticError("not requires one nested fact")
            return not self._evaluate_fact(expression.args[0])
        raise SchedulerSemanticError(
            f"unsupported scheduler fact '{head}'"
        )

    def _set_goal_action(self, expression: Expression) -> None:
        if len(expression.args) != 2:
            raise SchedulerSemanticError("set-goal requires GoalId and Value")
        self._goals[str(expression.args[0])] = self._parse_int(
            expression.args[1],
            "goal value",
        )

    def _set_strategic_number_action(self, expression: Expression) -> None:
        if len(expression.args) != 2:
            raise SchedulerSemanticError(
                "set-strategic-number requires SnId and Value"
            )
        self._strategic_numbers[str(expression.args[0])] = self._parse_int(
            expression.args[1],
            "strategic number value",
        )

    def _apply_strategic_number_mutation(
        self,
        expression: Expression,
        rule_order: int | None,
        within_rule_order: int,
        *,
        section: str = "ACTION",
    ) -> None:
        try:
            mutation = parse_strategic_number_mutation(
                expression,
                rule_order=rule_order,
                within_rule_order=within_rule_order,
                section=section,
            )
            result = evaluate_strategic_number_mutation(
                mutation,
                current_value=self._strategic_numbers.get(mutation.target, 0),
                goals=self._goals,
                strategic_numbers=self._strategic_numbers,
            )
        except StrategicNumberSemanticError as exc:
            raise SchedulerSemanticError(str(exc)) from exc
        self._strategic_numbers[mutation.target] = result

    def _evaluate_strategic_number_fact(self, expression: Expression) -> bool:
        if len(expression.args) != 3:
            raise SchedulerSemanticError(
                "strategic-number requires SnId, compareOp, and Value"
            )
        sn_id = str(expression.args[0])
        actual = self._strategic_numbers.get(sn_id, 0)
        operator = str(expression.args[1])
        value_token = expression.args[2]
        prefix = ""
        raw_operator = operator
        if ":" in operator:
            prefix, raw_operator = operator.split(":", 1)
        if prefix not in {"", "c", "g", "s"}:
            raise SchedulerSemanticError(
                f"unsupported Strategic Number compare operand prefix '{prefix}:'"
            )
        expected = self._resolve_compare_value(prefix, value_token, expression.head)
        if raw_operator in {"=", "=="}:
            return actual == expected
        if raw_operator == "!=":
            return actual != expected
        if raw_operator == "<":
            return actual < expected
        if raw_operator == "<=":
            return actual <= expected
        if raw_operator == ">":
            return actual > expected
        if raw_operator == ">=":
            return actual >= expected
        raise SchedulerSemanticError(
            f"unsupported Strategic Number comparison operator '{operator}'"
        )

    def _resolve_compare_value(
        self,
        prefix: str,
        value: object,
        command: str,
    ) -> int:
        identifier = str(value)
        if prefix in {"", "c"}:
            return self._parse_int(value, f"{command} compare value")
        if prefix == "g":
            return int(self._goals.get(identifier, 0))
        if prefix == "s":
            return int(self._strategic_numbers.get(identifier, 0))
        raise SchedulerSemanticError(
            f"unsupported Strategic Number comparison prefix '{prefix}:'"
        )

    def _timer_id_arg(self, expression: Expression, index: int) -> str:
        if len(expression.args) <= index:
            raise SchedulerSemanticError(
                f"{expression.head} is missing timer identifier"
            )
        timer_id = str(expression.args[index])
        if timer_id not in self._timers:
            raise SchedulerSemanticError(
                f"timer '{timer_id}' is not initialized in the scheduler"
            )
        return timer_id

    def _enable_args(self, expression: Expression) -> tuple[str, int]:
        if len(expression.args) != 2:
            raise SchedulerSemanticError(
                "enable-timer requires TimerId and duration"
            )
        timer_id = self._timer_id_arg(expression, 0)
        duration = self._parse_int(expression.args[1], "timer duration")
        if duration < 0:
            raise SchedulerSemanticError(
                "enable-timer duration must be non-negative"
            )
        return timer_id, duration

    def _up_set_timer_args(self, expression: Expression) -> tuple[str, int]:
        if len(expression.args) < 4:
            raise SchedulerSemanticError(
                "up-set-timer requires typeOp, TimerId, typeOp, and interval"
            )
        timer_id = self._timer_id_arg(expression, 1)
        interval = self._parse_int(expression.args[3], "up-set-timer interval")
        return timer_id, interval

    @staticmethod
    def _parse_int(value: object, label: str) -> int:
        try:
            return int(str(value), 10)
        except (TypeError, ValueError) as exc:
            raise SchedulerSemanticError(
                f"{label} must be an integer in the minimum scheduler model"
            ) from exc


__all__ = [
    "ControlTransfer",
    "PassScheduler",
    "PassTrace",
    "SchedulerSemanticError",
]
