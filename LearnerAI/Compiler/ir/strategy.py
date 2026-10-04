

def _strategy_control_plan(profile: StrategyProfile):
    """Lower posture transitions, SN modes, and explicit Goal assertions through one control plane."""
    posture_plan = _posture_transition_control_plan(profile)
    mode_plan = _strategic_number_arbitration_control_plan(profile)
    assertion_plan = _goal_state_control_plan(profile)
    attack_lifecycle_plan = _byzantine_attack_lifecycle_control_plan(profile)
    water_plan = None
    if profile.water_execution_plan is not None:
        from .water import lower_water_execution_plan
        water_plan = lower_water_execution_plan(
            profile.water_execution_plan,
            profile,
        )
    opening_plan = None
    if profile.opening_selector is not None:
        from .opening import lower_opening_selector
        opening_plan = lower_opening_selector(profile.opening_selector, profile)
    economy_plan = None
    if profile.economy_controller is not None:
        from .economic_control import lower_economy_controller
        economy_plan = lower_economy_controller(profile.economy_controller, profile)

    camp_plan = None
    if profile.camp_controller is not None:
        from .camp_control import lower_byzantine_camp_controller
        camp_plan = lower_byzantine_camp_controller(profile.camp_controller, profile)

    role_recovery_bridge_plan = None
    if profile.role_separation_plan is not None:
        from ..ast import SourceLocation
        from ..semantic.analyzer import parse_expression
        from .native_control import NativeControlPlan, NativeControlRule

        role_recovery_bridge_plan = NativeControlPlan(
            rules=(
                NativeControlRule(
                    "byzantine-role-recovery-bridge",
                    facts=(
                        parse_expression(
                            "(goal byzantine-army-role-recovery-request 1)",
                            SourceLocation(1),
                        ),
                    ),
                    actions=(
                        parse_expression(
                            "(up-reset-attack-now)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(set-goal byzantine-army-attack-ready 0)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(set-goal byzantine-army-role-recovery-request 0)",
                            SourceLocation(1),
                        ),
                    ),
                ),
            )
        )

    if any(
        state.identifier == _STRATEGY_POSTURE_STATE
        for state in (assertion_plan.states if assertion_plan is not None else ())
    ):
        raise ValueError(
            f"native strategy state '{_STRATEGY_POSTURE_STATE}' is reserved by posture transitions"
        )
    if posture_plan is not None and mode_plan is not None:
        mode_posture_state = mode_plan.state(_STRATEGY_POSTURE_STATE) if _STRATEGY_POSTURE_STATE in {
            state.identifier for state in mode_plan.states
        } else None
        if mode_posture_state is not None and mode_posture_state != posture_plan.state(
            _STRATEGY_POSTURE_STATE
        ):
            raise ValueError(
                f"native strategy state '{_STRATEGY_POSTURE_STATE}' conflicts with posture transition storage"
            )

    return _merge_native_control_plans(
        posture_plan,
        mode_plan,
        assertion_plan,
        attack_lifecycle_plan,
        water_plan,
        opening_plan,
        economy_plan,
        camp_plan,
        role_recovery_bridge_plan,
    )


def _posture_transition_control_plan(profile: StrategyProfile):
    """Lower the StrategyProfile posture FSM into native Goal control rules.

    Transition evidence is always read from verified StrategyObservationSpec
    references. Native same-pass Goal visibility remains engine-ordered, so
    this synthesis establishes deterministic policy/lowering without claiming
    an unproven runtime firing order.
    """
    if not profile.transitions:
        return None