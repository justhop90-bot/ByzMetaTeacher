"""Basilisk strategy-to-.per adapter built on the generic compiler."""

from __future__ import annotations

from ...compiler import compile_semantic_demands
from ...ir.strategy import lower_strategy_profile
from ...ir.strategy_runtime import evaluate_strategy_runtime


def compile_strategy_profile(
    profile,
    effective,
    base_goal: int = 41,
    *,
    binding_context=None,
) -> str:
    """Lower a downstream strategy profile through the generic compiler."""
    compilation = lower_strategy_profile(profile, effective)
    return compile_semantic_demands(
        compilation.demands,
        base_goal=base_goal,
        binding_context=binding_context,
        escrow_plan=compilation.escrow_plan,
    )


def compile_strategy_runtime_profile(
    profile,
    effective,
    runtime_profile,
    base_goal: int = 41,
    *,
    binding_context=None,
) -> str:
    """Select active downstream strategic demands, then use generic lowering."""
    runtime_state = evaluate_strategy_runtime(profile, effective, runtime_profile)
    compilation = lower_strategy_profile(profile, effective)
    active_ids = set(runtime_state.active_or_blocked_demands)
    selected = tuple(
        demand
        for demand in compilation.demands
        if demand.strategic_binding is not None
        and demand.strategic_binding.strategic_id in active_ids
    )
    return compile_semantic_demands(
        selected,
        base_goal=base_goal,
        binding_context=binding_context,
        escrow_plan=compilation.escrow_plan,
    )
