"""Practical DUC abstract-state analysis for native .per rules.

This module is driven by evidence-backed native contracts rather than a new DSL.
It tracks only compiler-visible DUC state and deliberately fails closed when
target lifetime cannot be established.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256

from ..ast import Expression
from ..diagnostics import DiagnosticSeverity
from ..ir.duc import (
    DucAnalysisReport,
    DucDiagnostic,
    DucExecutionEffect,
    DucFilterPredicate,
    DucFilterSnapshot,
    DucFilterState,
    DucListGeneration,
    DucListKind,
    DucObjectRef,
    DucPointRef,
    DucProvenance,
    DucResetEffect,
    DucResetKind,
    DucSearchListState,
    DucSearchOperation,
    DucSearchStateObservation,
    DucSemanticState,
    DucStateKind,
    DucTargetKind,
    DucTargetState,
    DucTargetStatus,
    DucVisibility,
)
from .rule_execution import EffectiveRule, RuleAction, RulePassBehavior


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
SET_POINT_TARGET = "up-set-target-point"
OBJECT_TARGET_CONSUMERS = frozenset({"up-target-objects"})
POINT_TARGET_CONSUMERS = frozenset({"up-target-point"})
OBJECT_LIST_MUTATORS = frozenset({"up-clean-search", "up-remove-objects"})


@dataclass(frozen=True)
class NativeDucSearchContract:
    command: str
    list_kind: DucListKind
    capacity: int
    appends_to_current_list: bool
    consumes_retained_filters: bool
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class NativeDucFilterContract:
    command: str
    retained: bool
    affects_next_search: bool
    resettable: bool
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class NativeDucResetResolution:
    invalidates_local_list: bool
    invalidates_remote_list: bool
    invalidates_filters: bool
    invalidates_object_target: bool
    invalidates_point_target: bool
    invalidates_local_index: bool
    invalidates_remote_index: bool


@dataclass(frozen=True)
class NativeDucResetContract:
    command: str
    reset_kind: DucResetKind
    invalidates_local_list: bool
    invalidates_remote_list: bool
    invalidates_filters: bool
    invalidates_object_target: bool
    invalidates_point_target: bool
    evidence_ids: tuple[str, ...]

    def resolve(self, arguments: tuple[str, ...]) -> NativeDucResetResolution:
        if self.reset_kind is DucResetKind.SEARCH_BOTH:
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
        return NativeDucResetResolution(
            invalidates_local_list=self.invalidates_local_list,
            invalidates_remote_list=self.invalidates_remote_list,
            invalidates_filters=self.invalidates_filters,
            invalidates_object_target=self.invalidates_object_target,
            invalidates_point_target=self.invalidates_point_target,
            invalidates_local_index=False,
            invalidates_remote_index=False,
        )


@dataclass(frozen=True)
class NativeDucTargetContract:
    command: str
    source_kinds: tuple[DucListKind, ...]
    target_kind: DucTargetKind
    requires_current_list: bool
    requires_current_point: bool
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class NativeDucContractCatalog:
    searches: tuple[NativeDucSearchContract, ...]
    filters: tuple[NativeDucFilterContract, ...]
    resets: tuple[NativeDucResetContract, ...]
    targets: tuple[NativeDucTargetContract, ...]
    consumer_commands: tuple[str, ...] = (
        "up-target-objects",
        "up-target-point",
    )

    def search(self, command: str) -> NativeDucSearchContract | None:
        return next((item for item in self.searches if item.command == command), None)

    def filter(self, command: str) -> NativeDucFilterContract | None:
        return next((item for item in self.filters if item.command == command), None)

    def reset(self, command: str) -> NativeDucResetContract | None:
        return next((item for item in self.resets if item.command == command), None)

    def target(self, command: str) -> NativeDucTargetContract | None:
        return next((item for item in self.targets if item.command == command), None)


def default_native_duc_contract_catalog() -> NativeDucContractCatalog:
    airef = "airef:duc"
    return NativeDucContractCatalog(
        searches=(
            NativeDucSearchContract("up-find-local", DucListKind.LOCAL, 240, True, True, (f"{airef}:find-local",)),
            NativeDucSearchContract("up-find-status-local", DucListKind.LOCAL, 240, True, True, (f"{airef}:find-status-local",)),
            NativeDucSearchContract("up-find-remote", DucListKind.REMOTE, 40, True, True, (f"{airef}:find-remote",)),
            NativeDucSearchContract("up-find-status-remote", DucListKind.REMOTE, 40, True, True, (f"{airef}:find-status-remote",)),
            NativeDucSearchContract("up-find-resource", DucListKind.REMOTE, 40, True, True, (f"{airef}:find-resource",)),
        ),
        filters=tuple(
            NativeDucFilterContract(command, True, True, True, (f"{airef}:{command}:retained",))
            for command in sorted(FILTER_COMMANDS)
        ),
        resets=(
            NativeDucResetContract(
                "up-reset-filters",
                DucResetKind.FILTERS,
                False,
                False,
                True,
                False,
                False,
                (f"{airef}:reset-filters",),
            ),
            NativeDucResetContract(
                "up-reset-search",
                DucResetKind.SEARCH_BOTH,
                False,
                False,
                False,
                False,
                False,
                (f"{airef}:reset-search",),
            ),
            NativeDucResetContract(
                "up-full-reset-search",
                DucResetKind.FULL,
                True,
                True,
                True,
                True,
                True,
                (f"{airef}:full-reset-search",),
            ),
        ),
        targets=(
            NativeDucTargetContract(
                SET_OBJECT_TARGET,
                (DucListKind.LOCAL, DucListKind.REMOTE),
                DucTargetKind.OBJECT,
                True,
                False,
                (f"{airef}:set-target-object",),
            ),
            NativeDucTargetContract(
                SET_POINT_TARGET,
                (),
                DucTargetKind.POINT,
                False,
                False,
                (f"{airef}:set-target-point",),
            ),
        ),
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
    inputs: tuple[int, ...] = (),
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
        input_state_generations=inputs,
        semantic_contract_id=contract_id,
        evidence_ids=evidence_ids,
    )


def _canonical_arguments(expression: Expression) -> tuple[str, ...]:
    return tuple(str(argument) for argument in expression.args)


def _list_state(
    kind: DucListKind,
    state: DucSearchListState,
    generation: DucListGeneration | None,
    *,
    next_generation: int | None = None,
    path_ambiguous: bool = False,
    generation_variants: tuple[DucListGeneration, ...] = (),
) -> DucSearchListState:
    return DucSearchListState(
        list_kind=kind,
        current_generation=generation,
        next_generation=state.next_generation if next_generation is None else next_generation,
        initialized=generation is not None,
        path_ambiguous=path_ambiguous,
        generation_variants=generation_variants,
    )


def _empty_state() -> DucSemanticState:
    return DucSemanticState(
        local_list=DucSearchListState(DucListKind.LOCAL, None, 1, False),
        remote_list=DucSearchListState(DucListKind.REMOTE, None, 1, False),
        filters=DucFilterState(0, (), "", True, False, None),
        target=None,
        point_target=None,
        state_revision=0,
    )


def _analyze_duc_linear(
    rules: tuple[EffectiveRule, ...],
    contracts: NativeDucContractCatalog | None = None,
    *,
    initial_state: DucSemanticState | None = None,
) -> DucAnalysisReport:
    contracts = contracts or default_native_duc_contract_catalog()
    state = initial_state or _empty_state()
    initial_state = state
    states: list[tuple[int, DucSemanticState]] = []
    searches: list[DucSearchOperation] = []
    resets: list[DucResetEffect] = []
    targets: list[DucTargetState] = []
    observations: list[DucSearchStateObservation] = []
    effects: list[DucExecutionEffect] = []
    diagnostics: list[DucDiagnostic] = []

    for rule in rules:
        state_revision = state.state_revision + 1
        rule_reads: set[DucStateKind] = set()
        rule_writes: set[DucStateKind] = set()
        rule_reset_lists: set[DucListKind] = set()

        for action in rule.actions:
            expression = action.expression
            command = expression.head
            args = _canonical_arguments(expression)

            search_contract = contracts.search(command)
            filter_contract = contracts.filter(command)
            reset_contract = contracts.reset(command)
            target_contract = contracts.target(command)

            if search_contract is not None:
                kind = search_contract.list_kind
                current = state.local_list if kind is DucListKind.LOCAL else state.remote_list
                if rule.pass_behavior is RulePassBehavior.RECURRENT and current.current_generation is not None:
                    if kind not in rule_reset_lists:
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
                provenance = _provenance(
                    rule,
                    action,
                    visibility=visible,
                    state_revision=state_revision,
                    inputs=(state.filters.generation,),
                    contract_id=f"duc.search.{command}",
                    evidence_ids=search_contract.evidence_ids,
                )
                generation_number = current.next_generation
                output_generation = DucListGeneration(
                    list_kind=kind,
                    generation=generation_number,
                    produced_by=provenance,
                    cardinality=None,
                    capacity=search_contract.capacity,
                    content_fingerprint=_fingerprint(
                        (kind.value, command, *args, filter_snapshot.fingerprint)
                    ),
                )
                updated_list = _list_state(
                    kind,
                    current,
                    output_generation,
                    next_generation=generation_number + 1,
                    path_ambiguous=current.path_ambiguous or filter_snapshot.path_ambiguous,
                    generation_variants=(),
                )
                if kind is DucListKind.LOCAL:
                    state = DucSemanticState(
                        updated_list,
                        state.remote_list,
                        state.filters,
                        state.target,
                        state.point_target,
                        state_revision,
                    )
                else:
                    state = DucSemanticState(
                        state.local_list,
                        updated_list,
                        state.filters,
                        state.target,
                        state.point_target,
                        state_revision,
                    )
                searches.append(
                    DucSearchOperation(
                        command,
                        kind,
                        expression.source,
                        args,
                        filter_snapshot,
                        output_generation,
                        visible,
                        provenance,
                    )
                )
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
                    inputs=(state.filters.generation,),
                    contract_id=f"duc.filter.{command}",
                    evidence_ids=filter_contract.evidence_ids,
                )
                state = DucSemanticState(
                    state.local_list,
                    state.remote_list,
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
                )
                rule_writes.add(DucStateKind.FILTER)
                continue

            if reset_contract is not None:
                resolution = reset_contract.resolve(args)
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
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
                            **{**target.__dict__, "validity": DucTargetStatus.STALE}
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
                            **{**target.__dict__, "validity": DucTargetStatus.STALE}
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
                )
                reset = DucResetEffect(
                    command,
                    reset_contract.reset_kind,
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
                    inputs=generations,
                    contract_id="duc.output.search-state",
                    evidence_ids=("airef:duc:get-search-state",),
                )
                observations.append(
                    DucSearchStateObservation(
                        DucListKind.LOCAL,
                        state.local_list.current_generation.generation if state.local_list.current_generation else None,
                        args[0] if args else "",
                        (
                            "local_search_count",
                            "local_list_count",
                            "remote_search_count",
                            "remote_list_count",
                        ),
                        _fingerprint(("search-state", *(str(item) for item in generations))),
                        provenance,
                    )
                )
                rule_reads.add(DucStateKind.LIST)
                rule_writes.add(DucStateKind.OUTPUT)
                continue

            if target_contract is not None:
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
                        continue
                    provenance = _provenance(
                        rule,
                        action,
                        visibility=DucVisibility.SAME_RULE,
                        state_revision=state_revision,
                        inputs=tuple(
                            sorted(set(generation_candidates))
                        ) + (state.filters.generation,),
                        contract_id="duc.target.object",
                        evidence_ids=target_contract.evidence_ids,
                    )
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
                        validity=(
                            DucTargetStatus.UNKNOWN
                            if current.path_ambiguous or state.filters.path_ambiguous
                            else DucTargetStatus.VALID
                        ),
                    )
                    state = DucSemanticState(
                        state.local_list,
                        state.remote_list,
                        state.filters,
                        target,
                        state.point_target,
                        state_revision,
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
                )
                rule_writes.add(DucStateKind.TARGET)
                continue

            if command in OBJECT_LIST_MUTATORS:
                provenance = _provenance(
                    rule,
                    action,
                    visibility=DucVisibility.SAME_RULE,
                    state_revision=state_revision,
                    contract_id=f"duc.list.mutator.{command}",
                    evidence_ids=("airef:duc:list-mutation",),
                )
                if state.target is not None and state.target.kind is DucTargetKind.OBJECT:
                    state = DucSemanticState(
                        state.local_list,
                        state.remote_list,
                        state.filters,
                        DucTargetState(
                            **{**state.target.__dict__, "validity": DucTargetStatus.UNKNOWN}
                        ),
                        state.point_target,
                        state_revision,
                    )
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-007",
                            DiagnosticSeverity.WARNING.value,
                            rule.rule_order,
                            f"{command} mutates a search list after an object target was established; target identity is no longer provable",
                            _location(action, rule.source_location),
                        )
                    )
                rule_writes.add(DucStateKind.LIST)
                continue

            if command in OBJECT_TARGET_CONSUMERS:
                target = state.target
                if target is None:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-005",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-target-objects executes without a current object target or known search list selection",
                            _location(action, rule.source_location),
                        )
                    )
                elif target.validity is DucTargetStatus.STALE:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-006",
                            DiagnosticSeverity.ERROR.value,
                            rule.rule_order,
                            "up-target-objects consumes an object target invalidated by later DUC reset state",
                            _location(action, rule.source_location),
                        )
                    )
                elif target.validity is DucTargetStatus.UNKNOWN:
                    diagnostics.append(
                        DucDiagnostic(
                            "DUC-007",
                            DiagnosticSeverity.WARNING.value,
                            rule.rule_order,
                            "up-target-objects consumes an object target whose source-list identity is no longer provable",
                            _location(action, rule.source_location),
                        )
                    )
                rule_reads.add(DucStateKind.TARGET)
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
        resets=tuple(resets),
        targets=tuple(targets),
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
    if all(_target_key(state) == _target_key(first) for state in states):
        if first is None:
            return None
        if all(state is not None and state.validity is first.validity for state in states):
            return first
        return replace(first, validity=DucTargetStatus.UNKNOWN)
    representatives = [state for state in states if state is not None]
    if not representatives:
        return None
    return replace(representatives[0], validity=DucTargetStatus.UNKNOWN)


def _state_key(state: DucSemanticState) -> tuple[object, ...]:
    return (
        _generation_key(state.local_list.current_generation)
        if state.local_list.current_generation is not None
        else (
            "AMBIGUOUS",
            tuple(_generation_key(item) for item in state.local_list.generation_variants),
        ),
        _generation_key(state.remote_list.current_generation)
        if state.remote_list.current_generation is not None
        else (
            "AMBIGUOUS",
            tuple(_generation_key(item) for item in state.remote_list.generation_variants),
        ),
        _filter_key(state.filters),
        _target_key(state.target),
        state.point_target,
    )


def _join_states(
    variants: tuple[DucSemanticState, ...],
) -> tuple[DucSemanticState, tuple[str, ...]]:
    local = _join_list_states(tuple(state.local_list for state in variants))
    remote = _join_list_states(tuple(state.remote_list for state in variants))
    filters = _join_filters(tuple(state.filters for state in variants))
    target = _join_targets(tuple(state.target for state in variants))
    fields: list[str] = []
    if any(
        _state_key(state)[0] != _state_key(variants[0])[0]
        for state in variants[1:]
    ):
        fields.append("LOCAL_LIST")
    if any(
        _state_key(state)[1] != _state_key(variants[0])[1]
        for state in variants[1:]
    ):
        fields.append("REMOTE_LIST")
    if any(
        _state_key(state)[2] != _state_key(variants[0])[2]
        for state in variants[1:]
    ):
        fields.append("FILTERS")
    if any(
        _state_key(state)[3] != _state_key(variants[0])[3]
        for state in variants[1:]
    ):
        fields.append("TARGET")
    if any(state.point_target != variants[0].point_target for state in variants[1:]):
        fields.append("POINT_TARGET")
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
        ),
        tuple(fields),
    )


def analyze_duc(
    execution: RuleExecutionReport | tuple[EffectiveRule, ...],
    contracts: NativeDucContractCatalog | None = None,
) -> DucAnalysisReport:
    contracts = contracts or default_native_duc_contract_catalog()
    if not isinstance(execution, RuleExecutionReport):
        return _analyze_duc_linear(tuple(execution), contracts)

    rules_by_order = {rule.rule_order: rule for rule in execution.rules}
    reachability = execution.reachability
    if reachability is None:
        return _analyze_duc_linear(execution.rules, contracts)

    outgoing = dict(reachability.outgoing_rule_orders)
    incoming_states: dict[int, list[tuple[int, DucSemanticState]]] = {1: [(0, _empty_state())]}
    states: list[tuple[int, DucSemanticState]] = []
    searches: list[DucSearchOperation] = []
    resets: list[DucResetEffect] = []
    targets: list[DucTargetState] = []
    observations: list[DucSearchStateObservation] = []
    effects: list[DucExecutionEffect] = []
    diagnostics: list[DucDiagnostic] = []
    branch_merges: list[DucBranchMerge] = []

    for rule_order in sorted(rules_by_order):
        entries = incoming_states.get(rule_order, [])
        if not entries:
            continue
        distinct: list[DucSemanticState] = []
        seen: set[tuple[object, ...]] = set()
        for _, state in entries:
            key = _state_key(state)
            if key in seen:
                continue
            seen.add(key)
            distinct.append(state)
        variants = tuple(distinct)
        if len(variants) == 1:
            entry_state = variants[0]
        else:
            entry_state, merged_fields = _join_states(variants)
            predecessor_orders = tuple(sorted({source for source, _ in entries if source != 0}))
            branch_merges.append(
                DucBranchMerge(
                    rule_order=rule_order,
                    predecessor_rule_orders=predecessor_orders,
                    merged_fields=merged_fields,
                    state_variants=len(variants),
                )
            )
        rule_report = _analyze_duc_linear(
            (rules_by_order[rule_order],),
            contracts,
            initial_state=entry_state,
        )
        states.extend(rule_report.states)
        searches.extend(rule_report.searches)
        resets.extend(rule_report.resets)
        targets.extend(rule_report.targets)
        observations.extend(rule_report.observations)
        effects.extend(rule_report.effects)
        diagnostics.extend(rule_report.diagnostics)

        current_state = rule_report.final_state
        for target_order in outgoing.get(rule_order, ()):
            if target_order <= rule_order:
                diagnostics.append(
                    DucDiagnostic(
                        "DUC-013",
                        DiagnosticSeverity.WARNING.value,
                        rule_order,
                        f"control transfer from rule {rule_order} loops to rule {target_order}; DUC state is widened at the back-edge boundary",
                        rules_by_order[rule_order].source_location,
                    )
                )
                continue
            incoming_states.setdefault(target_order, []).append(
                (rule_order, current_state)
            )

    terminal_states = [
        state
        for rule_order, state in states
        if not outgoing.get(rule_order)
    ]
    final_state = (
        _join_states(tuple(terminal_states))[0]
        if len(terminal_states) > 1
        else terminal_states[0]
        if terminal_states
        else _empty_state()
    )
    return DucAnalysisReport(
        initial_state=_empty_state(),
        final_state=final_state,
        states=tuple(states),
        searches=tuple(searches),
        resets=tuple(resets),
        targets=tuple(targets),
        observations=tuple(observations),
        effects=tuple(effects),
        diagnostics=tuple(diagnostics),
        branch_merges=tuple(branch_merges),
    )


__all__ = [
    "NativeDucContractCatalog",
    "NativeDucFilterContract",
    "NativeDucResetContract",
    "NativeDucSearchContract",
    "NativeDucTargetContract",
    "analyze_duc",
    "default_native_duc_contract_catalog",
]
