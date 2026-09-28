"""Typed semantic-to-native runtime storage binding."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable, Iterator

from .ir import (
    GoalRole,
    GoalSlotRequest,
    GoalSpanKind,
    GoalSpanRequest,
    SemanticId,
    StorageRequestId,
    StrategicNumberStorageRequest,
)


GOAL_ID_MIN = 1
GOAL_ID_MAX = 16_000
ORDINARY_GOAL_MAX = 512
LIFECYCLE_GOAL_MAX = ORDINARY_GOAL_MAX
SN_ID_MIN = 0
SN_ID_MAX = 511
TIMER_ID_MIN = 1
TIMER_ID_MAX = 50
ALLOCATOR_VERSION = "native-storage-v5"
BINDING_MANIFEST_SCHEMA = "aoe2.compiler.binding-manifest"
BINDING_MANIFEST_VERSION = 4
GoalStorageShape = GoalSpanKind


class StorageKind(str, Enum):
    GOAL_SLOT = "GOAL_SLOT"
    GOAL_SPAN = "GOAL_SPAN"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"


class NativeParameterKind(str, Enum):
    CONSTANT = "CONSTANT"
    GOAL_ID = "GOAL_ID"
    GOAL_VALUE = "GOAL_VALUE"
    GOAL_SPAN_START = "GOAL_SPAN_START"
    SN_ID = "SN_ID"
    TIMER_ID = "TIMER_ID"


@dataclass(frozen=True, order=True)
class PackageStorageReservation:
    kind: StorageKind
    start: int
    end: int
    provenance_id: str

    def __post_init__(self) -> None:
        if not self.provenance_id.strip():
            raise ValueError("package storage reservation requires provenance_id")
        if self.start > self.end:
            raise ValueError("package storage reservation start must not exceed end")

        if self.kind is StorageKind.GOAL_SLOT:
            if self.start != self.end:
                raise ValueError("GOAL_SLOT reservation must cover exactly one GoalId")
            GoalId(self.start)
            return

        if self.kind is StorageKind.GOAL_SPAN:
            GoalInterval(self.start, self.end)
            return

        if self.start != self.end:
            raise ValueError(
                f"{self.kind.value} reservation must cover exactly one identifier"
            )

        if self.kind is StorageKind.STRATEGIC_NUMBER:
            if not SN_ID_MIN <= self.start <= SN_ID_MAX:
                raise ValueError(
                    f"Strategic Number id must be in range {SN_ID_MIN}..{SN_ID_MAX}"
                )
        elif self.kind is StorageKind.TIMER:
            if not TIMER_ID_MIN <= self.start <= TIMER_ID_MAX:
                raise ValueError(
                    f"Timer id must be in range {TIMER_ID_MIN}..{TIMER_ID_MAX}"
                )
        else:
            raise ValueError(f"unsupported package storage kind {self.kind}")

    @property
    def interval(self) -> GoalInterval | None:
        if self.kind in {StorageKind.GOAL_SLOT, StorageKind.GOAL_SPAN}:
            return GoalInterval(self.start, self.end)
        return None


@dataclass(frozen=True)
class PackageStorageInventory:
    package_id: str
    package_revision: str
    reservations: tuple[PackageStorageReservation, ...] = ()

    def __post_init__(self) -> None:
        if not self.package_id.strip():
            raise ValueError("package storage inventory requires package_id")
        if not self.package_revision.strip():
            raise ValueError("package storage inventory requires package_revision")

        seen_provenance: set[str] = set()
        goal_intervals: list[GoalInterval] = []
        sn_ids: set[int] = set()
        timer_ids: set[int] = set()

        for reservation in self.reservations:
            if reservation.provenance_id in seen_provenance:
                raise ValueError(
                    f"duplicate package storage reservation provenance {reservation.provenance_id}"
                )
            seen_provenance.add(reservation.provenance_id)

            if reservation.interval is not None:
                interval = reservation.interval
                if any(interval.overlaps(existing) for existing in goal_intervals):
                    raise ValueError(
                        f"overlapping Goal storage reservations at "
                        f"{interval.start}..{interval.end}"
                    )
                goal_intervals.append(interval)
            elif reservation.kind is StorageKind.STRATEGIC_NUMBER:
                if reservation.start in sn_ids:
                    raise ValueError(
                        f"duplicate occupied Strategic Number {reservation.start}"
                    )
                sn_ids.add(reservation.start)
            elif reservation.kind is StorageKind.TIMER:
                if reservation.start in timer_ids:
                    raise ValueError(
                        f"duplicate occupied TimerId {reservation.start}"
                    )
                timer_ids.add(reservation.start)

    @property
    def inventory_sha(self) -> str:
        material = json.dumps(
            {
                "package_id": self.package_id,
                "package_revision": self.package_revision,
                "reservations": [
                    {
                        "kind": reservation.kind.value,
                        "start": reservation.start,
                        "end": reservation.end,
                        "provenance_id": reservation.provenance_id,
                    }
                    for reservation in sorted(self.reservations)
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @property
    def occupied_goal_ids(self) -> frozenset[int]:
        return frozenset(
            reservation.start
            for reservation in self.reservations
            if reservation.kind is StorageKind.GOAL_SLOT
        )

    @property
    def occupied_goal_intervals(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (reservation.start, reservation.end)
            for reservation in sorted(self.reservations)
            if reservation.kind is StorageKind.GOAL_SPAN
        )

    @property
    def occupied_sn_ids(self) -> frozenset[int]:
        return frozenset(
            reservation.start
            for reservation in self.reservations
            if reservation.kind is StorageKind.STRATEGIC_NUMBER
        )

    @property
    def occupied_timer_ids(self) -> frozenset[int]:
        return frozenset(
            reservation.start
            for reservation in self.reservations
            if reservation.kind is StorageKind.TIMER
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "format_version": 1,
            "package_id": self.package_id,
            "package_revision": self.package_revision,
            "inventory_sha": self.inventory_sha,
            "reservations": [
                {
                    "kind": reservation.kind.value,
                    "start": reservation.start,
                    "end": reservation.end,
                    "provenance_id": reservation.provenance_id,
                }
                for reservation in sorted(self.reservations)
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "PackageStorageInventory":
        expected = {
            "format_version",
            "package_id",
            "package_revision",
            "inventory_sha",
            "reservations",
        }
        if set(payload) != expected:
            raise ValueError("package storage inventory has missing or extra fields")
        if payload["format_version"] != 1:
            raise ValueError(
                f"unsupported package storage inventory version {payload['format_version']}"
            )
        raw_reservations = payload["reservations"]
        if not isinstance(raw_reservations, list):
            raise ValueError("package storage inventory reservations must be an array")

        reservations = []
        expected_reservation_fields = {
            "kind",
            "start",
            "end",
            "provenance_id",
        }
        for index, raw in enumerate(raw_reservations):
            if not isinstance(raw, dict):
                raise ValueError(
                    f"package storage inventory reservation {index} must be an object"
                )
            if set(raw) != expected_reservation_fields:
                raise ValueError(
                    "package storage inventory reservation has missing or extra fields"
                )
            reservations.append(
                PackageStorageReservation(
                    kind=StorageKind(str(raw["kind"])),
                    start=int(raw["start"]),
                    end=int(raw["end"]),
                    provenance_id=str(raw["provenance_id"]),
                )
            )

        inventory = cls(
            package_id=str(payload["package_id"]),
            package_revision=str(payload["package_revision"]),
            reservations=tuple(reservations),
        )
        if str(payload["inventory_sha"]) != inventory.inventory_sha:
            raise ValueError("package storage inventory fingerprint mismatch")
        return inventory

    @classmethod
    def from_json(cls, text: str) -> "PackageStorageInventory":
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("package storage inventory must be a JSON object")
        return cls.from_dict(payload)

    @classmethod
    def empty(
        cls,
        package_id: str,
        package_revision: str = "empty",
    ) -> "PackageStorageInventory":
        return cls(
            package_id=package_id,
            package_revision=package_revision,
            reservations=(),
        )


@dataclass(frozen=True, order=True)
class GoalInterval:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < GOAL_ID_MIN or self.end > GOAL_ID_MAX:
            raise ValueError(
                f"GoalInterval must remain in range {GOAL_ID_MIN}..{GOAL_ID_MAX}"
            )
        if self.start > self.end:
            raise ValueError("GoalInterval start must not exceed end")

    def overlaps(self, other: "GoalInterval") -> bool:
        return self.start <= other.end and other.start <= self.end


@dataclass(frozen=True)
class GoalId:
    value: int

    def __post_init__(self) -> None:
        if not GOAL_ID_MIN <= self.value <= GOAL_ID_MAX:
            raise ValueError(
                f"GoalId must be in range {GOAL_ID_MIN}..{GOAL_ID_MAX}, got {self.value}"
            )


@dataclass(frozen=True)
class GoalValue:
    value: int


@dataclass(frozen=True)
class GoalSlot:
    id: GoalId
    role: GoalRole
    provenance_id: str


@dataclass(frozen=True)
class GoalSpan:
    start: GoalId
    width: int
    shape: GoalStorageShape
    provenance_id: str
    role: GoalRole = GoalRole.NATIVE_OUTPUT

    def __post_init__(self) -> None:
        expected_width = {
            GoalStorageShape.POINT_PAIR: 2,
            GoalStorageShape.EXTENDED_4: 4,
        }.get(self.shape)
        if expected_width is None:
            raise ValueError(f"unsupported GoalSpan shape {self.shape}")
        if self.width != expected_width:
            raise ValueError(
                f"GoalSpan shape {self.shape.value} requires width {expected_width}, got {self.width}"
            )
        if self.start.value + self.width - 1 > GOAL_ID_MAX:
            raise ValueError("GoalSpan exceeds the native GoalId range")

    @property
    def interval(self) -> GoalInterval:
        return GoalInterval(
            self.start.value,
            self.start.value + self.width - 1,
        )


@dataclass(frozen=True)
class StrategicNumberInventory:
    """Explicit DE strategic-number inventory used for deterministic custom allocation."""

    inventory_sha: str
    documented_ids: frozenset[int]
    candidate_ids: frozenset[int]

    def __post_init__(self) -> None:
        for value in self.documented_ids | self.candidate_ids:
            if not SN_ID_MIN <= value <= SN_ID_MAX:
                raise ValueError(f"Strategic Number id must be in range {SN_ID_MIN}..{SN_ID_MAX}, got {value}")
        if self.documented_ids & self.candidate_ids:
            raise ValueError("documented and candidate Strategic Number ids must not overlap")

    @classmethod
    def from_records(cls, records: Iterable[dict], *, inventory_sha: str) -> "StrategicNumberInventory":
        documented = {int(record["sn_id"]) for record in records if record.get("de") == 1}
        candidates = frozenset(
            value
            for value in range(SN_ID_MIN, SN_ID_MAX + 1)
            if value not in documented and value != SN_ID_MAX
        )
        return cls(
            inventory_sha=inventory_sha,
            documented_ids=frozenset(documented),
            candidate_ids=candidates,
        )


StrategicNumberRequest = StrategicNumberStorageRequest

@dataclass(frozen=True)
class StrategicNumberBindingMetadata:
    request_id: StorageRequestId
    role: GoalRole
    stability_key: str
    why_not_goal: str
    native_contract_id: str | None
    request_fingerprint: str


def strategic_number_request_fingerprint(
    request: StrategicNumberRequest,
) -> str:
    material = {
        "request": {
            "source_unit": request.request_id.owner.source_unit,
            "local_name": request.request_id.owner.local_name,
            "purpose": request.request_id.purpose,
        },
        "role": request.role.value,
        "stability_key": request.stability_key.strip(),
        "why_not_goal": request.why_not_goal.strip(),
        "native_contract_id": request.native_contract_id,
    }
    canonical = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _strategic_number_binding_metadata(
    request: StrategicNumberRequest,
) -> StrategicNumberBindingMetadata:
    return StrategicNumberBindingMetadata(
        request_id=request.request_id,
        role=request.role,
        stability_key=request.stability_key.strip(),
        why_not_goal=request.why_not_goal.strip(),
        native_contract_id=request.native_contract_id,
        request_fingerprint=strategic_number_request_fingerprint(request),
    )


@dataclass(frozen=True)
class TimerRequest:
    request_id: StorageRequestId
    initialization_policy: str
    stability_key: str
    role: GoalRole = GoalRole.EXECUTION_MEMORY
