    registry: PrimitiveRegistry | None = None,
    control_plan: NativeControlPlan | None = None,
    duc_plan: NativeDucPlan | None = None,
    attack_plan: NativeAttackLifecyclePlan | AttackExecution | None = None,
    role_plan: NativeRoleSeparationPlan | None = None,
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None,
) -> str:
    registry = registry or default_de_registry()
    if control_plan is not None:
        validate_native_control_plan(
            control_plan,
            registry,
            external_goal_states=tuple(f"demand-{demand.name}" for demand in demands),
        )
    if duc_plan is not None:
        registry.validate_duc_plan(duc_plan)
    native_attack_plan = (
        attack_plan.native_plan
        if isinstance(attack_plan, AttackExecution)
        else attack_plan
    )