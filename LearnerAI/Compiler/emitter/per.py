"""Deterministic semantic IR -> AoE2 .per emitter."""
from __future__ import annotations
from ..ir import SemanticDemand


def emit(demands: list[SemanticDemand], compiler_version: str = "0.4") -> str:
    out = [
        ";============================================================",
        "; BASILISK GENERATED .PER",
        f"; Compiler: Basilisk compiler {compiler_version}",
        "; Generated from validated semantic IR. Do not edit by hand.",
        ";============================================================",
        "",
        "; Demand goal constants",
    ]
    for d in demands:
        out.append(f"(defconst demand-{d.name} {d.goal})")
        out.append(f"(defconst pending-{d.name} {d.pending_goal})")
        out.append(f"(defconst complete-{d.name} {d.completed_goal})")
    out += ["", "; Demand initialization", "(defrule", "    =>"]
    for d in demands:
        out.append(f"    (set-goal demand-{d.name} 1)")
    out += ["    (disable-self)", ")", ""]
    for d in demands:
        out += [
            f"; Pending diagnostics: {d.name}",
        ]
        for diagnostic in d.pending_diagnostics:
            out.append(
                f"; PENDING-DIAGNOSTIC [{diagnostic.severity}] "
                f"{diagnostic.code}: {diagnostic.message}"
            )

        # AoE2 goals update immediately, while many world facts are only
        # refreshed on the next script pass. Rule order must therefore place
        # later lifecycle transitions before earlier ones. This makes each
        # transition require a fresh pass:
        #   pass N:   ACTIVE -> PENDING
        #   pass N+1: PENDING -> COMPLETE
        #   pass N+2: COMPLETE -> RELEASED
        #
        # Reversing this order would allow an already-true witness/release
        # to collapse the entire lifecycle in one pass.
        #
        # The action also requires both completion and release predicates to be
        # false before entering pending. This is the stale-fact barrier:
        # a world fact that was already true before the action cannot later
        # masquerade as evidence that the action completed or that the demand
        # became releasable.
        out += [
            f"; Release: {d.name} | COMPLETE -> RELEASED",
            "(defrule",
            f"    (goal demand-{d.name} {d.completed_goal})",
            f"    {d.release.source}",
            "=>",
            f"    (set-goal demand-{d.name} 0)",
            ")",
            "",
            f"; Completion witness: {d.name} | PENDING -> COMPLETE",
            "(defrule",
            f"    (goal demand-{d.name} {d.pending_goal})",
            f"    {d.witness.source}",
            "=>",
            f"    (set-goal demand-{d.name} {d.completed_goal})",
            ")",
            "",
            f"; Demand: {d.name} | ACTIVE -> PENDING",
            "(defrule",
            f"    (goal demand-{d.name} 1)",
            f"    (not {d.witness.source})",
            f"    (not {d.release.source})",
        ]
        out.extend(f"    {r.expression.source}" for r in d.requirements)
        out += [
            "=>",
            f"    {d.action.expression.source}",
            f"    (set-goal demand-{d.name} {d.pending_goal})",
            ")",
            "",
        ]
    return "\n".join(out).rstrip() + "\n"
