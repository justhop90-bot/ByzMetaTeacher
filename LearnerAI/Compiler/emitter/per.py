"""Deterministic semantic IR -> AoE2 .per emitter."""
from __future__ import annotations

from ..ir import SemanticDemand
from ..runtime_binding import BindingResult, LifecycleEncoding


def emit(
    demands: list[SemanticDemand],
    bindings: BindingResult,
    compiler_version: str = "0.4",
) -> str:
    out = [
        ";============================================================",
        "; BASILISK GENERATED .PER",
        f"; Compiler: Basilisk compiler {compiler_version}",
        "; Generated from validated semantic IR. Do not edit by hand.",
        ";============================================================",
        "",
        "; Demand goal constants",
    ]
    encoded: dict[str, LifecycleEncoding] = {}
    for demand in demands:
        slot = bindings.binding_for(demand.lifecycle.slot.request_id)
        lifecycle = LifecycleEncoding.for_goal_slot(slot)
        encoded[demand.name] = lifecycle
        out.append(f"(defconst demand-{demand.name} {slot.id.value})")
        out.append(f"(defconst pending-{demand.name} {lifecycle.pending.value})")
        out.append(f"(defconst complete-{demand.name} {lifecycle.complete.value})")
    out += ["", "; Demand initialization", "(defrule", "    =>"]
    for demand in demands:
        out.append(f"    (set-goal demand-{demand.name} {encoded[demand.name].active.value})")
    out += ["    (disable-self)", ")", ""]
    for demand in demands:
        lifecycle = encoded[demand.name]
        out += [
            f"; Pending diagnostics: {demand.name}",
        ]
        for diagnostic in demand.pending_diagnostics:
            message = diagnostic.message.format(
                active_goal=encoded[demand.name].active.value,
                pending_goal=lifecycle.pending.value,
                completed_goal=lifecycle.complete.value,
            )
            out.append(
                f"; PENDING-DIAGNOSTIC [{diagnostic.severity}] "
                f"{diagnostic.code}: {message}"
            )

        # AoE2 goals update immediately, while many world facts are only
        # refreshed on the next script pass. Rule order therefore places later
        # lifecycle transitions before earlier ones, forcing each transition
        # to require a fresh script pass.
        out += [
            f"; Release: {demand.name} | COMPLETE -> RELEASED",
            "(defrule",
            f"    (goal demand-{demand.name} {lifecycle.complete.value})",
            f"    {demand.release.source}",
            "=>",
            f"    (set-goal demand-{demand.name} {lifecycle.released.value})",
            ")",
            "",
            f"; Completion witness: {demand.name} | PENDING -> COMPLETE",
            "(defrule",
            f"    (goal demand-{demand.name} {lifecycle.pending.value})",
            f"    {demand.witness.source}",
            "=>",
            f"    (set-goal demand-{demand.name} {lifecycle.complete.value})",
            ")",
            "",
            f"; Demand: {demand.name} | ACTIVE -> PENDING",
            "(defrule",
            f"    (goal demand-{demand.name} {lifecycle.active.value})",
            f"    (not {demand.witness.source})",
            f"    (not {demand.release.source})",
        ]
        out.extend(f"    {requirement.expression.source}" for requirement in demand.requirements)
        out += [
            "=>",
            f"    {demand.action.expression.source}",
            f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
            ")",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"
