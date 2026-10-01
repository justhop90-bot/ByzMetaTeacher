"""Semantic validation and lowering for Strategic Number controller arbitration."""
from __future__ import annotations

from ..ast import Expression, SourceLocation
from ..ir.native_control import NativeControlPlan, NativeControlRule, NativeControlState
from ..ir.strategic_number import StrategicNumberOrigin
from ..ir.strategic_number_arbitration import (
    StrategicNumberActionAttachment,
    StrategicNumberArbitrationLowering,
    StrategicNumberArbitrationPlan,
    StrategicNumberController,
    StrategicNumberControllerLayer,
    StrategicNumberControllerOrigin,
    StrategicNumberControllerScope,
    StrategicNumberReleaseEvidence,
)
from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
from .analyzer import parse_expression


def _age_token(mode) -> str:
    return {
        "DARK": "dark-age",
        "FEUDAL": "feudal-age",
        "CASTLE": "castle-age",
        "IMPERIAL": "imperial-age",
    }[mode.value]


def _next_age_token(mode) -> str | None:
    return {
        "DARK": "feudal-age",
        "FEUDAL": "castle-age",
        "CASTLE": "imperial-age",
        "IMPERIAL": None,
    }[mode.value]


def _fold(head: str, expressions: tuple[str, ...]) -> str:
    if not expressions:
        raise ValueError(f"cannot construct empty '{head}' guard")
    result = expressions[0]
    for expression in expressions[1:]:
        result = f"({head} {result} {expression})"
    return result


def _guard_text(expression: Expression | str | None) -> str | None:
    if expression is None:
        return None
    return expression.source if isinstance(expression, Expression) else expression


def _as_expression(expression: Expression | str) -> Expression:
    if isinstance(expression, Expression):
        return expression
    return parse_expression(expression, SourceLocation(1))


def strategic_number_mode_to_controller(
    mode,
    profile_id: str,
) -> StrategicNumberController:
    guards: list[str] = []
    if mode.minimum_age is mode.maximum_age:
        guards.append(f"(current-age == {_age_token(mode.minimum_age)})")
    else:
        guards.append(f"(current-age >= {_age_token(mode.minimum_age)})")
        if mode.maximum_age is not None:
            successor = _next_age_token(mode.maximum_age)
            if successor is not None:
                guards.append(f"(current-age < {successor})")

    layer = StrategicNumberControllerLayer.AGE_BASE
    if mode.postures:
        layer = StrategicNumberControllerLayer.STRATEGY
        posture_values = {
            "FLUSH": 1,
            "RUSH": 2,
            "BOOM": 3,
            "CASTLE-POWER": 4,
        }
        posture_guards = tuple(
            f"(goal strategy-posture {posture_values[posture.value]})"
            for posture in mode.postures
        )
        guards.append(_fold("or", posture_guards))

    if mode.reassertion_policy.value == "ON_DRIFT":
        guards.append(
            f"(up-compare-sn sn-native-{mode.native_strategic_number_id} != {mode.value})"
        )

    return StrategicNumberController(
        identity=mode.identity,
        native_strategic_number_id=mode.native_strategic_number_id,
        value=mode.value,
        layer=layer,
        priority=mode.priority,
        activation_guard=_fold("and", tuple(item for item in guards if "up-compare-sn" not in item)),
        owner=profile_id,
        origin=StrategicNumberControllerOrigin.STRATEGY_MODE,
    )


def build_strategic_number_arbitration_plan(
    profile,
    *,
    extra_controllers: tuple[StrategicNumberController, ...] = (),
) -> StrategicNumberArbitrationPlan:
    mode_controllers = tuple(
        strategic_number_mode_to_controller(mode, profile.profile_id)
        for mode in profile.strategic_number_modes
    )
    return StrategicNumberArbitrationPlan(
        controllers=(*mode_controllers, *extra_controllers)
    )


def _controller_activation(
    controller: StrategicNumberController,
) -> str:
    if controller.layer in {
        StrategicNumberControllerLayer.DEFAULT_BASE,
    }:
        return "(true)"
    if controller.layer in {
        StrategicNumberControllerLayer.AGE_BASE,
        StrategicNumberControllerLayer.STRATEGY,
    }:
        guard = _guard_text(controller.activation_guard)
        if guard is None:
            raise ValueError(
                f"persistent Strategic Number controller '{controller.identity}' "
                "requires activation_guard"
            )
        return guard
    return f"(goal {controller.activation_state_name} 1)"


