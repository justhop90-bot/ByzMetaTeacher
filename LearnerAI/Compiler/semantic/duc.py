"""Practical DUC abstract-state analysis for native .per rules.

This module is driven by evidence-backed native contracts rather than a new DSL.
It tracks only compiler-visible DUC state and deliberately fails closed when
target lifetime cannot be established.
"""
from __future__ import annotations

from collections import deque
from functools import lru_cache
from dataclasses import dataclass, replace
from hashlib import sha256

from ..ast import Expression
from ..diagnostics import DiagnosticSeverity
from ..ir.duc import (
    DucAnalysisReport,
    DucBranchMerge,
    DucCardinalityRange,
    DucDiagnostic,
    DucExecutionEffect,
    DucFilterPredicate,
    DucFilterSnapshot,
    DucFilterState,
    DucGoalOutputSpan,
    DucGroupFlagState,
    DucGroupOperation,
    DucGroupSizeObservation,
    DucGroupStatus,
    DucGroupState,
    DucListGeneration,
    DucListMutationEffect,
    DucListMutationKind,
    DucLoopWidening,
    DucListKind,
    DucObjectRef,
    DucPointRef,
    DucProvenance,
    DucResetEffect,
    DucResetKind,
    DucSearchListState,
    DucSearchOperation,
    DucSearchCursorDisposition,
    DucSearchFactResult,
    DucSearchIndexResetReason,
    DucSearchIndexState,
    DucSearchResultDisposition,
    DucSearchStateObservation,
    DucSemanticState,
    DucStateKind,
    DucTargetConsumerEffect,
    DucTargetFactObservation,
    DucTargetFactResult,
    DucTargetConsumerMode,
    DucTargetDataObservation,
    DucTargetDataRelation,
    DucTargetKind,
    DucTargetProof,
    DucTargetState,
    DucTargetStatus,
    DucTargetTransition,
    DucVisibility,
)
from ..ir.strategic_number import StrategicNumberMathOp, StrategicNumberOperandKind
from ..primitives.native_hygiene import NativeContractCatalog
from ..primitives.registry import default_native_contract_catalog
from .strategic_number_semantics import (
    StrategicNumberSemanticError,
    evaluate_strategic_number_mutation,
    parse_strategic_number_mutation,
)
from .native_controller_interactions import default_native_controller_interaction_catalog
from .recurrent_execution import (
    RecurrentExecutionReport,
    RecurrentExecutionStatus,
)
from .rule_execution import (
    EffectiveRule,
    RuleAction,
    RuleExecutionReport,
    RulePassBehavior,
)


LOCAL_SEARCHES = frozenset({
    "up-find-local",
    "up-find-status-local",
})
REMOTE_SEARCHES = frozenset({
    "up-find-remote",
    "up-find-status-remote",
    "up-find-resource",
})
FILTER_COMMANDS = frozenset({
    "up-filter-distance",
    "up-filter-exclude",
    "up-filter-garrison",
    "up-filter-include",
    "up-filter-range",
    "up-filter-status",
})
SEARCH_STATE_COMMAND = "up-get-search-state"
SET_OBJECT_TARGET = "up-set-target-object"
SET_OBJECT_ID_TARGET = "up-set-target-by-id"
SET_POINT_TARGET = "up-set-target-point"
OBJECT_TARGET_CONSUMERS = frozenset({"up-target-objects"})
POINT_TARGET_CONSUMERS = frozenset({"up-target-point"})
OBJECT_LIST_MUTATORS = frozenset({"up-clean-search", "up-remove-objects"})
FOCUS_PLAYER_SN = "sn-focus-player-number"
FOCUS_PLAYER_MUTATORS = frozenset({"set-strategic-number", "up-modify-sn"})
DUC_LOOP_WIDENING_LIMIT = 3
DUC_GROUP_COUNT = 20
DUC_GROUP_CAPACITY = 40


@lru_cache(maxsize=1)
def _duc_search_cost_interactions():
    catalog = default_native_controller_interaction_catalog()
    return {
        DucListKind.LOCAL: catalog.resolve("duc-local-search-feeds-target-control"),
        DucListKind.REMOTE: catalog.resolve("duc-remote-search-feeds-target-control"),
    }


def _append_recurrent_search_cost_diagnostic(
    diagnostics: list[DucDiagnostic],
    *,
    rule: EffectiveRule,
    action: RuleAction,
    kind: DucListKind,
    current: DucSearchListState,
    rule_reset_lists: set[DucListKind],
) -> None:
    if (
        rule.pass_behavior is not RulePassBehavior.RECURRENT
        or current.current_generation is None
        or kind in rule_reset_lists
    ):
        return

    cardinality = current.current_generation.cardinality
    if cardinality is None:
        return

    try:
        interaction = _duc_search_cost_interactions()[kind]
    except (KeyError, TypeError, ValueError):
        return

    evidence_cardinality = interaction.cardinality
    performance_class = interaction.performance_class
    if evidence_cardinality is None or performance_class is None:
        return

    diagnostics.append(
        DucDiagnostic(
            "DUC-015",
            DiagnosticSeverity.WARNING.value,
            rule.rule_order,
            (
                f"recurrent {action.expression.head} reuses retained "
                f"{kind.value.lower()} DUC search state with retained cardinality "
                f"upper bound {cardinality.maximum}; native capacity bound is "
                f"{evidence_cardinality.maximum} and AIRef benchmark class is "
                f"{performance_class.value}; performance diagnostic is advisory only"
            ),
            _location(action, rule.source_location),
        )
    )


@dataclass(frozen=True)
class NativeDucResetResolution:
    invalidates_local_list: bool
    invalidates_remote_list: bool
    invalidates_filters: bool
    invalidates_object_target: bool
    invalidates_point_target: bool
    invalidates_local_index: bool
    invalidates_remote_index: bool


def _resolve_duc_reset(contract, arguments: tuple[str, ...]) -> NativeDucResetResolution:
    if contract.reset_kind == DucResetKind.SEARCH_BOTH.value:
        if len(arguments) != 4:
            raise ValueError(
                "up-reset-search requires LocalIndex, LocalList, RemoteIndex, RemoteList"
            )
        return NativeDucResetResolution(
            invalidates_local_list=arguments[1] == "1",
            invalidates_remote_list=arguments[3] == "1",
            invalidates_filters=False,
            invalidates_object_target=False,
            invalidates_point_target=False,
            invalidates_local_index=arguments[0] == "1",
            invalidates_remote_index=arguments[2] == "1",
        )
    if contract.reset_kind in {
        DucResetKind.FILTERS.value,
        DucResetKind.FULL.value,
    }:
        return NativeDucResetResolution(
            invalidates_local_list=contract.invalidates_local_list,
            invalidates_remote_list=contract.invalidates_remote_list,
            invalidates_filters=contract.invalidates_filters,
            invalidates_object_target=contract.invalidates_object_target,
            invalidates_point_target=contract.invalidates_point_target,
            invalidates_local_index=True,
            invalidates_remote_index=True,
        )
    return NativeDucResetResolution(
        invalidates_local_list=contract.invalidates_local_list,
        invalidates_remote_list=contract.invalidates_remote_list,
        invalidates_filters=contract.invalidates_filters,
        invalidates_object_target=contract.invalidates_object_target,
        invalidates_point_target=contract.invalidates_point_target,
        invalidates_local_index=False,
        invalidates_remote_index=False,
    )


def _fingerprint(parts: tuple[str, ...]) -> str:
    return sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _location(action: RuleAction, fallback) -> object:
    return action.expression.location or fallback


def _visibility(current_rule: int, producer_rule: int) -> DucVisibility:
    return (
        DucVisibility.SAME_RULE
        if current_rule == producer_rule
        else DucVisibility.SAME_PASS_LATER_RULE
    )


def _provenance(
    rule: EffectiveRule,
    action: RuleAction,
    *,
    visibility: DucVisibility,
    state_revision: int,
    pass_id: int,
    inputs: tuple[int, ...] = (),
    input_group_generations: tuple[tuple[int, int], ...] = (),
    contract_id: str,
    evidence_ids: tuple[str, ...],
) -> DucProvenance:
    return DucProvenance(
        command=action.expression.head,
        source_location=_location(action, rule.source_location),
        source_instance_id=rule.instance_id,
        source_slice_ordinal=rule.source_slice_ordinal,
        rule_order=rule.rule_order,
        within_rule_order=action.within_rule_order,
        pass_behavior=rule.pass_behavior,
        visible_as=visibility,
        state_revision=state_revision,
        pass_id=pass_id,
        input_state_generations=inputs,
        input_group_generations=input_group_generations,
        semantic_contract_id=contract_id,
        evidence_ids=evidence_ids,
    )


def _canonical_arguments(expression: Expression) -> tuple[str, ...]:
    return tuple(str(argument) for argument in expression.args)


def _target_data_relation(contract_relation: str) -> DucTargetDataRelation:
    return DucTargetDataRelation(contract_relation)


def _target_data_read(
    state: DucSemanticState,
    *,
    rule: EffectiveRule,
    action: RuleAction,
    args: tuple[str, ...],
    contract,
    state_revision: int,
    source_kind: str,
) -> tuple[
    DucSemanticState,
    DucTargetDataObservation | None,
    tuple[DucDiagnostic, ...],
    bool,
    bool,
]:
    command = action.expression.head
    expected_args = 2 if contract.writes_goal else 3
    if len(args) != expected_args:
        return (
            state,
            None,
            (
                DucDiagnostic(
                    "DUC-005",
                    DiagnosticSeverity.ERROR.value,
                    rule.rule_order,
                    (
                        f"{command} requires ObjectData and OutputGoalId"
                        if contract.writes_goal
                        else f"{command} requires ObjectData, compareOp, and Value"
                    ),
                    _location(action, rule.source_location),
                ),
            ),
            True,
            False,
        )

    provenance = _provenance(
        rule,
        action,
        visibility=DucVisibility.SAME_RULE,
        state_revision=state_revision,
        pass_id=state.pass_id,
        inputs=((state.target.generation,) if state.target is not None else ()),
        contract_id=f"duc.target-data.{command}",
        evidence_ids=contract.evidence_ids,
    )
    target = state.target
    diagnostics: list[DucDiagnostic] = []

    if target is None:
        diagnostics.append(
            DucDiagnostic(
                "DUC-005",
                DiagnosticSeverity.ERROR.value,
                rule.rule_order,
                f"{command} requires a previously established object target",
                _location(action, rule.source_location),
            )
        )
        target_validity = DucTargetStatus.UNKNOWN
        target_proof = DucTargetProof.UNKNOWN
    elif target.validity is DucTargetStatus.STALE:
        diagnostics.append(
            DucDiagnostic(
                "DUC-006",
                DiagnosticSeverity.ERROR.value,
                rule.rule_order,
                f"{command} consumes an object target invalidated by later DUC reset state",
                _location(action, rule.source_location),
            )
        )
        target_validity = target.validity
        target_proof = target.proof
    else:
        target_validity = target.validity
        target_proof = target.proof
        if target.validity is DucTargetStatus.UNKNOWN:
            message = (
                f"{command} consumes an object target retained across a pass "
                "without a current-pass re-establishment; target lifetime is unknown"
                if target.proof is DucTargetProof.SYNTACTIC_RETENTION
                else f"{command} has a concrete native object identity, but runtime target liveness is unverified"
                if target.proof is DucTargetProof.NATIVE_ID_PROOF
                else f"{command} consumes an object target whose source-list identity is no longer provable"
            )
            diagnostics.append(
                DucDiagnostic(
                    "DUC-007",
                    DiagnosticSeverity.WARNING.value,
                    rule.rule_order,
                    message,
                    _location(action, rule.source_location),
                )
            )

    relation = _target_data_relation(contract.relation)
    if relation is DucTargetDataRelation.SELECTED_OBJECT_TARGET and target is not None:
        if target.validity is not DucTargetStatus.STALE:
            diagnostics.append(
                DucDiagnostic(
                    "DUC-007",
                    DiagnosticSeverity.WARNING.value,
                    rule.rule_order,
                    (
                        f"{command} reads the selected object's current target; "
                        "target-of-target identity is runtime-dependent and is not modeled as compiler state"
                    ),
                    _location(action, rule.source_location),
                )
            )

    next_state = state
    output_span = None
    if contract.writes_goal:
        goal_id = _int_or_none(args[1])
        if goal_id is None or not contract.output_goal_min <= goal_id <= contract.output_goal_max:
            diagnostics.append(
                DucDiagnostic(
                    "DUC-017",
                    DiagnosticSeverity.ERROR.value,
                    rule.rule_order,
                    (
                        f"{command} OutputGoalId must be within "
                        f"{contract.output_goal_min}..{contract.output_goal_max}"
                    ),
                    _location(action, rule.source_location),
                )
            )
        else:
            output_span, spans = _write_goal_output_span(
                state,
                goal_id=goal_id,
                cardinality=DucCardinalityRange(0, 1),
                provenance=provenance,
                width=contract.output_width,
                minimum_start=contract.output_goal_min,
                maximum_start=contract.output_goal_max,
            )
            next_state = replace(state, goal_output_spans=spans)

    observation = DucTargetDataObservation(
        command=command,
        relation=relation,
        object_data=args[0],
        source_kind=source_kind,
        writes_goal=contract.writes_goal,
        target_validity=target_validity,
        target_proof=target_proof,
        provenance=provenance,
        output_span=output_span,
    )
    return (
        next_state,
        observation,
        tuple(diagnostics),
        True,
        contract.writes_goal and output_span is not None,
    )


def _static_compare(left: int | None, operator: str, right: int | None) -> bool | None:
    if left is None or right is None:
        return None
    operator = operator.removeprefix("c:")
    if operator in {"=", "=="}:
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    return None


def _int_or_none(value: str) -> int | None:
    try:
        return int(value, 10)
    except ValueError:
        return None


