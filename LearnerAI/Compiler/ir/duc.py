"""Typed intermediate representation for practical AoE2 DUC state.

The model is intentionally an abstract interpreter boundary, not a game
simulator. It captures the durable native state that experienced .per scripts
must reason about: search-list lineage, retained filters, targets, resets, and
source/pass provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..ast import SourceLocation
from ..semantic.rule_execution import RulePassBehavior


class DucListKind(str, Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class DucTargetKind(str, Enum):
    OBJECT = "OBJECT"
    POINT = "POINT"


class DucStateKind(str, Enum):
    LIST = "LIST"
    FILTER = "FILTER"
    TARGET = "TARGET"
    OUTPUT = "OUTPUT"
    GROUP = "GROUP"


class DucResetKind(str, Enum):
    FILTERS = "FILTERS"
    SEARCH_LOCAL = "SEARCH_LOCAL"
    SEARCH_REMOTE = "SEARCH_REMOTE"
    SEARCH_BOTH = "SEARCH_BOTH"
    FULL = "FULL"


class DucVisibility(str, Enum):
    SAME_RULE = "SAME_RULE"
    SAME_PASS_LATER_RULE = "SAME_PASS_LATER_RULE"
    NEXT_PASS = "NEXT_PASS"
    UNKNOWN = "UNKNOWN"


class DucTargetStatus(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DucGroupStatus(str, Enum):
    EMPTY = "EMPTY"
    VALID = "VALID"
    UNKNOWN = "UNKNOWN"


class DucGroupFlagState(str, Enum):
    SET = "SET"
    CLEARED = "CLEARED"
    UNKNOWN = "UNKNOWN"


class DucTargetProof(str, Enum):
    CURRENT_PASS_PROOF = "CURRENT_PASS_PROOF"
    PRESERVED_PROOF = "PRESERVED_PROOF"
    SYNTACTIC_RETENTION = "SYNTACTIC_RETENTION"
    UNKNOWN = "UNKNOWN"


class DucListMutationKind(str, Enum):
    SORT = "SORT"
    DEDUPE = "DEDUPE"
    REMOVE_MATCHES = "REMOVE_MATCHES"


class DucTargetTransition(str, Enum):
    UNCHANGED = "UNCHANGED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DucProvenance:
    command: str
    source_location: SourceLocation
    source_instance_id: str
    source_slice_ordinal: int
    rule_order: int
    within_rule_order: int
    pass_behavior: RulePassBehavior
    visible_as: DucVisibility
    state_revision: int
    pass_id: int = 0
    input_state_generations: tuple[int, ...] = ()
    semantic_contract_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    input_group_generations: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class DucFilterPredicate:
    command: str
    canonical_arguments: tuple[str, ...]
    semantic_identity: str


@dataclass(frozen=True)
class DucFilterState:
    generation: int
    predicates: tuple[DucFilterPredicate, ...] = ()
    fingerprint: str = ""
    initialized: bool = True
    retained: bool = False
    last_mutation: Optional[DucProvenance] = None
    path_ambiguous: bool = False


@dataclass(frozen=True)
class DucFilterSnapshot:
    generation: int
    fingerprint: str
    predicates: tuple[DucFilterPredicate, ...]
    provenance: Optional[DucProvenance]
    path_ambiguous: bool = False


@dataclass(frozen=True)
class DucCardinalityRange:
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < self.minimum:
            raise ValueError("invalid DUC cardinality range")


@dataclass(frozen=True)
class DucListGeneration:
    list_kind: DucListKind
    generation: int
    produced_by: DucProvenance
    cardinality: Optional[DucCardinalityRange]
    capacity: int
    content_fingerprint: Optional[str]
    last_search_cardinality: Optional[DucCardinalityRange] = None


@dataclass(frozen=True)
class DucSearchListState:
    list_kind: DucListKind
    current_generation: Optional[DucListGeneration]
    next_generation: int = 1
    initialized: bool = False
    path_ambiguous: bool = False
    generation_variants: tuple[DucListGeneration, ...] = ()


@dataclass(frozen=True)
class DucObjectRef:
    list_kind: DucListKind
    list_generation: Optional[int]
    list_index: Optional[int]
    native_object_id: Optional[str]
    provenance: DucProvenance
    index_stable: bool = True


@dataclass(frozen=True)
class DucPointRef:
    goal_span_request_id: Optional[str]
    x_goal: Optional[str]
    y_goal: Optional[str]
    point_fingerprint: Optional[str]
    provenance: DucProvenance


@dataclass(frozen=True)
class DucTargetState:
    kind: DucTargetKind
    generation: int
    object_refs: tuple[DucObjectRef, ...] = ()
    point_ref: Optional[DucPointRef] = None
    source_list_generation: Optional[int] = None
    source_filter_generation: Optional[int] = None
    provenance: Optional[DucProvenance] = None
    validity: DucTargetStatus = DucTargetStatus.UNKNOWN
    pass_id: int = 0
    proof: DucTargetProof = DucTargetProof.UNKNOWN


@dataclass(frozen=True)
class DucGroupState:
    group_id: int
    generation: int
    cardinality: DucCardinalityRange
    capacity: int = 40
    source_list: Optional[DucListKind] = None
    source_list_generation: Optional[int] = None
    source_index_start: Optional[int] = None
    requested_max_objects: Optional[int] = None
    content_fingerprint: Optional[str] = None
    provenance: Optional[DucProvenance] = None
    validity: DucGroupStatus = DucGroupStatus.EMPTY
    flag_state: DucGroupFlagState = DucGroupFlagState.UNKNOWN
    path_ambiguous: bool = False
    pass_id: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.group_id <= 19:
            raise ValueError("DUC group id must be within 0..19")
        if self.capacity != 40:
            raise ValueError("DUC group capacity must be 40")
        if self.generation < 0:
            raise ValueError("DUC group generation must be non-negative")
        if self.validity is DucGroupStatus.EMPTY and self.cardinality != DucCardinalityRange(0, 0):
            raise ValueError("empty DUC group must have zero cardinality")


@dataclass(frozen=True)
class DucGoalOutputSpan:
    start_goal_id: int
    width: int
    generation: int
    overwritten_generation: Optional[int]
    provenance: Optional[DucProvenance]
    cardinality: DucCardinalityRange
    path_ambiguous: bool = False
    pass_id: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.start_goal_id <= 16000:
            raise ValueError("DUC Goal output must use GoalId range 1..16000")
        if self.width != 1:
            raise ValueError("DUC group-size Goal output span must have width 1")
        if self.generation < 1:
            raise ValueError("DUC Goal output generation must be positive")
        if self.overwritten_generation is not None:
            if self.overwritten_generation < 1 or self.overwritten_generation >= self.generation:
                raise ValueError("DUC Goal output overwrite generation must precede its writer generation")
        if self.path_ambiguous and self.provenance is not None:
            raise ValueError("ambiguous DUC Goal output cannot retain a unique provenance")


@dataclass(frozen=True)
class DucGroupOperation:
    command: str
    group_id: int
    previous_generation: int
    resulting_generation: int
    provenance: DucProvenance


@dataclass(frozen=True)
class DucGroupSizeObservation:
    command: str
    group_id: int
    cardinality: DucCardinalityRange
    provenance: DucProvenance
    output_span: Optional[DucGoalOutputSpan] = None


@dataclass(frozen=True)
class DucSearchOperation:
    command: str
    list_kind: DucListKind
    input_predicate: str
    canonical_arguments: tuple[str, ...]
    consumed_filter: DucFilterSnapshot
    output_generation: DucListGeneration
    visibility: DucVisibility
    provenance: DucProvenance


@dataclass(frozen=True)
class DucListMutationEffect:
    command: str
    list_kind: DucListKind
    kind: DucListMutationKind
    object_data: str
    compare_operator: Optional[str]
    compare_value: Optional[str]
    target_transition: DucTargetTransition
    provenance: DucProvenance


@dataclass(frozen=True)
class DucResetEffect:
    command: str
    reset_kind: DucResetKind
    invalidates_lists: tuple[DucListKind, ...]
    invalidates_filter_state: bool
    invalidates_object_targets: bool
    invalidates_point_target: bool
    provenance: DucProvenance
    invalidates_local_index: bool = False
    invalidates_remote_index: bool = False


@dataclass(frozen=True)
class DucSearchStateObservation:
    source_list: DucListKind
    source_generation: Optional[int]
    output_goal_span_request_id: str
    state_fields: tuple[str, ...]
    observation_fingerprint: str
    provenance: DucProvenance
    local_total_cardinality: Optional[DucCardinalityRange] = None
    local_last_search_cardinality: Optional[DucCardinalityRange] = None
    remote_total_cardinality: Optional[DucCardinalityRange] = None
    remote_last_search_cardinality: Optional[DucCardinalityRange] = None


@dataclass(frozen=True)
class DucLoopWidening:
    loop_head_rule_order: int
    back_edge_source_rule_order: int
    iteration_limit: int
    iterations: int
    widened_fields: tuple[str, ...]


@dataclass(frozen=True)
class DucBranchMerge:
    rule_order: int
    predecessor_rule_orders: tuple[int, ...]
    merged_fields: tuple[str, ...]
    state_variants: int


@dataclass(frozen=True)
class DucExecutionEffect:
    rule_order: int
    within_rule_order: int
    pass_behavior: RulePassBehavior
    reads: tuple[DucStateKind, ...]
    writes: tuple[DucStateKind, ...]
    visibility: DucVisibility
    may_repeat: bool
    may_self_disable: bool


@dataclass(frozen=True)
class DucSemanticState:
    local_list: DucSearchListState
    remote_list: DucSearchListState
    filters: DucFilterState
    target: Optional[DucTargetState]
    point_target: Optional[DucPointRef]
    state_revision: int
    pass_id: int = 0
    groups: tuple[DucGroupState, ...] = ()
    goal_output_spans: tuple[DucGoalOutputSpan, ...] = ()

    def __post_init__(self) -> None:
        if not self.groups:
            object.__setattr__(
                self,
                "groups",
                tuple(
                    DucGroupState(
                        group_id=group_id,
                        generation=0,
                        cardinality=DucCardinalityRange(0, 0),
                        validity=DucGroupStatus.EMPTY,
                    )
                    for group_id in range(20)
                ),
            )
        elif len(self.groups) != 20:
            raise ValueError("DUC semantic state requires exactly 20 groups")
        if tuple(group.group_id for group in self.groups) != tuple(range(20)):
            raise ValueError("DUC group state must be ordered by group id")
        starts = tuple(span.start_goal_id for span in self.goal_output_spans)
        if starts != tuple(sorted(starts)) or len(starts) != len(set(starts)):
            raise ValueError("DUC Goal output spans must be uniquely ordered by start GoalId")


@dataclass(frozen=True)
class DucDiagnostic:
    code: str
    severity: str
    rule_order: int
    message: str
    location: SourceLocation


@dataclass(frozen=True)
class DucAnalysisReport:
    initial_state: DucSemanticState
    final_state: DucSemanticState
    states: tuple[tuple[int, DucSemanticState], ...]
    searches: tuple[DucSearchOperation, ...] = ()
    group_operations: tuple[DucGroupOperation, ...] = ()
    group_observations: tuple[DucGroupSizeObservation, ...] = ()
    resets: tuple[DucResetEffect, ...] = ()
    mutations: tuple[DucListMutationEffect, ...] = ()
    targets: tuple[DucTargetState, ...] = ()
    observations: tuple[DucSearchStateObservation, ...] = ()
    effects: tuple[DucExecutionEffect, ...] = ()
    diagnostics: tuple[DucDiagnostic, ...] = ()
    branch_merges: tuple[DucBranchMerge, ...] = ()
    loop_widenings: tuple[DucLoopWidening, ...] = ()
    next_pass_state: Optional[DucSemanticState] = None


__all__ = [
    "DucAnalysisReport",
    "DucCardinalityRange",
    "DucGoalOutputSpan",
    "DucGroupFlagState",
    "DucGroupOperation",
    "DucGroupSizeObservation",
    "DucGroupState",
    "DucGroupStatus",
    "DucBranchMerge",
    "DucDiagnostic",
    "DucExecutionEffect",
    "DucFilterPredicate",
    "DucFilterSnapshot",
    "DucFilterState",
    "DucListGeneration",
    "DucLoopWidening",
    "DucListMutationEffect",
    "DucListMutationKind",
    "DucListKind",
    "DucObjectRef",
    "DucPointRef",
    "DucProvenance",
    "DucResetEffect",
    "DucResetKind",
    "DucSearchListState",
    "DucSearchOperation",
    "DucSearchStateObservation",
    "DucSemanticState",
    "DucStateKind",
    "DucTargetKind",
    "DucTargetProof",
    "DucTargetTransition",
    "DucTargetState",
    "DucTargetStatus",
    "DucVisibility",
]