def _controller_claim_guard(
    controller: StrategicNumberController,
) -> str:
    if controller.layer in {
        StrategicNumberControllerLayer.DEFAULT_BASE,
        StrategicNumberControllerLayer.AGE_BASE,
        StrategicNumberControllerLayer.STRATEGY,
    }:
        return _controller_activation(controller)

    if controller.activation_guard is None:
        raise ValueError(
            f"Strategic Number override '{controller.identity}' requires activation_guard"
        )
    if controller.layer in {
        StrategicNumberControllerLayer.TEMPORARY,
        StrategicNumberControllerLayer.RECOVERY,
        StrategicNumberControllerLayer.ACTION,
    }:
        return f"(goal {controller.activation_state_name} 1)"


def _higher_controller_suppression(
    controller: StrategicNumberController,
    same_sn: tuple[StrategicNumberController, ...],
) -> tuple[str, ...]:
    higher = tuple(
        other
        for other in same_sn
        if (
            other.layer.precedence > controller.layer.precedence
            or (
                other.layer is controller.layer
                and other.priority > controller.priority
            )
        )
    )
    suppression: list[str] = []
    for other in higher:
        claim = _controller_claim_guard(other)
        suppression.append(f"(not {claim})")
    return tuple(suppression)


def validate_strategic_number_arbitration(
    plan: StrategicNumberArbitrationPlan,
    *,
    documented_native_ids: frozenset[int],
    action_identities: frozenset[str] = frozenset(),
) -> None:
    if not isinstance(plan, StrategicNumberArbitrationPlan):
        raise TypeError("plan must be a StrategicNumberArbitrationPlan")
    for controller in plan.controllers:
        if controller.native_strategic_number_id not in documented_native_ids:
            raise ValueError(
                "Strategic Number controller references undocumented native "
                f"Strategic Number {controller.native_strategic_number_id}"
            )
        if (
            controller.layer is StrategicNumberControllerLayer.ACTION
            and controller.action_identity not in action_identities
        ):
            raise ValueError(
                f"ACTION Strategic Number controller '{controller.identity}' "
                f"references unknown action identity '{controller.action_identity}'"
            )

        if controller.layer is StrategicNumberControllerLayer.TEMPORARY and (
            controller.scope is not StrategicNumberControllerScope.UNTIL_RELEASE
        ):
            raise ValueError("TEMPORARY controller must use UNTIL_RELEASE scope")

        if controller.layer is StrategicNumberControllerLayer.ACTION and (
            controller.scope is not StrategicNumberControllerScope.ACTION_SCOPED
        ):
            raise ValueError("ACTION controller must use ACTION_SCOPED scope")

    for controller in plan.controllers:
        if controller.layer in {
            StrategicNumberControllerLayer.TEMPORARY,
            StrategicNumberControllerLayer.ACTION,
            StrategicNumberControllerLayer.RECOVERY,
        }:
            if not any(
                other.native_strategic_number_id
                == controller.native_strategic_number_id
                and other.layer.precedence < controller.layer.precedence
                for other in plan.controllers
            ):
                raise ValueError(
                    f"Strategic Number override '{controller.identity}' has no lower-precedence "
                    "underlay to restore"
                )

    for sn_id in plan.native_strategic_number_ids:
        controllers = plan.controllers_for_sn(sn_id)
        for index, first in enumerate(controllers):
            for second in controllers[index + 1 :]:
                if first.layer is not second.layer:
                    continue
                if first.priority != second.priority:
                    continue
                if first.value == second.value:
                    continue
                first_guard = _guard_text(first.activation_guard)
                second_guard = _guard_text(second.activation_guard)
                if first.origin is StrategicNumberControllerOrigin.STRATEGY_MODE and (
                    second.origin is StrategicNumberControllerOrigin.STRATEGY_MODE
                ):
                    if first_guard == second_guard:
                        raise ValueError(
                            "conflicting Strategic Number controllers at equal "
                            "precedence and activation: "
                            f"'{first.identity}' vs '{second.identity}'"
                        )
                    continue
                raise ValueError(
                    "conflicting explicit Strategic Number controllers at equal "
                    "precedence and priority: "
                    f"'{first.identity}' vs '{second.identity}'"
                )


