"""Basilisk strategy-to-.per adapter built on the generic compiler."""

from __future__ import annotations

from dataclasses import replace

from ...compiler import compile_semantic_demands
from ...ir.strategy import lower_strategy_profile
from ...ir.resource_control import NativeEscrowReleasePlan
from ...ir.strategy_runtime import evaluate_strategy_runtime


def compile_strategy_profile(
    profile,
    effective,
    base_goal: int = 41,
    *,
    binding_context=None,
    attack_plan=None,
    duc_plan=None,
) -> str:
    """Lower a downstream strategy profile through the generic compiler."""
    compilation = lower_strategy_profile(profile, effective)
    effective_attack_plan = (
        attack_plan
        if attack_plan is not None
        else compilation.attack_plan
    )
    effective_duc_plan = (
        duc_plan
        if duc_plan is not None
        else compilation.duc_plan
    )
    return compile_semantic_demands(
        compilation.demands,
        base_goal=base_goal,
        binding_context=binding_context,
        control_plan=compilation.control_plan,
        attack_plan=effective_attack_plan,
        duc_plan=effective_duc_plan,
        escrow_plan=compilation.escrow_plan,
    )


def compile_strategy_runtime_profile(
    profile,
    effective,
    runtime_profile,
    base_goal: int = 41,
    *,
    binding_context=None,
    attack_plan=None,
    duc_plan=None,
) -> str:
    """Select active downstream strategic demands, then use generic lowering."""
    compilation = lower_strategy_profile(profile, effective)
    effective_attack_plan = (
        attack_plan
        if attack_plan is not None
        else compilation.attack_plan
    )
    effective_duc_plan = (
        duc_plan
        if duc_plan is not None
        else compilation.duc_plan
    )
    lifecycle_inputs = tuple(
        (
            demand.name,
            demand.production_lifecycle,
        )
        for demand in compilation.demands
        if demand.production_lifecycle is not None
    )
    runtime_snapshot = replace(
        runtime_profile,
        production_lifecycles=(
            runtime_profile.production_lifecycles
            if runtime_profile.production_lifecycles
            else lifecycle_inputs
        ),
    )
    runtime_state = evaluate_strategy_runtime(
        profile,
        effective,
        runtime_snapshot,
    )
    active_ids = set(runtime_state.active_or_blocked_demands)
    selected = tuple(
        demand
        for demand in compilation.demands
        if demand.strategic_binding is not None
        and demand.strategic_binding.strategic_id in active_ids
    )
    selected_ids = {demand.identity for demand in selected}
    escrow_plan = compilation.escrow_plan
    if escrow_plan is not None:
        escrow_plan = NativeEscrowReleasePlan(
            tuple(
                operation
                for operation in escrow_plan.operations
                if operation.target_demand is None
                or operation.target_demand in selected_ids
            )
        )
    return compile_semantic_demands(
        selected,
        base_goal=base_goal,
        binding_context=binding_context,
        control_plan=compilation.control_plan,
        attack_plan=effective_attack_plan,
        duc_plan=effective_duc_plan,
        escrow_plan=escrow_plan,
    )
