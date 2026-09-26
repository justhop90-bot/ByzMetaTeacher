"""Deterministic semantic IR -> AoE2 .per emitter."""
from __future__ import annotations
from ..ir import SemanticDemand

def emit(demands: list[SemanticDemand], compiler_version: str = "0.2") -> str:
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
    out += ["", "; Demand initialization", "(defrule", "    =>"]
    for d in demands:
        out.append(f"    (set-goal demand-{d.name} 1)")
    out += ["    (disable-self)", ")", ""]
    for d in demands:
        out += [
            f"; Demand: {d.name}", "(defrule", f"    (goal demand-{d.name} 1)"
        ]
        out.extend(f"    {r.expression.source}" for r in d.requirements)
        out += ["=>", f"    {d.action.expression.source}", ")", ""]
        out += [
            f"; Completion witness: {d.name}", "(defrule",
            f"    (goal demand-{d.name} 1)", f"    {d.witness.source}",
            "=>", f"    (set-goal demand-{d.name} 2)", ")", ""
        ]
        out += [
            f"; Release: {d.name}", "(defrule",
            f"    (goal demand-{d.name} 2)", f"    {d.release.source}",
            "=>", f"    (set-goal demand-{d.name} 0)", ")", ""
        ]
    return "\n".join(out).rstrip() + "\n"
