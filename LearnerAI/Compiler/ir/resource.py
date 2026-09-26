"""Typed transient resource-claim and conflict semantic IR."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import SourceLocation
from .model import SemanticId


class ResourceScope(str, Enum):
    TRANSIENT = "TRANSIENT"


class ResourceKind(str, Enum):
    ACTION_EXCLUSION = "ACTION_EXCLUSION"


@dataclass(frozen=True, order=True)
class ResourceClaimId:
    source_unit: str
    local_name: str


@dataclass(frozen=True)
class ResourceClaim:
    identity: ResourceClaimId
    kind: ResourceKind
    scope: ResourceScope
    claimant: SemanticId
    conflict_class: str
    arbitration_owner: SemanticId
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ConflictContract:
    conflict_class: str
    kind: ResourceKind
    scope: ResourceScope
    arbitration_owner: SemanticId
    providers: tuple[SemanticId, ...]


@dataclass(frozen=True)
class ResourceConflictGraph:
    claims: tuple[ResourceClaim, ...]
    conflicts: tuple[ConflictContract, ...]


__all__ = [
    "ConflictContract",
    "ResourceClaim",
    "ResourceClaimId",
    "ResourceConflictGraph",
    "ResourceKind",
    "ResourceScope",
]
