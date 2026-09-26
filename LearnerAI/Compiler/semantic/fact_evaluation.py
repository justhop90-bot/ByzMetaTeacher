"""Runtime-independent evaluation of normalized semantic facts."""

from __future__ import annotations

from .fact_registry import FactSemanticAdapter
from .fact_values import NormalizedFact, StaticTruth


def evaluate_static_truth(
    fact: NormalizedFact,
    adapter: FactSemanticAdapter,
) -> StaticTruth:
    """
    Evaluate only proposition truth proved by the semantic fact adapter.

    FactDomain metadata is deliberately not consulted for proposition truth.
    Domains describe legal value spaces; adapters own any compile-time proof
    that a specific normalized fact is necessarily true, necessarily false, or
    still runtime-dependent.
    """
    if not isinstance(fact, NormalizedFact):
        raise TypeError("fact must be a NormalizedFact")
    if not isinstance(adapter, FactSemanticAdapter):
        raise TypeError("adapter must be a FactSemanticAdapter")

    return adapter.evaluate_static_truth(fact)


__all__ = ["evaluate_static_truth"]