def _transition_affects_list(
    transition_contract,
    list_kind: DucListKind,
) -> bool:
    if transition_contract is None or not transition_contract.reset_offset_to_zero:
        return False
    scopes = set(transition_contract.affected_lists)
    return (
        "BOTH" in scopes
        or list_kind.value in scopes
        or "SEARCHED_LIST" in scopes
    )


def _reset_search_index(
    index: DucSearchIndexState,
    reason: DucSearchIndexResetReason,
) -> DucSearchIndexState:
    return replace(
        index,
        offset=0,
        generation=index.generation + 1,
        known=True,
        last_reset_reason=reason,
        cursor_disposition=DucSearchCursorDisposition.RESET_START,
    )


def _focus_player_signature_after_mutation(
    index: DucSearchIndexState,
    action: RuleAction,
) -> str | None:
    command = action.expression.head
    arguments = _canonical_arguments(action.expression)
    if command == "set-strategic-number":
        if len(arguments) != 2 or arguments[0] != FOCUS_PLAYER_SN:
            return index.focus_player_signature
        try:
            return str(int(arguments[1], 10))
        except ValueError:
            return None

    if (
        command != "up-modify-sn"
        or len(arguments) != 3
        or arguments[0] != FOCUS_PLAYER_SN
    ):
        return index.focus_player_signature

    try:
        mutation = parse_strategic_number_mutation(
            action.expression,
        )
    except StrategicNumberSemanticError:
        return None

    if mutation.operand.kind is not StrategicNumberOperandKind.CONSTANT:
        return None

    current = index.focus_player_signature
    if current is None:
        if mutation.operator is StrategicNumberMathOp.ASSIGN:
            return str(int(mutation.operand.value))
        if mutation.operator is StrategicNumberMathOp.NEGATE:
            return str(-int(mutation.operand.value))
        return None

    try:
        result = evaluate_strategic_number_mutation(
            mutation,
            current_value=int(current),
            goals={},
            strategic_numbers={},
        )
    except (StrategicNumberSemanticError, ValueError):
        return None
    return str(result)


def _apply_focus_player_mutation(
    state: DucSemanticState,
    *,
    rule: EffectiveRule,
    action: RuleAction,
    state_revision: int,
    transition_contract,
) -> DucSemanticState:
    command = action.expression.head
    arguments = _canonical_arguments(action.expression)
    if (
        command not in FOCUS_PLAYER_MUTATORS
        or not arguments
        or arguments[0] != FOCUS_PLAYER_SN
    ):
        return state

    previous_index = state.remote_list.search_index
    next_signature = _focus_player_signature_after_mutation(
        previous_index,
        action,
    )
    previous_signature = previous_index.focus_player_signature
    proven_unchanged = (
        previous_signature is not None
        and next_signature is not None
        and previous_signature == next_signature
    )
    provenance = _provenance(
        rule,
        action,
        visibility=DucVisibility.SAME_RULE,
        state_revision=state_revision,
        pass_id=state.pass_id,
        inputs=(previous_index.generation,),
        contract_id="duc.search-index.focus-player",
        evidence_ids=(),
    )
    if proven_unchanged or not _transition_affects_list(
        transition_contract,
        DucListKind.REMOTE,
    ):
        updated_index = replace(
            previous_index,
            focus_player_signature=next_signature,
            focus_player_provenance=provenance,
        )
    else:
        updated_index = replace(
            _reset_search_index(
                previous_index,
                DucSearchIndexResetReason.FOCUS_PLAYER_CHANGED,
            ),
            focus_player_signature=next_signature,
            focus_player_provenance=provenance,
        )
    return replace(
        state,
        remote_list=replace(
            state.remote_list,
            search_index=updated_index,
        ),
    )


def _prepare_search_index_for_query(
    index: DucSearchIndexState,
    query_signature: tuple[str, ...],
    *,
    list_kind: DucListKind,
    transition_contract,
) -> tuple[
    DucSearchIndexState,
    Optional[DucSearchIndexResetReason],
    Optional[int],
    DucSearchCursorDisposition,
]:
    reset_reason = index.last_reset_reason
    prepared = index
    if (
        index.query_signature is not None
        and index.query_signature != query_signature
        and _transition_affects_list(transition_contract, list_kind)
    ):
        prepared = _reset_search_index(
            index,
            DucSearchIndexResetReason.QUERY_CHANGED,
        )
        reset_reason = DucSearchIndexResetReason.QUERY_CHANGED
    cursor_before = prepared.cursor_disposition
    if cursor_before is DucSearchCursorDisposition.RESET_START and prepared.offset != 0:
        prepared = replace(
            prepared,
            offset=0,
            known=True,
        )
    index_before = prepared.offset
    after_search = replace(
        prepared,
        query_signature=query_signature,
        last_reset_reason=None,
    )
    return after_search, reset_reason, index_before, cursor_before


def _zero_cardinality() -> DucCardinalityRange:
    return DucCardinalityRange(0, 0)


def _search_cardinality(
    current: DucListGeneration | None,
    *,
    capacity: int,
    guaranteed_empty: bool = False,
) -> tuple[DucCardinalityRange, DucCardinalityRange]:
    previous = (
        current.cardinality
        if current is not None and current.cardinality is not None
        else DucCardinalityRange(0, 0)
    )
    available_maximum = max(0, capacity - previous.minimum)
    maximum_added = available_maximum
    last_search = (
        DucCardinalityRange(0, 0)
        if guaranteed_empty
        else DucCardinalityRange(0, maximum_added)
    )
    total = DucCardinalityRange(
        previous.minimum,
        min(capacity, previous.maximum + last_search.maximum),
    )
    return total, last_search


def _search_cursor_transition(
    prepared_index: DucSearchIndexState,
    *,
    guaranteed_empty: bool,
    blocked_by_capacity: bool,
) -> tuple[
    DucSearchIndexState,
    DucSearchCursorDisposition,
    DucSearchResultDisposition,
]:
    if blocked_by_capacity:
        disposition = DucSearchCursorDisposition.BLOCKED_BY_CAPACITY
        return (
            replace(
                prepared_index,
                cursor_disposition=disposition,
            ),
            disposition,
            DucSearchResultDisposition.GUARANTEED_EMPTY,
        )
    if prepared_index.path_ambiguous:
        disposition = DucSearchCursorDisposition.PATH_AMBIGUOUS
        return (
            replace(
                prepared_index,
                offset=None,
                known=False,
                cursor_disposition=disposition,
            ),
            disposition,
            DucSearchResultDisposition.RUNTIME_DEPENDENT,
        )
    if guaranteed_empty:
        disposition = DucSearchCursorDisposition.AT_END
        return (
            replace(
                prepared_index,
                offset=None,
                known=False,
                cursor_disposition=disposition,
            ),
            disposition,
            DucSearchResultDisposition.GUARANTEED_EMPTY,
        )
    disposition = DucSearchCursorDisposition.RUNTIME_ADVANCED
    return (
        replace(
            prepared_index,
            offset=None,
            known=False,
            cursor_disposition=disposition,
        ),
        disposition,
        DucSearchResultDisposition.RUNTIME_DEPENDENT,
    )


def _preceding_index_can_match(
    target_index: int | None,
    operator: str,
    compare_value: int | None,
) -> bool | None:
    if target_index is None or compare_value is None:
        return None
    operator = operator.removeprefix("c:")
    if target_index <= 0:
        return False
    last_preceding = target_index - 1
    if operator in {"=", "=="}:
        return 0 <= compare_value <= last_preceding
    if operator == "!=":
        if target_index == 1:
            return compare_value != 0
        return True
    if operator == ">":
        return last_preceding > compare_value
    if operator == ">=":
        return last_preceding >= compare_value
    if operator == "<":
        return compare_value > 0
    if operator == "<=":
        return compare_value >= 0
    return None


def _mutate_list_generation(
    state: DucSearchListState,
    *,
    command: str,
    arguments: tuple[str, ...],
    mutation_kind: DucListMutationKind,
) -> DucSearchListState:
    generation = state.current_generation
    if generation is None:
        return state
    previous_fingerprint = generation.content_fingerprint or ""
    fingerprint = _fingerprint(
        (
            "mutation",
            previous_fingerprint,
            command,
            *arguments,
        )
    )
    cardinality = (
        generation.cardinality
        if mutation_kind is DucListMutationKind.SORT
        else None
    )
    updated = replace(
        generation,
        cardinality=cardinality,
        content_fingerprint=fingerprint,
    )
    return _list_state(
        state.list_kind,
        state,
        updated,
        next_generation=state.next_generation,
        path_ambiguous=state.path_ambiguous,
        generation_variants=(),
    )


def _target_with_unstable_index(target: DucTargetState) -> DucTargetState:
    return replace(
        target,
        object_refs=tuple(
            replace(ref, index_stable=False)
            for ref in target.object_refs
        ),
    )


def _target_after_list_mutation(
    target: DucTargetState | None,
    *,
    list_kind: DucListKind,
    mutation_kind: DucListMutationKind,
    object_data: str,
    compare_operator: str | None,
    compare_value: str | None,
) -> tuple[DucTargetState | None, DucTargetTransition]:
    if target is None or target.kind is not DucTargetKind.OBJECT:
        return target, DucTargetTransition.UNCHANGED
    if not target.object_refs or target.object_refs[0].list_kind is not list_kind:
        return target, DucTargetTransition.UNCHANGED
    if target.validity is DucTargetStatus.STALE:
        return target, DucTargetTransition.STALE
    if target.validity is DucTargetStatus.UNKNOWN:
        return target, DucTargetTransition.UNKNOWN

    object_ref = target.object_refs[0]
    target_index = object_ref.list_index

    if mutation_kind is DucListMutationKind.SORT:
        if object_ref.list_kind is None or object_ref.native_object_id is not None:
            return target, DucTargetTransition.UNCHANGED
        return (
            replace(
                _target_with_unstable_index(target),
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.UNKNOWN,
            ),
            DucTargetTransition.UNKNOWN,
        )

    if mutation_kind is DucListMutationKind.DEDUPE:
        return (
            replace(
                _target_with_unstable_index(target),
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.UNKNOWN,
            ),
            DucTargetTransition.UNKNOWN,
        )

    if (
        object_data != "-1"
        or compare_operator is None
        or compare_value is None
        or not object_ref.index_stable
    ):
        return (
            replace(
                _target_with_unstable_index(target),
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.UNKNOWN,
            ),
            DucTargetTransition.UNKNOWN,
        )

    result = _static_compare(target_index, compare_operator, _int_or_none(compare_value))
    if result is True:
        return (
            replace(
                _target_with_unstable_index(target),
                validity=DucTargetStatus.STALE,
                proof=DucTargetProof.UNKNOWN,
            ),
            DucTargetTransition.STALE,
        )
    if result is False:
        preceding_matches = _preceding_index_can_match(
            target_index,
            compare_operator or "",
            _int_or_none(compare_value),
        )
        if preceding_matches is True:
            return _target_with_unstable_index(target), DucTargetTransition.UNCHANGED
        if preceding_matches is False:
            return target, DucTargetTransition.UNCHANGED
        return (
            replace(
                _target_with_unstable_index(target),
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.UNKNOWN,
            ),
            DucTargetTransition.UNKNOWN,
        )

    return (
        replace(
            _target_with_unstable_index(target),
            validity=DucTargetStatus.UNKNOWN,
            proof=DucTargetProof.UNKNOWN,
        ),
        DucTargetTransition.UNKNOWN,
    )


def _list_state(
    kind: DucListKind,
    state: DucSearchListState,
    generation: DucListGeneration | None,
    *,
    next_generation: int | None = None,
    path_ambiguous: bool = False,
    generation_variants: tuple[DucListGeneration, ...] = (),
    search_index: DucSearchIndexState | None = None,
) -> DucSearchListState:
    return DucSearchListState(
        list_kind=kind,
        current_generation=generation,
        next_generation=state.next_generation if next_generation is None else next_generation,
        initialized=generation is not None,
        path_ambiguous=path_ambiguous,
        generation_variants=generation_variants,
        search_index=state.search_index if search_index is None else search_index,
    )


def _empty_groups() -> tuple[DucGroupState, ...]:
    return tuple(
        DucGroupState(
            group_id=group_id,
            generation=0,
            cardinality=DucCardinalityRange(0, 0),
            validity=DucGroupStatus.EMPTY,
        )
        for group_id in range(DUC_GROUP_COUNT)
    )


def _group_state(state: DucSemanticState, group_id: int) -> DucGroupState:
    return state.groups[group_id]


def _replace_group(state: DucSemanticState, group: DucGroupState) -> DucSemanticState:
    groups = list(state.groups)
    groups[group.group_id] = group
    return replace(state, groups=tuple(groups))


def _group_id_from_args(
    args: tuple[str, ...],
    *,
    command: str,
    index: int = -1,
) -> int | None:
    if not args:
        return None
    try:
        group_id = int(args[index], 10)
    except (IndexError, ValueError):
        return None
    if not 0 <= group_id < DUC_GROUP_COUNT:
        raise ValueError(f"{command} group id must be within 0..19")
    return group_id


def _write_goal_output_span(
    state: DucSemanticState,
    *,
    goal_id: int,
    cardinality: DucCardinalityRange,
    provenance: DucProvenance,
    width: int = 1,
    minimum_start: int = 1,
    maximum_start: int = 16000,
) -> tuple[DucGoalOutputSpan, tuple[DucGoalOutputSpan, ...]]:
    if not minimum_start <= goal_id <= maximum_start:
        raise ValueError(
            f"DUC Goal output span permits starts {minimum_start}..{maximum_start}, got {goal_id}"
        )
    previous = next(
        (
            span
            for span in state.goal_output_spans
            if span.start_goal_id == goal_id
        ),
        None,
    )
    span = DucGoalOutputSpan(
        start_goal_id=goal_id,
        width=width,
        generation=(previous.generation + 1 if previous is not None else 1),
        overwritten_generation=(previous.generation if previous is not None else None),
        overwritten_provenance=(previous.provenance if previous is not None else None),
        provenance=provenance,
        cardinality=cardinality,
        pass_id=state.pass_id,
    )
    remaining = tuple(
        existing
        for existing in state.goal_output_spans
        if existing.start_goal_id != goal_id
    )
    return span, tuple(sorted((*remaining, span), key=lambda item: item.start_goal_id))