def _storage_state(
    controller: StrategicNumberController,
    profile_id: str,
) -> NativeControlState:
    from ..ir.model import SemanticId, StorageRequestId
    from ..ir.model import GoalRole

    owner = SemanticId(profile_id, controller.native_state_name)
    return NativeControlState(
        controller.native_state_name,
        StrategicNumberRequest(
            StorageRequestId(
                owner,
                f"strategy-sn-native:{controller.native_strategic_number_id}",
            ),
            why_not_goal=(
                "This state is a compiler policy reference to a DE-documented "
                "native Strategic Number; native per-SN effect semantics remain "
                "evidence-bounded."
            ),
            stability_key=f"{profile_id}:strategic-number:{controller.native_strategic_number_id}",
            role=GoalRole.PERSISTENT_STATE,
            origin=StrategicNumberOrigin.NATIVE_REFERENCE,
            native_strategic_number_id=controller.native_strategic_number_id,
        ),
    )


def _activation_state(
    controller: StrategicNumberController,
    profile_id: str,
) -> NativeControlState:
    from ..ir.model import GoalRole, SemanticId, StorageRequestId

    owner = SemanticId(profile_id, controller.activation_state_name)
    return NativeControlState(
        controller.activation_state_name,
        GoalSlotRequest(
            StorageRequestId(
                owner,
                f"strategic-number-controller:{controller.identity}",
            ),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )


def _release_block_state(
    controller: StrategicNumberController,
    profile_id: str,
) -> NativeControlState:
    from ..ir.model import GoalRole, SemanticId, StorageRequestId

    owner = SemanticId(profile_id, controller.release_block_state_name)
    return NativeControlState(
        controller.release_block_state_name,
        GoalSlotRequest(
            StorageRequestId(
                owner,
                f"strategic-number-controller-rearm:{controller.identity}",
            ),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )


def lower_strategic_number_arbitration(
    plan: StrategicNumberArbitrationPlan,
    *,
    profile_id: str,
    documented_native_ids: frozenset[int],
    action_identities: frozenset[str] = frozenset(),
) -> StrategicNumberArbitrationLowering:
    validate_strategic_number_arbitration(
        plan,
        documented_native_ids=documented_native_ids,
        action_identities=action_identities,
    )

    states: dict[str, NativeControlState] = {}
    rules: list[NativeControlRule] = []
    attachments: list[StrategicNumberActionAttachment] = []

    for sn_id in plan.native_strategic_number_ids:
        controllers = plan.controllers_for_sn(sn_id)
        states[f"sn-native-{sn_id}"] = _storage_state(controllers[0], profile_id)

    ordered_controllers = tuple(
        sorted(
            plan.controllers,
            key=lambda item: (
                item.native_strategic_number_id,
                -item.layer.precedence,
                -item.priority,
                item.identity,
            ),
        )
    )

    for controller in ordered_controllers:
        same_sn = plan.controllers_for_sn(controller.native_strategic_number_id)
        higher_suppression = _higher_controller_suppression(controller, same_sn)

        if controller.layer in {
            StrategicNumberControllerLayer.TEMPORARY,
            StrategicNumberControllerLayer.RECOVERY,
        }:
            states[controller.activation_state_name] = _activation_state(
                controller,
                profile_id,
            )
            states[controller.release_block_state_name] = _release_block_state(
                controller,
                profile_id,
            )

        if controller.layer is StrategicNumberControllerLayer.ACTION:
            states[controller.activation_state_name] = _activation_state(
                controller,
                profile_id,
            )
            attachments.append(
                StrategicNumberActionAttachment(
                    identity=f"{controller.identity}-attachment",
                    controller_identity=controller.identity,
                    action_identity=controller.action_identity or "",
                    native_strategic_number_id=controller.native_strategic_number_id,
                    value=controller.value,
                    activation_state_name=controller.activation_state_name,
                )
            )

            release_guard = _as_expression(
                _guard_text(controller.release_guard) or "(false)"
            )
            guard = _fold(
                "and",
                (
                    f"(goal {controller.activation_state_name} 1)",
                    release_guard.source,
                ),
            )
            rules.append(
                NativeControlRule(
                    f"sn-controller-{controller.identity}-release",
                    facts=(parse_expression(guard, SourceLocation(1)),),
                    actions=(
                        parse_expression(
                            f"(set-goal {controller.activation_state_name} 0)",
                            SourceLocation(1),
                        ),
                    ),
                )
            )
            continue

        trigger = _controller_claim_guard(controller)
        write_guard = _fold(
            "and",
            (
                trigger,
                *higher_suppression,
                f"(up-compare-sn {controller.native_state_name} != {controller.value})",
            ),
        )

        if controller.layer in {
            StrategicNumberControllerLayer.DEFAULT_BASE,
            StrategicNumberControllerLayer.AGE_BASE,
            StrategicNumberControllerLayer.STRATEGY,
        }:
            rule_identity = (
                f"sn-mode-{controller.identity}-"
                f"{sum(1 for item in rules if item.identity.startswith('sn-mode-')):03d}"
                if controller.origin is StrategicNumberControllerOrigin.STRATEGY_MODE
                else f"sn-controller-{controller.identity}-write"
            )
            rules.append(
                NativeControlRule(
                    rule_identity,
                    facts=(parse_expression(write_guard, SourceLocation(1)),),
                    actions=(
                        parse_expression(
                            f"(set-strategic-number {controller.native_state_name} {controller.value})",
                            SourceLocation(1),
                        ),
                    ),
                )
            )
            continue

        activation = _as_expression(_guard_text(controller.activation_guard) or "(false)")
        activation_guard = _fold(
            "and",
            (
                activation.source,
                *higher_suppression,
                f"(goal {controller.activation_state_name} 0)",
                f"(goal {controller.release_block_state_name} 0)",
            ),
        )
        rules.append(
            NativeControlRule(
                f"sn-controller-{controller.identity}-activate",
                facts=(parse_expression(activation_guard, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-goal {controller.activation_state_name} 1)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-strategic-number {controller.native_state_name} {controller.value})",
                        SourceLocation(1),
                    ),
                ),
            )
        )

        release_guard = _as_expression(
            _guard_text(controller.release_guard) or "(false)"
        )
        release = _fold(
            "and",
            (
                f"(goal {controller.activation_state_name} 1)",
                release_guard.source,
            ),
        )
        rules.append(
            NativeControlRule(
                f"sn-controller-{controller.identity}-release",
                facts=(parse_expression(release, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-goal {controller.activation_state_name} 0)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        f"(set-goal {controller.release_block_state_name} 1)",
                        SourceLocation(1),
                    ),
                ),
            )
        )

        rearm_guard = _fold(
            "and",
            (
                f"(goal {controller.activation_state_name} 0)",
                f"(goal {controller.release_block_state_name} 1)",
                f"(not {activation.source})",
            ),
        )
        rules.append(
            NativeControlRule(
                f"sn-controller-{controller.identity}-rearm",
                facts=(parse_expression(rearm_guard, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-goal {controller.release_block_state_name} 0)",
                        SourceLocation(1),
                    ),
                ),
            )
        )

        steady_guard = _fold(
            "and",
            (
                f"(goal {controller.activation_state_name} 1)",
                *higher_suppression,
                f"(up-compare-sn {controller.native_state_name} != {controller.value})",
            ),
        )
        rules.append(
            NativeControlRule(
                f"sn-controller-{controller.identity}-steady",
                facts=(parse_expression(steady_guard, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-strategic-number {controller.native_state_name} {controller.value})",
                        SourceLocation(1),
                    ),
                ),
            )
        )

    return StrategicNumberArbitrationLowering(
        arbitration_plan=plan,
        control_plan=NativeControlPlan(
            states=tuple(states[key] for key in sorted(states)),
            rules=tuple(rules),
        )
        if states or rules
        else None,
        action_attachments=tuple(attachments),
    )


__all__ = [
    "build_strategic_number_arbitration_plan",
    "lower_strategic_number_arbitration",
    "strategic_number_mode_to_controller",
    "validate_strategic_number_arbitration",
]
