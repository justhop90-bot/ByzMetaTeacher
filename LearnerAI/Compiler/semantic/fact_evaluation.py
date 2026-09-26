"""Runtime-independent evaluation of normalized semantic facts."""

from __future__ import annotations

from .fact_values import FactDomain, NormalizedFact, StaticTruth


def evaluate_static_truth(
    fact: NormalizedFact,
    domain: FactDomain,
) -> StaticTruth:
    """
    Evaluate only truth that is provable from immutable semantic metadata.

    This function never observes engine state. A domain defaults to UNKNOWN;
    TRUE or FALSE require an explicit invariant proof carried by that domain.

    If the NormalizedFact already carries a domain, its semantic domain identity
    must match the supplied domain. Provenance is deliberately ignored when
    checking compatibility.
    """
    if not isinstance(fact, NormalizedFact):
        raise TypeError("fact must be a NormalizedFact")
    if not isinstance(domain, FactDomain):
        raise TypeError("domain must be a FactDomain")

    if fact.domain is not None and fact.domain.identity != domain.identity:
        raise ValueError(
            f"fact domain '{fact.domain.identity}' does not describe fact "
            f"under supplied domain '{domain.identity}'"
        )

    return domain.invariant_truth


__all__ = ["evaluate_static_truth"]