def _group_create_bounds(args: tuple[str, ...]) -> tuple[int | None, int | None]:
    def decode(value: str, special_zero: int | None = None) -> int | None:
        if special_zero is not None and value == "0":
            return special_zero
        try:
            return int(value, 10)
        except ValueError:
            return None

    start_index = decode(args[0], 0)
    requested_max = decode(args[1], DUC_GROUP_CAPACITY)
    if requested_max is not None:
        requested_max = max(0, min(requested_max, DUC_GROUP_CAPACITY))
    return start_index, requested_max


def _group_cardinality(
    generation: DucListGeneration,
    *,
    start_index: int | None,
    requested_max_objects: int | None,
) -> DucCardinalityRange:
    if start_index is None or requested_max_objects is None or generation.cardinality is None:
        return DucCardinalityRange(0, DUC_GROUP_CAPACITY)
    minimum = max(0, generation.cardinality.minimum - start_index)
    maximum = max(0, generation.cardinality.maximum - start_index)
    return DucCardinalityRange(
        min(requested_max_objects, minimum, DUC_GROUP_CAPACITY),
        min(requested_max_objects, maximum, DUC_GROUP_CAPACITY),
    )


def _group_validity(
    cardinality: DucCardinalityRange,
    *,
    path_ambiguous: bool,
) -> DucGroupStatus:
    if cardinality.maximum == 0:
        return DucGroupStatus.EMPTY
    if path_ambiguous or cardinality.minimum == 0:
        return DucGroupStatus.UNKNOWN
    return DucGroupStatus.VALID


def _search_list_proven_empty(state: DucSearchListState) -> bool:
    generation = state.current_generation
    return (
        generation is not None
        and generation.cardinality is not None
        and generation.cardinality.maximum == 0
        and not state.path_ambiguous
    )


def _empty_state(pass_id: int = 0) -> DucSemanticState:
    return DucSemanticState(
        local_list=DucSearchListState(DucListKind.LOCAL, None, 1, False),
        remote_list=DucSearchListState(
            DucListKind.REMOTE,
            None,
            1,
            False,
            search_index=replace(
                DucSearchIndexState(),
                focus_player_signature="0",
            ),
        ),
        filters=DucFilterState(0, (), "", True, False, None),
        target=None,
        point_target=None,
        state_revision=0,
        pass_id=pass_id,
        groups=_empty_groups(),
        goal_output_spans=(),
    )


def _apply_duc_search(
    state: DucSemanticState,
    *,
    rule: EffectiveRule,
    action: RuleAction,
    args: tuple[str, ...],
    search_contract,
    query_transition_contract,
    state_revision: int,
    rule_reset_lists: set[DucListKind],
    source_kind: str,
) -> tuple[
    DucSemanticState,
    DucSearchOperation,
    tuple[DucDiagnostic, ...],
]:
    """Apply one native find operation without fabricating runtime scan positions.

    The index is a scan frontier. A normal search advances it, but the exact
    numeric endpoint depends on the runtime object universe and visibility.
    Known end-of-scan and known-full-list states are the only statically
    guaranteed zero-result cases in this model.
    """
    command = action.expression.head
    diagnostics: list[DucDiagnostic] = []
    kind = DucListKind(search_contract.list_kind)
    current = state.local_list if kind is DucListKind.LOCAL else state.remote_list

    if source_kind == "FACT" and not search_contract.supports_fact:
        diagnostics.append(
            DucDiagnostic(
                "DUC-005",
                DiagnosticSeverity.ERROR.value,
                rule.rule_order,
                f"{command} is not a valid DUC Fact under its native contract",
                _location(action, rule.source_location),
            )
        )
        raise ValueError(f"{command} does not support Fact evaluation")

    if rule.pass_behavior is RulePassBehavior.RECURRENT and current.current_generation is not None:
        if kind not in rule_reset_lists:
            _append_recurrent_search_cost_diagnostic(
                diagnostics,
                rule=rule,
                action=action,
                kind=kind,
                current=current,
                rule_reset_lists=rule_reset_lists,
            )
            diagnostics.append(
                DucDiagnostic(
                    "DUC-008",
                    DiagnosticSeverity.WARNING.value,
                    rule.rule_order,
                    f"recurrent {command} can accumulate results in retained {kind.value.lower()} DUC list generation {current.current_generation.generation}",
                    _location(action, rule.source_location),
                )
            )

    filter_snapshot = DucFilterSnapshot(
        generation=state.filters.generation,
        fingerprint=state.filters.fingerprint,
        predicates=state.filters.predicates,
        provenance=state.filters.last_mutation,
        path_ambiguous=state.filters.path_ambiguous,
    )
    query_signature = args
    (
        prepared_index,
        index_reset_reason,
        index_before,
        cursor_before_disposition,
    ) = _prepare_search_index_for_query(
        current.search_index,
        query_signature,
        list_kind=kind,
        transition_contract=query_transition_contract,
    )
    blocked_by_capacity = (
        current.current_generation is not None
        and current.current_generation.cardinality is not None
        and current.current_generation.cardinality.minimum >= search_contract.capacity
    )
    guaranteed_empty = (
        not blocked_by_capacity
        and index_reset_reason is None
        and cursor_before_disposition is DucSearchCursorDisposition.AT_END
    )
    (
        post_search_index,
        cursor_after_disposition,
        result_disposition,
    ) = _search_cursor_transition(
        prepared_index,
        guaranteed_empty=guaranteed_empty,
        blocked_by_capacity=blocked_by_capacity,
    )
    if filter_snapshot.path_ambiguous:
        diagnostics.append(
            DucDiagnostic(
                "DUC-012",
                DiagnosticSeverity.WARNING.value,
                rule.rule_order,
                f"{command} consumes a retained filter state that differs across control-flow paths",
                _location(action, rule.source_location),
            )
        )

    visible = DucVisibility.SAME_RULE
    list_generation_inputs = tuple(
        sorted(
            {
                generation.generation
                for generation in (
                    *current.generation_variants,
                    *(
                        (current.current_generation,)
                        if current.current_generation is not None
                        else ()
                    ),
                )
            }
        )
    )
    provenance = _provenance(
        rule,
        action,
        visibility=visible,
        state_revision=state_revision,
        pass_id=state.pass_id,
        inputs=list_generation_inputs + (
            state.filters.generation,
            prepared_index.generation,
        ),
        contract_id=f"duc.search.{command}",
        evidence_ids=search_contract.evidence_ids,
    )

    generation_number = current.next_generation
    total_cardinality, last_search_cardinality = _search_cardinality(
        current.current_generation,
        capacity=search_contract.capacity,
        guaranteed_empty=(
            result_disposition is DucSearchResultDisposition.GUARANTEED_EMPTY
        ),
    )
    previous_fingerprint = (
        current.current_generation.content_fingerprint
        if current.current_generation is not None
        else ""
    )
    output_generation = DucListGeneration(
        list_kind=kind,
        generation=generation_number,
        produced_by=provenance,
        cardinality=total_cardinality,
        capacity=search_contract.capacity,
        content_fingerprint=_fingerprint(
            (
                "append-search",
                previous_fingerprint,
                kind.value,
                command,
                *args,
                filter_snapshot.fingerprint,
                str(post_search_index.generation),
                index_reset_reason.value if index_reset_reason is not None else "NONE",
                cursor_before_disposition.value,
                cursor_after_disposition.value,
                result_disposition.value,
            )
        ),
        last_search_cardinality=last_search_cardinality,
    )
    updated_list = _list_state(
        kind,
        current,
        output_generation,
        next_generation=generation_number + 1,
        path_ambiguous=current.path_ambiguous or filter_snapshot.path_ambiguous,
        generation_variants=(),
        search_index=post_search_index,
    )
    if kind is DucListKind.LOCAL:
        state = DucSemanticState(
            updated_list,
            state.remote_list,
            state.filters,
            state.target,
            state.point_target,
            state_revision,
            state.pass_id,
            groups=state.groups,
            goal_output_spans=state.goal_output_spans,
        )
    else:
        state = DucSemanticState(
            state.local_list,
            updated_list,
            state.filters,
            state.target,
            state.point_target,
            state_revision,
            state.pass_id,
            groups=state.groups,
            goal_output_spans=state.goal_output_spans,
        )

    fact_result = (
        DucSearchFactResult.NOT_A_FACT
        if source_kind != "FACT"
        else (
            DucSearchFactResult.GUARANTEED_FALSE
            if (
                result_disposition is DucSearchResultDisposition.GUARANTEED_EMPTY
                and search_contract.returns_false_on_zero_results
            )
            else DucSearchFactResult.RUNTIME_DEPENDENT
        )
    )
    operation = DucSearchOperation(
        command,
        kind,
        action.expression.source,
        args,
        filter_snapshot,
        output_generation,
        visible,
        provenance,
        index_before=index_before,
        index_after=post_search_index.offset,
        index_generation=post_search_index.generation,
        index_reset_reason=index_reset_reason,
        cursor_before_disposition=cursor_before_disposition,
        cursor_after_disposition=cursor_after_disposition,
        result_disposition=result_disposition,
        source_kind=source_kind,
        fact_result=fact_result,
        focus_player_signature=post_search_index.focus_player_signature,
        focus_player_provenance=post_search_index.focus_player_provenance,
    )
    return state, operation, tuple(diagnostics)


def _analyze_target_object_fact(
    state: DucSemanticState,
    *,
    rule: EffectiveRule,
    action: RuleAction,
    args: tuple[str, ...],
    contract,
    state_revision: int,
) -> DucTargetFactObservation:
    provenance = _provenance(
        rule,
        action,
        visibility=DucVisibility.SAME_RULE,
        state_revision=state_revision,
        pass_id=state.pass_id,
        inputs=(
            state.filters.generation,
            state.local_list.current_generation.generation
            if state.local_list.current_generation is not None
            else -1,
            state.remote_list.current_generation.generation
            if state.remote_list.current_generation is not None
            else -1,
        ),
        contract_id="duc.target.object.fact",
        evidence_ids=contract.evidence_ids,
    )
    if len(args) != 3:
        raise ValueError(
            "up-set-target-object requires SearchSource, typeOp, and Index"
        )
    source = (
        DucListKind.LOCAL
        if args[0] == "search-local"
        else DucListKind.REMOTE
        if args[0] == "search-remote"
        else None
    )
    current = (
        state.local_list
        if source is DucListKind.LOCAL
        else state.remote_list
        if source is DucListKind.REMOTE
        else None
    )
    if source is None or current is None or not current.initialized:
        return DucTargetFactObservation(
            command=SET_OBJECT_TARGET,
            result=DucTargetFactResult.GUARANTEED_FALSE,
            target=None,
            provenance=provenance,
        )
    if _search_list_proven_empty(current):
        return DucTargetFactObservation(
            command=SET_OBJECT_TARGET,
            result=DucTargetFactResult.GUARANTEED_FALSE,
            target=None,
            provenance=provenance,
        )
    try:
        index = int(args[2], 10)
    except ValueError:
        return DucTargetFactObservation(
            command=SET_OBJECT_TARGET,
            result=DucTargetFactResult.RUNTIME_DEPENDENT,
            target=None,
            provenance=provenance,
        )
    generation = current.current_generation
    capacity = (
        generation.capacity
        if generation is not None
        else max((item.capacity for item in current.generation_variants), default=0)
    )
    if index < 0 or index >= capacity:
        return DucTargetFactObservation(
            command=SET_OBJECT_TARGET,
            result=DucTargetFactResult.GUARANTEED_FALSE,
            target=None,
            provenance=provenance,
        )
    return DucTargetFactObservation(
        command=SET_OBJECT_TARGET,
        result=DucTargetFactResult.RUNTIME_DEPENDENT,
        target=None,
        provenance=provenance,
    )


