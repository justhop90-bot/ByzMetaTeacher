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
    percentage: int | None = None
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


NATIVE_ESCROW_RELEASE_COMMAND = "release-escrow"
NATIVE_ESCROW_RELEASE_RESOURCES = ("food", "wood", "stone", "gold")
NATIVE_ESCROW_POLICY_COMMAND = "set-escrow-percentage"
NATIVE_ESCROW_POLICY_RESOURCES = NATIVE_ESCROW_RELEASE_RESOURCES


@dataclass(frozen=True)
class NativeEscrowPolicyPlan:
    """Typed compiler-owned plan for explicit escrow percentage policy mutation."""

    operations: tuple[EscrowOperation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.operations, tuple):
            raise TypeError("native escrow policy plan operations must be a tuple")
        identities = tuple(operation.contract_identity for operation in self.operations)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native escrow policy contract identity")
        keys = tuple(
            (operation.rule_order, operation.within_rule_order, operation.contract_identity)
            for operation in self.operations
        )
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native escrow policy operations must be declared in deterministic order"
            )
        for operation in self.operations:
            if operation.kind is not EscrowOperationKind.POLICY_RESET:
                raise ValueError(
                    "native escrow policy plan accepts only POLICY_RESET operations"
                )
            if operation.command != NATIVE_ESCROW_POLICY_COMMAND:
                raise ValueError(
                    "native escrow policy operations must use set-escrow-percentage"
                )
            if operation.resource not in NATIVE_ESCROW_POLICY_RESOURCES:
                raise ValueError(
                    f"unsupported native escrow policy resource '{operation.resource}'"
                )
            if operation.percentage is None or not 0 <= operation.percentage <= 100:
                raise ValueError(
                    "native escrow policy percentage must be an integer in 0..100"
                )

    @property
    def empty(self) -> bool:
        return not self.operations

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted({operation.command for operation in self.operations}))


@dataclass(frozen=True)
class NativeEscrowReleasePlan:
    """Typed compiler-owned plan for the promoted release-escrow slice."""

    operations: tuple[EscrowOperation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.operations, tuple):
            raise TypeError("native escrow release plan operations must be a tuple")
        identities = tuple(operation.contract_identity for operation in self.operations)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native escrow release contract identity")
        keys = tuple(
            (operation.rule_order, operation.within_rule_order, operation.contract_identity)
            for operation in self.operations
        )
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "native escrow release operations must be declared in deterministic order"
            )
        for operation in self.operations:
            if operation.kind is not EscrowOperationKind.RELEASE:
                raise ValueError(
                    "native escrow release plan accepts only RELEASE operations"
                )
            if operation.command != NATIVE_ESCROW_RELEASE_COMMAND:
                raise ValueError(
                    "native escrow release operations must use release-escrow"
                )
            if operation.resource not in NATIVE_ESCROW_RELEASE_RESOURCES:
                raise ValueError(
                    f"unsupported native escrow release resource '{operation.resource}'"
                )

    @property
    def empty(self) -> bool:
        return not self.operations

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted({operation.command for operation in self.operations}))


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
    "NATIVE_ESCROW_RELEASE_COMMAND",
    "NATIVE_ESCROW_RELEASE_RESOURCES",
    "NATIVE_ESCROW_POLICY_COMMAND",
    "NATIVE_ESCROW_POLICY_RESOURCES",
    "NativeEscrowPolicyPlan",
    "NativeEscrowReleasePlan",
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
