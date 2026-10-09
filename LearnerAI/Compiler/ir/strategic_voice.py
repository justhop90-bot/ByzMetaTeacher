"""Typed compiler-owned Strategos narration IR.

Voice is a read-only projection of already-established strategy transitions.
It owns narration latches/cooldowns only; it never owns strategic decisions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from enum import IntEnum

from ..ast import Expression
from .model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from .native_control import NativeControlState
from .recurrent import TimerRequest


_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_LOGICAL_ARITY = {"and": 2, "or": 2, "not": 1}


class VoicePriority(IntEnum):
    CRITICAL = 100
    DECISION = 80
    RECOVERY = 70
    TACTICAL = 60
    CONTEXT = 40
    FLAVOR = 20


class VoiceAudience(str, Enum):
    PLAYER = "PLAYER"
    ALLIES = "ALLIES"
    ALL = "ALL"


class VoiceLatchMode(str, Enum):
    REARM_ON_CLEAR = "REARM_ON_CLEAR"


@dataclass(frozen=True)
class NativeVoiceBudget:
    soft_match_limit: int = 36
    hard_match_limit: int = 48
    ordinary_global_cooldown_seconds: int = 12
    critical_global_cooldown_seconds: int = 4

    def __post_init__(self) -> None:
        if self.soft_match_limit <= 0 or self.hard_match_limit <= 0:
            raise ValueError("voice match limits must be positive")
        if self.soft_match_limit > self.hard_match_limit:
            raise ValueError("voice soft match limit must not exceed hard match limit")
        if self.ordinary_global_cooldown_seconds <= 0:
            raise ValueError("voice ordinary global cooldown must be positive")
        if self.critical_global_cooldown_seconds <= 0:
            raise ValueError("voice critical global cooldown must be positive")


@dataclass(frozen=True)
class VoiceRule:
    identity: str
    order: int
    priority: VoicePriority
    trigger: Expression
    clear: Expression | None
    message: str
    latch_state: str
    rearm_timer: str
    cooldown_seconds: int
    audience: VoiceAudience = VoiceAudience.PLAYER
    latch_mode: VoiceLatchMode = VoiceLatchMode.REARM_ON_CLEAR

    @property
    def critical(self) -> bool:
        return self.priority is VoicePriority.CRITICAL

    def __post_init__(self) -> None:
        if not _NAME_RE.fullmatch(self.identity):
            raise ValueError(f"invalid voice rule identity '{self.identity}'")
        if self.order < 0:
            raise ValueError("voice rule order must be non-negative")
        for label, value in (("latch", self.latch_state), ("rearm timer", self.rearm_timer)):
            if not _NAME_RE.fullmatch(value):
                raise ValueError(f"invalid voice {label} '{value}'")
        if self.cooldown_seconds <= 0:
            raise ValueError("voice rule cooldown must be positive")
        if not self.message.strip():
            raise ValueError("voice rule message must not be empty")
        if len(self.message) > 180:
            raise ValueError("voice rule message exceeds the compiler budget")
        if '"' in self.message or "\\" in self.message:
            raise ValueError("voice rule message contains an unsupported quote or backslash")
        if self.latch_mode is not VoiceLatchMode.REARM_ON_CLEAR:
            raise ValueError(f"unsupported voice latch mode '{self.latch_mode.value}'")
        if self.clear is None:
            raise ValueError(
                f"VOICE-POLLING-RULE: voice rule '{self.identity}' requires a clear witness"
            )


@dataclass(frozen=True)
class NativeVoicePlan:
    states: tuple[NativeControlState, ...] = ()
    rules: tuple[VoiceRule, ...] = ()
    budget: NativeVoiceBudget = NativeVoiceBudget()
    global_lock_state: str = "voice-global-lock"
    match_count_state: str = "voice-match-count"
    global_cooldown_timer: str = "voice-global-cooldown"

    def __post_init__(self) -> None:
        state_names = tuple(state.identifier for state in self.states)
        if len(state_names) != len(set(state_names)):
            raise ValueError("duplicate NativeVoicePlan state identifier")
        rule_ids = tuple(rule.identity for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("duplicate NativeVoicePlan rule identity")
        orders = tuple(rule.order for rule in self.rules)
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate NativeVoicePlan rule order")
        if orders != tuple(sorted(orders)):
            raise ValueError("NativeVoicePlan rules must be declared in deterministic order")

    @property
    def storage_requests(self) -> tuple[object, ...]:
        seen = set()
        requests = []
        for state in self.states:
            if state.request.request_id in seen:
                continue
            seen.add(state.request.request_id)
            requests.append(state.request)
        return tuple(requests)

    def state(self, identifier: str) -> NativeControlState:
        for state in self.states:
            if state.identifier == identifier:
                return state
        raise KeyError(identifier)


def make_voice_goal_state(profile_id: str, name: str) -> NativeControlState:
    return NativeControlState(
        name,
        GoalSlotRequest(
            StorageRequestId(SemanticId(profile_id, name), name),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )


def make_voice_timer_state(profile_id: str, name: str) -> NativeControlState:
    return NativeControlState(
        name,
        TimerRequest(
            StorageRequestId(
                SemanticId(profile_id, f"voice:{name}"),
                f"timer:{name}",
            ),
            initialization_policy="DISABLE_BEFORE_FIRST_USE",
            stability_key=f"{profile_id}:{name}",
        ),
    )


def _validate_fact_expression(expression: Expression, registry) -> None:
    if expression.head in _LOGICAL_ARITY:
        expected = _LOGICAL_ARITY[expression.head]
        if len(expression.args) != expected or any(
            not isinstance(argument, Expression) for argument in expression.args
        ):
            raise ValueError(
                f"VOICE-FACT-ARITY: logical '{expression.head}' has an invalid operand shape"
            )
        for argument in expression.args:
            _validate_fact_expression(argument, registry)
        return
    native = registry.native(expression.head)
    if native is None:
        raise ValueError(f"VOICE-NATIVE-UNKNOWN: '{expression.head}' is not registered")
    if native.command_type not in {"Fact", "Fact/Action"}:
        raise ValueError(f"VOICE-NATIVE-KIND: '{expression.head}' is not a Fact")
    if len(expression.args) != native.parameter_count:
        raise ValueError(
            f"VOICE-NATIVE-ARITY: '{expression.head}' expects {native.parameter_count} "
            f"argument(s), got {len(expression.args)}"
        )


def validate_native_voice_plan(plan: NativeVoicePlan, registry=None) -> None:
    if not isinstance(plan, NativeVoicePlan):
        raise TypeError("voice_plan must be a NativeVoicePlan")
    if registry is None:
        from ..primitives import default_de_registry
        registry = default_de_registry()

    states = {state.identifier: state for state in plan.states}
    for name in (plan.global_lock_state, plan.match_count_state, plan.global_cooldown_timer):
        if name not in states:
            raise ValueError(f"VOICE-STATE-MISSING: '{name}' is not declared")

    global_lock = states[plan.global_lock_state].request
    match_count = states[plan.match_count_state].request
    global_timer = states[plan.global_cooldown_timer].request
    if not isinstance(global_lock, GoalSlotRequest) or not isinstance(match_count, GoalSlotRequest):
        raise ValueError("VOICE-STATE-TYPE: global lock and match count must be GoalSlotRequest")
    if not isinstance(global_timer, TimerRequest):
        raise ValueError("VOICE-TIMER-TYPE: global cooldown must be TimerRequest")

    for rule in plan.rules:
        if rule.latch_state not in states:
            raise ValueError(f"VOICE-LATCH-MISSING: '{rule.identity}' references unknown latch")
        if rule.rearm_timer not in states:
            raise ValueError(f"VOICE-TIMER-MISSING: '{rule.identity}' references unknown timer")
        if not isinstance(states[rule.latch_state].request, GoalSlotRequest):
            raise ValueError(f"VOICE-LATCH-TYPE: '{rule.identity}' latch must be GoalSlotRequest")
        if not isinstance(states[rule.rearm_timer].request, TimerRequest):
            raise ValueError(f"VOICE-TIMER-TYPE: '{rule.identity}' timer must be TimerRequest")
        if rule.critical and rule.cooldown_seconds < plan.budget.critical_global_cooldown_seconds:
            raise ValueError(
                f"VOICE-COOLDOWN-CRITICAL: '{rule.identity}' cooldown is shorter than critical global cooldown"
            )
        _validate_fact_expression(rule.trigger, registry)
        _validate_fact_expression(rule.clear, registry)

    for state in plan.states:
        if not isinstance(state.request, (GoalSlotRequest, TimerRequest)):
            raise ValueError(
                f"VOICE-STORAGE-TYPE: '{state.identifier}' has unsupported request "
                f"'{type(state.request).__name__}'"
            )


__all__ = [
    "NativeVoiceBudget",
    "NativeVoicePlan",
    "VoiceAudience",
    "VoiceLatchMode",
    "VoicePriority",
    "VoiceRule",
    "make_voice_goal_state",
    "make_voice_timer_state",
    "validate_native_voice_plan",
]
