"""Typed Byzantine screen/main/siege/raid/reserve role-separation IR.

The role layer owns execution membership and recovery boundaries. It never owns an
attack action. Objective selection and attack issuance remain downstream owners.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ..ast import Expression, SourceLocation
from .model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
from .native_control import NativeControlState


class RoleControllerState(str, Enum):
    IDLE = "IDLE"
    FORMING = "FORMING"
    COMMITTED = "COMMITTED"
    RAID_SPLIT = "RAID_SPLIT"
    RECOVERING = "RECOVERING"


class RoleKind(str, Enum):
    SCREEN = "SCREEN"
    MAIN = "MAIN"
    SIEGE = "SIEGE"
    RAID = "RAID"
    RESERVE = "RESERVE"


@dataclass(frozen=True)
class RoleMembershipSpec:
    role: RoleKind
    group_id: int
    minimum: int
    description: str

    def __post_init__(self) -> None:
        if not 0 <= self.group_id <= 9:
            raise ValueError(f"role group id must be in 0..9, got {self.group_id}")
        if self.minimum < 0:
            raise ValueError("role minimum must be non-negative")
        if not self.description.strip():
            raise ValueError("role description must not be empty")


@dataclass(frozen=True)
class RoleWitnessSpec:
    identity: str
    role: RoleKind
    facts: tuple[Expression, ...]
    description: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("role witness identity must not be empty")
        if not self.facts:
            raise ValueError(
                f"role witness '{self.identity}' requires at least one fact"
            )
        if not self.description.strip():
            raise ValueError("role witness description must not be empty")


@dataclass(frozen=True)
class NativeRoleRule:
    identity: str
    order: int
    facts: tuple[Expression, ...]
    actions: tuple[Expression, ...]
    role: RoleKind | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native role rule identity must not be empty")
        if self.order < 0:
            raise ValueError("native role rule order must be non-negative")
        if not self.facts:
            raise ValueError(
                f"native role rule '{self.identity}' requires at least one fact"
            )
        if not isinstance(self.facts, tuple) or not isinstance(self.actions, tuple):
            raise TypeError("native role rule facts/actions must be tuples")


@dataclass(frozen=True)
class NativeRoleSeparationPlan:
    state: NativeControlState
    formation_mask: NativeControlState
    selection_cap: NativeControlState
    screen_size: NativeControlState
    main_size: NativeControlState
    siege_size: NativeControlState
    raid_size: NativeControlState
    reserve_size: NativeControlState
    fortified_latch: NativeControlState
    recovery_request: NativeControlState
    roles: tuple[RoleMembershipSpec, ...]
    witnesses: tuple[RoleWitnessSpec, ...]
    rules: tuple[NativeRoleRule, ...]
    constants: tuple[tuple[str, int], ...]
    state_values: tuple[tuple[RoleControllerState, int], ...] = (
        (RoleControllerState.IDLE, 0),
        (RoleControllerState.FORMING, 1),
        (RoleControllerState.COMMITTED, 2),
        (RoleControllerState.RAID_SPLIT, 3),
        (RoleControllerState.RECOVERING, 4),
    )

    def __post_init__(self) -> None:
        roles = tuple(role.role for role in self.roles)
        if roles != (
            RoleKind.SCREEN,
            RoleKind.MAIN,
            RoleKind.SIEGE,
            RoleKind.RAID,
            RoleKind.RESERVE,
        ):
            raise ValueError("role plan must declare roles in screen/main/siege/raid/reserve order")
        group_ids = tuple(role.group_id for role in self.roles)
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("role group ids must be unique")
        identities = tuple(rule.identity for rule in self.rules)
        if len(identities) != len(set(identities)):
            raise ValueError("role rule identities must be unique")
        orders = tuple((rule.order, rule.identity) for rule in self.rules)
        if orders != tuple(sorted(orders)):
            raise ValueError("role rules must be declared in deterministic order")
        constant_names = tuple(name for name, _value in self.constants)
        if len(constant_names) != len(set(constant_names)):
            raise ValueError("role constants must be unique")
        values = dict(self.state_values)
        if set(values) != set(RoleControllerState):
            raise ValueError("role controller state values are incomplete")
        if len(set(values.values())) != len(values):
            raise ValueError("role controller state values must be unique")
        witness_ids = tuple(w.identity for w in self.witnesses)
        if len(witness_ids) != len(set(witness_ids)):
            raise ValueError("role witness identities must be unique")

    @property
    def states(self) -> tuple[NativeControlState, ...]:
        return (
            self.state,
            self.formation_mask,
            self.selection_cap,
            self.screen_size,
            self.main_size,
            self.siege_size,
            self.raid_size,
            self.reserve_size,
            self.fortified_latch,
            self.recovery_request,
        )

    @property
    def storage_requests(self) -> tuple[GoalSlotRequest, ...]:
        return tuple(state.request for state in self.states)

    @property
    def state_value_map(self) -> dict[RoleControllerState, int]:
        return dict(self.state_values)

    @property
    def group_ids(self) -> dict[RoleKind, int]:
        return {role.role: role.group_id for role in self.roles}

    @property
    def constant_map(self) -> dict[str, int]:
        constants = dict(self.constants)
        for state, value in self.state_values:
            constants[f"byzantine-army-role-{state.value.lower().replace('_', '-')}"] = value
        return constants

    def commands(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    expression.head
                    for rule in self.rules
                    for expression in (*rule.facts, *rule.actions)
                }
            )
        )


def _expr(source: str) -> Expression:
    from ..semantic.analyzer import parse_expression

    return parse_expression(source.strip(), SourceLocation(1))


def _rule(
    order: int,
    identity: str,
    facts: Iterable[str],
    actions: Iterable[str],
    role: RoleKind | None = None,
) -> NativeRoleRule:
    try:
        parsed_facts = tuple(_expr(item) for item in facts)
        parsed_actions = tuple(_expr(item) for item in actions)
    except Exception as exc:
        raise ValueError(f"invalid native role rule '{identity}': {exc}") from exc
    return NativeRoleRule(
        identity=identity,
        order=order,
        facts=parsed_facts,
        actions=parsed_actions,
        role=role,
    )


def _state(
    profile_id: str,
    identifier: str,
    purpose: str,
    role: GoalRole,
) -> NativeControlState:
    return NativeControlState(
        identifier=identifier,
        request=GoalSlotRequest(
            StorageRequestId(
                SemanticId(profile_id, purpose),
                purpose,
            ),
            role=role,
        ),
        location=SourceLocation(1),
    )


def default_byzantine_role_separation_plan(
    profile_id: str,
) -> NativeRoleSeparationPlan:
    state_name = "byzantine-army-role-state"
    mask_name = "byzantine-army-role-formation-mask"
    cap_name = "byzantine-army-role-selection-cap"
    screen_size_name = "byzantine-army-role-screen-size"
    main_size_name = "byzantine-army-role-main-size"
    siege_size_name = "byzantine-army-role-siege-size"
    raid_size_name = "byzantine-army-role-raid-size"
    reserve_size_name = "byzantine-army-role-reserve-size"
    fortified_latch_name = "byzantine-army-role-fortified-latch"
    recovery_request_name = "byzantine-army-role-recovery-request"

    roles = (
        RoleMembershipSpec(RoleKind.SCREEN, 5, 2, "cheap threat-facing protective layer"),
        RoleMembershipSpec(RoleKind.MAIN, 6, 4, "primary non-screen non-siege combat body"),
        RoleMembershipSpec(RoleKind.SIEGE, 7, 1, "protected siege support"),
        RoleMembershipSpec(RoleKind.RAID, 8, 2, "detachable mobile force"),
        RoleMembershipSpec(RoleKind.RESERVE, 9, 0, "deliberately uncommitted combat capacity"),
    )

    witnesses = (
        RoleWitnessSpec(
            "role-screen-membership",
            RoleKind.SCREEN,
            (_expr("(up-compare-goal byzantine-army-role-screen-size >= c:bt-role-screen-floor)"),),
            "Screen membership is proven by the native group-size Goal output captured at formation.",
        ),
        RoleWitnessSpec(
            "role-main-membership",
            RoleKind.MAIN,
            (_expr("(up-compare-goal byzantine-army-role-main-size >= c:bt-role-main-floor)"),),
            "Main membership is proven by the native group-size Goal output captured at formation.",
        ),
        RoleWitnessSpec(
            "role-siege-membership",
            RoleKind.SIEGE,
            (
                _expr(
                    "(or (and (goal byzantine-fortification-threat 0) "
                    "(up-compare-goal byzantine-army-role-siege-size >= c:bt-role-siege-floor-standard)) "
                    "(and (goal byzantine-fortification-threat 1) "
                    "(up-compare-goal byzantine-army-role-siege-size >= c:bt-role-siege-floor-fortified)))"
                ),
            ),
            "Siege membership is proven against the active standard or fortified floor.",
        ),
        RoleWitnessSpec(
            "role-raid-membership",
            RoleKind.RAID,
            (_expr("(up-compare-goal byzantine-army-role-raid-size >= c:bt-role-raid-floor)"),),
            "Raid membership is proven by the native raid-group Goal output captured immediately after the split.",
        ),
        RoleWitnessSpec(
            "role-committed-package",
            RoleKind.MAIN,
            (
                _expr("(up-compare-goal byzantine-army-role-screen-size >= c:bt-role-screen-floor)"),
                _expr("(up-compare-goal byzantine-army-role-main-size >= c:bt-role-main-floor)"),
                _expr(
                    "(or (and (goal byzantine-fortification-threat 0) "
                    "(up-compare-goal byzantine-army-role-siege-size >= c:bt-role-siege-floor-standard)) "
                    "(and (goal byzantine-fortification-threat 1) "
                    "(up-compare-goal byzantine-army-role-siege-size >= c:bt-role-siege-floor-fortified)))"
                ),
            ),
            "Committed means screen, main, and required live siege floors were witnessed together.",
        ),
        RoleWitnessSpec(
            "role-fortified-siege",
            RoleKind.SIEGE,
            (
                _expr("(goal byzantine-fortification-threat 1)"),
                _expr("(goal byzantine-siege-scale byzantine-siege-scale-fortified)"),
                _expr("(up-compare-goal byzantine-army-role-siege-size >= c:bt-role-siege-floor-fortified)"),
            ),
            "Fortified posture requires the enlarged live siege floor.",
        ),
        RoleWitnessSpec(
            "role-recovery-admission",
            RoleKind.RESERVE,
            (
                _expr(
                    "(or (goal byzantine-army-attack-ready 0) "
                    "(goal byzantine-army-overmatch-state byzantine-army-overmatch-triggered))"
                ),
            ),
            "Loss of attack readiness or an overmatch trigger is a recovery admission.",
        ),
        RoleWitnessSpec(
            "role-raid-fortified-ineligible",
            RoleKind.RAID,
            (
                _expr("(goal byzantine-fortification-threat 1)"),
                _expr(
                    "(or (goal byzantine-offensive-objective-class 3) "
                    "(goal byzantine-offensive-objective-class 4))"
                ),
            ),
            "A fortified threat makes raid splitting inadmissible.",
        ),
    )

    rules = (
        _rule(
            20,
            "role-enter-forming",
            (
                f"(goal {state_name} byzantine-army-role-idle)",
                "(goal byzantine-army-attack-ready 1)",
                "(goal byzantine-offensive-objective-claim 1)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-forming)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
            ),
        ),
        _rule(
            30,
            "role-forming-reset",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 0)",
            ),
            (
                "(up-full-reset-search)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-filter-include cmdid-monk -1 -1 -1)",
                "(up-find-local c: all-units-class c: 240)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-modify-group-flag 0 c: 5)",
                "(up-modify-group-flag 0 c: 6)",
                "(up-modify-group-flag 0 c: 7)",
                "(up-modify-group-flag 0 c: 8)",
                "(up-modify-group-flag 0 c: 9)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
                f"(set-goal {cap_name} 4)",
                f"(set-goal {mask_name} 1)",
            ),
        ),
        _rule(
            40,
            "role-forming-screen",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 1)",
            ),
            (
                "(up-full-reset-search)",
                "(up-set-target-point byzantine-offensive-objective-point)",
                "(up-filter-distance c: -1 c: 60)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-find-local c: spearman-line c: 40)",
                "(up-find-local c: skirmisher-line c: 40)",
                "(up-find-local c: 359 c: 40)",
                "(up-remove-objects search-local object-data-status != 2)",
                f"(up-create-group 0 {cap_name} c: 5)",
                "(up-modify-group-flag 1 c: 5)",
                f"(set-goal {mask_name} 3)",
            ),
            RoleKind.SCREEN,
        ),
        _rule(
            50,
            "role-forming-siege",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 3)",
            ),
            (
                "(up-full-reset-search)",
                "(up-set-target-point byzantine-offensive-objective-point)",
                "(up-filter-distance c: -1 c: 60)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-find-local c: mangonel-line c: 40)",
                "(up-find-local c: bombard-cannon c: 40)",
                "(up-find-local c: trebuchet-set c: 40)",
                "(up-find-local c: battering-ram-line c: 40)",
                "(up-remove-objects search-local object-data-status != 2)",
                f"(set-goal {cap_name} 2)",
                f"(up-create-group 0 {cap_name} c: 7)",
                "(up-modify-group-flag 1 c: 7)",
                f"(set-goal {mask_name} 7)",
            ),
            RoleKind.SIEGE,
        ),
        _rule(
            60,
            "role-forming-reserve",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 15)",
                "(up-group-size c: 6 >= 6)",
            ),
            (
                "(up-full-reset-search)",
                "(up-set-target-point byzantine-offensive-objective-point)",
                "(up-filter-distance c: -1 c: 60)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-find-local c: all-units-class c: 240)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-remove-objects search-local object-data-group-flag != 6)",
                f"(set-goal {cap_name} 2)",
                f"(up-create-group 0 {cap_name} c: 9)",
                "(up-modify-group-flag 1 c: 9)",
                "(up-full-reset-search)",
                "(up-find-local c: all-units-class c: 240)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-remove-objects search-local object-data-group-flag != 9)",
                "(up-modify-group-flag 0 c: 6)",
                f"(set-goal {mask_name} 23)",
            ),
            RoleKind.RESERVE,
        ),

        _rule(
            65,
            "role-forming-reserve-skip",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 15)",
                "(up-group-size c: 6 < 6)",
            ),
            (f"(set-goal {mask_name} 23)",),
            RoleKind.RESERVE,
        ),

        _rule(
            70,
            "role-forming-main",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 7)",
            ),
            (
                "(up-full-reset-search)",
                "(up-set-target-point byzantine-offensive-objective-point)",
                "(up-filter-distance c: -1 c: 60)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-find-local c: all-units-class c: 240)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-remove-objects search-local object-data-group-flag == 5)",
                "(up-remove-objects search-local object-data-group-flag == 7)",
                "(up-remove-objects search-local object-data-group-flag == 9)",
                "(up-remove-objects search-local object-data-type == monk)",
                f"(set-goal {cap_name} 40)",
                f"(up-create-group 0 {cap_name} c: 6)",
                "(up-modify-group-flag 1 c: 6)",
                f"(set-goal {mask_name} 15)",
            ),
            RoleKind.MAIN,
        ),

        _rule(
            80,
            "role-forming-size-witness",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 23)",
                "(goal byzantine-army-attack-ready 1)",
            ),
            (
                f"(up-get-group-size c: 5 {screen_size_name})",
                f"(up-get-group-size c: 6 {main_size_name})",
                f"(up-get-group-size c: 7 {siege_size_name})",
                f"(up-get-group-size c: 8 {raid_size_name})",
                f"(up-get-group-size c: 9 {reserve_size_name})",
                f"(set-goal {mask_name} 31)",
            ),
        ),
        _rule(
            85,
            "role-forming-cancel-not-ready",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                "(goal byzantine-army-attack-ready 0)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
        ),

        _rule(
            90,
            "role-forming-commit",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 31)",
                "(goal byzantine-army-attack-ready 1)",
                f"(up-compare-goal {screen_size_name} >= c:bt-role-screen-floor)",
                f"(up-compare-goal {main_size_name} >= c:bt-role-main-floor)",
                f"(or (and (goal byzantine-fortification-threat 0) "
                f"(up-compare-goal {siege_size_name} >= c:bt-role-siege-floor-standard)) "
                f"(and (goal byzantine-fortification-threat 1) "
                f"(up-compare-goal {siege_size_name} >= c:bt-role-siege-floor-fortified)))",
            ),
            (f"(set-goal {state_name} byzantine-army-role-committed)",),
        ),
        _rule(
            100,
            "role-forming-fail-screen",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 31)",
                "(goal byzantine-army-attack-ready 1)",
                f"(up-compare-goal {screen_size_name} < c:bt-role-screen-floor)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
            ),
            RoleKind.SCREEN,
        ),
        _rule(
            101,
            "role-forming-fail-main",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 31)",
                "(goal byzantine-army-attack-ready 1)",
                f"(up-compare-goal {main_size_name} < c:bt-role-main-floor)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
            ),
            RoleKind.MAIN,
        ),
        _rule(
            102,
            "role-forming-fail-siege-standard",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 31)",
                "(goal byzantine-army-attack-ready 1)",
                f"(goal byzantine-fortification-threat 0)",
                f"(up-compare-goal {siege_size_name} < c:bt-role-siege-floor-standard)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
            ),
            RoleKind.SIEGE,
        ),
        _rule(
            103,
            "role-forming-fail-siege-fortified",
            (
                f"(goal {state_name} byzantine-army-role-forming)",
                f"(goal {mask_name} 31)",
                "(goal byzantine-army-attack-ready 1)",
                "(goal byzantine-fortification-threat 1)",
                f"(up-compare-goal {siege_size_name} < c:bt-role-siege-floor-fortified)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
            ),
            RoleKind.SIEGE,
        ),
        _rule(
            110,
            "role-committed-recovery-attack-ready",
            (
                f"(or (goal {state_name} byzantine-army-role-committed) "
                f"(goal {state_name} byzantine-army-role-raid-split))",
                "(goal byzantine-army-attack-ready 0)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
            ),
        ),
        _rule(
            120,
            "role-committed-recovery-overmatch",
            (
                f"(or (goal {state_name} byzantine-army-role-committed) "
                f"(goal {state_name} byzantine-army-role-raid-split))",
                "(goal byzantine-army-overmatch-state byzantine-army-overmatch-triggered)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
            ),
        ),
        _rule(
            125,
            "role-committed-recovery-siege-loss",
            (
                f"(or (goal {state_name} byzantine-army-role-committed) "
                f"(goal {state_name} byzantine-army-role-raid-split))",
                f"(or (and (goal byzantine-fortification-threat 1) "
                f"(and (goal byzantine-siege-scale byzantine-siege-scale-fortified) "
                f"(up-group-size c: 7 < 2))) "
                f"(and (goal byzantine-fortification-threat 0) "
                f"(up-group-size c: 7 < 1)))",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
            ),
            RoleKind.SIEGE,
        ),

        _rule(
            130,
            "role-raid-fortification-block",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(goal byzantine-fortification-threat 1)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-forming)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            140,
            "role-objective-release",
            (
                f"(or (goal {state_name} byzantine-army-role-committed) "
                f"(goal {state_name} byzantine-army-role-raid-split))",
                "(goal byzantine-offensive-objective-claim 0)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-idle)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
        ),

        _rule(
            150,
            "role-recovery-to-forming",
            (
                f"(goal {state_name} byzantine-army-role-recovering)",
                "(goal byzantine-army-attack-ready 1)",
                "(goal byzantine-offensive-objective-claim 1)",
            ),
            (f"(set-goal {state_name} byzantine-army-role-forming)",),
        ),
        _rule(
            160,
            "role-recovery-to-idle",
            (
                f"(goal {state_name} byzantine-army-role-recovering)",
                "(or (goal byzantine-army-attack-ready 0) "
                "(goal byzantine-offensive-objective-claim 0))",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-idle)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {recovery_request_name} 0)",
            ),
        ),
        _rule(
            170,
            "role-raid-admission",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                "(goal byzantine-offensive-objective-class 3)",
                "(goal byzantine-fortification-threat 0)",
                f"(up-compare-goal {screen_size_name} >= c:bt-role-screen-floor)",
                f"(up-compare-goal {main_size_name} >= c:bt-role-main-floor)",
                f"(up-compare-goal {siege_size_name} >= c:bt-role-siege-floor-standard)",
                f"(up-compare-goal {reserve_size_name} >= c:bt-role-raid-floor)",
                "(or (unit-type-count-total knight-line >= bt-role-raid-floor) "
                "(or (unit-type-count-total camel-line >= bt-role-raid-floor) "
                "(unit-type-count-total cataphract-line >= bt-role-raid-floor)))",
            ),
            (
                "(up-reset-group c: 8)",
                "(up-full-reset-search)",
                "(up-set-target-point byzantine-offensive-objective-point)",
                "(up-filter-distance c: -1 c: 60)",
                "(up-filter-include cmdid-military -1 -1 -1)",
                "(up-find-local c: cavalry-class c: 40)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-remove-objects search-local object-data-group-flag != 9)",
                f"(set-goal {cap_name} 2)",
                f"(up-create-group 0 {cap_name} c: 8)",
                "(up-modify-group-flag 1 c: 8)",
                "(up-full-reset-search)",
                "(up-find-local c: all-units-class c: 240)",
                "(up-remove-objects search-local object-data-status != 2)",
                "(up-remove-objects search-local object-data-group-flag != 8)",
                "(up-modify-group-flag 0 c: 9)",
                f"(set-goal {mask_name} 40)",
            ),
            RoleKind.RAID,
        ),

        _rule(
            180,
            "role-raid-size-witness",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                f"(goal {mask_name} 40)",
            ),
            (
                f"(up-get-group-size c: 5 {screen_size_name})",
                f"(up-get-group-size c: 6 {main_size_name})",
                f"(up-get-group-size c: 7 {siege_size_name})",
                f"(up-get-group-size c: 8 {raid_size_name})",
                f"(set-goal {mask_name} 41)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            190,
            "role-raid-commit",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                f"(goal {mask_name} 41)",
                f"(up-compare-goal {raid_size_name} >= c:bt-role-raid-floor)",
                f"(up-compare-goal {screen_size_name} >= c:bt-role-screen-floor)",
                f"(up-compare-goal {main_size_name} >= c:bt-role-main-floor)",
                f"(up-compare-goal {siege_size_name} >= c:bt-role-siege-floor-standard)",
            ),
            (f"(set-goal {state_name} byzantine-army-role-raid-split)",),
            RoleKind.RAID,
        ),
        _rule(
            200,
            "role-raid-fail-rejoin",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                f"(goal {mask_name} 41)",
                f"(up-compare-goal {raid_size_name} < c:bt-role-raid-floor)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),

        _rule(
            210,
            "role-raid-release-fortified",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(goal byzantine-fortification-threat 1)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-forming)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            211,
            "role-raid-release-siege-objective",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(or (goal byzantine-offensive-objective-class 1) "
                "(goal byzantine-offensive-objective-class 2))",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-forming)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            212,
            "role-raid-release-unclaimed-objective",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(goal byzantine-offensive-objective-claim 0)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-idle)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            213,
            "role-raid-release-attack-loss",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(goal byzantine-army-attack-ready 0)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            214,
            "role-raid-release-overmatch",
            (
                f"(goal {state_name} byzantine-army-role-raid-split)",
                "(goal byzantine-army-overmatch-state byzantine-army-overmatch-triggered)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                f"(set-goal {mask_name} 0)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
            ),
            RoleKind.RAID,
        ),
        _rule(
            220,
            "role-fortified-latch-clear",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                "(goal byzantine-siege-approach byzantine-siege-approach-normal)",
                f"(goal {fortified_latch_name} 1)",
            ),
            (f"(set-goal {fortified_latch_name} 0)",),
            RoleKind.SIEGE,
        ),
        _rule(
            230,
            "role-fortified-siege-refresh",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                "(goal byzantine-fortification-threat 1)",
                "(goal byzantine-siege-approach byzantine-siege-approach-fortified)",
                f"(goal {fortified_latch_name} 0)",
            ),
            (
                f"(up-get-group-size c: 7 {siege_size_name})",
                f"(set-goal {mask_name} 50)",
                f"(set-goal {fortified_latch_name} 1)",
            ),
            RoleKind.SIEGE,
        ),
        _rule(
            240,
            "role-fortified-siege-check",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                "(goal byzantine-fortification-threat 1)",
                "(goal byzantine-siege-scale byzantine-siege-scale-fortified)",
                f"(up-group-size c: 7 < 2)",
            ),
            (
                f"(set-goal {state_name} byzantine-army-role-recovering)",
                f"(set-goal {recovery_request_name} 1)",
                "(up-reset-group c: 5)",
                "(up-reset-group c: 6)",
                "(up-reset-group c: 7)",
                "(up-reset-group c: 8)",
                "(up-reset-group c: 9)",
                f"(set-goal {mask_name} 0)",
                f"(set-goal {fortified_latch_name} 0)",
            ),
            RoleKind.SIEGE,
        ),

        _rule(
            250,
            "role-fortified-siege-armed",
            (
                f"(goal {state_name} byzantine-army-role-committed)",
                "(goal byzantine-fortification-threat 1)",
                f"(goal {mask_name} 50)",
                f"(up-compare-goal {siege_size_name} >= c:bt-role-siege-floor-fortified)",
            ),
            (f"(set-goal {mask_name} 31)",),
            RoleKind.SIEGE,
        ),
    )

    constants = (
        ("byzantine-army-role-id-screen", 5),
        ("byzantine-army-role-id-main", 6),
        ("byzantine-army-role-id-siege", 7),
        ("byzantine-army-role-id-raid", 8),
        ("byzantine-army-role-id-reserve", 9),
        ("bt-role-screen-floor", 2),
        ("bt-role-main-floor", 4),
        ("bt-role-siege-floor-standard", 1),
        ("bt-role-siege-floor-fortified", 2),
        ("bt-role-raid-floor", 2),
    )

    return NativeRoleSeparationPlan(
        state=_state(
            profile_id,
            state_name,
            "byzantine-army-role-state",
            GoalRole.PERSISTENT_STATE,
        ),
        formation_mask=_state(
            profile_id,
            mask_name,
            "byzantine-army-role-formation-mask",
            GoalRole.EXECUTION_MEMORY,
        ),
        selection_cap=_state(
            profile_id,
            cap_name,
            "byzantine-army-role-selection-cap",
            GoalRole.DERIVED_SCALAR,
        ),
        screen_size=_state(
            profile_id,
            screen_size_name,
            "byzantine-army-role-screen-size",
            GoalRole.NATIVE_OUTPUT,
        ),
        main_size=_state(
            profile_id,
            main_size_name,
            "byzantine-army-role-main-size",
            GoalRole.NATIVE_OUTPUT,
        ),
        siege_size=_state(
            profile_id,
            siege_size_name,
            "byzantine-army-role-siege-size",
            GoalRole.NATIVE_OUTPUT,
        ),
        raid_size=_state(
            profile_id,
            raid_size_name,
            "byzantine-army-role-raid-size",
            GoalRole.NATIVE_OUTPUT,
        ),
        reserve_size=_state(
            profile_id,
            reserve_size_name,
            "byzantine-army-role-reserve-size",
            GoalRole.NATIVE_OUTPUT,
        ),
        fortified_latch=_state(
            profile_id,
            fortified_latch_name,
            "byzantine-army-role-fortified-latch",
            GoalRole.EXECUTION_MEMORY,
        ),
        recovery_request=_state(
            profile_id,
            recovery_request_name,
            "byzantine-army-role-recovery-request",
            GoalRole.PERSISTENT_STATE,
        ),
        roles=roles,
        witnesses=witnesses,
        rules=rules,
        constants=constants,
    )


def validate_native_role_separation_plan(plan, registry) -> None:
    if not isinstance(plan, NativeRoleSeparationPlan):
        raise TypeError("role_separation_plan must be a NativeRoleSeparationPlan")

    forbidden_actions = {
        "attack-now",
        "attack-groups",
        "action-attack-move",
        "up-target-objects",
        "up-target-point",
        "action-move",
        "stop",
    }
    allowed_actions = {
        "set-goal",
        "up-reset-group",
        "up-create-group",
        "up-modify-group-flag",
        "up-reset-search",
        "up-full-reset-search",
        "up-set-target-point",
        "up-filter-include",
        "up-filter-distance",
        "up-find-local",
        "up-remove-objects",
        "up-get-group-size",
    }

    request_ids = {request.request_id for request in plan.storage_requests}
    if len(request_ids) != len(plan.storage_requests):
        raise ValueError("role separation storage requests must be unique")

    logical_arity = {
        "and": 2,
        "or": 2,
        "nand": 2,
        "nor": 2,
        "xor": 2,
        "xnor": 2,
        "not": 1,
    }

    def validate_expression(expression, *, rule_identity: str, section: str) -> None:
        if expression.head in logical_arity:
            expected = logical_arity[expression.head]
            if len(expression.args) != expected:
                raise ValueError(
                    f"role rule '{rule_identity}' logical operator '{expression.head}' "
                    f"expects {expected} operands, got {len(expression.args)}"
                )
            for argument in expression.args:
                if isinstance(argument, type(expression)):
                    validate_expression(
                        argument,
                        rule_identity=rule_identity,
                        section=section,
                    )
            return

        registry.validate_native_signature(expression.head, len(expression.args))
        native = registry.require_native(expression.head)
        if section == "FACT":
            if native.command_type not in {"Fact", "Fact/Action"}:
                raise ValueError(
                    f"role rule fact '{expression.head}' is not a native fact"
                )
        else:
            if expression.head in forbidden_actions:
                raise ValueError(
                    f"role rule '{rule_identity}' illegally owns objective/movement action "
                    f"'{expression.head}'"
                )
            if expression.head not in allowed_actions:
                raise ValueError(
                    f"role rule '{rule_identity}' uses unsupported action '{expression.head}'"
                )
            if native.command_type not in {"Action", "Fact/Action"}:
                raise ValueError(
                    f"role rule action '{expression.head}' is not a native action"
                )
        for argument in expression.args:
            if isinstance(argument, type(expression)):
                validate_expression(
                    argument,
                    rule_identity=rule_identity,
                    section=section,
                )

    for rule in plan.rules:
        for expression in rule.facts:
            validate_expression(
                expression,
                rule_identity=rule.identity,
                section="FACT",
            )
        for expression in rule.actions:
            validate_expression(
                expression,
                rule_identity=rule.identity,
                section="ACTION",
            )

    for role in plan.roles:
        if role.group_id < 0 or role.group_id > 9:
            raise ValueError(
                f"role '{role.role.value}' group id {role.group_id} is outside native range 0..9"
            )

    if any(
        name in {"byzantine-siege-scale-standard", "byzantine-siege-scale-fortified"}
        for name, _value in plan.constants
    ):
        raise ValueError("role plan must not redeclare existing siege-scale constants")


__all__ = [
    "NativeRoleRule",
    "NativeRoleSeparationPlan",
    "RoleControllerState",
    "RoleKind",
    "RoleMembershipSpec",
    "RoleWitnessSpec",
    "default_byzantine_role_separation_plan",
]
