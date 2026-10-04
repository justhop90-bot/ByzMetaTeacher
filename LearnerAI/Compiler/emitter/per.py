"""Deterministic semantic IR -> AoE2 .per emitter."""
from __future__ import annotations

from dataclasses import replace

from ..errors import CompileError
from ..ir import (
    AttackExecution,
    ConstructionTransitionKind,
    NativeAttackLifecyclePlan,
    NativeControlPlan,
    NativeDucPlan,
    NativeEscrowPolicyPlan,
    NativeEscrowReleasePlan,
    SemanticDemand,
    StrategicNumberOrigin,
)
from ..primitives import PrimitiveRegistry, default_de_registry
from ..runtime_binding import (
    BindingResult,
    GoalSlot,
    GoalSpan,
    LifecycleEncoding,
    StrategicNumberSlot,
    TimerSlot,
)
from ..semantic.native_control import validate_native_control_plan
from ..semantic.construction import construction_transition_rules

MAX_RULES = 10_000
MAX_RULE_ELEMENTS = 32
MAX_LINE_LENGTH = 255
INITIALIZATION_CHUNK = 30


def _claim_name(conflict_class: str) -> str:
    return "action-claim-" + conflict_class.lower().replace("_", "-")


def _research_runtime_source(expression, research) -> str:
    """Lower source-level research aliases to the exact runtime TechId symbol."""
    source = expression.source
    if research is None or not isinstance(source, str):
        return source

    pending_args = getattr(research.pending_fact, "args", ())
    if len(pending_args) < 2 or pending_args[0] != "c:":
        return source
    runtime_symbol = pending_args[1]
    if not isinstance(runtime_symbol, str) or not runtime_symbol:
        return source

    research_heads = {
        "research",
        "research-available",
        "research-completed",
        "can-research",
        "can-afford-research",
        "can-research-with-escrow",
    }
    if getattr(expression, "head", None) not in research_heads:
        return source

    technology = research.technology
    if not technology or technology == runtime_symbol:
        return source

    return source.replace(f" {technology}", f" {runtime_symbol}")


