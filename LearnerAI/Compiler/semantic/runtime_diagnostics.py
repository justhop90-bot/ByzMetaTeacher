"""Conservative mapping from runtime witness claims to compiler feature traces."""
from __future__ import annotations

from dataclasses import dataclass

from ..diagnostics import DiagnosticSeverity
from .semantic_manifest import SemanticManifest
from .strategy_dependency import FeatureTrace, first_broken_edge


@dataclass(frozen=True)
class RuntimeDiagnosticResult:
    scenario_id: str
    claim_id: str
    status: str
    feature_id: str | None = None
    diagnostic_code: str | None = None
    severity: str | None = None
    message: str | None = None


def diagnose_runtime_claim(
    scenario_id: str,
    claim: dict[str, object],
    manifest: SemanticManifest,
    feature_traces: tuple[FeatureTrace, ...],
    *,
    rejected: bool,
) -> RuntimeDiagnosticResult:
    """Map a rejected runtime claim to an implicated compiler edge when evidence permits.

    A runtime rejection is never treated as proof of a compiler defect by itself.
    We only report a broken compiler edge when a named rule identity resolves through
    the semantic manifest to a rule order carried by a feature trace whose first
    broken edge is already statically established.
    """
    claim_id = str(claim.get("id", ""))
    identities = tuple(str(value) for value in claim.get("rule_identities", ()) if value)
    if not rejected:
        return RuntimeDiagnosticResult(scenario_id, claim_id, "OPEN")

    rule_orders = {
        rule.rule_order
        for rule in manifest.rules
        if rule.identity in identities
    }
    if not rule_orders:
        return RuntimeDiagnosticResult(scenario_id, claim_id, "UNKNOWN")

    candidates = tuple(
        trace
        for trace in feature_traces
        if any(order in rule_orders for node in trace.nodes for order in node.rule_orders)
    )
    candidates = tuple(sorted(candidates, key=lambda trace: trace.feature_id))
    for trace in candidates:
        broken = first_broken_edge(trace)
        if broken is None:
            continue
        return RuntimeDiagnosticResult(
            scenario_id=scenario_id,
            claim_id=claim_id,
            status="COMPILER_EDGE_BROKEN",
            feature_id=trace.feature_id,
            diagnostic_code=broken.diagnostic_code,
            severity=DiagnosticSeverity.ERROR.value,
            message=broken.message,
        )

    if candidates:
        return RuntimeDiagnosticResult(scenario_id, claim_id, "RUNTIME_EDGE_OPEN")
    return RuntimeDiagnosticResult(scenario_id, claim_id, "UNKNOWN")


__all__ = ["RuntimeDiagnosticResult", "diagnose_runtime_claim"]
