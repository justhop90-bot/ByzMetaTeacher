"""Typed operational-semantics IR for recurrent AoE2 .per control.

This layer describes how a semantic demand drives a persistent, partially
observable native engine. It is deliberately not a simulator and does not
invent native acknowledgements.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression, SourceLocation
from .model import SemanticId
from .versioning import EvidenceRef


class OperationalDomain(str, Enum):
    GENERIC = "GENERIC"
    ATTACK = "ATTACK"
    PRODUCTION = "PRODUCTION"
    CONSTRUCTION = "CONSTRUCTION"
    RESEARCH = "RESEARCH"
    DUC = "DUC"
    ESCROW = "ESCROW"
    TIMER = "TIMER"
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"


class OperationalEvidenceClass(str, Enum):
    ENGINE_FACT = "ENGINE FACT"
    COMMUNITY_PRACTICE = "COMMUNITY PRACTICE"
    COMPILER_POLICY = "COMPILER POLICY"
    OPEN_UNKNOWN = "OPEN / UNKNOWN"


class OperationalRequestKind(str, Enum):
    ACTION = "ACTION"
    ATTACK_CONTROLLER = "ATTACK_CONTROLLER"
    DUC_OPERATION = "DUC_OPERATION"
    ESCROW_OPERATION = "ESCROW_OPERATION"
    GOAL_MUTATION = "GOAL_MUTATION"
    STRATEGIC_NUMBER_MUTATION = "STRATEGIC_NUMBER_MUTATION"
    TIMER_MUTATION = "TIMER_MUTATION"


class OperationalObservationRole(str, Enum):
    ADMISSION = "ADMISSION"
    DEBOUNCE = "DEBOUNCE"
    WORLD_STATE = "WORLD_STATE"
    CONTROL_STATE = "CONTROL_STATE"
    IDENTITY = "IDENTITY"
    CAPABILITY = "CAPABILITY"
    TIMING = "TIMING"
    REASSESSMENT = "REASSESSMENT"


class OperationalControlKind(str, Enum):
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"
    DUC_IDENTITY = "DUC_IDENTITY"
    ESCROW = "ESCROW"
    RETRY_BARRIER = "RETRY_BARRIER"


class OperationalControlUse(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DEBOUNCE = "DEBOUNCE"
    REASSERT = "REASSERT"


class OperationalCombination(str, Enum):
    ALL = "ALL"
    ANY = "ANY"


class OperationalRecoveryStrategy(str, Enum):
    REISSUE_REQUEST = "REISSUE_REQUEST"
    RESTORE_GOAL = "RESTORE_GOAL"
    RESTORE_STRATEGIC_NUMBER = "RESTORE_STRATEGIC_NUMBER"
    REARM_TIMER = "REARM_TIMER"
    REACQUIRE_DUC_IDENTITY = "REACQUIRE_DUC_IDENTITY"
    RELEASE_ESCROW = "RELEASE_ESCROW"
    HANDOFF_RESOURCE_CONTROL = "HANDOFF_RESOURCE_CONTROL"
    REASSESS = "REASSESS"


@dataclass(frozen=True)
class OperationalObservation:
    """One native/compiler-visible observation used by an operational loop."""

    identity: str
    role: OperationalObservationRole
    evidence_class: OperationalEvidenceClass
    expression: Expression | None = None
    reference: str | None = None
    provenance: tuple[EvidenceRef, ...] = ()
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational observation identity must not be empty")
        if (self.expression is None) == (self.reference is None):
            raise ValueError(
                "operational observation requires exactly one of expression or reference"
            )
        if self.reference is not None and not self.reference.strip():
            raise ValueError("operational observation reference must not be empty")
        if (
            self.evidence_class is not OperationalEvidenceClass.COMPILER_POLICY
            and not self.provenance
        ):
            raise ValueError(
                "non-policy operational observations require evidence provenance"
            )


@dataclass(frozen=True)
class OperationalStage:
    """Ordered observation references participating in one control stage."""

    identity: str
    observation_ids: tuple[str, ...]
    combination: OperationalCombination = OperationalCombination.ALL

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational stage identity must not be empty")
        if len(self.observation_ids) != len(set(self.observation_ids)):
            raise ValueError("operational stage observation IDs must be unique")
        if any(not item.strip() for item in self.observation_ids):
            raise ValueError("operational stage observation IDs must be non-empty")


@dataclass(frozen=True)
class OperationalCondition:
    """Boolean condition over one named operational observation."""

    observation_id: str
    expected: bool = True

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("operational condition observation ID must not be empty")


@dataclass(frozen=True)
class OperationalGuard:
    """Boolean guard used for admission, debounce, or retry."""

    identity: str
    conditions: tuple[OperationalCondition, ...]
    combination: OperationalCombination = OperationalCombination.ALL

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational guard identity must not be empty")
        if len(self.conditions) != len(
            {condition.observation_id for condition in self.conditions}
        ):
            raise ValueError("operational guard observation IDs must be unique")


@dataclass(frozen=True)
class OperationalRequest:
    """Native/compiler request issued after successful admission."""

    identity: str
    kind: OperationalRequestKind
    commands: tuple[Expression, ...] = ()
    execution_ref: str | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational request identity must not be empty")
        if not self.commands and not (
            self.execution_ref is not None and self.execution_ref.strip()
        ):
            raise ValueError(
                "operational request requires commands or an execution reference"
            )
        if self.execution_ref is not None and not self.execution_ref.strip():
            raise ValueError("operational request execution reference must not be empty")


@dataclass(frozen=True)
class OperationalControlRef:
    """Existing persistent compiler/native state participating in the loop."""

    kind: OperationalControlKind
    reference: str
    use: OperationalControlUse

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("operational control reference must not be empty")


@dataclass(frozen=True)
class OperationalRecovery:
    """Reassertion policy after the desired state is not established."""

    identity: str
    strategies: tuple[OperationalRecoveryStrategy, ...]
    preserves_demand: bool = True
    max_retries: int | None = None
    retry_guard: OperationalGuard | None = None
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational recovery identity must not be empty")
        if not self.strategies:
            raise ValueError("operational recovery requires at least one strategy")
        if self.max_retries is not None and self.max_retries < 0:
            raise ValueError("operational recovery max_retries must be non-negative")


@dataclass(frozen=True)
class OperationalLoopContract:
    """One complete observe/admit/request/debounce/reobserve/reassert loop."""

    identity: str
    domain: OperationalDomain
    demand: SemanticId
    observations: tuple[OperationalObservation, ...]
    observe: OperationalStage
    admission: OperationalGuard
    request: OperationalRequest
    debounce: OperationalGuard
    reobserve: OperationalStage
    recovery: OperationalRecovery
    controls: tuple[OperationalControlRef, ...] = ()
    evidence_class: OperationalEvidenceClass = OperationalEvidenceClass.COMPILER_POLICY
    provenance: tuple[EvidenceRef, ...] = ()
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("operational loop identity must not be empty")
        observation_ids = tuple(item.identity for item in self.observations)
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("operational observation identities must be unique")
        control_keys = tuple((item.kind.value, item.reference, item.use.value) for item in self.controls)
        if len(control_keys) != len(set(control_keys)):
            raise ValueError("operational control references must be unique")
        if (
            self.evidence_class is not OperationalEvidenceClass.COMPILER_POLICY
            and not self.provenance
        ):
            raise ValueError(
                "non-policy operational loops require evidence provenance"
            )


@dataclass(frozen=True)
class OperationalSemanticsPlan:
    """Deterministically ordered collection of operational contracts."""

    contracts: tuple[OperationalLoopContract, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(contract.identity for contract in self.contracts)
        if len(identities) != len(set(identities)):
            raise ValueError("operational contract identities must be unique")
        ordered = tuple(
            sorted(
                self.contracts,
                key=lambda contract: (
                    contract.domain.value,
                    contract.demand,
                    contract.identity,
                ),
            )
        )
        if ordered != self.contracts:
            raise ValueError(
                "operational contracts must be declared in deterministic order"
            )

    @property
    def empty(self) -> bool:
        return not self.contracts

    @property
    def identities(self) -> tuple[str, ...]:
        return tuple(contract.identity for contract in self.contracts)


__all__ = [
    "OperationalCombination",
    "OperationalCondition",
    "OperationalControlKind",
    "OperationalControlRef",
    "OperationalControlUse",
    "OperationalDomain",
    "OperationalEvidenceClass",
    "OperationalLoopContract",
    "OperationalObservation",
    "OperationalObservationRole",
    "OperationalRecovery",
    "OperationalRecoveryStrategy",
    "OperationalRequest",
    "OperationalRequestKind",
    "OperationalSemanticsPlan",
    "OperationalStage",
]