def _analyze_duc_linear(
    rules: tuple[EffectiveRule, ...],
    contracts: NativeContractCatalog | None = None,
    *,
    initial_state: DucSemanticState | None = None,
) -> DucAnalysisReport:
    contracts = contracts or default_native_contract_catalog()
    state = initial_state or _empty_state()
    initial_state = state
    states: list[tuple[int, DucSemanticState]] = []
    searches: list[DucSearchOperation] = []
    resets: list[DucResetEffect] = []
    mutations: list[DucListMutationEffect] = []
    groups: list[DucGroupOperation] = []
    group_observations: list[DucGroupSizeObservation] = []
    targets: list[DucTargetState] = []
    target_fact_observations: list[DucTargetFactObservation] = []
    target_consumers: list[DucTargetConsumerEffect] = []
    target_data_observations: list[DucTargetDataObservation] = []
    observations: list[DucSearchStateObservation] = []
    effects: list[DucExecutionEffect] = []
    diagnostics: list[DucDiagnostic] = []

    for rule in rules:
        state_revision = state.state_revision + 1
        rule_reads: set[DucStateKind] = set()
        rule_writes: set[DucStateKind] = set()
        rule_reset_lists: set[DucListKind] = set()

        for fact_index, fact in enumerate(rule.facts):
            fact_action = RuleAction(
                expression=fact,
                within_rule_order=-1 - fact_index,
            )
            fact_args = _canonical_arguments(fact)

            target_data_contract = contracts.duc_target_data_contract(fact.head)
            if target_data_contract is not None:
                (
                    state,
                    target_data_observation,
                    target_data_diagnostics,
                    fact_reads_target,
                    fact_writes_output,
                ) = _target_data_read(
                    state,
                    rule=rule,
                    action=fact_action,
                    args=fact_args,
                    contract=target_data_contract,
                    state_revision=state_revision,
                    source_kind="FACT",
                )
                diagnostics.extend(target_data_diagnostics)
                if target_data_observation is not None:
                    target_data_observations.append(target_data_observation)
                if fact_reads_target:
                    rule_reads.add(DucStateKind.TARGET)
                if fact_writes_output:
                    rule_writes.add(DucStateKind.OUTPUT)
                continue

            fact_target_contract = contracts.duc_target(fact.head)
            if fact_target_contract is not None:
                if not fact_target_contract.supports_fact:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-005",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            f"{fact.head} is not a valid DUC Fact under its native target contract",
                            _location(fact_action, rule.source_location),
                        )
                    )
                elif fact_target_contract.identity_kind == "LIST_INDEX":
                    try:
                        observation = _analyze_target_object_fact(
                            state,
                            rule=rule,
                            action=fact_action,
                            args=fact_args,
                            contract=fact_target_contract,
                            state_revision=state_revision,
                        )
                    except ValueError as exc:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-017",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                str(exc),
                                _location(fact_action, rule.source_location),
                            )
                        )
                    else:
                        target_fact_observations.append(observation)
                        rule_reads.add(DucStateKind.LIST)
                        rule_reads.add(DucStateKind.FILTER)
                continue

            fact_search_contract = contracts.duc_search(fact.head)
            if fact_search_contract is not None:
                try:
                    (
                        state,
                        search_operation,
                        search_diagnostics,
                    ) = _apply_duc_search(
                        state,
                        rule=rule,
                        action=fact_action,
                        args=fact_args,
                        search_contract=fact_search_contract,
                        query_transition_contract=contracts.duc_search_index_transition("QUERY_CHANGE"),
                        state_revision=state_revision,
                        rule_reset_lists=rule_reset_lists,
                        source_kind="FACT",
                    )
                except ValueError as exc:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-017",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            str(exc),
                            _location(fact_action, rule.source_location),
                        )
                    )
                    continue
                diagnostics.extend(search_diagnostics)
                searches.append(search_operation)
                rule_reads.add(DucStateKind.FILTER)
                rule_writes.add(DucStateKind.LIST)

        for action in rule.actions:
            expression = action.expression
            command = expression.head
            args = _canonical_arguments(expression)

            if command in FOCUS_PLAYER_MUTATORS and args and args[0] == FOCUS_PLAYER_SN:
                state = _apply_focus_player_mutation(
                    state,
                    rule=rule,
                    action=action,
                    state_revision=state_revision,
                    transition_contract=contracts.duc_search_index_transition("FOCUS_PLAYER_CHANGE"),
                )
                continue

            search_contract = contracts.duc_search(command)
            filter_contract = contracts.duc_filter(command)
            reset_contract = contracts.duc_reset(command)
            target_contract = contracts.duc_target(command)
            target_data_contract = contracts.duc_target_data_contract(command)
            target_consumer_contract = contracts.duc_target_consumer(command)
            group_contract = contracts.duc_group(command)

            if target_data_contract is not None:
                (
                    state,
                    target_data_observation,
                    target_data_diagnostics,
                    target_data_reads_target,
                    target_data_writes_output,
                ) = _target_data_read(
                    state,
                    rule=rule,
                    action=action,
                    args=args,
                    contract=target_data_contract,
                    state_revision=state_revision,
                    source_kind="ACTION",
                )
                diagnostics.extend(target_data_diagnostics)
                if target_data_observation is not None:
                    target_data_observations.append(target_data_observation)
                if target_data_reads_target:
                    rule_reads.add(DucStateKind.TARGET)
                if target_data_writes_output:
                    rule_writes.add(DucStateKind.OUTPUT)
                continue

            if group_contract is not None:
                operation = group_contract.operation
                try:
                    group_id_index = {
                        "CREATE": 3,
                        "RESET": 1,
                        "SET": 2,
                        "MODIFY_FLAG": 2,
                        "SIZE_FACT": 1,
                        "SIZE_OUTPUT": 1,
                    }.get(operation, -1)
                    group_id = _group_id_from_args(
                        args,
                        command=command,
                        index=group_id_index,
                    )
                    if group_id is None:
                        raise ValueError(f"{command} requires a constant GroupId")

                    if operation == "CREATE":
                        if len(args) != 4:
                            raise ValueError("up-create-group requires 4 arguments")
                        start_index, requested_max = _group_create_bounds(args)
                        previous = _group_state(state, group_id)
                        provenance = _provenance(
                            rule,
                            action,
                            visibility=DucVisibility.SAME_RULE,
                            state_revision=state_revision,
                            pass_id=state.pass_id,
                            inputs=(
                                (state.local_list.current_generation.generation,)
                                if state.local_list.current_generation is not None
                                else ()
                            ),
                            contract_id="duc.group.create",
                            evidence_ids=group_contract.evidence_ids,
                        )
                        generation = previous.generation + 1
                        if state.local_list.current_generation is None:
                            cardinality = DucCardinalityRange(0, 0)
                            validity = DucGroupStatus.EMPTY
                            source_generation = None
                            fingerprint = _fingerprint(("empty-group", str(group_id), str(generation)))
                        else:
                            current = state.local_list.current_generation
                            cardinality = _group_cardinality(
                                current,
                                start_index=start_index,
                                requested_max_objects=requested_max,
                            )
                            validity = _group_validity(
                                cardinality,
                                path_ambiguous=state.local_list.path_ambiguous,
                            )
                            source_generation = current.generation
                            fingerprint = _fingerprint(
                                (
                                    "group-create",
                                    str(group_id),
                                    str(generation),
                                    current.content_fingerprint or "",
                                    str(start_index),
                                    str(requested_max),
                                )
                            )
                        group = DucGroupState(
                            group_id=group_id,
                            generation=generation,
                            cardinality=cardinality,
                            source_list=DucListKind.LOCAL,
                            source_list_generation=source_generation,
                            source_index_start=start_index,
                            requested_max_objects=requested_max,
                            content_fingerprint=fingerprint,
                            provenance=provenance,
                            validity=validity,
                            flag_state=DucGroupFlagState.UNKNOWN,
                            path_ambiguous=state.local_list.path_ambiguous,
                            pass_id=state.pass_id,
                        )
                        state = _replace_group(state, group)
                        groups.append(
                            DucGroupOperation(command, group_id, previous.generation, generation, provenance)
                        )
                        rule_writes.add(DucStateKind.GROUP)
                        continue

                    if operation == "RESET":
                        if len(args) != 2:
                            raise ValueError("up-reset-group requires 2 arguments")
                        previous = _group_state(state, group_id)
                        provenance = _provenance(
                            rule,
                            action,
                            visibility=DucVisibility.SAME_RULE,
                            state_revision=state_revision,
                            pass_id=state.pass_id,
                            contract_id="duc.group.reset",
                            evidence_ids=group_contract.evidence_ids,
                        )
                        group = DucGroupState(
                            group_id=group_id,
                            generation=previous.generation + 1,
                            cardinality=DucCardinalityRange(0, 0),
                            provenance=provenance,
                            validity=DucGroupStatus.EMPTY,
                            flag_state=DucGroupFlagState.UNKNOWN,
                            pass_id=state.pass_id,
                        )
                        state = _replace_group(state, group)
                        groups.append(
                            DucGroupOperation(
                                command,
                                group_id,
                                previous.generation,
                                group.generation,
                                provenance,
                            )
                        )
                        rule_writes.add(DucStateKind.GROUP)
                        continue

                    current_group = _group_state(state, group_id)
                    provenance = _provenance(
                        rule,
                        action,
                        visibility=DucVisibility.SAME_RULE,
                        state_revision=state_revision,
                        pass_id=state.pass_id,
                        inputs=(current_group.generation,),
                        input_group_generations=((group_id, current_group.generation),),
                        contract_id=f"duc.group.{operation.lower()}",
                        evidence_ids=group_contract.evidence_ids,
                    )

                    if operation == "SET":
                        if len(args) != 3:
                            raise ValueError("up-set-group requires 3 arguments")
                        source = (
                            DucListKind.LOCAL
                            if args[0] == "search-local"
                            else DucListKind.REMOTE
                            if args[0] == "search-remote"
                            else None
                        )
                        if source is None:
                            raise ValueError("up-set-group requires search-local or search-remote")
                        current_list = (
                            state.local_list if source is DucListKind.LOCAL else state.remote_list
                        )
                        target = state.target
                        if (
                            target is not None
                            and target.kind is DucTargetKind.OBJECT
                            and target.object_refs
                            and target.object_refs[0].list_kind is source
                        ):
                            target = replace(
                                target,
                                validity=DucTargetStatus.STALE,
                                proof=DucTargetProof.UNKNOWN,
                            )
                        destination_generation = current_list.next_generation
                        destination = DucListGeneration(
                            list_kind=source,
                            generation=destination_generation,
                            produced_by=provenance,
                            cardinality=current_group.cardinality,
                            capacity=240 if source is DucListKind.LOCAL else 40,
                            content_fingerprint=_fingerprint(
                                (
                                    "group-set",
                                    str(group_id),
                                    str(current_group.generation),
                                    current_group.content_fingerprint or "",
                                )
                            ),
                        )
                        destination_list = _list_state(
                            source,
                            current_list,
                            destination,
                            next_generation=destination_generation + 1,
                            path_ambiguous=(
                                current_group.path_ambiguous
                                or current_group.validity is DucGroupStatus.UNKNOWN
                            ),
                        )
                        state = replace(
                            state,
                            local_list=(
                                destination_list
                                if source is DucListKind.LOCAL
                                else state.local_list
                            ),
                            remote_list=(
                                destination_list
                                if source is DucListKind.REMOTE
                                else state.remote_list
                            ),
                            target=target,
                        )
                        groups.append(
                            DucGroupOperation(
                                command,
                                group_id,
                                current_group.generation,
                                current_group.generation,
                                provenance,
                            )
                        )
                        rule_reads.add(DucStateKind.GROUP)
                        rule_writes.update({DucStateKind.LIST, DucStateKind.TARGET})
                        continue

                    if operation == "MODIFY_FLAG":
                        if len(args) != 3:
                            raise ValueError("up-modify-group-flag requires 3 arguments")
                        flag_state = (
                            DucGroupFlagState.SET
                            if args[0] == "1"
                            else DucGroupFlagState.CLEARED
                            if args[0] == "0"
                            else DucGroupFlagState.UNKNOWN
                        )
                        updated = replace(
                            current_group,
                            flag_state=flag_state,
                            provenance=provenance,
                            pass_id=state.pass_id,
                        )
                        state = _replace_group(state, updated)
                        groups.append(
                            DucGroupOperation(
                                command,
                                group_id,
                                current_group.generation,
                                current_group.generation,
                                provenance,
                            )
                        )
                        rule_reads.add(DucStateKind.GROUP)
                        rule_writes.add(DucStateKind.GROUP)
                        continue

                    if operation in {"SIZE_FACT", "SIZE_OUTPUT"}:
                        expected_arity = 4 if operation == "SIZE_FACT" else 3
                        if len(args) != expected_arity:
                            raise ValueError(
                                f"{command} requires {expected_arity} arguments"
                            )
                        output_span = None
                        if operation == "SIZE_OUTPUT":
                            if group_contract.output_width != 1:
                                raise ValueError(
                                    f"{command} requires a width-1 Goal output contract"
                                )
                            output_goal_id = _int_or_none(args[2])
                            if (
                                output_goal_id is None
                                or not group_contract.output_goal_min
                                <= output_goal_id
                                <= group_contract.output_goal_max
                            ):
                                raise ValueError(
                                    f"{command} OutputGoalId must be within "
                                    f"{group_contract.output_goal_min}..{group_contract.output_goal_max}"
                                )
                            output_provenance = _provenance(
                                rule,
                                action,
                                visibility=DucVisibility.SAME_RULE,
                                state_revision=state_revision,
                                pass_id=state.pass_id,
                                inputs=(current_group.generation,),
                                input_group_generations=((group_id, current_group.generation),),
                                contract_id=group_contract.output_contract_id
                                or f"{command}.output-goal",
                                evidence_ids=group_contract.output_evidence_ids
                                or group_contract.evidence_ids,
                            )
                            output_span, output_spans = _write_goal_output_span(
                                state,
                                goal_id=output_goal_id,
                                cardinality=current_group.cardinality,
                                provenance=output_provenance,
                            )
                            state = replace(
                                state,
                                goal_output_spans=output_spans,
                            )
                        group_observations.append(
                            DucGroupSizeObservation(
                                command,
                                group_id,
                                current_group.cardinality,
                                provenance,
                                output_span,
                            )
                        )
                        rule_reads.add(DucStateKind.GROUP)
                        if operation == "SIZE_OUTPUT":
                            rule_writes.add(DucStateKind.OUTPUT)
                        continue

                except ValueError as exc:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-017",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            str(exc),
                            _location(action, rule.source_location),
                        )
                    )
                    continue

            if search_contract is not None:
                try:
                    (
                        state,
                        search_operation,
                        search_diagnostics,
                    ) = _apply_duc_search(
                        state,
                        rule=rule,
                        action=action,
                        args=args,
                        search_contract=search_contract,
                        query_transition_contract=contracts.duc_search_index_transition("QUERY_CHANGE"),
                        state_revision=state_revision,
                        rule_reset_lists=rule_reset_lists,
                        source_kind="ACTION",
                    )
                except ValueError as exc:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-017",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            str(exc),
                            _location(action, rule.source_location),
                        )
                    )
                    continue
                diagnostics.extend(search_diagnostics)
                searches.append(search_operation)
                rule_reads.add(DucStateKind.FILTER)
                rule_writes.add(DucStateKind.LIST)
                continue

            if filter_contract is not None:
                predicate = DucFilterPredicate(
                    command=command,
                    canonical_arguments=args,
                    semantic_identity=f"duc.filter.{command}",
                )
                predicates = state.filters.predicates + (predicate,)
                fingerprint = _fingerprint(
                    tuple(
                        item.semantic_identity + ":" + "".join(item.canonical_arguments)
                        for item in predicates
                    )
                )
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    inputs=(state.filters.generation,),
                    contract_id=f"duc.filter.{command}",
                    evidence_ids=filter_contract.evidence_ids,
                )
                local_list = state.local_list
                remote_list = state.remote_list
                if filter_contract.resets_search_indices:
                    transition_contract = contracts.duc_search_index_transition("FILTER_CHANGE")
                    if _transition_affects_list(transition_contract, DucListKind.LOCAL):
                        local_list = replace(
                            local_list,
                            search_index=_reset_search_index(
                                local_list.search_index,
                                DucSearchIndexResetReason.FILTER_CHANGED,
                            ),
                        )
                    if _transition_affects_list(transition_contract, DucListKind.REMOTE):
                        remote_list = replace(
                            remote_list,
                            search_index=_reset_search_index(
                                remote_list.search_index,
                                DucSearchIndexResetReason.FILTER_CHANGED,
                            ),
                        )
                state = DucSemanticState(
                    local_list,
                    remote_list,
                    DucFilterState(
                        state.filters.generation + 1,
                        predicates,
                        fingerprint,
                        True,
                        True,
                        provenance,
                        state.filters.path_ambiguous,
                    ),
                    state.target,
                    state.point_target,
                    state_revision,
                    state.pass_id,
                    groups=state.groups,
                    goal_output_spans=state.goal_output_spans,
                )
                rule_writes.add(DucStateKind.FILTER)
                continue

            if reset_contract is not None:
                resolution = _resolve_duc_reset(reset_contract, args)
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    inputs=(
                        state.local_list.current_generation.generation
                        if state.local_list.current_generation else 0,
                        state.remote_list.current_generation.generation
                        if state.remote_list.current_generation else 0,
                        state.filters.generation,
                    ),
                    contract_id=f"duc.reset.{command}",
                    evidence_ids=reset_contract.evidence_ids,
                )
                invalidated = []
                local = state.local_list
                remote = state.remote_list
                target = state.target
                point_target = state.point_target
                filters = state.filters
                if resolution.invalidates_local_list:
                    local = _list_state(
                        DucListKind.LOCAL,
                        local,
                        None,
                        next_generation=local.next_generation + 1
                        if local.current_generation else local.next_generation,
                    )
                    invalidated.append(DucListKind.LOCAL)
                    if (
                        target is not None
                        and target.kind is DucTargetKind.OBJECT
                        and target.object_refs
                        and target.object_refs[0].list_kind is DucListKind.LOCAL
                    ):
                        target = DucTargetState(
                            **{**target.__dict__, "validity": DucTargetStatus.STALE, "proof": DucTargetProof.UNKNOWN}
                        )
                if resolution.invalidates_remote_list:
                    remote = _list_state(
                        DucListKind.REMOTE,
                        remote,
                        None,
                        next_generation=remote.next_generation + 1
                        if remote.current_generation else remote.next_generation,
                    )
                    invalidated.append(DucListKind.REMOTE)
                    if (
                        target is not None
                        and target.kind is DucTargetKind.OBJECT
                        and target.object_refs
                        and target.object_refs[0].list_kind is DucListKind.REMOTE
                    ):
                        target = DucTargetState(
                            **{**target.__dict__, "validity": DucTargetStatus.STALE, "proof": DucTargetProof.UNKNOWN}
                        )
                if resolution.invalidates_local_index:
                    local = replace(
                        local,
                        search_index=_reset_search_index(
                            local.search_index,
                            DucSearchIndexResetReason.EXPLICIT,
                        ),
                    )
                if resolution.invalidates_remote_index:
                    remote = replace(
                        remote,
                        search_index=_reset_search_index(
                            remote.search_index,
                            DucSearchIndexResetReason.EXPLICIT,
                        ),
                    )
                if resolution.invalidates_filters:
                    next_filter_generation = (
                        filters.generation + 1
                        if filters.predicates or filters.retained or filters.path_ambiguous
                        else filters.generation
                    )
                    filters = DucFilterState(
                        next_filter_generation,
                        (),
                        "",
                        True,
                        False,
                        provenance,
                    )
                if resolution.invalidates_object_target:
                    target = None
                if resolution.invalidates_point_target:
                    point_target = None
                state = DucSemanticState(
                    local,
                    remote,
                    filters,
                    target,
                    point_target,
                    state_revision,
                    state.pass_id,
                    groups=state.groups,
                    goal_output_spans=state.goal_output_spans,
                )
                reset = DucResetEffect(
                    command,
                    DucResetKind(reset_contract.reset_kind),
                    tuple(invalidated),
                    resolution.invalidates_filters,
                    resolution.invalidates_object_target,
                    resolution.invalidates_point_target,
                    provenance,
                    resolution.invalidates_local_index,
                    resolution.invalidates_remote_index,
                )
                resets.append(reset)
                rule_reset_lists.update(invalidated)
                rule_writes.update({
                    DucStateKind.LIST,
                    DucStateKind.FILTER,
                    DucStateKind.TARGET,
                })
                continue

            if command == SEARCH_STATE_COMMAND:
                generations = tuple(
                    generation
                    for generation in (
                        state.local_list.current_generation.generation if state.local_list.current_generation else None,
                        state.remote_list.current_generation.generation if state.remote_list.current_generation else None,
                    )
                    if generation is not None
                )
                search_state_span_contract = contracts.goal_span_contract(
                    "extended-4-goal-span"
                )
                output_span = None
                if len(args) != 1:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-017",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-get-search-state requires exactly one OutputGoalId",
                            _location(action, rule.source_location),
                        )
                    )
                    continue
                output_goal_id = _int_or_none(args[0])
                if output_goal_id is not None:
                    try:
                        search_state_span_contract.validate_shape(
                            output_goal_id,
                            output_goal_id + search_state_span_contract.width - 1,
                        )
                    except ValueError as exc:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-017",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                str(exc),
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                if not generations:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-001",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-get-search-state reads DUC state before either search list has been initialized",
                            _location(action, rule.source_location),
                        )
                    )
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    inputs=generations,
                    contract_id="duc.output.search-state",
                    evidence_ids=contracts.duc_output_evidence_ids,
                )
                local_generation = state.local_list.current_generation
                remote_generation = state.remote_list.current_generation
                if output_goal_id is not None:
                    combined_cardinality = DucCardinalityRange(
                        (
                            local_generation.cardinality.minimum
                            if local_generation
                            else 0
                        )
                        + (
                            remote_generation.cardinality.minimum
                            if remote_generation
                            else 0
                        ),
                        (
                            local_generation.cardinality.maximum
                            if local_generation
                            else 0
                        )
                        + (
                            remote_generation.cardinality.maximum
                            if remote_generation
                            else 0
                        ),
                    )
                    output_provenance = replace(
                        provenance,
                        semantic_contract_id=search_state_span_contract.identity,
                    )
                    output_span, output_spans = _write_goal_output_span(
                        state,
                        goal_id=output_goal_id,
                        width=search_state_span_contract.width,
                        minimum_start=search_state_span_contract.minimum_start,
                        maximum_start=search_state_span_contract.maximum_start,
                        cardinality=combined_cardinality,
                        provenance=output_provenance,
                    )
                    state = replace(
                        state,
                        goal_output_spans=output_spans,
                    )
                observations.append(
                    DucSearchStateObservation(
                        DucListKind.LOCAL,
                        local_generation.generation if local_generation else None,
                        args[0],
                        (
                            "local_search_count",
                            "local_list_count",
                            "remote_search_count",
                            "remote_list_count",
                        ),
                        _fingerprint(
                            (
                                "search-state",
                                str(local_generation.cardinality if local_generation else _zero_cardinality()),
                                str(local_generation.last_search_cardinality if local_generation and local_generation.last_search_cardinality else _zero_cardinality()),
                                str(remote_generation.cardinality if remote_generation else _zero_cardinality()),
                                str(remote_generation.last_search_cardinality if remote_generation and remote_generation.last_search_cardinality else _zero_cardinality()),
                            )
                        ),
                        provenance,
                        local_total_cardinality=(
                            local_generation.cardinality if local_generation else _zero_cardinality()
                        ),
                        local_last_search_cardinality=(
                            local_generation.last_search_cardinality
                            if local_generation and local_generation.last_search_cardinality
                            else _zero_cardinality()
                        ),
                        remote_total_cardinality=(
                            remote_generation.cardinality if remote_generation else _zero_cardinality()
                        ),
                        remote_last_search_cardinality=(
                            remote_generation.last_search_cardinality
                            if remote_generation and remote_generation.last_search_cardinality
                            else _zero_cardinality()
                        ),
                        local_search_cursor_disposition=(
                            state.local_list.search_index.cursor_disposition
                        ),
                        remote_search_cursor_disposition=(
                            state.remote_list.search_index.cursor_disposition
                        ),
                        output_span=output_span,
                    )
                )
                rule_reads.add(DucStateKind.LIST)
                rule_writes.add(DucStateKind.OUTPUT)
                continue

            if command == "up-get-cost-delta":
                cost_span_contract = contracts.goal_span_contract(
                    "cost-data-4-goal-span"
                )
                if len(args) != 1:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-017",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-get-cost-delta requires exactly one OutputGoalId",
                            _location(action, rule.source_location),
                        )
                    )
                    continue
                output_goal_id = _int_or_none(args[0])
                if output_goal_id is not None:
                    try:
                        cost_span_contract.validate_shape(
                            output_goal_id,
                            output_goal_id + cost_span_contract.width - 1,
                        )
                    except ValueError as exc:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-017",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                str(exc),
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    output_provenance = _provenance(
                        rule,
                        action,
                        visibility=DucVisibility.SAME_RULE,
                        state_revision=state_revision,
                        pass_id=state.pass_id,
                        contract_id=cost_span_contract.identity,
                        evidence_ids=tuple(
                            item.citation_id
                            for item in cost_span_contract.provenance
                        ),
                    )
                    _, output_spans = _write_goal_output_span(
                        state,
                        goal_id=output_goal_id,
                        width=cost_span_contract.width,
                        minimum_start=cost_span_contract.minimum_start,
                        maximum_start=cost_span_contract.maximum_start,
                        cardinality=DucCardinalityRange(0, 1),
                        provenance=output_provenance,
                    )
                    state = replace(
                        state,
                        goal_output_spans=output_spans,
                    )
                rule_writes.add(DucStateKind.OUTPUT)
                continue

            if target_contract is not None:
                if target_contract.identity_kind == "NATIVE_ID":
                    if len(args) != 2:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-set-target-by-id requires typeOp and Id",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    type_op, object_id_operand = args
                    if type_op not in {"c:", "g:", "s:"}:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-set-target-by-id requires typeOp c:, g:, or s:",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    native_object_id = None
                    numeric_id = _int_or_none(object_id_operand)
                    if type_op == "c:" and numeric_id is not None:
                        if numeric_id < 0:
                            diagnostics.append(
                                DucDiagnostic(
                                    "DUC-005",
                                    DiagnosticSeverity.ERROR.value,
                                    rule.rule_order,
                                    "up-set-target-by-id Id must be non-negative",
                                    _location(action, rule.source_location),
                                )
                            )
                            continue
                        native_object_id = str(numeric_id)
                    provenance = _provenance(
                        rule,
                        action,
                        visibility=DucVisibility.SAME_RULE,
                        state_revision=state_revision,
                        pass_id=state.pass_id,
                        contract_id="duc.target.object-id",
                        evidence_ids=target_contract.evidence_ids,
                    )
                    target = DucTargetState(
                        kind=DucTargetKind.OBJECT,
                        generation=state_revision,
                        object_refs=(
                            DucObjectRef(
                                None,
                                None,
                                None,
                                native_object_id,
                                provenance,
                            ),
                        ),
                        source_list_generation=None,
                        source_filter_generation=None,
                        provenance=provenance,
                        validity=DucTargetStatus.UNKNOWN,
                        pass_id=state.pass_id,
                        proof=(
                            DucTargetProof.NATIVE_ID_PROOF
                            if native_object_id is not None
                            else DucTargetProof.UNKNOWN
                        ),
                    )
                    state = DucSemanticState(
                        state.local_list,
                        state.remote_list,
                        state.filters,
                        target,
                        state.point_target,
                        state_revision,
                        state.pass_id,
                        groups=state.groups,
                        goal_output_spans=state.goal_output_spans,
                    )
                    targets.append(target)
                    rule_writes.add(DucStateKind.TARGET)
                    continue

                if command == SET_OBJECT_TARGET:
                    if len(args) != 3:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-set-target-object requires SearchSource, typeOp, and Index",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    source = DucListKind.LOCAL if args[0] == "search-local" else DucListKind.REMOTE if args[0] == "search-remote" else None
                    current = state.local_list if source is DucListKind.LOCAL else state.remote_list if source is DucListKind.REMOTE else None
                    if source is None or current is None or not current.initialized:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-set-target-object has no initialized search list in the requested source scope",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    generation_candidates = tuple(
                        generation.generation
                        for generation in current.generation_variants
                    )
                    current_generation = (
                        current.current_generation
                        if current.current_generation is not None
                        else (
                            current.generation_variants[0]
                            if current.generation_variants
                            else None
                        )
                    )
                    try:
                        index = int(args[2], 10)
                    except ValueError:
                        index = None
                    capacity = (
                        current_generation.capacity
                        if current_generation is not None
                        else max(
                            (generation.capacity for generation in current.generation_variants),
                            default=0,
                        )
                    )
                    if index is not None and _search_list_proven_empty(current):
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-014",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                (
                                    f"DUC object index {index} cannot be established because "
                                    f"{source.value.lower()} search list has proven zero cardinality"
                                ),
                                _location(action, rule.source_location),
                            )
                        )
                        if (
                            state.target is not None
                            and target_contract.failed_action_preserves_previous_target is None
                        ):
                            diagnostics.append(
                                DucDiagnostic(
                                    "DUC-007",
                                    DiagnosticSeverity.WARNING.value,
                                    rule.rule_order,
                                    (
                                        "up-set-target-object failed target establishment Action; "
                                        "native effect on the previous target is unresolved, so the "
                                        "compiler preserves the existing target without claiming runtime preservation"
                                    ),
                                    _location(action, rule.source_location),
                                )
                            )
                        continue
                    if index is not None and not 0 <= index < capacity:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-014",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                f"DUC object index {index} exceeds {source.value.lower()} list capacity {capacity}",
                                _location(action, rule.source_location),
                            )
                        )
                        if (
                            state.target is not None
                            and target_contract.failed_action_preserves_previous_target is None
                        ):
                            diagnostics.append(
                                DucDiagnostic(
                                    "DUC-007",
                                    DiagnosticSeverity.WARNING.value,
                                    rule.rule_order,
                                    (
                                        "up-set-target-object failed target establishment Action; "
                                        "native effect on the previous target is unresolved, so the "
                                        "compiler preserves the existing target without claiming runtime preservation"
                                    ),
                                    _location(action, rule.source_location),
                                )
                            )
                        continue
                    provenance = _provenance(
                        rule,
                        action,
                        visibility=DucVisibility.SAME_RULE,
                        state_revision=state_revision,
                    pass_id=state.pass_id,
                        inputs=tuple(
                            sorted(set(generation_candidates))
                        ) + (state.filters.generation,),
                        contract_id="duc.target.object",
                        evidence_ids=target_contract.evidence_ids,
                    )
                    source_generation_pass_id = (
                        current_generation.produced_by.pass_id
                        if current_generation is not None
                        else None
                    )
                    if current.path_ambiguous or state.filters.path_ambiguous:
                        target_validity = DucTargetStatus.UNKNOWN
                        target_proof = DucTargetProof.UNKNOWN
                    elif source_generation_pass_id == state.pass_id:
                        target_validity = DucTargetStatus.VALID
                        target_proof = DucTargetProof.CURRENT_PASS_PROOF
                    else:
                        target_validity = DucTargetStatus.VALID
                        target_proof = DucTargetProof.PRESERVED_PROOF

                    target = DucTargetState(
                        kind=DucTargetKind.OBJECT,
                        generation=state_revision,
                        object_refs=(
                            DucObjectRef(
                                source,
                                current_generation.generation if current_generation is not None else None,
                                index,
                                None,
                                provenance,
                            ),
                        ),
                        source_list_generation=(
                            current_generation.generation
                            if current_generation is not None and not current.path_ambiguous
                            else None
                        ),
                        source_filter_generation=state.filters.generation,
                        provenance=provenance,
                        validity=target_validity,
                        pass_id=state.pass_id,
                        proof=target_proof,
                    )
                    state = DucSemanticState(
                        state.local_list,
                        state.remote_list,
                        state.filters,
                        target,
                        state.point_target,
                        state_revision,
                        state.pass_id,
                        groups=state.groups,
                        goal_output_spans=state.goal_output_spans,
                    )
                    targets.append(target)
                    rule_reads.add(DucStateKind.LIST)
                    rule_reads.add(DucStateKind.FILTER)
                    rule_writes.add(DucStateKind.TARGET)
                    continue

                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    inputs=(state.filters.generation,),
                    contract_id="duc.target.point",
                    evidence_ids=target_contract.evidence_ids,
                )
                point = DucPointRef(
                    goal_span_request_id=args[0] if args else None,
                    x_goal=args[0] if args else None,
                    y_goal=str(int(args[0]) + 1) if args and args[0].isdigit() else None,
                    point_fingerprint=_fingerprint(("point", *args)),
                    provenance=provenance,
                )
                state = DucSemanticState(
                    state.local_list,
                    state.remote_list,
                    state.filters,
                    state.target,
                    point,
                    state_revision,
                    state.pass_id,
                    groups=state.groups,
                    goal_output_spans=state.goal_output_spans,
                )
                rule_writes.add(DucStateKind.TARGET)
                continue

            mutation_contract = contracts.duc_mutation(command)
            if mutation_contract is not None:
                if command == "up-clean-search" and len(args) != 3:
                    raise ValueError("up-clean-search requires SearchSource, ObjectData, and SearchOrder")
                if command == "up-remove-objects" and len(args) != 4:
                    raise ValueError("up-remove-objects requires SearchSource, ObjectData, compareOp, and Value")

                source = (
                    DucListKind.LOCAL
                    if args[0] == "search-local"
                    else DucListKind.REMOTE
                    if args[0] == "search-remote"
                    else None
                )
                if source is None or source.value not in mutation_contract.list_kinds:
                    raise ValueError(f"{command} requires search-local or search-remote")
                object_data = args[1]
                compare_operator = args[2] if command == "up-remove-objects" else None
                compare_value = args[3] if command == "up-remove-objects" else None
                mutation_kind = (
                    DucListMutationKind.DEDUPE
                    if command == "up-clean-search"
                    and object_data == mutation_contract.sentinel_object_data
                    else DucListMutationKind.SORT
                    if command == "up-clean-search"
                    else DucListMutationKind.REMOVE_MATCHES
                )
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    contract_id=f"duc.list.mutator.{command}",
                    evidence_ids=mutation_contract.evidence_ids,
                )
                target, target_transition = _target_after_list_mutation(
                    state.target,
                    list_kind=source,
                    mutation_kind=mutation_kind,
                    object_data=object_data,
                    compare_operator=compare_operator,
                    compare_value=compare_value,
                )
                current_list = (
                    state.local_list
                    if source is DucListKind.LOCAL
                    else state.remote_list
                )
                updated_list = _mutate_list_generation(
                    current_list,
                    command=command,
                    arguments=args,
                    mutation_kind=mutation_kind,
                )
                local_list = (
                    updated_list
                    if source is DucListKind.LOCAL
                    else state.local_list
                )
                remote_list = (
                    updated_list
                    if source is DucListKind.REMOTE
                    else state.remote_list
                )
                state = DucSemanticState(
                    local_list,
                    remote_list,
                    state.filters,
                    target,
                    state.point_target,
                    state_revision,
                    state.pass_id,
                    groups=state.groups,
                    goal_output_spans=state.goal_output_spans,
                )
                mutations.append(
                    DucListMutationEffect(
                        command=command,
                        list_kind=source,
                        kind=mutation_kind,
                        object_data=object_data,
                        compare_operator=compare_operator,
                        compare_value=compare_value,
                        target_transition=target_transition,
                        provenance=provenance,
                    )
                )
                if target_transition is DucTargetTransition.UNKNOWN:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-007",
                            DiagnosticSeverity.WARNING.value,
                            rule.rule_order,
                            (
                                f"{command} may remove or invalidate an object target in "
                                f"{source.value.lower()} DUC state; target lifetime is unknown"
                            ),
                            _location(action, rule.source_location),
                        )
                    )
                rule_writes.add(DucStateKind.LIST)
                continue

            if target_consumer_contract is not None:
                if len(args) != 4:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-005",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-target-objects requires Option, DUCAction, Formation, and AttackStance",
                            _location(action, rule.source_location),
                        )
                    )
                    continue
                option = _int_or_none(args[0])
                if (
                    option is None
                    or option < target_consumer_contract.option_min
                    or option > target_consumer_contract.option_max
                ):
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-005",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-target-objects Option must be 0 or 1",
                            _location(action, rule.source_location),
                        )
                    )
                    continue

                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    pass_id=state.pass_id,
                    inputs=(
                        tuple(
                            generation.generation
                            for generation in (
                                state.local_list.current_generation,
                                state.remote_list.current_generation,
                            )
                            if generation is not None
                        )
                        + ((state.target.generation,) if state.target is not None else ())
                    ),
                    contract_id="duc.target-consumer",
                    evidence_ids=target_consumer_contract.evidence_ids,
                )

                target = state.target
                mode = (
                    DucTargetConsumerMode.LOCAL_SEARCH_RESULTS
                    if option == 0
                    else DucTargetConsumerMode.SELECTED_OBJECT_ONLY
                )
                if option == 0:
                    if target_consumer_contract.option_zero_requires_local_list and (
                        state.local_list.current_generation is None
                        or not state.local_list.initialized
                    ):
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-target-objects Option 0 requires an initialized local search list",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    rule_reads.add(DucStateKind.LIST)
                else:
                    if target is None and target_consumer_contract.option_one_requires_object_target:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-005",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-target-objects Option 1 requires a current object target",
                                _location(action, rule.source_location),
                            )
                        )
                        continue
                    if target is not None and target.validity is DucTargetStatus.STALE:
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-006",
                                DiagnosticSeverity.ERROR.value,
                                rule.rule_order,
                                "up-target-objects consumes an object target invalidated by later DUC reset state",
                                _location(action, rule.source_location),
                            )
                        )
                    elif target is not None and target.validity is DucTargetStatus.UNKNOWN:
                        message = (
                            "up-target-objects consumes an object target retained across a pass "
                            "without a current-pass re-establishment; target lifetime is unknown"
                            if target.proof is DucTargetProof.SYNTACTIC_RETENTION
                            else "up-target-objects has a concrete native object identity, but runtime target liveness is unverified"
                            if target.proof is DucTargetProof.NATIVE_ID_PROOF
                            else "up-target-objects consumes an object target whose source-list identity is no longer provable"
                        )
                        diagnostics.append(
                            DucDiagnostic(
                                "DUC-007",
                                DiagnosticSeverity.WARNING.value,
                                rule.rule_order,
                                message,
                                _location(action, rule.source_location),
                            )
                        )
                    rule_reads.add(DucStateKind.TARGET)

                target_consumers.append(
                    DucTargetConsumerEffect(
                        command=command,
                        mode=mode,
                        provenance=provenance,
                        local_list_generation=(
                            state.local_list.current_generation.generation
                            if state.local_list.current_generation is not None
                            else None
                        ),
                        remote_list_generation=(
                            state.remote_list.current_generation.generation
                            if state.remote_list.current_generation is not None
                            else None
                        ),
                        target_validity=(
                            target.validity
                            if target is not None
                            else DucTargetStatus.UNKNOWN
                        ),
                        target_proof=(
                            target.proof
                            if target is not None
                            else DucTargetProof.UNKNOWN
                        ),
                    )
                )
                continue

            if command in POINT_TARGET_CONSUMERS:
                if state.point_target is None:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-005",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-target-point executes without a previously established point target",
                            _location(action, rule.source_location),
                        )
                    )
                rule_reads.add(DucStateKind.TARGET)
                continue

            if command == "disable-self":
                continue

            effects.append(
                DucExecutionEffect(
                    rule_order=rule.rule_order,
                    within_rule_order=action.within_rule_order,
                    pass_behavior=rule.pass_behavior,
                    reads=tuple(sorted(rule_reads, key=lambda item: item.value)),
                    writes=tuple(sorted(rule_writes, key=lambda item: item.value)),
                    visibility=DucVisibility.SAME_RULE,
                    may_repeat=rule.pass_behavior is RulePassBehavior.RECURRENT,
                    may_self_disable=rule.disable_self_action_index is not None,
                )
            )

        states.append((rule.rule_order, state))

        if state.filters.retained and rule.pass_behavior is RulePassBehavior.RECURRENT:
            if not any(action.expression.head == "up-reset-filters" for action in rule.actions):
                diagnostics.append(
                    DucDiagnostic(
                        "DUC-003",
                        DiagnosticSeverity.INFO.value,
                        rule.rule_order,
                        "recurrent rule leaves retained DUC filters active across later searches until explicitly reset",
                        state.filters.last_mutation.source_location
                        if state.filters.last_mutation is not None
                        else rule.source_location,
                    )
                )

    return DucAnalysisReport(
        initial_state=initial_state,
        final_state=state,
        states=tuple(states),
        searches=tuple(searches),
        group_operations=tuple(groups),
        group_observations=tuple(group_observations),
        resets=tuple(resets),
        mutations=tuple(mutations),
        targets=tuple(targets),
        target_fact_observations=tuple(target_fact_observations),
        target_consumers=tuple(target_consumers),
        target_data_observations=tuple(target_data_observations),
        observations=tuple(observations),
        effects=tuple(effects),
        diagnostics=tuple(diagnostics),
    )


