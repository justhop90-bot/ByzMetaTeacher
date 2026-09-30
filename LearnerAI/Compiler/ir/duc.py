"""Typed intermediate representation for practical AoE2 DUC state.

The model is intentionally an abstract interpreter boundary, not a game
simulator. It captures the durable native state that experienced .per scripts
must reason about: search-list lineage, retained filters, targets, resets, and
source/pass provenance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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


class DucObjectLifecycleState(str, Enum):
    """Compiler-side identity lifecycle independent of native target-slot lifetime."""

    UNBOUND = "UNBOUND"
    DISCOVERED = "DISCOVERED"
    STORED = "STORED"
    REACQUIRED = "REACQUIRED"
    VALIDATED = "VALIDATED"
    INVALIDATED_NATIVE = "INVALIDATED_NATIVE"
    INVALIDATED_WORLD = "INVALIDATED_WORLD"
    INVALIDATED_UNKNOWN = "INVALIDATED_UNKNOWN"


class DucObjectLifecycleEvent(str, Enum):
    DISCOVER = "DISCOVER"
    STORE_ID = "STORE_ID"
    BIND_ID = "BIND_ID"
    REACQUIRE_BY_ID = "REACQUIRE_BY_ID"
    REACQUIRE_BY_SEARCH = "REACQUIRE_BY_SEARCH"
    VALIDATE = "VALIDATE"
    RELEASE = "RELEASE"
    NATIVE_FAILURE = "NATIVE_FAILURE"
    WORLD_WITNESS_GONE = "WORLD_WITNESS_GONE"
    IDENTITY_CONFLICT = "IDENTITY_CONFLICT"
    FRESH_DISCOVER = "FRESH_DISCOVER"


@dataclass(frozen=True)
class DucObjectLifecycleTransition:
    event: DucObjectLifecycleEvent
    from_state: DucObjectLifecycleState
    to_state: DucObjectLifecycleState
    identity_ref: Optional[str]
    failure_reason: Optional[str] = None


class DucObjectLifecycleError(ValueError):
    """Illegal compiler-side object lifecycle transition."""


@dataclass(frozen=True)
class DucObjectLifecycle:
    state: DucObjectLifecycleState = DucObjectLifecycleState.UNBOUND
    identity_ref: Optional[str] = None
    native_object_id: Optional[str] = None
    history: tuple[DucObjectLifecycleTransition, ...] = field(
        default=(),
        compare=False,
    )

    def _require(
        self,
        event: DucObjectLifecycleEvent,
        allowed: tuple[DucObjectLifecycleState, ...],
    ) -> None:
        if self.state not in allowed:
            raise DucObjectLifecycleError(
                f"{event.value} is illegal from {self.state.value}"
            )

    def _transition(
        self,
        event: DucObjectLifecycleEvent,
        to_state: DucObjectLifecycleState,
        *,
        identity_ref: Optional[str] = None,
        native_object_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> "DucObjectLifecycle":
        return DucObjectLifecycle(
            state=to_state,
            identity_ref=(
                self.identity_ref if identity_ref is None else identity_ref
            ),
            native_object_id=(
                self.native_object_id
                if native_object_id is None
                else native_object_id
            ),
            history=self.history
            + (
                DucObjectLifecycleTransition(
                    event=event,
                    from_state=self.state,
                    to_state=to_state,
                    identity_ref=(
                        self.identity_ref if identity_ref is None else identity_ref
                    ),
                    failure_reason=failure_reason,
                ),
            ),
        )

    def discover(self) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.DISCOVER,
            (DucObjectLifecycleState.UNBOUND,),
        )
        return self._transition(
            DucObjectLifecycleEvent.DISCOVER,
            DucObjectLifecycleState.DISCOVERED,
            identity_ref=None,
            native_object_id=None,
        )

    def fresh_discover(self) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.FRESH_DISCOVER,
            (
                DucObjectLifecycleState.INVALIDATED_NATIVE,
                DucObjectLifecycleState.INVALIDATED_WORLD,
                DucObjectLifecycleState.INVALIDATED_UNKNOWN,
            ),
        )
        return DucObjectLifecycle(
            state=DucObjectLifecycleState.DISCOVERED,
            identity_ref=None,
            native_object_id=None,
            history=self.history
            + (
                DucObjectLifecycleTransition(
                    event=DucObjectLifecycleEvent.FRESH_DISCOVER,
                    from_state=self.state,
                    to_state=DucObjectLifecycleState.DISCOVERED,
                    identity_ref=None,
                ),
            ),
        )

    def store_id(self, *, identity_ref: str) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.STORE_ID,
            (DucObjectLifecycleState.DISCOVERED,),
        )
        if not identity_ref:
            raise DucObjectLifecycleError("STORE_ID requires an identity binding")
        native_id = (
            identity_ref.removeprefix("native:")
            if identity_ref.startswith("native:")
            else None
        )
        return self._transition(
            DucObjectLifecycleEvent.STORE_ID,
            DucObjectLifecycleState.STORED,
            identity_ref=identity_ref,
            native_object_id=native_id,
        )

    def bind_id(self, *, native_object_id: str) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.BIND_ID,
            (DucObjectLifecycleState.UNBOUND,),
        )
        if not native_object_id:
            raise DucObjectLifecycleError(
                "BIND_ID requires a native object identity"
            )
        return self._transition(
            DucObjectLifecycleEvent.BIND_ID,
            DucObjectLifecycleState.STORED,
            identity_ref=f"native:{native_object_id}",
            native_object_id=native_object_id,
        )

    def reacquire_by_id(
        self,
        *,
        success: Optional[bool] = None,
    ) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.REACQUIRE_BY_ID,
            (DucObjectLifecycleState.STORED,),
        )
        if self.identity_ref is None:
            raise DucObjectLifecycleError(
                "REACQUIRE_BY_ID requires a stored identity"
            )
        if success is False:
            return self._transition(
                DucObjectLifecycleEvent.NATIVE_FAILURE,
                DucObjectLifecycleState.INVALIDATED_NATIVE,
                failure_reason="NATIVE_ACQUISITION_FAILED",
            )
        return self._transition(
            DucObjectLifecycleEvent.REACQUIRE_BY_ID,
            DucObjectLifecycleState.REACQUIRED,
        )

    def reacquire_by_search(
        self,
        *,
        candidate_identity_ref: str,
        success: Optional[bool] = None,
    ) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.REACQUIRE_BY_SEARCH,
            (DucObjectLifecycleState.STORED,),
        )
        if candidate_identity_ref != self.identity_ref:
            return self._transition(
                DucObjectLifecycleEvent.IDENTITY_CONFLICT,
                DucObjectLifecycleState.INVALIDATED_UNKNOWN,
                failure_reason="IDENTITY_CONFLICT",
            )
        if success is False:
            return self._transition(
                DucObjectLifecycleEvent.NATIVE_FAILURE,
                DucObjectLifecycleState.INVALIDATED_NATIVE,
                failure_reason="NATIVE_ACQUISITION_FAILED",
            )
        return self._transition(
            DucObjectLifecycleEvent.REACQUIRE_BY_SEARCH,
            DucObjectLifecycleState.REACQUIRED,
        )

    def validate(self, *, success: bool) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.VALIDATE,
            (DucObjectLifecycleState.REACQUIRED,),
        )
        if not success:
            return self._transition(
                DucObjectLifecycleEvent.NATIVE_FAILURE,
                DucObjectLifecycleState.INVALIDATED_NATIVE,
                failure_reason="NATIVE_VALIDATION_FAILED",
            )
        return self._transition(
            DucObjectLifecycleEvent.VALIDATE,
            DucObjectLifecycleState.VALIDATED,
        )

    def release(self) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.RELEASE,
            (
                DucObjectLifecycleState.REACQUIRED,
                DucObjectLifecycleState.VALIDATED,
            ),
        )
        return self._transition(
            DucObjectLifecycleEvent.RELEASE,
            DucObjectLifecycleState.STORED,
        )

    def invalidate_native(self) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.NATIVE_FAILURE,
            (
                DucObjectLifecycleState.STORED,
                DucObjectLifecycleState.REACQUIRED,
                DucObjectLifecycleState.VALIDATED,
            ),
        )
        return self._transition(
            DucObjectLifecycleEvent.NATIVE_FAILURE,
            DucObjectLifecycleState.INVALIDATED_NATIVE,
            failure_reason="NATIVE_ACQUISITION_FAILED",
        )

    def invalidate_world(self, *, world_witness: bool) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.WORLD_WITNESS_GONE,
            (
                DucObjectLifecycleState.STORED,
                DucObjectLifecycleState.REACQUIRED,
                DucObjectLifecycleState.VALIDATED,
            ),
        )
        if not world_witness:
            raise DucObjectLifecycleError(
                "WORLD_WITNESS_GONE requires an independent world witness"
            )
        return self._transition(
            DucObjectLifecycleEvent.WORLD_WITNESS_GONE,
            DucObjectLifecycleState.INVALIDATED_WORLD,
            failure_reason="WORLD_LIVENESS_WITNESS_FALSE",
        )

    def invalidate_unknown(self) -> "DucObjectLifecycle":
        self._require(
            DucObjectLifecycleEvent.IDENTITY_CONFLICT,
            (
                DucObjectLifecycleState.STORED,
                DucObjectLifecycleState.REACQUIRED,
                DucObjectLifecycleState.VALIDATED,
            ),
        )
        return self._transition(
            DucObjectLifecycleEvent.IDENTITY_CONFLICT,
            DucObjectLifecycleState.INVALIDATED_UNKNOWN,
            failure_reason="IDENTITY_UNRESOLVED",
        )


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
    NATIVE_ID_PROOF = "NATIVE_ID_PROOF"
    SYNTACTIC_RETENTION = "SYNTACTIC_RETENTION"
    UNKNOWN = "UNKNOWN"


class DucListMutationKind(str, Enum):
    ADD_OBJECT = "ADD_OBJECT"
    SORT = "SORT"
    DEDUPE = "DEDUPE"
    REMOVE_MATCHES = "REMOVE_MATCHES"


class DucSearchIndexResetReason(str, Enum):
    INITIAL = "INITIAL"
    EXPLICIT = "EXPLICIT"
    FILTER_CHANGED = "FILTER_CHANGED"
    QUERY_CHANGED = "QUERY_CHANGED"
    FOCUS_PLAYER_CHANGED = "FOCUS_PLAYER_CHANGED"
    UNKNOWN = "UNKNOWN"


class DucSearchCursorDisposition(str, Enum):
    INITIAL = "INITIAL"
    RESET_START = "RESET_START"
    RUNTIME_ADVANCED = "RUNTIME_ADVANCED"
    AT_END = "AT_END"
    BLOCKED_BY_CAPACITY = "BLOCKED_BY_CAPACITY"
    PATH_AMBIGUOUS = "PATH_AMBIGUOUS"


class DucSearchResultDisposition(str, Enum):
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    GUARANTEED_EMPTY = "GUARANTEED_EMPTY"


class DucSearchFactResult(str, Enum):
    NOT_A_FACT = "NOT_A_FACT"
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    GUARANTEED_FALSE = "GUARANTEED_FALSE"


class DucSearchAvailabilityResult(str, Enum):
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    GUARANTEED_FALSE = "GUARANTEED_FALSE"


class DucTargetFactResult(str, Enum):
    NOT_A_FACT = "NOT_A_FACT"
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    GUARANTEED_FALSE = "GUARANTEED_FALSE"


class DucTargetTransition(str, Enum):
    UNCHANGED = "UNCHANGED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class DucObjectLiveness(str, Enum):
    """Engine-world liveness is separate from compiler-side DUC retention."""

    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"
    WITNESSED_ALIVE = "WITNESSED_ALIVE"
    WITNESSED_GONE = "WITNESSED_GONE"


class DucTargetConsumerMode(str, Enum):
    LOCAL_SEARCH_RESULTS = "LOCAL_SEARCH_RESULTS"
    SELECTED_OBJECT_ONLY = "SELECTED_OBJECT_ONLY"


class DucTargetDataRelation(str, Enum):
    SELECTED_OBJECT = "SELECTED_OBJECT"
    SELECTED_OBJECT_TARGET = "SELECTED_OBJECT_TARGET"


@dataclass(frozen=True)
class DucTargetDataObservation:
    command: str
    relation: DucTargetDataRelation
    object_data: str
    source_kind: str
    writes_goal: bool
    target_validity: DucTargetStatus
    target_proof: DucTargetProof
    target_liveness: DucObjectLiveness
    provenance: DucProvenance
    output_span: Optional["DucGoalOutputSpan"] = None


@dataclass(frozen=True)
class DucTargetConsumerEffect:
    command: str
    mode: DucTargetConsumerMode
    provenance: DucProvenance
    local_list_generation: Optional[int]
    remote_list_generation: Optional[int]
    target_validity: DucTargetStatus
    target_proof: DucTargetProof
    target_liveness: DucObjectLiveness


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
class DucSearchIndexState:
    offset: Optional[int] = 0
    generation: int = 0
    query_signature: Optional[tuple[str, ...]] = None
    focus_player_signature: Optional[str] = None
    known: bool = True
    last_reset_reason: Optional[DucSearchIndexResetReason] = None
    cursor_disposition: DucSearchCursorDisposition = DucSearchCursorDisposition.INITIAL
    path_ambiguous: bool = False
    focus_player_provenance: Optional["DucProvenance"] = None

    def __post_init__(self) -> None:
        if self.offset is not None and self.offset < 0:
            raise ValueError("DUC search index offset must be non-negative")
        if self.generation < 0:
            raise ValueError("DUC search index generation must be non-negative")


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
    search_index: DucSearchIndexState = DucSearchIndexState()


@dataclass(frozen=True)
class DucObjectRef:
    list_kind: Optional[DucListKind]
    list_generation: Optional[int]
    list_index: Optional[int]
    native_object_id: Optional[str]
    provenance: DucProvenance
    index_stable: bool = True
    lifecycle: DucObjectLifecycle = DucObjectLifecycle()

    def __post_init__(self) -> None:
        if self.list_kind is None and (
            self.list_generation is not None or self.list_index is not None
        ):
            raise ValueError("direct DUC object identity cannot carry list coordinates")


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
    liveness: DucObjectLiveness = DucObjectLiveness.RUNTIME_DEPENDENT


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
    overwritten_provenance: Optional[DucProvenance]
    provenance: Optional[DucProvenance]
    cardinality: DucCardinalityRange
    path_ambiguous: bool = False
    pass_id: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.start_goal_id <= 16000:
            raise ValueError("DUC Goal output must use GoalId range 1..16000")
        if self.width not in {1, 2, 4}:
            raise ValueError("DUC Goal output span must have width 1, 2, or 4")
        if self.start_goal_id + self.width - 1 > 16000:
            raise ValueError("DUC Goal output span exceeds the native GoalId range")
        if self.generation < 1:
            raise ValueError("DUC Goal output generation must be positive")
        if self.overwritten_generation is None:
            if self.overwritten_provenance is not None:
                raise ValueError(
                    "DUC Goal output cannot retain overwritten provenance without an overwritten generation"
                )
        elif self.overwritten_generation < 1 or self.overwritten_generation >= self.generation:
            raise ValueError("DUC Goal output overwrite generation must precede its writer generation")
        if self.path_ambiguous and (
            self.provenance is not None
            or self.overwritten_provenance is not None
        ):
            raise ValueError("ambiguous DUC Goal output cannot retain unique provenance")


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
    index_before: Optional[int] = None
    index_after: Optional[int] = None
    index_generation: int = 0
    index_reset_reason: Optional[DucSearchIndexResetReason] = None
    cursor_before_disposition: DucSearchCursorDisposition = DucSearchCursorDisposition.INITIAL
    cursor_after_disposition: DucSearchCursorDisposition = DucSearchCursorDisposition.INITIAL
    result_disposition: DucSearchResultDisposition = DucSearchResultDisposition.RUNTIME_DEPENDENT
    source_kind: str = "ACTION"
    fact_result: DucSearchFactResult = DucSearchFactResult.NOT_A_FACT
    focus_player_signature: Optional[str] = None
    focus_player_provenance: Optional["DucProvenance"] = None


@dataclass(frozen=True)
class DucSearchAvailabilityObservation:
    command: str
    source_list: DucListKind
    result: DucSearchAvailabilityResult
    cursor_disposition: DucSearchCursorDisposition
    list_initialized: bool
    cardinality: Optional[DucCardinalityRange]
    provenance: "DucProvenance"


@dataclass(frozen=True)
class DucTargetFactObservation:
    command: str
    result: DucTargetFactResult
    target: Optional["DucTargetState"]
    provenance: "DucProvenance"


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
    local_search_cursor_disposition: DucSearchCursorDisposition = DucSearchCursorDisposition.INITIAL
    remote_search_cursor_disposition: DucSearchCursorDisposition = DucSearchCursorDisposition.INITIAL
    output_span: Optional[DucGoalOutputSpan] = None


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
    target_fact_observations: tuple[DucTargetFactObservation, ...] = ()
    search_availability: tuple[DucSearchAvailabilityObservation, ...] = ()
    target_consumers: tuple[DucTargetConsumerEffect, ...] = ()
    target_data_observations: tuple[DucTargetDataObservation, ...] = ()
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
    "DucTargetConsumerEffect",
    "DucObjectLifecycle",
    "DucObjectLifecycleError",
    "DucObjectLifecycleEvent",
    "DucObjectLifecycleState",
    "DucObjectLifecycleTransition",
    "DucObjectLiveness",
    "DucTargetFactObservation",
    "DucTargetConsumerMode",
    "DucTargetDataObservation",
    "DucTargetDataRelation",
    "DucFilterPredicate",
    "DucFilterSnapshot",
    "DucFilterState",
    "DucListGeneration",
    "DucSearchCursorDisposition",
    "DucSearchIndexResetReason",
    "DucSearchIndexState",
    "DucSearchResultDisposition",
    "DucSearchFactResult",
    "DucSearchAvailabilityObservation",
    "DucSearchAvailabilityResult",
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
    "DucTargetFactResult",
    "DucTargetKind",
    "DucTargetProof",
    "DucTargetTransition",
    "DucTargetState",
    "DucTargetStatus",
    "DucVisibility",
]
