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
    input_state_generations: tuple[int, ...] = ()
    semantic_contract_id: str = ""
    evidence_ids: tuple[str, ...] = ()


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


@dataclass(frozen=True)
class DucFilterSnapshot:
    generation: int
    fingerprint: str
    predicates: tuple[DucFilterPredicate, ...]
    provenance: Optional[DucProvenance]


@dataclass(frozen=True)
class DucListGeneration:
    list_kind: DucListKind
    generation: int
    produced_by: DucProvenance
    cardinality: Optional[int]
    capacity: int
    content_fingerprint: Optional[str]


@dataclass(frozen=True)
class DucSearchListState:
    list_kind: DucListKind
    current_generation: Optional[DucListGeneration]
    next_generation: int = 1
    initialized: bool = False


@dataclass(frozen=True)
class DucObjectRef:
    list_kind: DucListKind
    list_generation: int
    list_index: Optional[int]
    native_object_id: Optional[str]
    provenance: DucProvenance


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
class DucResetEffect:
    command: str
    reset_kind: DucResetKind
    invalidates_lists: tuple[DucListKind, ...]
    invalidates_filter_state: bool
    invalidates_object_targets: bool
    invalidates_point_target: bool
    provenance: DucProvenance


@dataclass(frozen=True)
class DucSearchStateObservation:
    source_list: DucListKind
    source_generation: Optional[int]
    output_goal_span_request_id: str
    state_fields: tuple[str, ...]
    observation_fingerprint: str
    provenance: DucProvenance


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
    resets: tuple[DucResetEffect, ...] = ()
    targets: tuple[DucTargetState, ...] = ()
    observations: tuple[DucSearchStateObservation, ...] = ()
    effects: tuple[DucExecutionEffect, ...] = ()
    diagnostics: tuple[DucDiagnostic, ...] = ()


__all__ = [
    "DucAnalysisReport",
    "DucDiagnostic",
    "DucExecutionEffect",
    "DucFilterPredicate",
    "DucFilterSnapshot",
    "DucFilterState",
    "DucListGeneration",
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
    "DucTargetState",
    "DucTargetStatus",
    "DucVisibility",
]
