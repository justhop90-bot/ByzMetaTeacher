"""Immutable patch and evidence primitives for the compiler data layer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class PatchId:
    product: str
    update: str
    build: str | None
    release_date: str

    @property
    def key(self) -> str:
        return f"{self.product}:{self.update}:{self.build or '-'}"

    @staticmethod
    def _component_key(value: str) -> tuple[int, object]:
        return (0, int(value)) if value.isdigit() else (1, value)

    @property
    def sort_key(self) -> tuple[object, object, object, object]:
        return (
            self.product,
            self._component_key(self.update),
            self._component_key(self.build or ""),
            self.release_date,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PatchId):
            return NotImplemented
        return self.sort_key < other.sort_key


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
    REPOSITORY_CONTROLLER = "REPOSITORY_CONTROLLER"


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
    target_patch: PatchId | None = None

    def verify_previous(self, actual_fingerprint: str) -> None:
        if self.previous_fingerprint is None:
            return
        if actual_fingerprint != self.previous_fingerprint:
            raise ValueError(
                f"patch change {self.entity_kind}:{self.entity_key} expected "
                f"previous fingerprint {self.previous_fingerprint}, got {actual_fingerprint}"
            )

    def applies_to(self, patch: PatchId) -> bool:
        return self.target_patch is None or self.target_patch == patch
