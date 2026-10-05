"""Typed Byzantine end-game strategy and runtime contract.

The end-game layer owns strategic intent and state shape only. It does not emit
native attack, production, construction, DUC, Strategic Number, or timer
actions. Existing execution subsystems remain the owners of those behaviors.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EndgameMode(str, Enum):
    BREAKTHROUGH = "BREAKTHROUGH"
    ATTRITION = "ATTRITION"
    RESOURCE_DENIAL = "RESOURCE_DENIAL"
    RECOVERY = "RECOVERY"


class EndgameWinCondition(str, Enum):
    CAPABILITY_COLLAPSE = "CAPABILITY_COLLAPSE"
    RESOURCE_CONTROL = "RESOURCE_CONTROL"
    ATTRITION = "ATTRITION"
    MAP_CONTROL = "MAP_CONTROL"


class EndgamePushState(str, Enum):
    FORMING = "FORMING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    WITNESS = "WITNESS"
    ADVANCE = "ADVANCE"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class EndgamePolicyRule:
    identity: str
    mode: EndgameMode
    win_condition: EndgameWinCondition
    observation_refs: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("endgame policy rule identity must not be empty")
        if not isinstance(self.mode, EndgameMode):
            raise TypeError("endgame policy rule mode must be EndgameMode")
        if not isinstance(self.win_condition, EndgameWinCondition):
            raise TypeError(
                "endgame policy rule win_condition must be EndgameWinCondition"
            )
        if any(not reference.strip() for reference in self.observation_refs):
            raise ValueError(
                f"endgame policy rule '{self.identity}' contains an empty observation reference"
            )
        if len(self.observation_refs) != len(set(self.observation_refs)):
            raise ValueError(
                f"endgame policy rule '{self.identity}' observation references must be unique"
            )


@dataclass(frozen=True)
class EndgamePlan:
    identity: str
    rules: tuple[EndgamePolicyRule, ...]
    objective_priority: tuple[str, ...]
    push_states: tuple[EndgamePushState, ...] = (
        EndgamePushState.FORMING,
        EndgamePushState.READY,
        EndgamePushState.EXECUTING,
        EndgamePushState.WITNESS,
        EndgamePushState.ADVANCE,
        EndgamePushState.RECOVERY,
    )

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("endgame plan identity must not be empty")
        if not self.rules:
            raise ValueError("endgame plan requires at least one policy rule")

        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("endgame policy rule identities must be unique")
        if not isinstance(self.rules, tuple):
            raise TypeError("endgame plan rules must be a tuple")

        ordered = tuple(sorted(self.rules, key=lambda item: (-item.priority, item.identity)))
        if ordered != self.rules:
            raise ValueError(
                "endgame policy rules must be declared in deterministic priority order"
            )

        if not self.objective_priority:
            raise ValueError("endgame plan requires at least one objective priority")
        if any(not item.strip() for item in self.objective_priority):
            raise ValueError("endgame objective priorities must not contain empty values")
        if len(self.objective_priority) != len(set(self.objective_priority)):
            raise ValueError("endgame objective priorities must be unique")

        expected_states = (
            EndgamePushState.FORMING,
            EndgamePushState.READY,
            EndgamePushState.EXECUTING,
            EndgamePushState.WITNESS,
            EndgamePushState.ADVANCE,
            EndgamePushState.RECOVERY,
        )
        if self.push_states != expected_states:
            raise ValueError(
                "endgame push states must use the canonical forming/ready/executing/"
                "witness/advance/recovery sequence"
            )

    @property
    def observation_references(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    reference
                    for rule in self.rules
                    for reference in rule.observation_refs
                }
            )
        )


@dataclass(frozen=True)
class EndgameRuntimeState:
    mode: EndgameMode
    win_condition: EndgameWinCondition
    push_state: EndgamePushState
    frontier_valid: bool
    recovery_required: bool

    def __post_init__(self) -> None:
        if not isinstance(self.mode, EndgameMode):
            raise TypeError("endgame runtime mode must be EndgameMode")
        if not isinstance(self.win_condition, EndgameWinCondition):
            raise TypeError(
                "endgame runtime win_condition must be EndgameWinCondition"
            )
        if not isinstance(self.push_state, EndgamePushState):
            raise TypeError("endgame runtime push_state must be EndgamePushState")
        if self.mode is EndgameMode.RECOVERY and self.push_state is not EndgamePushState.RECOVERY:
            raise ValueError("RECOVERY endgame mode requires RECOVERY push state")
        if self.push_state is EndgamePushState.RECOVERY and not self.recovery_required:
            raise ValueError(
                "RECOVERY push state requires recovery_required=True"
            )
        if self.recovery_required and self.push_state is not EndgamePushState.RECOVERY:
            raise ValueError(
                "recovery_required=True requires RECOVERY push state"
            )


def validate_endgame_plan(
    plan: EndgamePlan,
    *,
    observation_ids: tuple[str, ...] = (),
) -> None:
    if not isinstance(plan, EndgamePlan):
        raise TypeError("endgame plan must be EndgamePlan")
    known = set(observation_ids)
    unknown = sorted(
        reference
        for reference in plan.observation_references
        if known and reference not in known
    )
    if unknown:
        raise ValueError(
            "endgame plan references unknown strategic observation(s): "
            + ", ".join(unknown)
        )
