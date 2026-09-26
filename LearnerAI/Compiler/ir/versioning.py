"""Immutable patch and evidence primitives for the compiler data layer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, order=True)
class PatchId:
    product: str
    update: str
    build: str | None
    release_date: str

    @property
    def key(self) -> str:
        return f"{self.product}:{self.update}:{self.build or '-'}"


@dataclass(frozen=True)
class Validity:
    introduced: PatchId
    removed: PatchId | None = None

    def contains(self, patch: PatchId) -> bool:
        if patch.product != self.introduced.product or patch < self.introduced:
            return False
        return self.removed is None or patch < self.removed


class EvidenceKind(str, Enum):
    ENGINE_DATA = "ENGINE_DATA"
    AIREF = "AIREF"
    OFFICIAL_PATCH = "OFFICIAL_PATCH"
    COMMUNITY_REFERENCE = "COMMUNITY_REFERENCE"
    RUNTIME_VERIFIED = "RUNTIME_VERIFIED"
    REPOSITORY_MANIFEST = "REPOSITORY_MANIFEST"


@dataclass(frozen=True)
class EvidenceRef:
    kind: EvidenceKind
    source: str
    revision: str
    locator: str
    patch: PatchId
    content_hash: str | None = None
    extraction_version: str = "1"
    verification: str = "verified"

    def stable_key(self) -> str:
        return "|".join(
            (
                self.kind.value,
                self.source,
                self.revision,
                self.locator,
                self.patch.key,
                self.content_hash or "",
                self.extraction_version,
                self.verification,
            )
        )


class PatchOperationKind(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    REPLACE = "REPLACE"


@dataclass(frozen=True)
class PatchChange:
    entity_kind: str
    entity_key: str
    operation: PatchOperationKind
    previous_fingerprint: str | None
    replacement_fingerprint: str | None
    changes: tuple[tuple[str, str], ...]
    provenance: tuple[EvidenceRef, ...]