def _generation_key(generation: DucListGeneration) -> tuple[object, ...]:
    return (
        generation.list_kind,
        generation.generation,
        generation.capacity,
        generation.content_fingerprint,
        generation.cardinality,
        generation.last_search_cardinality,
    )


def _filter_key(filters: DucFilterState) -> tuple[object, ...]:
    return (
        filters.generation,
        filters.fingerprint,
        filters.predicates,
        filters.retained,
        filters.path_ambiguous,
    )


def _target_key(target: DucTargetState | None) -> tuple[object, ...] | None:
    if target is None:
        return None
    return (
        target.kind,
        target.object_refs,
        target.point_ref,
        target.source_list_generation,
        target.source_filter_generation,
        target.pass_id,
        target.proof,
    )


def _search_index_key(index: DucSearchIndexState) -> tuple[object, ...]:
    return (
        index.offset,
        index.generation,
        index.query_signature,
        index.focus_player_signature,
        index.known,
        index.last_reset_reason,
        index.cursor_disposition,
        index.path_ambiguous,
    )


def _focus_provenance_if_equal(
    indices: tuple[DucSearchIndexState, ...],
) -> Optional[DucProvenance]:
    provenances = tuple(index.focus_player_provenance for index in indices)
    first = provenances[0]
    return first if all(item == first for item in provenances[1:]) else None


