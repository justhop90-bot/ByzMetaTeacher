"""Validated semantic intermediate representation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression


class LifecycleState(str, Enum):
    RELEASED = "RELEASED"
    ACTIVE = "ACTIVE"
    ISSUED = "ISSUED"
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"


class GoalSpanKind(str, Enum):
    POINT_PAIR = "POINT_PAIR"
    EXTENDED_4 = "EXTENDED_4"


class AccessKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


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


@dataclass(frozen=True, order=True)
class StateAccess:
    state: StorageRequestId
    owner: SemanticId | None
    demand: SemanticId
    kind: AccessKind
    phase: LifecycleAccessPhase
    source_order: int
    operation: str


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


@dataclass(frozen=True)
class SemanticAction:
    expression: Expression
    role: str
    arbitration_request: GoalSlotRequest | None = None


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
    completion_witness: CompletionWitnessContract | None = None
    release: Expression
    action_issuance: ActionIssuance | None = None
    ownership: DemandOwnership | None = None
    state_accesses: tuple[StateAccess, ...] = ()
    pending_diagnostics: tuple[PendingDiagnostic, ...] = ()

    @property
    def name(self) -> str:
        return self.identity.local_name