def _defconst_bindings(lines: list[str]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        fields = stripped.rstrip(")").split()
        if stripped.startswith("(defconst ") and len(fields) >= 3:
            bindings[fields[1]] = fields[2]
    return bindings


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
    lines = text.splitlines()
    longest_line = max((len(line) for line in lines), default=0)
    if longest_line > MAX_LINE_LENGTH:
        line_number = max(range(len(lines)), key=lambda index: len(lines[index])) + 1
        offending_line = lines[line_number - 1]
        raise CompileError(
            f"EMITTER-LINE-LIMIT: generated line {line_number} has "
            f"{longest_line} characters; DE limit is {MAX_LINE_LENGTH}: "
            f"{offending_line}"
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
    *,
    registry: PrimitiveRegistry | None = None,
    control_plan: NativeControlPlan | None = None,
    duc_plan: NativeDucPlan | None = None,
    attack_plan: NativeAttackLifecyclePlan | AttackExecution | None = None,
    escrow_plan: NativeEscrowReleasePlan | NativeEscrowPolicyPlan | None = None,
) -> str:
    registry = registry or default_de_registry()
    if control_plan is not None:
        validate_native_control_plan(control_plan, registry)
    if duc_plan is not None:
        registry.validate_duc_plan(duc_plan)
    native_attack_plan = (
        attack_plan.native_plan
        if isinstance(attack_plan, AttackExecution)
        else attack_plan
    )
    if native_attack_plan is not None:
        registry.validate_attack_plan(native_attack_plan)
    if escrow_plan is not None:
        registry.validate_escrow_plan(escrow_plan)

    targeted_releases: dict[object, list] = {}
    if isinstance(escrow_plan, NativeEscrowReleasePlan):
        demand_by_identity = {demand.identity: demand for demand in demands}
        for operation in escrow_plan.operations:
            if operation.target_demand is None:
                continue
            demand = demand_by_identity.get(operation.target_demand)
            if demand is None:
                raise CompileError(
                    f"EMITTER-ESCROW-TARGET: targeted release '{operation.contract_identity}' "
                    f"references unknown demand '{operation.target_demand.source_unit}:{operation.target_demand.local_name}'"
                )
            if demand.action.expression.head != "research":
                raise CompileError(
                    f"EMITTER-ESCROW-TARGET: demand '{demand.name}' may target only research actions"
                )
            if len(demand.action.expression.args) != 1:
                raise CompileError(
                    f"EMITTER-ESCROW-TARGET: research demand '{demand.name}' "
                    "must have one literal technology argument"
                )
            technology = str(demand.action.expression.args[0])
            admissions = tuple(
                requirement.expression
                for requirement in demand.requirements
                if requirement.expression.head == "can-research-with-escrow"
            )
            if not any(
                len(expression.args) == 1
                and str(expression.args[0]) == technology
                for expression in admissions
            ):
                raise CompileError(
                    f"EMITTER-ESCROW-TARGET: demand '{demand.name}' "
                    "requires can-research-with-escrow for the same technology"
                )
            targeted_releases.setdefault(operation.target_demand, []).append(operation)

        for demand_identity, operations in targeted_releases.items():
            rule_orders = {operation.rule_order for operation in operations}
            if len(rule_orders) != 1:
                raise CompileError(
                    f"EMITTER-ESCROW-TARGET: demand '{demand_identity.local_name}' "
                    "has targeted releases assigned to multiple rule orders"
                )
            operations.sort(
                key=lambda operation: (operation.within_rule_order, operation.contract_identity)
            )

    out = [
        ";============================================================",
        "; AOE2 .PER GENERATED BY COMPILER",
        f"; Compiler: AoE2 .per Compiler {compiler_version}",
        "; Generated from validated semantic IR. Do not edit by hand.",
        ";============================================================",
        "",
        "; Demand goal constants",
    ]

    encoded: dict[str, LifecycleEncoding] = {}
    arbitration_requests = {}
    strategic_number_states = []
    timer_states = []
    research_tech_states = []

    for demand in demands:
        for state in demand.strategic_number_states:
            if any(
                existing_state.name == state.name
                for existing_state, _ in strategic_number_states
            ):
                raise CompileError(
                    f"EMITTER-SN-DUPLICATE: duplicate Strategic Number state '{state.name}'"
                )
            binding = bindings.binding_for(state.request.request_id)
            if binding.__class__.__name__ != "StrategicNumberSlot":
                raise CompileError(
                    f"EMITTER-SN-BINDING: state '{state.name}' has non-SN binding "
                    f"{type(binding).__name__}"
                )
            strategic_number_states.append((state, binding))

        for state in demand.timer_states:
            binding = bindings.binding_for(state.request.request_id)
            if not isinstance(binding, TimerSlot):
                raise CompileError(
                    f"EMITTER-TIMER-BINDING: state '{state.name}' has non-Timer binding "
                    f"{type(binding).__name__}"
                )
            if any(existing_state.name == state.name for existing_state, _ in timer_states):
                raise CompileError(
                    f"EMITTER-TIMER-DUPLICATE: duplicate Timer state '{state.name}'"
                )
            timer_states.append((state, binding))

        if demand.research_lifecycle is not None:
            state = demand.research_lifecycle
            if any(
                existing_state.native_tech_id != state.native_tech_id
                and existing_state.technology == state.technology
                for existing_state in research_tech_states
            ):
                raise CompileError(
                    f"EMITTER-RESEARCH-TECH-DUPLICATE: conflicting TechId for "
                    f"'{state.technology}'"
                )
            research_tech_states.append(state)

    if timer_states:
        out.extend([
            "",
            "; Timer state constants",
        ])
        for state, binding in sorted(
            timer_states,
            key=lambda item: (
                item[0].request.request_id.owner.source_unit,
                item[0].request.request_id.owner.local_name,
                item[0].request.request_id.purpose,
            ),
        ):
            out.append(f"(defconst {state.name} {binding.id})")

        out.extend([
            "",
            "; Timer state initialization",
        ])
        for start in range(0, len(timer_states), INITIALIZATION_CHUNK):
            chunk = timer_states[start : start + INITIALIZATION_CHUNK]
            out += ["(defrule", "    (true)", "=>"]
            for state, _binding in chunk:
                if state.request.initialization_policy != "DISABLE_BEFORE_FIRST_USE":
                    raise CompileError(
                        f"EMITTER-TIMER-INIT-POLICY: unsupported initialization policy "
                        f"'{state.request.initialization_policy}' for timer '{state.name}'"
                    )
                out.append(f"    (disable-timer {state.name})")
            out.extend(["    (disable-self)", ")", ""])

    if research_tech_states:
        out.extend([
            "",
            "; Research technology constants",
        ])
        seen_tech_symbols: set[str] = set()
        seen_tech_ids: dict[int, str] = {}
        for state in sorted(
            research_tech_states,
            key=lambda item: (item.technology, item.native_tech_id),
        ):
            if state.technology in seen_tech_symbols:
                continue
            previous = seen_tech_ids.get(state.native_tech_id)
            if previous is not None and previous != state.technology:
                raise CompileError(
                    f"EMITTER-RESEARCH-TECH-ID: TechId {state.native_tech_id} "
                    f"is assigned to both '{previous}' and '{state.technology}'"
                )
            seen_tech_symbols.add(state.technology)
            seen_tech_ids[state.native_tech_id] = state.technology
            out.append(
                f"(defconst {state.technology} {state.native_tech_id})"
            )

            pending_args = getattr(state.pending_fact, "args", ())
            if (
                len(pending_args) >= 2
                and pending_args[0] == "c:"
                and isinstance(pending_args[1], str)
                and pending_args[1] != state.technology
            ):
                runtime_symbol = pending_args[1]
                if runtime_symbol not in seen_tech_symbols:
                    out.append(
                        f"(defconst {runtime_symbol} {state.native_tech_id})"
                    )
                    seen_tech_symbols.add(runtime_symbol)

    for state, binding in sorted(
        strategic_number_states,
        key=lambda item: (
            item[0].request.request_id.owner.source_unit,
            item[0].request.request_id.owner.local_name,
            item[0].request.request_id.purpose,
        ),
    ):
        out.append(f"(defconst {state.name} {binding.id})")

    if strategic_number_states:
        out.extend([
            "",
            "; Strategic Number state initialization",
        ])
        for start in range(0, len(strategic_number_states), INITIALIZATION_CHUNK):
            chunk = strategic_number_states[start : start + INITIALIZATION_CHUNK]
            out += ["(defrule", "    (true)", "=>"]
            for state, _binding in chunk:
                if state.request.origin is StrategicNumberOrigin.NATIVE_REFERENCE:
                    continue
                out.append(
                    f"    (set-strategic-number {state.name} {state.initial_value})"
                )
            out.extend(["    (disable-self)", ")", ""])

    for demand in demands:
        slot = bindings.binding_for(demand.lifecycle.slot.request_id)
        lifecycle = LifecycleEncoding.for_goal_slot(slot)
        research = demand.research_lifecycle
        encoded[demand.name] = lifecycle

        native_pass_constraints = registry.pass_constraints_for(demand.action.expression.head)
        for constraint in native_pass_constraints:
            out.append(
                f"; NATIVE-PASS-CONSTRAINT {demand.action.expression.head} "
                f"maximum-successes={constraint.maximum_successes}"
            )
            if (
                constraint.maximum_successes == 1
                and demand.action.arbitration_request is None
            ):
                raise CompileError(
                    f"EMITTER-NATIVE-PASS-CONSTRAINT: action '{demand.action.expression.head}' "
                    "requires a transient arbitration owner for maximum-successes=1"
                )

        request = demand.action.arbitration_request
        if request is not None:
            arbitration_requests[request.request_id] = request

        out.append(f"(defconst demand-{demand.name} {slot.id.value})")
        out.append(f"(defconst issued-{demand.name} {lifecycle.issued.value})")
        out.append(f"(defconst pending-{demand.name} {lifecycle.pending.value})")
        out.append(f"(defconst complete-{demand.name} {lifecycle.complete.value})")
        if demand.invalidation is not None:
            out.append(
                f"(defconst cancelled-{demand.name} {lifecycle.cancelled.value})"
            )
        if demand.construction_retry_barrier is not None:
            barrier_slot = bindings.binding_for(
                demand.construction_retry_barrier.request_id
            )
            if not isinstance(barrier_slot, GoalSlot):
                raise CompileError(
                    f"CONSTRUCTION-BARRIER-BINDING: construction retry barrier for "
                    f"'{demand.name}' resolved to '{type(barrier_slot).__name__}', expected GoalSlot"
                )
            out.append(
                f"(defconst construction-retry-barrier-{demand.name} "
                f"{barrier_slot.id.value})"
            )
        if demand.production_lifecycle is not None:
            barrier_slot = bindings.binding_for(
                demand.production_lifecycle.retry_barrier.request_id
            )
            if not isinstance(barrier_slot, GoalSlot):
                raise CompileError(
                    f"PRODUCTION-BARRIER-BINDING: production retry barrier for "
                    f"'{demand.name}' resolved to '{type(barrier_slot).__name__}', expected GoalSlot"
                )
            out.append(
                f"(defconst production-retry-barrier-{demand.name} "
                f"{barrier_slot.id.value})"
            )
        if demand.research_retry_barrier is not None:
            barrier_slot = bindings.binding_for(
                demand.research_retry_barrier.request_id
            )
            if not isinstance(barrier_slot, GoalSlot):
                raise CompileError(
                    f"RESEARCH-BARRIER-BINDING: research retry barrier for "
                    f"'{demand.name}' resolved to '{type(barrier_slot).__name__}', expected GoalSlot"
                )
            out.append(
                f"(defconst research-retry-barrier-{demand.name} "
                f"{barrier_slot.id.value})"
            )

    for request_id, _request in sorted(
        arbitration_requests.items(),
        key=lambda item: (item[0].owner.source_unit, item[0].purpose),
    ):
        slot = bindings.binding_for(request_id)
        conflict_class = request_id.purpose.split(":", 1)[1]
        out.append(f"(defconst {_claim_name(conflict_class)} {slot.id.value})")

    out.append("")

    if duc_plan is not None and not duc_plan.empty:
        out.append("; Native DUC execution plan")
        output_requests = {
            request.site_key: request
            for request in duc_plan.output_requests
        }
        input_requests: dict[tuple[str, str, int], list] = {}
        for request in duc_plan.input_requests:
            input_requests.setdefault(
                (
                    request.rule_identity,
                    request.section,
                    request.expression_index,
                ),
                [],
            ).append(request)

        def _render_duc_expression(section: str, expression_index: int, expression) -> str:
            request = output_requests.get(
                (current_rule.identity, section, expression_index)
            )
            readers = input_requests.get(
                (current_rule.identity, section, expression_index), ()
            )
            if request is None and not readers:
                return expression.source

            arguments = list(expression.args)
            if request is not None:
                binding = bindings.binding_for(request.request.request_id)
                if isinstance(binding, GoalSpan):
                    output_goal = binding.start.value
                elif isinstance(binding, GoalSlot):
                    output_goal = binding.id.value
                else:
                    raise CompileError(
                        f"EMITTER-DUC-GOAL-OUTPUT: output '{request.site_key}' "
                        f"resolved to '{type(binding).__name__}', expected GoalSlot or GoalSpan"
                    )
                if request.argument_index >= len(arguments):
                    raise CompileError(
                        f"EMITTER-DUC-GOAL-OUTPUT: output '{request.site_key}' "
                        "argument index is outside the expression"
                    )
                arguments[request.argument_index] = str(output_goal)
            for reader in readers:
                writer_binding = bindings.binding_for(reader.source)
                if not isinstance(writer_binding, GoalSlot):
                    raise CompileError(
                        f"EMITTER-DUC-GOAL-INPUT: input '{reader.site_key}' "
                        f"resolved to '{type(writer_binding).__name__}', expected GoalSlot"
                    )
                if reader.argument_index >= len(arguments):
                    raise CompileError(
                        f"EMITTER-DUC-GOAL-INPUT: input '{reader.site_key}' "
                        "argument index is outside the expression"
                    )
                arguments[reader.argument_index] = str(writer_binding.id.value)
            return f"({expression.head} {' '.join(str(arg) for arg in arguments)})"

        for current_rule in duc_plan.rules:
            out.append(f"; Native DUC rule: {current_rule.identity}")
            out.append("(defrule")
            for expression_index, expression in enumerate(current_rule.facts):
                out.append(
                    f"    {_render_duc_expression('FACT', expression_index, expression)}"
                )
            out.append("=>")
            for expression_index, expression in enumerate(current_rule.actions):
                out.append(
                    f"    {_render_duc_expression('ACTION', expression_index, expression)}"
                )
            out += [")", ""]

    if native_attack_plan is not None and not native_attack_plan.empty:
        out.append("; Native attack lifecycle plan")
        attack_sn_aliases = sorted(
            {
                attachment.native_strategic_number_id
                for attachment in native_attack_plan.strategic_number_action_attachments
            }
        )
        existing_defconsts = _defconst_bindings(out)
        for native_id in attack_sn_aliases:
            alias = f"sn-native-{native_id}"
            existing_value = existing_defconsts.get(alias)
            if existing_value is not None:
                if existing_value != str(native_id):
                    raise CompileError(
                        f"EMITTER-SN-ALIAS-CONFLICT: defconst '{alias}' "
                        f"is already bound to {existing_value}, expected {native_id}"
                    )
                continue
            out.append(f"(defconst {alias} {native_id})")
            existing_defconsts[alias] = str(native_id)
        if attack_sn_aliases:
            out.append("")

        goal_inputs = {
            request.site_key: request
            for request in native_attack_plan.goal_input_requests
        }

        def _render_attack_expression(rule_identity, section, expression_index, expression):
            request = goal_inputs.get((rule_identity, section, expression_index, 0))
            if request is None:
                return expression.source
            binding = bindings.binding_for(request.request.request_id)
            if not isinstance(binding, GoalSlot):
                raise CompileError(
                    f"EMITTER-ATTACK-GOAL-INPUT: input '{request.site_key}' "
                    f"resolved to '{type(binding).__name__}', expected GoalSlot"
                )
            if request.argument_index >= len(expression.args):
                raise CompileError(
                    f"EMITTER-ATTACK-GOAL-INPUT: input '{request.site_key}' "
                    "argument index is outside the expression"
                )
            arguments = list(expression.args)
            arguments[request.argument_index] = str(binding.id.value)
            return f"({expression.head} {' '.join(str(arg) for arg in arguments)})"
        attachments_by_rule: dict[str, dict[int, list]] = {}
        control_state_names = (
            {state.identifier for state in control_plan.states}
            if control_plan is not None
            else set()
        )
        if control_plan is not None:
            missing_activation_states = tuple(
                sorted(
                    {
                        attachment.activation_state_name
                        for attachment in native_attack_plan.strategic_number_action_attachments
                        if attachment.activation_state_name not in control_state_names
                    }
                )
            )
            if missing_activation_states:
                raise CompileError(
                    "EMITTER-SN-ACTION-ACTIVATION: ACTION Strategic Number "
                    "attachment references activation state(s) missing from "
                    f"the native control plan: {', '.join(missing_activation_states)}"
                )

        for attachment in native_attack_plan.strategic_number_action_attachments:
            assert attachment.owned_rule_identity is not None
            assert attachment.action_index is not None
            attachments_by_rule.setdefault(
                attachment.owned_rule_identity, {}
            ).setdefault(attachment.action_index, []).append(attachment)

        for rule in native_attack_plan.rules:
            out.append(f"; Native attack rule: {rule.identity}")
            out.append("(defrule")
            out.extend(
                f"    {_render_attack_expression(rule.identity, 'FACT', index, fact)}"
                for index, fact in enumerate(rule.facts)
            )
            out.append("=>")
            for action_index, action in enumerate(rule.actions):
                for attachment in attachments_by_rule.get(rule.identity, {}).get(
                    action_index, ()
                ):
                    if attachment.activation_state_name in control_state_names:
                        out.append(
                            f"    (set-goal {attachment.activation_state_name} 1)"
                        )
                    out.append(
                        f"    (set-strategic-number sn-native-"
                        f"{attachment.native_strategic_number_id} {attachment.value})"
                    )
                out.append(
                    f"    {_render_attack_expression(rule.identity, 'ACTION', action_index, action)}"
                )
            out += [")", ""]

    if escrow_plan is not None and not escrow_plan.empty:
        if isinstance(escrow_plan, NativeEscrowPolicyPlan):
            out.append("; Native escrow policy plan")
            current_rule_order = None
            for operation in (
                operation
                for operation in escrow_plan.operations
                if operation.target_demand is None
            ):
                if operation.rule_order != current_rule_order:
                    if current_rule_order is not None:
                        out += [")", ""]
                    current_rule_order = operation.rule_order
                    out.append(
                        f"; Native escrow policy rule: {current_rule_order}"
                    )
                    out += ["(defrule", "    (true)", "=>"]
                assert operation.percentage is not None
                out.append(
                    f"    (set-escrow-percentage {operation.resource} "
                    f"{operation.percentage})"
                )
            if current_rule_order is not None:
                out += [")", ""]
        else:
            out.append("; Native escrow release plan")
            current_rule_order = None
            for operation in escrow_plan.operations:
                if operation.rule_order != current_rule_order:
                    if current_rule_order is not None:
                        out += [")", ""]
                    current_rule_order = operation.rule_order
                    out.append(
                        f"; Native escrow release rule: {current_rule_order}"
                    )
                    out += ["(defrule", "    (true)", "=>"]
                out.append(f"    (release-escrow {operation.resource})")
            if current_rule_order is not None:
                out += [")", ""]

    if control_plan is not None:
        out.append("; Native persistent control plane")
        emitted_defconsts = _defconst_bindings(out)
        for state in sorted(control_plan.states, key=lambda item: item.identifier):
            binding = bindings.binding_for(state.request.request_id)
            if isinstance(binding, GoalSlot):
                value = binding.id.value
            elif isinstance(binding, StrategicNumberSlot):
                value = binding.id
            elif isinstance(binding, TimerSlot):
                value = binding.id
            else:
                raise CompileError(
                    f"CONTROL-PLANE-BINDING: state '{state.identifier}' resolved to unsupported "
                    f"binding type '{type(binding).__name__}'"
                )
            existing_value = emitted_defconsts.get(state.identifier)
            if existing_value is not None:
                if (
                    isinstance(binding, StrategicNumberSlot)
                    and state.identifier == f"sn-native-{binding.id}"
                    and existing_value == str(binding.id)
                ):
                    continue
                raise CompileError(
                    f"CONTROL-PLANE-SYMBOL: duplicate emitted defconst "
                    f"'{state.identifier}'"
                )
            emitted_defconsts[state.identifier] = str(value)
            out.append(f"(defconst {state.identifier} {value})")

        out.append("")
        for rule in control_plan.rules:
            out.append(f"; Native control rule: {rule.identity}")
            out.append("(defrule")
            out.extend(f"    {fact.source}" for fact in rule.facts)
            out.append("=>")
            out.extend(f"    {action.source}" for action in rule.actions)
            out += [")", ""]

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

    construction_barrier_demands = tuple(
        demand for demand in demands if demand.construction_retry_barrier is not None
    )
    if construction_barrier_demands:
        out.append("; Per-pass construction retry barriers")
        for demand in construction_barrier_demands:
            out += [
                "(defrule",
                "    (true)",
                "=>",
                f"    (set-goal construction-retry-barrier-{demand.name} 0)",
                ")",
                "",
            ]

    production_barrier_demands = tuple(
        demand for demand in demands if demand.production_lifecycle is not None
    )
    if production_barrier_demands:
        out.append("; Per-pass production retry barriers")
        for demand in production_barrier_demands:
            out += [
                "(defrule",
                "    (true)",
                "=>",
                f"    (set-goal production-retry-barrier-{demand.name} 0)",
                ")",
                "",
            ]

    research_barrier_demands = tuple(
        demand for demand in demands if demand.research_retry_barrier is not None
    )
    if research_barrier_demands:
        out.append("; Per-pass research retry barriers")
        for demand in research_barrier_demands:
            out += [
                "(defrule",
                "    (true)",
                "=>",
                f"    (set-goal research-retry-barrier-{demand.name} 0)",
                ")",
                "",
            ]

    if demands:
        out.append("; Demand initialization")
        for start in range(0, len(demands), INITIALIZATION_CHUNK):
            chunk = demands[start : start + INITIALIZATION_CHUNK]
            out += ["(defrule", "    (true)", "=>"]
            for demand in chunk:
                out.append(
                    f"    (set-goal demand-{demand.name} "
                    f"{encoded[demand.name].active.value})"
                )
            out.append("    (disable-self)")
            out += [")", ""]

    for demand in demands:
        slot = bindings.binding_for(demand.lifecycle.slot.request_id)
        lifecycle = encoded[demand.name]
        research = demand.research_lifecycle
        if demand.invalidation is not None:
            out += [
                f"; Invalidation: {demand.name} | ACTIVE / ISSUED / PENDING -> CANCELLED",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.active.value})",
                "        (or",
                f"            (goal demand-{demand.name} {lifecycle.issued.value})",
                f"            (goal demand-{demand.name} {lifecycle.pending.value})",
                "        )",
                "    )",
                f"    {demand.invalidation.expression.source}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.cancelled.value})",
                ")",
                "",
            ]

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
            f"; Issuance failure: {demand.name} | RETAIN-ACTIVE",
            f"; An unsatisfied issuance guard leaves demand-{demand.name} in ACTIVE; it is not PENDING.",
            f"; Release: {demand.name} | COMPLETE -> RELEASED",
            "(defrule",
            f"    (goal demand-{demand.name} {lifecycle.complete.value})",
            f"    {_research_runtime_source(demand.release, research)}",
            "=>",
            f"    (set-goal demand-{demand.name} {lifecycle.released.value})",
            ")",
            "",
        ]

        construction = demand.construction_lifecycle
        production = demand.production_lifecycle
        if construction is not None:
            out += [
                f"; Construction observation: {demand.name}",
                "; Precedence: COMPLETE > FOUNDATION_PENDING > PLACEMENT_PENDING > RETRY",
                f"; Completion witness: {demand.name} | PENDING/ISSUED -> COMPLETE",
            ]
            for transition in construction_transition_rules():
                if transition.kind is ConstructionTransitionKind.COMPLETE:
                    label = "; COMPLETE | ISSUED/PENDING -> COMPLETE"
                    guards = [
                        "    (or",
                        f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                        f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                        "    )",
                        f"    {_research_runtime_source(demand.witness, research)}",
                    ]
                    actions = [
                        f"    (set-goal demand-{demand.name} {lifecycle.complete.value})",
                    ]
                elif transition.kind is ConstructionTransitionKind.FOUNDATION_PENDING:
                    label = f"; Pending admission: {demand.name} | ISSUED/PENDING -> PENDING"
                    guards = [
                        "    (or",
                        f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                        f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                        "    )",
                        f"    (not {_research_runtime_source(demand.witness, research)})",
                        f"    {construction.pending_foundation_fact.source}",
                    ]
                    actions = [
                        f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
                    ]
                elif transition.kind is ConstructionTransitionKind.PLACEMENT_PENDING:
                    label = f"; PLACEMENT_PENDING | ISSUED/PENDING -> PENDING"
                    guards = [
                        "    (or",
                        f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                        f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                        "    )",
                        f"    (not {_research_runtime_source(demand.witness, research)})",
                        f"    (up-pending-objects c: {construction.native_building_id} == 0)",
                        f"    {construction.pending_placement_fact.source}",
                    ]
                    actions = [
                        f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
                    ]
                else:
                    label = "; RETRY | ISSUED/PENDING -> ACTIVE"
                    guards = [
                        "    (or",
                        f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                        f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                        "    )",
                        f"    (not {_research_runtime_source(demand.witness, research)})",
                        f"    (up-pending-objects c: {construction.native_building_id} == 0)",
                        f"    (not {construction.pending_placement_fact.source})",
                    ]
                    actions = [
                        f"    (set-goal demand-{demand.name} {lifecycle.active.value})",
                    ]
                    if demand.construction_retry_barrier is None:
                        raise CompileError(
                            f"CONSTRUCTION-BARRIER-MISSING: construction demand '{demand.name}' "
                            "has no retry barrier storage"
                        )
                    actions.append(
                        f"    (set-goal construction-retry-barrier-{demand.name} 1)"
                    )
                out += [label, "(defrule", *guards, "=>", *actions, ")", ""]
        elif demand.research_lifecycle is not None:
            out += [
                f"; Completion witness: {demand.name} | PENDING/ISSUED -> COMPLETE",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    {_research_runtime_source(demand.witness, research)}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.complete.value})",
                ")",
                "",
                f"; Pending admission: {demand.name} | ISSUED/PENDING -> PENDING",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    (not {_research_runtime_source(demand.witness, research)})",
                f"    {research.pending_fact.source}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
                ")",
                "",
                f"; RETRY | ISSUED/PENDING -> ACTIVE",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    (not {_research_runtime_source(demand.witness, research)})",
                f"    (not {research.pending_fact.source})",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.active.value})",
            ]
            if demand.research_retry_barrier is None:
                raise CompileError(
                    f"RESEARCH-BARRIER-MISSING: research demand '{demand.name}' "
                    "has no retry barrier storage"
                )
            out += [
                f"    (set-goal research-retry-barrier-{demand.name} 1)",
                ")",
                "",
            ]
        elif production is not None:
            out += [
                f"; Completion witness: {demand.name} | PENDING/ISSUED -> COMPLETE",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    {_research_runtime_source(demand.witness, research)}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.complete.value})",
                ")",
                "",
                f"; Pending admission: {demand.name} | ISSUED/PENDING -> PENDING",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    (not {_research_runtime_source(demand.witness, research)})",
                f"    {production.pending_fact.source}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
                ")",
                "",
                f"; RETRY | ISSUED/PENDING -> ACTIVE",
                "(defrule",
                "    (or",
                f"        (goal demand-{demand.name} {lifecycle.issued.value})",
                f"        (goal demand-{demand.name} {lifecycle.pending.value})",
                "    )",
                f"    (not {_research_runtime_source(demand.witness, research)})",
                f"    (not {production.pending_fact.source})",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.active.value})",
            ]
            if production.retry_barrier is None:
                raise CompileError(
                    f"PRODUCTION-BARRIER-MISSING: production demand '{demand.name}' "
                    "has no retry barrier storage"
                )
            out += [
                f"    (set-goal production-retry-barrier-{demand.name} 1)",
                ")",
                "",
            ]
        else:
            out += [
                f"; Completion witness: {demand.name} | PENDING -> COMPLETE",
                "(defrule",
                f"    (goal demand-{demand.name} {lifecycle.pending.value})",
                f"    {_research_runtime_source(demand.witness, research)}",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.complete.value})",
                ")",
                "",
                f"; Pending admission: {demand.name} | ISSUED -> PENDING",
                "(defrule",
                f"    (goal demand-{demand.name} {lifecycle.issued.value})",
                "=>",
                f"    (set-goal demand-{demand.name} {lifecycle.pending.value})",
                ")",
                "",
            ]

        out += [
            f"; Action issuance: {demand.name} | ACTIVE -> ISSUED",
            "(defrule",
            f"    (goal demand-{demand.name} {lifecycle.active.value})",
            f"    (not {_research_runtime_source(demand.witness, research)})",
        ]

        if construction is not None:
            out += [
                f"    (goal construction-retry-barrier-{demand.name} 0)",
                f"    (up-pending-objects c: {construction.native_building_id} == 0)",
                f"    (not {construction.pending_placement_fact.source})",
            ]

        if production is not None:
            out += [
                f"    (goal production-retry-barrier-{demand.name} 0)",
                f"    (not {production.pending_fact.source})",
            ]

        if demand.research_lifecycle is not None:
            out += [
                f"    (goal research-retry-barrier-{demand.name} 0)",
                f"    (not {demand.research_lifecycle.pending_fact.source})",
            ]

        out += [
            f"    (not {_research_runtime_source(demand.release, research)})",
        ]

        request = demand.action.arbitration_request
        if request is not None:
            conflict_class = request.request_id.purpose.split(":", 1)[1]
            out.append(f"    (goal {_claim_name(conflict_class)} 0)")

        out.extend(
            (
                f"    {_research_runtime_source(requirement.expression, research)}"
                if demand.research_lifecycle is not None
                else f"    {requirement.expression.source}"
            )
            for requirement in demand.requirements
        )
        out.extend(
            (
                f"    {_research_runtime_source(gate, research)}"
                if demand.research_lifecycle is not None
                else f"    {gate.source}"
            )
            for gate in demand.action_witness_gates
        )
        out += [
            "=>",
        ]
        for operation in targeted_releases.get(demand.identity, ()):
            out.append(f"    (release-escrow {operation.resource})")
        out.append(
            (
                f"    {_research_runtime_source(demand.action.expression, research)}"
                if demand.research_lifecycle is not None
                else f"    {demand.action.expression.source}"
            )
        )

        if request is not None:
            conflict_class = request.request_id.purpose.split(":", 1)[1]
            out.append(f"    (set-goal {_claim_name(conflict_class)} 1)")

        out += [
            f"    (set-goal demand-{demand.name} {lifecycle.issued.value})",
            ")",
            "",
        ]

    result = "\n".join(out).rstrip() + "\n"
    _validate_artifact_budget(result)
    return result