def _join_search_indices(
    indices: tuple[DucSearchIndexState, ...],
) -> DucSearchIndexState:
    first = indices[0]
    if all(_search_index_key(index) == _search_index_key(first) for index in indices[1:]):
        return first
    same_query = all(index.query_signature == first.query_signature for index in indices)
    same_focus = all(index.focus_player_signature == first.focus_player_signature for index in indices)
    same_reason = all(index.last_reset_reason is first.last_reset_reason for index in indices)
    return DucSearchIndexState(
        offset=first.offset if all(index.offset == first.offset for index in indices) else None,
        generation=max(index.generation for index in indices),
        query_signature=first.query_signature if same_query else None,
        focus_player_signature=first.focus_player_signature if same_focus else None,
        focus_player_provenance=(
            _focus_provenance_if_equal(indices)
            if same_focus
            else None
        ),
        known=all(index.known for index in indices) and all(index.offset == first.offset for index in indices),
        last_reset_reason=first.last_reset_reason if same_reason else DucSearchIndexResetReason.UNKNOWN,
        cursor_disposition=(
            first.cursor_disposition
            if all(index.cursor_disposition is first.cursor_disposition for index in indices)
            else DucSearchCursorDisposition.PATH_AMBIGUOUS
        ),
        path_ambiguous=True,
    )


