"""Typed native resource-control and transient action-exclusion IR."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from .model import SemanticId, StorageRequestId


class NativeControlStorage(str, Enum):
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"


class NativeArbitrationReleaseKind(str, Enum):
    RESET_TO_FREE = "RESET_TO_FREE"
    HANDOFF = "HANDOFF"


class NativeArbitrationRecoveryKind(str, Enum):
    RETAIN_DEMAND = "RETAIN_DEMAND"
    RELEASE_AND_RETRY = "RELEASE_AND_RETRY"
    HANDOFF_AND_RETRY = "HANDOFF_AND_RETRY"


class NativeArbitrationStarvationPolicy(str, Enum):
    REQUIRE_RELEASE_OR_HANDOFF = "REQUIRE_RELEASE_OR_HANDOFF"


class EscrowAdmissionMode(str, Enum):
    NORMAL_STOCKPILE_ONLY = "NORMAL_STOCKPILE_ONLY"
    INCLUDE_ESCROW = "INCLUDE_ESCROW"


class EscrowOperationKind(str, Enum):
    """Executable escrow mutation/consumption step within one lifecycle package."""

    RELEASE = "RELEASE"
    CONSUME = "CONSUME"
    POLICY_RESET = "POLICY_RESET"


@dataclass(frozen=True)
class EscrowOperation:
    """One ordered native escrow operation tied to one semantic contract."""

    contract_identity: str
    owner: SemanticId
    kind: EscrowOperationKind
    resource: str
    command: str
    rule_order: int
    within_rule_order: int = 0
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.contract_identity.strip():
            raise ValueError("escrow operation contract identity must not be empty")
        if not self.resource.strip():
            raise ValueError("escrow operation resource must not be empty")
        if not self.command.strip():
            raise ValueError("escrow operation command must not be empty")
        if self.rule_order < 0 or self.within_rule_order < 0:
            raise ValueError("escrow operation order values must be non-negative")


class EscrowReserveKind(str, Enum):
    SET_PERCENTAGE = "SET_PERCENTAGE"
    MODIFY_AMOUNT = "MODIFY_AMOUNT"


class EscrowReleaseKind(str, Enum):
    RELEASE_TO_STOCKPILE = "RELEASE_TO_STOCKPILE"


class EscrowRetentionPolicy(str, Enum):
    REQUIRE_RELEASE_OR_CONSUMPTION = "REQUIRE_RELEASE_OR_CONSUMPTION"


class EscrowConsumptionMode(str, Enum):
    NON_ESCROW_ACTION = "NON_ESCROW_ACTION"
    ESCROW_AWARE_ACTION = "ESCROW_AWARE_ACTION"


class TransientClaimKind(str, Enum):
    ACTION_EXCLUSION = "ACTION_EXCLUSION"


class TransientClaimScope(str, Enum):
    RULE_PASS = "RULE_PASS"


@dataclass(frozen=True)
class NativeArbitrationRelease:
    kind: NativeArbitrationReleaseKind
    trigger: Expression
    handoff_owner: SemanticId | None = None


@dataclass(frozen=True)
class NativeArbitrationRecovery:
    kind: NativeArbitrationRecoveryKind
    trigger: Expression
    preserves_demand: bool = True


@dataclass(frozen=True)
class NativeArbitrationContract:
    identity: str
    owner: SemanticId
    storage: StorageRequestId
    storage_kind: NativeControlStorage
    surface_id: str
    free_value: int
    claim_value: int
    acquisition_guard: Expression
    release: NativeArbitrationRelease
    recovery: NativeArbitrationRecovery
    starvation_policy: NativeArbitrationStarvationPolicy = (
        NativeArbitrationStarvationPolicy.REQUIRE_RELEASE_OR_HANDOFF
    )
    location: SourceLocation | None = None


@dataclass(frozen=True)
class EscrowReserve:
    kind: EscrowReserveKind
    command: str
    percentage: int | None = None
    amount_expression: Expression | None = None


@dataclass(frozen=True)
class EscrowRelease:
    kind: EscrowReleaseKind
    command: str
    trigger: Expression


@dataclass(frozen=True)
class EscrowConsumption:
    mode: EscrowConsumptionMode
    action_primitive: str


@dataclass(frozen=True)
class EscrowContract:
    identity: str
    owner: SemanticId
    resources: tuple[str, ...]
    admission_mode: EscrowAdmissionMode
    reserve: EscrowReserve
    release: EscrowRelease
    consumption: EscrowConsumption
    arbitration_identity: str | None = None
    retention_policy: EscrowRetentionPolicy = (
        EscrowRetentionPolicy.REQUIRE_RELEASE_OR_CONSUMPTION
    )
    location: SourceLocation | None = None


@dataclass(frozen=True)
class TransientActionExclusionClaim:
    identity_source_unit: str
    identity_local_name: str
    claimant: SemanticId
    conflict_class: str
    arbitration_owner: SemanticId
    kind: TransientClaimKind = TransientClaimKind.ACTION_EXCLUSION
    scope: TransientClaimScope = TransientClaimScope.RULE_PASS
    location: SourceLocation | None = None

    @property
    def identity(self) -> str:
        return f"{self.identity_source_unit}:{self.identity_local_name}"


__all__ = [
    "EscrowAdmissionMode",
    "EscrowOperation",
    "EscrowOperationKind",
    "EscrowConsumption",
    "EscrowConsumptionMode",
    "EscrowContract",
    "EscrowRelease",
    "EscrowReleaseKind",
    "EscrowReserve",
    "EscrowReserveKind",
    "EscrowRetentionPolicy",
    "NativeArbitrationContract",
    "NativeArbitrationRecovery",
    "NativeArbitrationRecoveryKind",
    "NativeArbitrationRelease",
    "NativeArbitrationReleaseKind",
    "NativeArbitrationStarvationPolicy",
    "NativeControlStorage",
    "TransientActionExclusionClaim",
    "TransientClaimKind",
    "TransientClaimScope",
]
