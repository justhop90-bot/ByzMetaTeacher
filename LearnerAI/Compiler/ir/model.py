"""Validated semantic intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from .strategy import StrategicBinding


class LifecycleState(str, Enum):
    RELEASED = "RELEASED"
    ACTIVE = "ACTIVE"
    ISSUED = "ISSUED"
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"


class GoalSpanKind(str, Enum):
    POINT_PAIR = "POINT_PAIR"
    EXTENDED_4 = "EXTENDED_4"


class AccessKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class StateStorageKind(str, Enum):
    LIFECYCLE = "LIFECYCLE"
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"


class LifecycleAccessPhase(str, Enum):
    INITIALIZATION = "INITIALIZATION"
    RELEASE = "RELEASE"
    COMPLETION_WITNESS = "COMPLETION_WITNESS"
    PENDING_ADMISSION = "PENDING_ADMISSION"
    ISSUANCE = "ISSUANCE"
    ACTION = "ISSUANCE"


class GoalRole(str, Enum):
    LIFECYCLE_STATE = "LIFECYCLE_STATE"
    PERSISTENT_STATE = "PERSISTENT_STATE"
    DERIVED_SCALAR = "DERIVED_SCALAR"
    NATIVE_OUTPUT = "NATIVE_OUTPUT"
    EXECUTION_MEMORY = "EXECUTION_MEMORY"


@dataclass(frozen=True, order=True)
class SemanticId:
    source_unit: str
    local_name: str


@dataclass(frozen=True)
class StateAccess:
    state: StorageRequestId
    owner: SemanticId | None
    demand: SemanticId
    kind: AccessKind
    phase: LifecycleAccessPhase | None
    source_order: int
    operation: str
    storage_kind: StateStorageKind = StateStorageKind.LIFECYCLE
    rule_order: int | None = None
    within_rule_order: int = 0

    def __post_init__(self) -> None:
        if self.source_order < 0:
            raise ValueError("state access source_order must be non-negative")
        if self.rule_order is not None and self.rule_order < 0:
            raise ValueError("state access rule_order must be non-negative")
        if self.within_rule_order < 0:
            raise ValueError("state access within_rule_order must be non-negative")


@dataclass(frozen=True)
class DemandOwnership:
    demand: SemanticId
    owner: SemanticId | None
    state: StorageRequestId


@dataclass(frozen=True, order=True)
class StorageRequestId:
    owner: SemanticId
    purpose: str


@dataclass(frozen=True)
class GoalSlotRequest:
    request_id: StorageRequestId
    role: GoalRole = GoalRole.LIFECYCLE_STATE

    @property
    def owner_id(self) -> SemanticId:
        return self.request_id.owner


@dataclass(frozen=True)
class GoalSpanRequest:
    request_id: StorageRequestId
    width: int
    shape: GoalSpanKind
    contract_id: str
    start_min: int
    start_max: int
    role: GoalRole = GoalRole.NATIVE_OUTPUT

    @property
    def owner_id(self) -> SemanticId:
        return self.request_id.owner


@dataclass(frozen=True)
class SemanticRequirement:
    expression: Expression
    role: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class SemanticAction:
    expression: Expression
    role: str
    arbitration_request: GoalSlotRequest | None = None
    location: SourceLocation | None = None


class WitnessEvidenceKind(str, Enum):
    WORLD_STATE = "WORLD_STATE"


@dataclass(frozen=True)
class CompletionWitnessContract:
    identity: SemanticId
    evidence_kind: WitnessEvidenceKind
    primitive: str
    expression: Expression
    establishes: SemanticId
    source_order: int
    issuance_source_order: int
    location: SourceLocation | None = None


class ReleaseEvidenceKind(str, Enum):
    WORLD_STATE = "WORLD_STATE"


@dataclass(frozen=True)
class ReleaseStateContract:
    identity: SemanticId
    evidence_kind: ReleaseEvidenceKind
    primitive: str
    expression: Expression
    establishes: SemanticId
    from_state: LifecycleState
    to_state: LifecycleState
    source_order: int
    witness_source_order: int
    location: SourceLocation | None = None


class InvalidationEvidenceKind(str, Enum):
    WORLD_STATE = "WORLD_STATE"


@dataclass(frozen=True)
class InvalidationContract:
    identity: SemanticId
    evidence_kind: InvalidationEvidenceKind
    primitive: str
    expression: Expression
    invalidates: SemanticId
    source_order: int
    action_source_order: int
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CancellationStateContract:
    identity: SemanticId
    trigger: SemanticId
    from_states: tuple[LifecycleState, ...]
    to_state: LifecycleState
    source_order: int
    invalidation_source_order: int
    release_source_order: int


@dataclass(frozen=True)
class ActionIssuance:
    demand: SemanticId
    primitive: str
    phase: ActionIssuancePhase
    issued_state: LifecycleState
    pending_state: LifecycleState
    failure: "ActionIssuanceFailure"
    retryable: bool = True
    source_order: int = 0
    location: SourceLocation | None = None


class ActionIssuancePhase(str, Enum):
    ATTEMPT = "ATTEMPT"
    PENDING_ADMISSION = "PENDING_ADMISSION"


class ActionIssuanceFailure(str, Enum):
    RETAIN_ACTIVE = "RETAIN_ACTIVE"


@dataclass(frozen=True)
class PendingDiagnostic:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class LifecycleStorage:
    slot: GoalSlotRequest
    initial_state: LifecycleState = LifecycleState.ACTIVE


@dataclass(frozen=True)
class SemanticDemand:
    identity: SemanticId
    lifecycle: LifecycleStorage
    requirements: tuple[SemanticRequirement, ...]
    action: SemanticAction
    witness: Expression
    release: Expression
    completion_witness: CompletionWitnessContract | None = None
    release_state: ReleaseStateContract | None = None
    invalidation: InvalidationContract | None = None
    cancellation: CancellationStateContract | None = None
    action_issuance: ActionIssuance | None = None
    ownership: DemandOwnership | None = None
    state_accesses: tuple[StateAccess, ...] = ()
    pending_diagnostics: tuple[PendingDiagnostic, ...] = ()
    strategic_binding: StrategicBinding | None = None
    location: SourceLocation | None = None

    @property
    def name(self) -> str:
        return self.identity.local_name