def _widen_search_index(
    previous: DucSearchIndexState,
    current: DucSearchIndexState,
) -> DucSearchIndexState:
    if _search_index_key(previous) == _search_index_key(current):
        return previous
    same_query = previous.query_signature == current.query_signature
    same_focus = previous.focus_player_signature == current.focus_player_signature
    same_offset = previous.offset == current.offset
    return DucSearchIndexState(
        offset=previous.offset if same_offset else None,
        generation=0,
        query_signature=previous.query_signature if same_query else None,
        focus_player_signature=(
            previous.focus_player_signature if same_focus else None
        ),
        focus_player_provenance=(
            previous.focus_player_provenance
            if same_focus and previous.focus_player_provenance == current.focus_player_provenance
            else None
        ),
        known=(
            previous.known
            and current.known
            and same_offset
        ),
        last_reset_reason=(
            previous.last_reset_reason
            if previous.last_reset_reason is current.last_reset_reason
            else DucSearchIndexResetReason.UNKNOWN
        ),
        cursor_disposition=(
            previous.cursor_disposition
            if previous.cursor_disposition is current.cursor_disposition
            else DucSearchCursorDisposition.PATH_AMBIGUOUS
        ),
        path_ambiguous=True,
    )


def _list_semantic_key(state: DucSearchListState) -> tuple[object, ...]:
    if state.current_generation is not None:
        return (
            _generation_key(state.current_generation),
            state.path_ambiguous,
        )
    return (
        "AMBIGUOUS",
        state.path_ambiguous,
        tuple(_generation_key(item) for item in state.generation_variants),
    )


def _widen_list_state(
    previous: DucSearchListState,
    current: DucSearchListState,
) -> DucSearchListState:
    if _list_semantic_key(previous) == _list_semantic_key(current):
        return replace(
            previous,
            search_index=_widen_search_index(
                previous.search_index,
                current.search_index,
            ),
        )
    candidates: dict[tuple[object, ...], DucListGeneration] = {}
    for generation in (
        *previous.generation_variants,
        *current.generation_variants,
        *(
            (previous.current_generation,)
            if previous.current_generation is not None
            else ()
        ),
        *(
            (current.current_generation,)
            if current.current_generation is not None
            else ()
        ),
    ):
        candidates[_generation_key(generation)] = generation
    representative = min(
        candidates.values(),
        key=lambda generation: (
            generation.generation,
            generation.content_fingerprint or "",
        ),
        default=None,
    )
    next_generation = representative.generation + 1 if representative is not None else 1
    return DucSearchListState(
        list_kind=previous.list_kind,
        current_generation=None,
        next_generation=next_generation,
        initialized=previous.initialized or current.initialized,
        path_ambiguous=True,
        generation_variants=(representative,) if representative is not None else (),
        search_index=_widen_search_index(
            previous.search_index,
            current.search_index,
        ),
    )


def _widen_filter_state(
    previous: DucFilterState,
    current: DucFilterState,
) -> DucFilterState:
    if _filter_key(previous) == _filter_key(current):
        return previous
    return DucFilterState(
        generation=0,
        predicates=(),
        fingerprint="AMBIGUOUS",
        initialized=previous.initialized or current.initialized,
        retained=previous.retained or current.retained,
        last_mutation=None,
        path_ambiguous=True,
    )


def _widen_target_state(
    previous: DucTargetState | None,
    current: DucTargetState | None,
) -> DucTargetState | None:
    if _target_key(previous) == _target_key(current):
        if previous is None:
            return None
        if previous.validity is current.validity and previous.proof is current.proof:
            return previous
        return replace(
            previous,
            validity=DucTargetStatus.UNKNOWN,
            proof=DucTargetProof.UNKNOWN,
        )
    representative = previous if previous is not None else current
    if representative is None:
        return None
    return replace(representative, validity=DucTargetStatus.UNKNOWN)


def _widen_loop_state(
    previous: DucSemanticState,
    current: DucSemanticState,
) -> tuple[DucSemanticState, tuple[str, ...]]:
    local = _widen_list_state(previous.local_list, current.local_list)
    remote = _widen_list_state(previous.remote_list, current.remote_list)
    filters = _widen_filter_state(previous.filters, current.filters)
    target = _widen_target_state(previous.target, current.target)
    groups = _join_groups((previous.groups, current.groups))
    goal_output_spans = _join_goal_output_spans(
        (previous.goal_output_spans, current.goal_output_spans)
    )
    if previous.point_target == current.point_target:
        point_target = previous.point_target
    else:
        point_target = None
    widened_fields: list[str] = []
    if _list_semantic_key(previous.local_list) != _list_semantic_key(current.local_list):
        widened_fields.append("LOCAL_LIST")
    if _list_semantic_key(previous.remote_list) != _list_semantic_key(current.remote_list):
        widened_fields.append("REMOTE_LIST")
    if _filter_key(previous.filters) != _filter_key(current.filters):
        widened_fields.append("FILTERS")
    if _target_key(previous.target) != _target_key(current.target) or (
        previous.target is not None
        and current.target is not None
        and previous.target.validity is not current.target.validity
    ):
        widened_fields.append("TARGET")
    if point_target != previous.point_target:
        widened_fields.append("POINT_TARGET")
    if tuple(_group_key(group) for group in previous.groups) != tuple(
        _group_key(group) for group in current.groups
    ):
        widened_fields.append("GROUPS")
    if tuple(_goal_output_key(span) for span in previous.goal_output_spans) != tuple(
        _goal_output_key(span) for span in current.goal_output_spans
    ):
        widened_fields.append("GOAL_OUTPUTS")
    return (
        DucSemanticState(
            local,
            remote,
            filters,
            target,
            point_target,
            max(previous.state_revision, current.state_revision),
            max(previous.pass_id, current.pass_id),
            groups=groups,
            goal_output_spans=goal_output_spans,
        ),
        tuple(widened_fields),
    )


def _join_list_states(states: tuple[DucSearchListState, ...]) -> DucSearchListState:
    first = states[0]
    unique_generations: dict[tuple[object, ...], DucListGeneration] = {}
    for state in states:
        for generation in state.generation_variants:
            unique_generations[_generation_key(generation)] = generation
        if state.current_generation is not None:
            unique_generations[_generation_key(state.current_generation)] = state.current_generation

    current_keys = {
        _generation_key(state.current_generation)
        for state in states
        if state.current_generation is not None
    }
    all_initialized = all(state.initialized for state in states)
    same_current = (
        all_initialized
        and len(current_keys) == 1
        and not any(state.current_generation is None for state in states)
    )
    ambiguous = (
        any(state.path_ambiguous for state in states)
        or not all_initialized
        or len(current_keys) > 1
        or any(state.current_generation is None for state in states)
    )
    current_generation = first.current_generation if same_current else None
    return DucSearchListState(
        list_kind=first.list_kind,
        current_generation=current_generation,
        next_generation=max(state.next_generation for state in states),
        initialized=any(state.initialized for state in states),
        path_ambiguous=ambiguous,
        generation_variants=tuple(
            unique_generations[key]
            for key in sorted(unique_generations, key=str)
        ),
        search_index=_join_search_indices(tuple(state.search_index for state in states)),
    )


def _join_filters(states: tuple[DucFilterState, ...]) -> DucFilterState:
    first = states[0]
    if all(_filter_key(state) == _filter_key(first) for state in states):
        return replace(first, path_ambiguous=any(state.path_ambiguous for state in states))
    return DucFilterState(
        generation=max(state.generation for state in states),
        predicates=(),
        fingerprint="AMBIGUOUS",
        initialized=any(state.initialized for state in states),
        retained=any(state.retained for state in states),
        last_mutation=None,
        path_ambiguous=True,
    )


def _join_targets(states: tuple[DucTargetState | None, ...]) -> DucTargetState | None:
    first = states[0]

    direct_id_targets = tuple(
        state
        for state in states
        if (
            state is not None
            and state.kind is DucTargetKind.OBJECT
            and len(state.object_refs) == 1
            and state.object_refs[0].list_kind is None
            and state.object_refs[0].native_object_id is not None
        )
    )
    if len(direct_id_targets) == len(states) and direct_id_targets:
        native_ids = {
            state.object_refs[0].native_object_id
            for state in direct_id_targets
        }
        if len(native_ids) == 1:
            representative = direct_id_targets[0]
            return replace(
                representative,
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.NATIVE_ID_PROOF,
            )

    if all(_target_key(state) == _target_key(first) for state in states):
        if first is None:
            return None
        if all(
            state is not None
            and state.validity is first.validity
            and state.proof is first.proof
            for state in states
        ):
            return first
        return replace(
            first,
            validity=DucTargetStatus.UNKNOWN,
            proof=DucTargetProof.UNKNOWN,
        )
    representatives = [state for state in states if state is not None]
    if not representatives:
        return None
    representative = representatives[0]
    if (
        representative.kind is DucTargetKind.OBJECT
        and representative.object_refs
        and representative.object_refs[0].list_kind is None
    ):
        representative = replace(
            representative,
            object_refs=tuple(
                replace(ref, native_object_id=None)
                for ref in representative.object_refs
            ),
        )
    return replace(
        representative,
        validity=DucTargetStatus.UNKNOWN,
        proof=DucTargetProof.UNKNOWN,
    )


def _group_key(group: DucGroupState) -> tuple[object, ...]:
    return (
        group.group_id,
        group.generation,
        group.cardinality,
        group.capacity,
        group.source_list,
        group.source_list_generation,
        group.source_index_start,
        group.requested_max_objects,
        group.content_fingerprint,
        group.validity,
        group.flag_state,
        group.path_ambiguous,
    )


def _join_groups(
    variants: tuple[tuple[DucGroupState, ...], ...],
) -> tuple[DucGroupState, ...]:
    merged: list[DucGroupState] = []
    for group_id in range(DUC_GROUP_COUNT):
        candidates = tuple(values[group_id] for values in variants)
        first = candidates[0]
        if all(
            _group_key(candidate) == _group_key(first)
            for candidate in candidates[1:]
        ):
            merged.append(first)
            continue
        minimum = min(candidate.cardinality.minimum for candidate in candidates)
        maximum = max(candidate.cardinality.maximum for candidate in candidates)
        same_source = all(
            candidate.source_list == first.source_list
            for candidate in candidates
        )
        same_source_generation = all(
            candidate.source_list_generation == first.source_list_generation
            for candidate in candidates
        )
        same_start = all(
            candidate.source_index_start == first.source_index_start
            for candidate in candidates
        )
        same_requested_max = all(
            candidate.requested_max_objects == first.requested_max_objects
            for candidate in candidates
        )
        same_fingerprint = all(
            candidate.content_fingerprint == first.content_fingerprint
            for candidate in candidates
        )
        same_flag = all(
            candidate.flag_state is first.flag_state
            for candidate in candidates
        )
        same_provenance = all(
            candidate.provenance == first.provenance
            for candidate in candidates
        )
        merged.append(
            replace(
                first,
                generation=max(candidate.generation for candidate in candidates),
                cardinality=DucCardinalityRange(minimum, maximum),
                source_list=first.source_list if same_source else None,
                source_list_generation=(
                    first.source_list_generation if same_source_generation else None
                ),
                source_index_start=first.source_index_start if same_start else None,
                requested_max_objects=(
                    first.requested_max_objects if same_requested_max else None
                ),
                content_fingerprint=(
                    first.content_fingerprint if same_fingerprint else None
                ),
                validity=DucGroupStatus.UNKNOWN,
                flag_state=first.flag_state if same_flag else DucGroupFlagState.UNKNOWN,
                provenance=first.provenance if same_provenance else None,
                path_ambiguous=True,
            )
        )
    return tuple(merged)


def _goal_output_key(span: DucGoalOutputSpan) -> tuple[object, ...]:
    return (
        span.start_goal_id,
        span.width,
        span.generation,
        span.overwritten_generation,
        span.overwritten_provenance,
        span.cardinality,
        span.pass_id,
        span.path_ambiguous,
        span.provenance,
    )


