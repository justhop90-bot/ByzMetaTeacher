"""Deterministic semantic IR -> AoE2 .per emitter."""
from __future__ import annotations

from ..errors import CompileError
from ..ir import SemanticDemand
from ..runtime_binding import BindingResult, LifecycleEncoding

MAX_RULES = 10_000
MAX_RULE_ELEMENTS = 32
MAX_LINE_LENGTH = 255
INITIALIZATION_CHUNK = 31


def _claim_name(conflict_class: str) -> str:
    return "action-claim-" + conflict_class.lower().replace("_", "-")


def _extract_rules(text: str) -> list[str]:
    rules = []
    cursor = 0
    while True:
        start = text.find("(defrule", cursor)
        if start < 0:
            return rules
        depth = 0
        end = None
        for index in range(start, len(text)):
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise CompileError("EMITTER-UNBALANCED-RULE: generated rule is not closed")
        rules.append(text[start:end])
        cursor = end


def _validate_artifact_budget(text: str) -> None:
    rules = _extract_rules(text)
    if len(rules) > MAX_RULES:
        raise CompileError(
            f"EMITTER-RULE-LIMIT: generated artifact has {len(rules)} rules; "
            f"DE limit is {MAX_RULES}"
        )
    longest_line = max((len(line) for line in text.splitlines()), default=0)
    if longest_line > MAX_LINE_LENGTH:
        raise CompileError(
            f"EMITTER-LINE-LIMIT: generated line has {longest_line} characters; "
            f"DE limit is {MAX_LINE_LENGTH}"
        )
    for index, rule in enumerate(rules, 1):
        elements = rule.count("(") - 1
        if elements > MAX_RULE_ELEMENTS:
            raise CompileError(
                f"EMITTER-RULE-ELEMENT-LIMIT: generated rule {index} has "
                f"{elements} elements; DE limit is {MAX_RULE_ELEMENTS}"
            )


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
    arbitration_requests = {}
    for demand in demands:
        slot = bindings.binding_for(demand.lifecycle.slot.request_id)
        lifecycle = LifecycleEncoding.for_goal_slot(slot)
        encoded[demand.name] = lifecycle

        request = demand.action.arbitration_request
        if request is not None:
            arbitration_requests[request.request_id] = request

        out.append(f"(defconst demand-{demand.name} {slot.id.value})")
        out.append(f"(defconst pending-{demand.name} {lifecycle.pending.value})")
        out.append(f"(defconst complete-{demand.name} {lifecycle.complete.value})")

    for request_id, _request in sorted(
        arbitration_requests.items(),
        key=lambda item: (item[0].owner.source_unit, item[0].purpose),
    ):
        slot = bindings.binding_for(request_id)
        conflict_class = request_id.purpose.split(":", 1)[1]
        out.append(f"(defconst {_claim_name(conflict_class)} {slot.id.value})")

    out.append("")
    if arbitration_requests:
        out.append("; Per-pass transient action arbitration")
        for request_id, _request in sorted(
            arbitration_requests.items(),
            key=lambda item: (item[0].owner.source_unit, item[0].purpose),
        ):
            conflict_class = request_id.purpose.split(":", 1)[1]
            out += [
                "(defrule",
                "    (true)",
                "=>",
                f"    (set-goal {_claim_name(conflict_class)} 0)",
                ")",
                "",
            ]

    if demands:
        out.append("; Demand initialization")
        for start in range(0, len(demands), INITIALIZATION_CHUNK):
            chunk = demands[start : start + INITIALIZATION_CHUNK]
            out += ["(defrule", "    =>"]
            for demand in chunk:
                out.append(
                    f"    (set-goal demand-{demand.name} "
                    f"{encoded[demand.name].active.value})"
                )
            if start + INITIALIZATION_CHUNK >= len(demands):
                out.append("    (disable-self)")
            out += [")", ""]

    for demand in demands:
        slot = bindings.binding_for(demand.lifecycle.slot.request_id)
        lifecycle = encoded[demand.name]
        out += [
            f"; Pending diagnostics: {demand.name}",
        ]
        for diagnostic in demand.pending_diagnostics:
            message = diagnostic.message.format(
                active_goal=slot.id.value,
                pending_goal=lifecycle.pending.value,
                completed_goal=lifecycle.complete.value,
            )
            out.append(
                f"; PENDING-DIAGNOSTIC [{diagnostic.severity}] "
                f"{diagnostic.code}: {message}"
            )

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

        request = demand.action.arbitration_request
        if request is not None:
            conflict_class = request.request_id.purpose.split(":", 1)[1]
            out.append(f"    (goal {_claim_name(conflict_class)} 0)")

        out.extend(
            f"    {requirement.expression.source}"
            for requirement in demand.requirements
        )
        out += [
            "=>",
            f"    {demand.action.expression.source}",
        ]

        if request is not None:
            conflict_class = request.request_id.purpose.split(":", 1)[1]
            out.append(f"    (set-goal {_claim_name(conflict_class)} 1)")

        out += [
            f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
            ")",
            "",
        ]

    result = "\n".join(out).rstrip() + "\n"
    _validate_artifact_budget(result)
    return result
