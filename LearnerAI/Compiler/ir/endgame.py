"""Typed Byzantine end-game strategy and runtime contract.

The end-game layer owns typed strategic policy and persistent control state.
Native execution remains owned by the existing attack, DUC, production,
construction, Strategic Number, and timer subsystems.
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


class EndgameObjectiveState(str, Enum):
    IDLE = "idle"
    SIEGE = "siege"
    DEFENSE = "defense"
    PRODUCTION = "production"
    TOWN_CENTER = "town-center"
    EXECUTING = "executing"
    WITNESS = "witness"


class EndgameObjectiveClass(str, Enum):
    NONE = "none"
    SIEGE = "siege"
    DEFENSE = "defense"
    PRODUCTION = "production"
    TOWN_CENTER = "town-center"


class EndgameObjectiveReleaseReason(str, Enum):
    NONE = "none"
    COMPLETED = "completed"
    LOST_OUT_OF_BOUNDS = "lost-out-of-bounds"
    FAILED_EXECUTION = "failed-execution"
    FORTIFICATION_ABORT = "fortification-abort"
    TC_EXHAUSTED = "tc-exhausted"


class EndgameFrontierState(str, Enum):
    SIEGE = "SIEGE"
    DEFENSE = "DEFENSE"
    PRODUCTION = "PRODUCTION"
    TOWN_CENTER = "TOWN_CENTER"


class EndgameTargetQueryKind(str, Enum):
    OBJECT_TYPE = "OBJECT_TYPE"
    OBJECT_CLASS = "OBJECT_CLASS"


@dataclass(frozen=True)
class EndgameTargetCandidate:
    identity: str
    frontier: EndgameFrontierState
    query_kind: EndgameTargetQueryKind
    native_id: int
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("endgame target candidate identity must not be empty")
        if not isinstance(self.frontier, EndgameFrontierState):
            raise TypeError("endgame target candidate frontier must be EndgameFrontierState")
        if not isinstance(self.query_kind, EndgameTargetQueryKind):
            raise TypeError("endgame target candidate query_kind must be EndgameTargetQueryKind")
        if not isinstance(self.native_id, int) or isinstance(self.native_id, bool):
            raise TypeError("endgame target candidate native_id must be an integer")
        if not 0 <= self.native_id <= 32767:
            raise ValueError("endgame target candidate native_id must be in 0..32767")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise TypeError("endgame target candidate priority must be an integer")


@dataclass(frozen=True)
class EndgameTargetControlContract:
    identity: str
    anchor_goal: str
    search_radius: int
    candidates: tuple[EndgameTargetCandidate, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("endgame target control identity must not be empty")
        if not isinstance(self.anchor_goal, str) or not self.anchor_goal.strip():
            raise ValueError("endgame target control anchor_goal must not be empty")
        if not isinstance(self.search_radius, int) or isinstance(self.search_radius, bool):
            raise TypeError("endgame target control search_radius must be an integer")
        if not 1 <= self.search_radius <= 40:
            raise ValueError("endgame target control search_radius must be in 1..40")
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise ValueError("endgame target control requires candidates")
        if any(not isinstance(candidate, EndgameTargetCandidate) for candidate in self.candidates):
            raise TypeError("endgame target control candidates must use EndgameTargetCandidate")
        identities = tuple(candidate.identity for candidate in self.candidates)
        if len(identities) != len(set(identities)):
            raise ValueError("endgame target candidate identities must be unique")
        expected_frontiers = (
            EndgameFrontierState.SIEGE,
            EndgameFrontierState.DEFENSE,
            EndgameFrontierState.PRODUCTION,
            EndgameFrontierState.TOWN_CENTER,
        )
        compressed = tuple(dict.fromkeys(candidate.frontier for candidate in self.candidates))
        if compressed != expected_frontiers:
            raise ValueError(
                "endgame target candidates must use the canonical siege/defense/"
                "production/town-center frontier order"
            )
        for frontier in expected_frontiers:
            frontier_candidates = tuple(
                candidate for candidate in self.candidates if candidate.frontier is frontier
            )
            if not frontier_candidates:
                raise ValueError(
                    f"endgame target control requires candidates for {frontier.value}"
                )
            expected_order = tuple(
                sorted(
                    frontier_candidates,
                    key=lambda candidate: (-candidate.priority, candidate.identity),
                )
            )
            if frontier_candidates != expected_order:
                raise ValueError(
                    f"endgame target candidates for {frontier.value} must be in "
                    "deterministic priority order"
                )

@dataclass(frozen=True)
class EndgameObjectiveControlContract:
    """Typed ownership contract for the existing late-objective Goal state."""

    identity: str
    state_goal: str = "byzantine-offensive-objective-state"
    class_goal: str = "byzantine-offensive-objective-class"
    point_goal: str = "byzantine-offensive-objective-point"
    search_goal: str = "byzantine-offensive-objective-search"
    enemy_player_goal: str = "byzantine-offensive-enemy-player"
    claim_goal: str = "byzantine-offensive-objective-claim"
    release_reason_goal: str = "byzantine-offensive-objective-release-reason"
    release_search_goal: str = "byzantine-offensive-objective-release-search"
    release_search_radius: int = 60
    timer_name: str = "byzantine-offensive-objective-timer"

    def __post_init__(self) -> None:
        fields = (
            self.identity,
            self.state_goal,
            self.class_goal,
            self.point_goal,
            self.search_goal,
            self.enemy_player_goal,
            self.claim_goal,
            self.release_reason_goal,
            self.release_search_goal,
            self.timer_name,
        )
        if any(not isinstance(item, str) or not item.strip() for item in fields):
            raise ValueError("endgame objective control identifiers must be non-empty strings")
        control_identifiers = fields[1:]
        if len(control_identifiers) != len(set(control_identifiers)):
            raise ValueError("endgame objective control identifiers must be unique")

        if not isinstance(self.release_search_radius, int) or isinstance(
            self.release_search_radius, bool
        ):
            raise TypeError("endgame objective release_search_radius must be an integer")
        if not 41 <= self.release_search_radius <= 80:
            raise ValueError(
                "endgame objective release_search_radius must be in 41..80"
            )

    @property
    def state_constants(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (f"{self.state_goal}-{state.value}", index)
            for index, state in enumerate(EndgameObjectiveState)
        )

    @property
    def class_constants(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (f"{self.class_goal}-{objective_class.value}", index)
            for index, objective_class in enumerate(EndgameObjectiveClass)
        )

    @property
    def release_reason_constants(self) -> tuple[tuple[str, int], ...]:
        return tuple(
            (f"{self.release_reason_goal}-{reason.value}", index)
            for index, reason in enumerate(EndgameObjectiveReleaseReason)
        )

    @property
    def constants(self) -> tuple[tuple[str, int], ...]:
        return self.state_constants + self.class_constants + self.release_reason_constants


@dataclass(frozen=True)
class EndgamePushContract:
    identity: str
    attack_group_count: int
    attack_soldier_percent: int
    minimum_group_size: int
    maximum_group_size: int
    active_window_seconds: int
    live_witness_ref: str
    cleared_witness_ref: str
    frontier: tuple[EndgameFrontierState, ...]
    frontier_witness_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("endgame push contract identity must not be empty")
        if not isinstance(self.live_witness_ref, str):
            raise TypeError("endgame push contract live_witness_ref must be a string")
        if not isinstance(self.cleared_witness_ref, str):
            raise TypeError("endgame push contract cleared_witness_ref must be a string")
        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (
                self.attack_group_count,
                self.attack_soldier_percent,
                self.minimum_group_size,
                self.maximum_group_size,
                self.active_window_seconds,
            )
        ):
            raise TypeError("endgame push contract numeric fields must be integers")
        if not 1 <= self.attack_group_count <= 32767:
            raise ValueError("endgame attack group count must be in 1..32767")
        if not 0 <= self.attack_soldier_percent <= 100:
            raise ValueError("endgame attack soldier percent must be in 0..100")
        if not 1 <= self.minimum_group_size <= self.maximum_group_size <= 32767:
            raise ValueError("endgame attack group size bounds are invalid")
        if not 1 <= self.active_window_seconds <= 300:
            raise ValueError("endgame attack-group active window must be in 1..300 seconds")
        if not self.live_witness_ref.strip():
            raise ValueError("endgame push contract requires a live witness reference")
        if not self.cleared_witness_ref.strip():
            raise ValueError("endgame push contract requires a cleared witness reference")
        if self.frontier_witness_ref is not None and not isinstance(self.frontier_witness_ref, str):
            raise TypeError("endgame push contract frontier_witness_ref must be a string or None")
        if self.frontier_witness_ref is not None and not self.frontier_witness_ref.strip():
            raise ValueError("endgame push contract frontier_witness_ref must not be empty")
        if not isinstance(self.frontier, tuple):
            raise TypeError("endgame push contract frontier must be a tuple")
        if any(not isinstance(item, EndgameFrontierState) for item in self.frontier):
            raise TypeError("endgame push contract frontier must use EndgameFrontierState")
        if not self.frontier:
            raise ValueError("endgame push contract requires at least one frontier state")
        if len(self.frontier) != len(set(self.frontier)):
            raise ValueError("endgame frontier states must be unique")
        expected = (
            EndgameFrontierState.SIEGE,
            EndgameFrontierState.DEFENSE,
            EndgameFrontierState.PRODUCTION,
            EndgameFrontierState.TOWN_CENTER,
        )
        if self.frontier != expected:
            raise ValueError(
                "endgame frontier must use the canonical siege/defense/production/"
                "town-center sequence"
            )


@dataclass(frozen=True)
class EndgameConversionContract:
    identity: str
    frontier_required: EndgameFrontierState
    forward_production_buildings: tuple[str, ...]
    resource_denial_native_ids: tuple[int, ...]
    resource_denial_query_kind: EndgameTargetQueryKind = EndgameTargetQueryKind.OBJECT_CLASS

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("endgame conversion identity must not be empty")
        if not isinstance(self.frontier_required, EndgameFrontierState):
            raise TypeError("endgame conversion frontier_required must be EndgameFrontierState")
        if not self.forward_production_buildings:
            raise ValueError("endgame conversion requires forward production buildings")
        if any(not isinstance(item, str) or not item.strip() for item in self.forward_production_buildings):
            raise ValueError("endgame conversion production buildings must be non-empty strings")
        if len(self.forward_production_buildings) != len(set(self.forward_production_buildings)):
            raise ValueError("endgame conversion production buildings must be unique")
        if not self.resource_denial_native_ids:
            raise ValueError("endgame conversion requires resource-denial native ids")
        if any(not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 32767 for item in self.resource_denial_native_ids):
            raise ValueError("endgame conversion resource-denial native ids must be valid native ids")
        if not isinstance(self.resource_denial_query_kind, EndgameTargetQueryKind):
            raise TypeError("endgame conversion resource-denial query kind must be EndgameTargetQueryKind")


@dataclass(frozen=True)
class EndgamePolicyRule:
    identity: str
    mode: EndgameMode
    win_condition: EndgameWinCondition
    observation_refs: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.identity, str) or not self.identity.strip():
            raise ValueError("endgame policy rule identity must not be empty")
        if not isinstance(self.mode, EndgameMode):
            raise TypeError("endgame policy rule mode must be EndgameMode")
        if not isinstance(self.win_condition, EndgameWinCondition):
            raise TypeError(
                "endgame policy rule win_condition must be EndgameWinCondition"
            )
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise TypeError("endgame policy rule priority must be an integer")
        if not isinstance(self.observation_refs, tuple):
            raise TypeError("endgame policy rule observation_refs must be a tuple")
        if any(not isinstance(reference, str) for reference in self.observation_refs):
            raise TypeError("endgame policy rule observation_refs must contain strings")
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
    push_contract: EndgamePushContract | None = None
    target_control: EndgameTargetControlContract | None = None
    objective_control: EndgameObjectiveControlContract | None = None
    conversion_contract: EndgameConversionContract | None = None
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

        if not isinstance(self.rules, tuple):
            raise TypeError("endgame plan rules must be a tuple")
        if any(not isinstance(rule, EndgamePolicyRule) for rule in self.rules):
            raise TypeError("endgame plan rules must use EndgamePolicyRule")
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("endgame policy rule identities must be unique")
        if self.push_contract is not None and not isinstance(
            self.push_contract, EndgamePushContract
        ):
            raise TypeError("endgame plan push_contract must be EndgamePushContract or None")
        if self.conversion_contract is not None and not isinstance(self.conversion_contract, EndgameConversionContract):
            raise TypeError("endgame plan conversion_contract must be EndgameConversionContract or None")
        if self.target_control is not None and not isinstance(
            self.target_control, EndgameTargetControlContract
        ):
            raise TypeError(
                "endgame plan target_control must be EndgameTargetControlContract or None"
            )
        if self.objective_control is not None and not isinstance(
            self.objective_control, EndgameObjectiveControlContract
        ):
            raise TypeError(
                "endgame plan objective_control must be EndgameObjectiveControlContract or None"
            )

        if not isinstance(self.objective_priority, tuple):
            raise TypeError("endgame plan objective_priority must be a tuple")
        if any(not isinstance(item, str) for item in self.objective_priority):
            raise TypeError("endgame plan objective_priority must contain strings")
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
        if not isinstance(self.push_states, tuple):
            raise TypeError("endgame plan push_states must be a tuple")
        if any(not isinstance(item, EndgamePushState) for item in self.push_states):
            raise TypeError("endgame plan push_states must use EndgamePushState")
        if self.push_states != expected_states:
            raise ValueError(
                "endgame push states must use the canonical forming/ready/executing/"
                "witness/advance/recovery sequence"
            )

    @property
    def observation_references(self) -> tuple[str, ...]:
        references = {
            reference
            for rule in self.rules
            for reference in rule.observation_refs
        }
        if self.push_contract is not None:
            references.add(self.push_contract.live_witness_ref)
            references.add(self.push_contract.cleared_witness_ref)
            if self.push_contract.frontier_witness_ref is not None:
                references.add(self.push_contract.frontier_witness_ref)
        return tuple(sorted(references))


@dataclass(frozen=True)
class EndgameRuntimeState:
    mode: EndgameMode
    win_condition: EndgameWinCondition
    push_state: EndgamePushState
    frontier_valid: bool
    recovery_required: bool
    frontier: EndgameFrontierState = EndgameFrontierState.SIEGE

    def __post_init__(self) -> None:
        if not isinstance(self.mode, EndgameMode):
            raise TypeError("endgame runtime mode must be EndgameMode")
        if not isinstance(self.win_condition, EndgameWinCondition):
            raise TypeError(
                "endgame runtime win_condition must be EndgameWinCondition"
            )
        if not isinstance(self.push_state, EndgamePushState):
            raise TypeError("endgame runtime push_state must be EndgamePushState")
        if not isinstance(self.frontier, EndgameFrontierState):
            raise TypeError("endgame runtime frontier must be EndgameFrontierState")
        if not isinstance(self.frontier_valid, bool):
            raise TypeError("endgame runtime frontier_valid must be bool")
        if not isinstance(self.recovery_required, bool):
            raise TypeError("endgame runtime recovery_required must be bool")
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
    frontier_witness_provenance: dict[str, tuple[object, ...]] | None = None,
) -> None:
    if not isinstance(plan, EndgamePlan):
        raise TypeError("endgame plan must be EndgamePlan")
    known = set(observation_ids)
    unknown = sorted(
        reference
        for reference in plan.observation_references
        if reference not in known
    )
    if unknown:
        raise ValueError(
            "endgame plan references unknown strategic observation(s): "
            + ", ".join(unknown)
        )

    if plan.push_contract is not None and plan.push_contract.frontier_witness_ref is not None:
        provenance = (frontier_witness_provenance or {}).get(
            plan.push_contract.frontier_witness_ref,
            (),
        )
        if not provenance:
            raise ValueError(
                "endgame frontier witness must carry external world-state provenance"
            )
        from .versioning import EvidenceKind
        allowed = {
            EvidenceKind.ENGINE_DATA,
            EvidenceKind.RUNTIME_VERIFIED,
        }
        if not any(getattr(item, "kind", None) in allowed for item in provenance):
            raise ValueError(
                "endgame frontier witness provenance must include engine/world evidence"
            )