def _join_goal_output_spans(
    variants: tuple[tuple[DucGoalOutputSpan, ...], ...],
) -> tuple[DucGoalOutputSpan, ...]:
    starts = sorted({
        span.start_goal_id
        for spans in variants
        for span in spans
    })
    merged: list[DucGoalOutputSpan] = []
    for start in starts:
        candidates = tuple(
            next((span for span in spans if span.start_goal_id == start), None)
            for spans in variants
        )
        present = tuple(span for span in candidates if span is not None)
        if not present:
            continue
        first = present[0]
        if len(present) == len(candidates) and all(
            _goal_output_key(span) == _goal_output_key(first)
            for span in present[1:]
        ):
            merged.append(first)
            continue
        minimum = (
            0
            if len(present) < len(candidates)
            else min(span.cardinality.minimum for span in present)
        )
        maximum = max(span.cardinality.maximum for span in present)
        generation = max(span.generation for span in present)
        width = max(span.width for span in present)
        merged.append(
            DucGoalOutputSpan(
                start_goal_id=start,
                width=width,
                generation=generation,
                overwritten_generation=None,
                overwritten_provenance=None,
                provenance=None,
                cardinality=DucCardinalityRange(minimum, maximum),
                path_ambiguous=True,
                pass_id=max(span.pass_id for span in present),
            )
        )
    return tuple(merged)


def _state_key(state: DucSemanticState) -> tuple[object, ...]:
    return (
        state.pass_id,
        _search_index_key(state.local_list.search_index),
        (
            _generation_key(state.local_list.current_generation),
            state.local_list.path_ambiguous,
        )
        if state.local_list.current_generation is not None
        else (
            "AMBIGUOUS",
            state.local_list.path_ambiguous,
            tuple(_generation_key(item) for item in state.local_list.generation_variants),
        ),
        _search_index_key(state.remote_list.search_index),
        (
            _generation_key(state.remote_list.current_generation),
            state.remote_list.path_ambiguous,
        )
        if state.remote_list.current_generation is not None
        else (
            "AMBIGUOUS",
            state.remote_list.path_ambiguous,
            tuple(_generation_key(item) for item in state.remote_list.generation_variants),
        ),
        _filter_key(state.filters),
        _target_key(state.target),
        state.point_target,
        tuple(_group_key(group) for group in state.groups),
        tuple(_goal_output_key(span) for span in state.goal_output_spans),
    )


def _join_states(
    variants: tuple[DucSemanticState, ...],
) -> tuple[DucSemanticState, tuple[str, ...]]:
    local = _join_list_states(tuple(state.local_list for state in variants))
    remote = _join_list_states(tuple(state.remote_list for state in variants))
    filters = _join_filters(tuple(state.filters for state in variants))
    target = _join_targets(tuple(state.target for state in variants))
    groups = _join_groups(tuple(state.groups for state in variants))
    goal_output_spans = _join_goal_output_spans(
        tuple(state.goal_output_spans for state in variants)
    )
    fields: list[str] = []
    if any(
        _list_semantic_key(state.local_list) != _list_semantic_key(variants[0].local_list)
        for state in variants[1:]
    ):
        fields.append("LOCAL_LIST")
    if any(
        _list_semantic_key(state.remote_list) != _list_semantic_key(variants[0].remote_list)
        for state in variants[1:]
    ):
        fields.append("REMOTE_LIST")
    if any(
        _filter_key(state.filters) != _filter_key(variants[0].filters)
        for state in variants[1:]
    ):
        fields.append("FILTERS")
    if any(
        _target_key(state.target) != _target_key(variants[0].target)
        for state in variants[1:]
    ):
        fields.append("TARGET")
    if any(state.point_target != variants[0].point_target for state in variants[1:]):
        fields.append("POINT_TARGET")
    if any(
        tuple(_group_key(group) for group in state.groups)
        != tuple(_group_key(group) for group in variants[0].groups)
        for state in variants[1:]
    ):
        fields.append("GROUPS")
    if any(
        tuple(_goal_output_key(span) for span in state.goal_output_spans)
        != tuple(_goal_output_key(span) for span in variants[0].goal_output_spans)
        for state in variants[1:]
    ):
        fields.append("GOAL_OUTPUTS")
    return (
        DucSemanticState(
            local,
            remote,
            filters,
            target,
            variants[0].point_target if all(
                state.point_target == variants[0].point_target for state in variants
            ) else None,
            max(state.state_revision for state in variants),
            max(state.pass_id for state in variants),
            groups=groups,
            goal_output_spans=goal_output_spans,
        ),
        tuple(fields),
    )


def analyze_duc(
    execution: RuleExecutionReport | tuple[EffectiveRule, ...],
    contracts: NativeContractCatalog | None = None,
    *,
    loop_widening_limit: int = DUC_LOOP_WIDENING_LIMIT,
    initial_state: DucSemanticState | None = None,
    recurrent_execution: RecurrentExecutionReport | None = None,
) -> DucAnalysisReport:
    contracts = contracts or default_native_contract_catalog()
    seed_state = initial_state or _empty_state()
    if not isinstance(execution, RuleExecutionReport):
        report = _analyze_duc_linear(
            tuple(execution),
            contracts,
            initial_state=seed_state,
        )
        return replace(report, next_pass_state=advance_duc_pass(report.final_state))

    if loop_widening_limit < 1:
        raise ValueError("loop_widening_limit must be >= 1")

    rules_by_order = {rule.rule_order: rule for rule in execution.rules}
    reachability = execution.reachability
    if reachability is None:
        report = _analyze_duc_linear(
            execution.rules,
            contracts,
            initial_state=seed_state,
        )
        return replace(report, next_pass_state=advance_duc_pass(report.final_state))

    outgoing = dict(reachability.outgoing_rule_orders)
    firing_status = (
        {
            rule.rule_order: recurrent_execution.status_for_rule(rule.rule_order)
            for rule in execution.rules
        }
        if recurrent_execution is not None
        else {}
    )
    max_rule_order = max(rules_by_order, default=0)
    incoming_states: dict[int, dict[int, DucSemanticState]] = {
        1: {0: seed_state}
    }
    last_entry_keys: dict[int, tuple[object, ...]] = {}
    rule_reports: dict[int, DucAnalysisReport] = {}
    rule_outputs: dict[int, DucSemanticState] = {}
    branch_merges: dict[int, DucBranchMerge] = {}
    back_edge_iterations: dict[tuple[int, int], int] = {}
    loop_widenings: dict[tuple[int, int], DucLoopWidening] = {}
    pending = deque([1])

    while pending:
        rule_order = pending.popleft()
        entries_by_predecessor = incoming_states.get(rule_order, {})
        if not entries_by_predecessor:
            continue
        entries = tuple(entries_by_predecessor.values())
        distinct: list[DucSemanticState] = []
        seen: set[tuple[object, ...]] = set()
        for state in entries:
            key = _state_key(state)
            if key in seen:
                continue
            seen.add(key)
            distinct.append(state)
        variants = tuple(distinct)
        if len(variants) == 1:
            entry_state = variants[0]
            merged_fields = ()
        else:
            entry_state, merged_fields = _join_states(variants)
        predecessor_orders = tuple(sorted(source for source in entries_by_predecessor if source != 0))
        if len(entries_by_predecessor) > 1:
            branch_merges[rule_order] = DucBranchMerge(
                rule_order=rule_order,
                predecessor_rule_orders=predecessor_orders,
                merged_fields=merged_fields,
                state_variants=len(variants),
            )

        entry_key = _state_key(entry_state)
        if last_entry_keys.get(rule_order) == entry_key:
            continue
        last_entry_keys[rule_order] = entry_key

        if (
            firing_status.get(rule_order)
            is RecurrentExecutionStatus.NEVER_RUNNABLE
        ):
            rule_report = DucAnalysisReport(
                initial_state=entry_state,
                final_state=entry_state,
                states=((rule_order, entry_state),),
                next_pass_state=entry_state,
            )
            rule_outgoing = (
                (rule_order + 1,)
                if rule_order < max_rule_order
                else ()
            )
        else:
            rule_report = _analyze_duc_linear(
                (rules_by_order[rule_order],),
                contracts,
                initial_state=entry_state,
            )
            rule_outgoing = outgoing.get(rule_order, ())
        rule_reports[rule_order] = rule_report
        current_state = rule_report.final_state
        rule_outputs[rule_order] = current_state

        for target_order in rule_outgoing:
            if target_order <= rule_order:
                edge = (rule_order, target_order)
                back_edge_iterations[edge] = min(
                    back_edge_iterations.get(edge, 0) + 1,
                    loop_widening_limit,
                )
                iteration = back_edge_iterations[edge]
                if iteration < loop_widening_limit:
                    propagated_state = current_state
                else:
                    previous_target_state = _join_states(
                        tuple(incoming_states.get(target_order, {}).values())
                    )[0] if incoming_states.get(target_order) else _empty_state()
                    propagated_state, widened_fields = _widen_loop_state(
                        previous_target_state,
                        current_state,
                    )
                    loop_widenings.setdefault(
                        edge,
                        DucLoopWidening(
                            loop_head_rule_order=target_order,
                            back_edge_source_rule_order=rule_order,
                            iteration_limit=loop_widening_limit,
                            iterations=iteration,
                            widened_fields=widened_fields,
                        ),
                    )
            else:
                propagated_state = current_state
            prior = incoming_states.setdefault(target_order, {}).get(rule_order)
            propagated_key = _state_key(propagated_state)
            prior_key = _state_key(prior) if prior is not None else None
            if prior is None or propagated_key != prior_key:
                incoming_states[target_order][rule_order] = propagated_state
                if target_order not in pending:
                    pending.append(target_order)

    states = tuple(
        (rule_order, rule_outputs[rule_order])
        for rule_order in sorted(rule_outputs)
    )
    searches = tuple(
        operation
        for rule_order in sorted(rule_reports)
        for operation in rule_reports[rule_order].searches
    )
    group_operations = tuple(
        operation
        for rule_order in sorted(rule_reports)
        for operation in rule_reports[rule_order].group_operations
    )
    group_observations = tuple(
        observation
        for rule_order in sorted(rule_reports)
        for observation in rule_reports[rule_order].group_observations
    )
    resets = tuple(
        effect
        for rule_order in sorted(rule_reports)
        for effect in rule_reports[rule_order].resets
    )
    mutations = tuple(
        effect
        for rule_order in sorted(rule_reports)
        for effect in rule_reports[rule_order].mutations
    )
    targets = tuple(
        target
        for rule_order in sorted(rule_reports)
        for target in rule_reports[rule_order].targets
    )
    target_fact_observations = tuple(
        observation
        for rule_order in sorted(rule_reports)
        for observation in rule_reports[rule_order].target_fact_observations
    )
    target_consumers = tuple(
        consumer
        for rule_order in sorted(rule_reports)
        for consumer in rule_reports[rule_order].target_consumers
    )
    target_data_observations = tuple(
        observation
        for rule_order in sorted(rule_reports)
        for observation in rule_reports[rule_order].target_data_observations
    )
    observations = tuple(
        observation
        for rule_order in sorted(rule_reports)
        for observation in rule_reports[rule_order].observations
    )
    effects = tuple(
        effect
        for rule_order in sorted(rule_reports)
        for effect in rule_reports[rule_order].effects
    )
    diagnostics = [
        diagnostic
        for rule_order in sorted(rule_reports)
        for diagnostic in rule_reports[rule_order].diagnostics
    ]
    terminal_states = [
        rule_outputs[rule_order]
        for rule_order in sorted(rule_outputs)
        if not outgoing.get(rule_order)
    ]
    final_state = (
        _join_states(tuple(terminal_states))[0]
        if len(terminal_states) > 1
        else terminal_states[0]
        if terminal_states
        else _empty_state()
    )
    for edge in sorted(loop_widenings):
        widening = loop_widenings[edge]
        widened_fields = ", ".join(widening.widened_fields) or "NONE"
        diagnostics.append(
            DucDiagnostic(
                "DUC-016",
                DiagnosticSeverity.WARNING.value,
                widening.back_edge_source_rule_order,
                (
                    f"DUC loop widening: loop head {widening.loop_head_rule_order}, "
                    f"back-edge source {widening.back_edge_source_rule_order}, "
                    f"iteration bound {widening.iteration_limit}, "
                    f"widened fields: {widened_fields}"
                ),
                rules_by_order[widening.back_edge_source_rule_order].source_location,
            )
        )

    return DucAnalysisReport(
        initial_state=seed_state,
        final_state=final_state,
        states=states,
        searches=searches,
        group_operations=group_operations,
        group_observations=group_observations,
        resets=resets,
        mutations=mutations,
        targets=targets,
        target_fact_observations=target_fact_observations,
        target_consumers=target_consumers,
        target_data_observations=target_data_observations,
        observations=observations,
        effects=effects,
        diagnostics=tuple(diagnostics),
        branch_merges=tuple(branch_merges[order] for order in sorted(branch_merges)),
        loop_widenings=tuple(loop_widenings[key] for key in sorted(loop_widenings)),
        next_pass_state=advance_duc_pass(final_state),
    )


def advance_duc_pass(state: DucSemanticState) -> DucSemanticState:
    """Advance persistent DUC state to the next engine pass.

    Search/filter state persists, but an object target established on an earlier
    pass cannot remain a current-pass proof merely because the syntax still
    contains it. Without a fresh target establishment or native object-lifetime
    witness, its status becomes UNKNOWN and is marked as SYNTACTIC_RETENTION.
    Explicit reset invalidation remains STALE and is never weakened to UNKNOWN.
    """
    target = state.target
    if target is not None:
        if target.validity is DucTargetStatus.STALE:
            target = replace(target, proof=DucTargetProof.UNKNOWN)
        else:
            target = replace(
                target,
                validity=DucTargetStatus.UNKNOWN,
                proof=DucTargetProof.SYNTACTIC_RETENTION,
            )
    return DucSemanticState(
        state.local_list,
        state.remote_list,
        state.filters,
        target,
        state.point_target,
        0,
        state.pass_id + 1,
        groups=state.groups,
        goal_output_spans=state.goal_output_spans,
    )


__all__ = [
    "analyze_duc",
    "advance_duc_pass",
]
