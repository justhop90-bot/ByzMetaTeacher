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

    def __post_init__(self) -> None:
        if not self.initialization_policy.strip():
            raise ValueError("TimerRequest initialization_policy must not be empty")


@dataclass(frozen=True)
class StrategicNumberSlot:
    id: int
    role: GoalRole
    provenance_id: str
    inventory_sha: str

    def __post_init__(self) -> None:
        if not SN_ID_MIN <= self.id <= SN_ID_MAX:
            raise ValueError(f"Strategic Number id must be in range {SN_ID_MIN}..{SN_ID_MAX}, got {self.id}")
        if not self.inventory_sha.strip():
            raise ValueError("Strategic Number slot requires inventory provenance")


@dataclass(frozen=True)
class TimerSlot:
    id: int
    role: GoalRole
    provenance_id: str
    initialization_policy: str

    def __post_init__(self) -> None:
        if not TIMER_ID_MIN <= self.id <= TIMER_ID_MAX:
            raise ValueError(f"Timer id must be in range {TIMER_ID_MIN}..{TIMER_ID_MAX}, got {self.id}")
        if not self.initialization_policy.strip():
            raise ValueError("TimerSlot initialization_policy must not be empty")


Binding = GoalSlot | GoalSpan | StrategicNumberSlot | TimerSlot
StorageRequest = GoalSlotRequest | GoalSpanRequest | StrategicNumberRequest | TimerRequest


@dataclass(frozen=True)
class LifecycleEncoding:
    released: GoalValue
    active: GoalValue
    issued: GoalValue
    pending: GoalValue
    complete: GoalValue
    cancelled: GoalValue

    @staticmethod
    def for_goal_slot(slot: GoalSlot) -> "LifecycleEncoding":
        goal = slot.id.value
        if goal > LIFECYCLE_GOAL_MAX:
            raise ValueError(
                f"lifecycle GoalId must leave room through GoalValue {GOAL_ID_MAX}; got {goal}"
            )
        return LifecycleEncoding(
            released=GoalValue(0),
            active=GoalValue(1),
            pending=GoalValue(goal + 1),
            complete=GoalValue(goal + 2),
            issued=GoalValue(goal + 3),
            cancelled=GoalValue(goal + 4),
        )


@dataclass(frozen=True)
class NativeParameterContract:
    index: int
    kind: NativeParameterKind
    width: int = 1
    contiguous: bool = False
    writes: bool = False

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("native parameter index must be non-negative")
        if self.width <= 0:
            raise ValueError("native parameter width must be positive")
        if self.contiguous and self.kind is not NativeParameterKind.GOAL_SPAN_START:
            raise ValueError(
                "contiguous native storage is only valid for GOAL_SPAN_START"
            )


@dataclass(frozen=True)
class NativeStorageContract:
    contract_id: str
    command: str
    parameters: tuple[NativeParameterContract, ...]
    shape: GoalStorageShape | None = None
    start_min: int | None = None
    start_max: int | None = None

    def validate_start(self, start: int) -> None:
        if self.start_min is not None and start < self.start_min:
            raise ValueError(
                f"{self.contract_id} start {start} is below minimum {self.start_min}"
            )
        if self.start_max is not None and start > self.start_max:
            raise ValueError(
                f"{self.contract_id} start {start} exceeds maximum {self.start_max}"
            )

    def validate_span(self, width: int, shape: GoalStorageShape) -> None:
        if self.shape is not None and shape is not self.shape:
            raise ValueError(
                f"{self.contract_id} requires shape {self.shape.value}, got {shape.value}"
            )
        expected = {
            GoalStorageShape.POINT_PAIR: 2,
            GoalStorageShape.EXTENDED_4: 4,
        }.get(shape)
        if expected is None:
            raise ValueError(f"unsupported GoalSpan shape {shape}")
        if width != expected:
            raise ValueError(
                f"{self.contract_id} requires width {expected}, got {width}"
            )


@dataclass(frozen=True)
class BindingContext:
    occupied_goal_ids: frozenset[int] = frozenset()
    occupied_goal_intervals: tuple[tuple[int, int], ...] = ()
    occupied_sn_ids: frozenset[int] = frozenset()
    occupied_timer_ids: frozenset[int] = frozenset()
    strategic_number_inventory: StrategicNumberInventory | None = None
    existing_bindings: tuple[tuple[StorageRequestId, Binding], ...] = ()
    package_inventory_sha: str = ""
    allocator_version: str = ALLOCATOR_VERSION
    package_inventory: PackageStorageInventory | None = None

    def __post_init__(self) -> None:
        if (
            self.package_inventory is not None
            and self.package_inventory_sha
            and self.package_inventory_sha != self.package_inventory.inventory_sha
        ):
            raise ValueError("package inventory fingerprint mismatch")

    @classmethod
    def from_package_inventory(
        cls,
        package_inventory: PackageStorageInventory,
        *,
        strategic_number_inventory: StrategicNumberInventory | None = None,
        existing_bindings: tuple[tuple[StorageRequestId, Binding], ...] = (),
        allocator_version: str = ALLOCATOR_VERSION,
    ) -> "BindingContext":
        return cls(
            strategic_number_inventory=strategic_number_inventory,
            existing_bindings=existing_bindings,
            package_inventory_sha=package_inventory.inventory_sha,
            allocator_version=allocator_version,
            package_inventory=package_inventory,
        )


@dataclass(frozen=True)
class BindingRecord:
    request_id: StorageRequestId
    binding: Binding


@dataclass(frozen=True)
class BindingResult:
    records: tuple[BindingRecord, ...]
    strategic_number_metadata: tuple[StrategicNumberBindingMetadata, ...] = ()

    def binding_for(self, request_id: StorageRequestId) -> Binding:
        for record in self.records:
            if record.request_id == request_id:
                return record.binding
        raise KeyError(f"no binding for storage request {request_id}")

    def to_manifest(
        self,
        *,
        package_inventory_sha: str = "",
        allocator_version: str = ALLOCATOR_VERSION,
    ) -> "BindingManifest":
        return BindingManifest(
            format_version=BINDING_MANIFEST_VERSION,
            package_inventory_sha=package_inventory_sha,
            allocator_version=allocator_version,
            records=self.records,
            strategic_number_metadata=self.strategic_number_metadata,
        )


@dataclass(frozen=True)
class BindingManifest:
    format_version: int
    package_inventory_sha: str
    allocator_version: str
    records: tuple[BindingRecord, ...]
    strategic_number_metadata: tuple[StrategicNumberBindingMetadata, ...] = ()
    integrity_sha256: str = ""

    def binding_for(self, request_id: StorageRequestId) -> Binding:
        for record in self.records:
            if record.request_id == request_id:
                return record.binding
        raise KeyError(f"no binding for storage request {request_id}")

    def _strategic_metadata(self) -> dict[StorageRequestId, StrategicNumberBindingMetadata]:
        return {item.request_id: item for item in self.strategic_number_metadata}

    def _records_payload(self) -> list[dict[str, object]]:
        metadata = self._strategic_metadata()
        serialized_records: list[dict[str, object]] = []
        for record in sorted(
            self.records,
            key=lambda item: (
                item.request_id.owner.source_unit,
                item.request_id.owner.local_name,
                item.request_id.purpose,
                metadata[item.request_id].stability_key if item.request_id in metadata else "",
            ),
        ):
            payload = {
                "source_unit": record.request_id.owner.source_unit,
                "local_name": record.request_id.owner.local_name,
                "purpose": record.request_id.purpose,
                "role": record.binding.role.value,
                "provenance_id": record.binding.provenance_id,
            }
            if isinstance(record.binding, GoalSlot):
                payload.update(
                    {
                        "binding_kind": StorageKind.GOAL_SLOT.value,
                        "goal_id": record.binding.id.value,
                    }
                )
            elif isinstance(record.binding, GoalSpan):
                payload.update(
                    {
                        "binding_kind": StorageKind.GOAL_SPAN.value,
                        "start_goal_id": record.binding.start.value,
                        "width": record.binding.width,
                        "shape": record.binding.shape.value,
                    }
                )
            elif isinstance(record.binding, StrategicNumberSlot):
                contract = metadata.get(record.request_id)
                if contract is None:
                    raise ValueError(
                        f"Strategic Number binding {record.request_id} has no request metadata"
                    )
                expected_request = StrategicNumberRequest(
                    request_id=contract.request_id,
                    why_not_goal=contract.why_not_goal,
                    stability_key=contract.stability_key,
                    role=contract.role,
                    native_contract_id=contract.native_contract_id,
                )
                if contract.request_fingerprint != strategic_number_request_fingerprint(expected_request):
                    raise ValueError(
                        f"Strategic Number binding {record.request_id} request fingerprint is invalid"
                    )
                if contract.role is not record.binding.role:
                    raise ValueError(
                        f"Strategic Number binding {record.request_id} role does not match request metadata"
                    )
                payload.update(
                    {
                        "binding_kind": StorageKind.STRATEGIC_NUMBER.value,
                        "strategic_number_id": record.binding.id,
                        "request_contract": {
                            "role": contract.role.value,
                            "stability_key": contract.stability_key,
                            "why_not_goal": contract.why_not_goal,
                            "native_contract_id": contract.native_contract_id,
                        },
                        "provenance": {
                            "strategic_number_inventory_sha": record.binding.inventory_sha,
                            "request_fingerprint": contract.request_fingerprint,
                        },
                    }
                )
            else:
                payload.update(
                    {
                        "binding_kind": StorageKind.TIMER.value,
                        "timer_id": record.binding.id,
                        "initialization_policy": record.binding.initialization_policy,
                    }
                )
            serialized_records.append(payload)
        return serialized_records

    def canonical_content_payload(self) -> dict[str, object]:
        return {
            "format_version": BINDING_MANIFEST_VERSION,
            "schema": BINDING_MANIFEST_SCHEMA,
            "package_inventory_sha": self.package_inventory_sha,
            "allocator_version": self.allocator_version,
            "records": self._records_payload(),
        }

    def canonical_content_bytes(self) -> bytes:
        return json.dumps(
            self.canonical_content_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def content_sha256(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def verify_integrity(self, *, expected_content_sha256: str | None = None) -> None:
        actual = self.content_sha256()
        if self.integrity_sha256 and self.integrity_sha256 != actual:
            raise ValueError("binding manifest integrity mismatch")
        if expected_content_sha256 is not None and expected_content_sha256 != actual:
            raise ValueError("binding manifest does not match expected external digest")

    def to_json(self) -> str:
        digest = self.content_sha256()
        if self.integrity_sha256 and self.integrity_sha256 != digest:
            raise ValueError("binding manifest integrity mismatch")
        payload = dict(self.canonical_content_payload())
        payload["integrity"] = {
            "algorithm": "SHA-256",
            "content_sha256": digest,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str, *, verify_integrity: bool = True) -> "BindingManifest":
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("binding manifest must be a JSON object")
        version = payload.get("format_version")
        if version != BINDING_MANIFEST_VERSION:
            raise ValueError(
                f"binding manifest format {version} requires explicit migration to v{BINDING_MANIFEST_VERSION}"
            )
        expected_fields = {
            "format_version",
            "schema",
            "package_inventory_sha",
            "allocator_version",
            "records",
            "integrity",
        }
        if set(payload) != expected_fields:
            raise ValueError("binding manifest has missing or extra fields")
        if payload["schema"] != BINDING_MANIFEST_SCHEMA:
            raise ValueError("binding manifest schema identifier mismatch")
        integrity = payload["integrity"]
        if not isinstance(integrity, dict) or set(integrity) != {"algorithm", "content_sha256"}:
            raise ValueError("binding manifest integrity block is invalid")
        if integrity["algorithm"] != "SHA-256":
            raise ValueError("binding manifest integrity algorithm is unsupported")

        raw_records = payload["records"]
        if not isinstance(raw_records, list):
            raise ValueError("binding manifest records must be an array")

        records: list[BindingRecord] = []
        strategic_metadata: list[StrategicNumberBindingMetadata] = []
        seen_requests: set[StorageRequestId] = set()
        seen_sn_ids: set[int] = set()
        occupied: list[GoalInterval] = []

        for raw in raw_records:
            if not isinstance(raw, dict):
                raise ValueError("binding manifest record must be an object")
            owner = SemanticId(
                source_unit=str(raw["source_unit"]),
                local_name=str(raw["local_name"]),
            )
            request_id = StorageRequestId(owner=owner, purpose=str(raw["purpose"]))
            if request_id in seen_requests:
                raise ValueError(f"duplicate binding manifest request {request_id}")

            role = GoalRole(str(raw["role"]))
            binding_kind = str(raw.get("binding_kind", StorageKind.GOAL_SLOT.value))
            if binding_kind == StorageKind.GOAL_SLOT.value:
                binding = GoalSlot(
                    id=GoalId(int(raw["goal_id"])),
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                )
            elif binding_kind == StorageKind.GOAL_SPAN.value:
                binding = GoalSpan(
                    start=GoalId(int(raw["start_goal_id"])),
                    width=int(raw["width"]),
                    shape=GoalStorageShape(str(raw["shape"])),
                    provenance_id=str(raw["provenance_id"]),
                    role=role,
                )
            elif binding_kind == StorageKind.STRATEGIC_NUMBER.value:
                request_contract = raw.get("request_contract")
                provenance = raw.get("provenance")
                if not isinstance(request_contract, dict) or set(request_contract) != {
                    "role",
                    "stability_key",
                    "why_not_goal",
                    "native_contract_id",
                }:
                    raise ValueError("Strategic Number manifest request_contract is invalid")
                if not isinstance(provenance, dict) or set(provenance) != {
                    "strategic_number_inventory_sha",
                    "request_fingerprint",
                }:
                    raise ValueError("Strategic Number manifest provenance is invalid")
                contract_role = GoalRole(str(request_contract["role"]))
                if contract_role is not role:
                    raise ValueError("Strategic Number request role does not match binding role")
                sn_inventory_sha = str(provenance["strategic_number_inventory_sha"])
                binding = StrategicNumberSlot(
                    id=int(raw["strategic_number_id"]),
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                    inventory_sha=sn_inventory_sha,
                )
                if binding.id in seen_sn_ids:
                    raise ValueError(
                        f"duplicate binding manifest Strategic Number {binding.id}"
                    )
                request = StrategicNumberRequest(
                    request_id=request_id,
                    why_not_goal=str(request_contract["why_not_goal"]),
                    stability_key=str(request_contract["stability_key"]),
                    role=contract_role,
                    native_contract_id=(
                        None
                        if request_contract["native_contract_id"] is None
                        else str(request_contract["native_contract_id"])
                    ),
                )
                fingerprint = str(provenance["request_fingerprint"])
                expected_fingerprint = strategic_number_request_fingerprint(request)
                if fingerprint != expected_fingerprint:
                    raise ValueError(
                        f"Strategic Number request fingerprint mismatch for {request_id}"
                    )
                strategic_metadata.append(
                    StrategicNumberBindingMetadata(
                        request_id=request_id,
                        role=contract_role,
                        stability_key=request.stability_key,
                        why_not_goal=request.why_not_goal,
                        native_contract_id=request.native_contract_id,
                        request_fingerprint=fingerprint,
                    )
                )
                seen_sn_ids.add(binding.id)
            elif binding_kind == StorageKind.TIMER.value:
                binding = TimerSlot(
                    id=int(raw["timer_id"]),
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                    initialization_policy=str(raw["initialization_policy"]),
                )
            else:
                raise ValueError(f"unknown binding kind {binding_kind}")

            if isinstance(binding, (GoalSlot, GoalSpan)):
                interval = _binding_interval(binding)
                if any(interval.overlaps(existing) for existing in occupied):
                    raise ValueError(
                        f"overlapping binding manifest storage at {interval.start}..{interval.end}"
                    )
                occupied.append(interval)
            seen_requests.add(request_id)
            records.append(BindingRecord(request_id, binding))

        manifest = cls(
            format_version=BINDING_MANIFEST_VERSION,
            package_inventory_sha=str(payload["package_inventory_sha"]),
            allocator_version=str(payload["allocator_version"]),
            records=tuple(records),
            strategic_number_metadata=tuple(strategic_metadata),
            integrity_sha256=str(integrity["content_sha256"]),
        )
        if manifest._records_payload() != raw_records:
            raise ValueError("binding manifest records are not in canonical order")
        if verify_integrity:
            manifest.verify_integrity()
        return manifest

    @classmethod
    def migrate_to_v4(
        cls,
        text: str,
        *,
        strategic_number_requests: tuple[StrategicNumberRequest, ...] = (),
        strategic_number_inventory: StrategicNumberInventory | None = None,
        package_inventory_sha: str | None = None,
        allocator_version: str = ALLOCATOR_VERSION,
    ) -> "BindingManifest":
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("legacy binding manifest must be a JSON object")
        version = payload.get("format_version")
        if version not in {1, 2, 3}:
            raise ValueError(f"unsupported legacy binding manifest format {version}")
        legacy_package_sha = str(payload.get("package_inventory_sha", ""))
        if package_inventory_sha is None:
            package_inventory_sha = legacy_package_sha
        elif legacy_package_sha and package_inventory_sha != legacy_package_sha:
            raise ValueError("legacy binding manifest package inventory mismatch")

        requests_by_id = {request.request_id: request for request in strategic_number_requests}
        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            raise ValueError("legacy binding manifest records must be an array")

        records: list[BindingRecord] = []
        strategic_metadata: list[StrategicNumberBindingMetadata] = []
        seen_requests: set[StorageRequestId] = set()
        seen_sn_ids: set[int] = set()
        occupied: list[GoalInterval] = []

        for raw in raw_records:
            if not isinstance(raw, dict):
                raise ValueError("legacy binding manifest record must be an object")
            owner = SemanticId(
                source_unit=str(raw["source_unit"]),
                local_name=str(raw["local_name"]),
            )
            request_id = StorageRequestId(owner=owner, purpose=str(raw["purpose"]))
            if request_id in seen_requests:
                raise ValueError(f"duplicate legacy binding request {request_id}")
            role = GoalRole(str(raw["role"]))
            binding_kind = str(raw.get("binding_kind", StorageKind.GOAL_SLOT.value))
            if binding_kind == StorageKind.GOAL_SLOT.value:
                binding = GoalSlot(
                    id=GoalId(int(raw["goal_id"])),
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                )
            elif binding_kind == StorageKind.GOAL_SPAN.value:
                binding = GoalSpan(
                    start=GoalId(int(raw["start_goal_id"])),
                    width=int(raw["width"]),
                    shape=GoalStorageShape(str(raw["shape"])),
                    provenance_id=str(raw["provenance_id"]),
                    role=role,
                )
            elif binding_kind == StorageKind.STRATEGIC_NUMBER.value:
                request = requests_by_id.get(request_id)
                if request is None or strategic_number_inventory is None:
                    raise ValueError(
                        f"legacy Strategic Number binding {request_id} requires migration context"
                    )
                legacy_inventory_sha = str(raw.get("strategic_number_inventory_sha", ""))
                if legacy_inventory_sha != strategic_number_inventory.inventory_sha:
                    raise ValueError(
                        f"legacy Strategic Number binding {request_id} inventory mismatch"
                    )
                sn_id = int(raw["strategic_number_id"])
                if sn_id not in strategic_number_inventory.candidate_ids:
                    raise ValueError(
                        f"legacy Strategic Number binding {request_id} is no longer a candidate"
                    )
                binding = StrategicNumberSlot(
                    id=sn_id,
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                    inventory_sha=strategic_number_inventory.inventory_sha,
                )
                if binding.id in seen_sn_ids:
                    raise ValueError(
                        f"duplicate legacy Strategic Number {binding.id}"
                    )
                strategic_metadata.append(
                    _strategic_number_binding_metadata(request)
                )
                seen_sn_ids.add(binding.id)
            elif binding_kind == StorageKind.TIMER.value:
                binding = TimerSlot(
                    id=int(raw["timer_id"]),
                    role=role,
                    provenance_id=str(raw["provenance_id"]),
                    initialization_policy=str(raw["initialization_policy"]),
                )
            else:
                raise ValueError(f"unknown legacy binding kind {binding_kind}")

            if isinstance(binding, (GoalSlot, GoalSpan)):
                interval = _binding_interval(binding)
                if any(interval.overlaps(existing) for existing in occupied):
                    raise ValueError(
                        f"overlapping legacy binding storage at {interval.start}..{interval.end}"
                    )
                occupied.append(interval)
            seen_requests.add(request_id)
            records.append(BindingRecord(request_id, binding))

        manifest = cls(
            format_version=BINDING_MANIFEST_VERSION,
            package_inventory_sha=str(package_inventory_sha or ""),
            allocator_version=allocator_version,
            records=tuple(records),
            strategic_number_metadata=tuple(strategic_metadata),
        )
        return cls.from_json(manifest.to_json())

    def to_context(
        self,
        *,
        occupied_goal_ids: frozenset[int] = frozenset(),
        occupied_goal_intervals: tuple[tuple[int, int], ...] = (),
        occupied_sn_ids: frozenset[int] = frozenset(),
        occupied_timer_ids: frozenset[int] = frozenset(),
        strategic_number_inventory: StrategicNumberInventory | None = None,
    ) -> BindingContext:
        return BindingContext(
            occupied_goal_ids=occupied_goal_ids,
            occupied_goal_intervals=occupied_goal_intervals,
            occupied_sn_ids=occupied_sn_ids,
            occupied_timer_ids=occupied_timer_ids,
            strategic_number_inventory=strategic_number_inventory,
            existing_bindings=tuple(
                (record.request_id, record.binding) for record in self.records
            ),
            package_inventory_sha=self.package_inventory_sha,
            allocator_version=self.allocator_version,
        )


class RuntimeBinder:
    """Deterministically bind symbolic storage requests to native Goal storage."""

    def __init__(self, base_goal: int = 41) -> None:
        if not 41 <= base_goal <= ORDINARY_GOAL_MAX:
            raise ValueError(
                f"ordinary Goal storage base must be in range 41..{ORDINARY_GOAL_MAX}, got {base_goal}"
            )
        self._base_goal = base_goal

    def bind(
        self,
        requests: tuple[StorageRequest, ...],
        context: BindingContext = BindingContext(),
    ) -> BindingResult:
        occupied_ids = set(context.occupied_goal_ids)
        occupied_intervals = [
            _coerce_interval(interval) for interval in context.occupied_goal_intervals
        ]
        if context.package_inventory is not None:
            occupied_ids.update(context.package_inventory.occupied_goal_ids)
            occupied_intervals.extend(
                _coerce_interval(interval)
                for interval in context.package_inventory.occupied_goal_intervals
            )
        for value in occupied_ids:
            GoalId(value)
            if not 1 <= value <= ORDINARY_GOAL_MAX:
                raise ValueError(
                    f"occupied ordinary GoalId must be in range 1..{ORDINARY_GOAL_MAX}"
                )
        occupied_sn_ids = set(context.occupied_sn_ids)
        if context.package_inventory is not None:
            occupied_sn_ids.update(context.package_inventory.occupied_sn_ids)
        for value in occupied_sn_ids:
            if not SN_ID_MIN <= value <= SN_ID_MAX:
                raise ValueError(
                    f"Strategic Number id must be in range {SN_ID_MIN}..{SN_ID_MAX}"
                )
        occupied_timer_ids = set(context.occupied_timer_ids)
        if context.package_inventory is not None:
            occupied_timer_ids.update(context.package_inventory.occupied_timer_ids)
        for value in occupied_timer_ids:
            if not TIMER_ID_MIN <= value <= TIMER_ID_MAX:
                raise ValueError(
                    f"Timer id must be in range {TIMER_ID_MIN}..{TIMER_ID_MAX}"
                )

        for interval in occupied_intervals:
            if any(
                GoalInterval(value, value).overlaps(interval)
                for value in occupied_ids
            ):
                raise ValueError(
                    f"occupied GoalId overlaps occupied GoalInterval {interval.start}..{interval.end}"
                )

        existing_pairs = tuple(context.existing_bindings)
        existing_request_ids = [request_id for request_id, _ in existing_pairs]
        if len(existing_request_ids) != len(set(existing_request_ids)):
            raise ValueError("duplicate existing binding request identity")

        existing_intervals: list[GoalInterval] = []
        existing: dict[StorageRequestId, Binding] = {}
        for request_id, binding in existing_pairs:
            if isinstance(binding, GoalSlot):
                if not 1 <= binding.id.value <= ORDINARY_GOAL_MAX:
                    raise ValueError(
                        f"existing GoalSlot id must be in range 1..{ORDINARY_GOAL_MAX}"
                    )
            if isinstance(binding, (GoalSlot, GoalSpan)):
                interval = _binding_interval(binding)
                if any(interval.overlaps(other) for other in existing_intervals):
                    if isinstance(binding, GoalSlot) and any(
                        isinstance(existing_binding, GoalSlot)
                        and existing_binding.id.value == binding.id.value
                        for _, existing_binding in existing_pairs
                    ):
                        raise ValueError("duplicate existing binding GoalId")
                    raise ValueError(
                        f"duplicate existing binding storage overlap at "
                        f"{interval.start}..{interval.end}"
                    )
                if any(interval.overlaps(other) for other in occupied_intervals):
                    raise ValueError(
                        f"existing binding {request_id} conflicts with occupied GoalInterval"
                    )
                if any(
                    GoalInterval(value, value).overlaps(interval)
                    for value in occupied_ids
                ):
                    raise ValueError(
                        f"existing binding {request_id} conflicts with occupied GoalId"
                    )
                existing_intervals.append(interval)
            elif isinstance(binding, StrategicNumberSlot):
                if binding.id in occupied_sn_ids:
                    raise ValueError(
                        f"existing binding {request_id} conflicts with occupied Strategic Number {binding.id}"
                    )
                occupied_sn_ids.add(binding.id)
            elif isinstance(binding, TimerSlot):
                if binding.id in occupied_timer_ids:
                    raise ValueError(
                        f"existing binding {request_id} conflicts with occupied TimerId {binding.id}"
                    )
                occupied_timer_ids.add(binding.id)
            else:
                raise TypeError(f"unsupported existing binding type {type(binding).__name__}")
            existing[request_id] = binding

        role_order = {
            GoalRole.LIFECYCLE_STATE: 0,
            GoalRole.PERSISTENT_STATE: 1,
            GoalRole.DERIVED_SCALAR: 2,
            GoalRole.NATIVE_OUTPUT: 3,
            GoalRole.EXECUTION_MEMORY: 4,
        }
        storage_order = {
            GoalSlotRequest: 0,
            GoalSpanRequest: 1,
            StrategicNumberRequest: 2,
            TimerRequest: 3,
        }
        ordered = tuple(
            sorted(
                requests,
                key=lambda request: (
                    storage_order[type(request)],
                    role_order.get(request.role, 99),
                    request.request_id.owner.source_unit,
                    request.request_id.owner.local_name,
                    request.request_id.purpose,
                ),
            )
        )

        request_ids = [request.request_id for request in ordered]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("duplicate storage request identity")

        records: list[BindingRecord] = []
        strategic_number_metadata: list[StrategicNumberBindingMetadata] = []
        allocated_intervals = list(occupied_intervals) + list(existing_intervals)

        for request in ordered:
            binding = existing.get(request.request_id)
            if binding is None:
                if isinstance(request, GoalSlotRequest):
                    max_goal = ORDINARY_GOAL_MAX
                    goal_id = self._next_free_goal(
                        occupied_ids,
                        allocated_intervals,
                        max_goal=max_goal,
                    )
                    binding = GoalSlot(
                        id=GoalId(goal_id),
                        role=request.role,
                        provenance_id=_provenance_id(request.request_id, goal_id),
                    )
                elif isinstance(request, GoalSpanRequest):
                    start = self._next_free_span(
                        request,
                        occupied_ids,
                        allocated_intervals,
                    )
                    binding = GoalSpan(
                        start=GoalId(start),
                        width=request.width,
                        shape=request.shape,
                        provenance_id=_provenance_id(
                            request.request_id,
                            start,
                        ),
                        role=request.role,
                    )
                elif isinstance(request, StrategicNumberRequest):
                    sn_id = self._next_free_strategic_number(
                        request,
                        occupied_sn_ids,
                        context.strategic_number_inventory,
                    )
                    inventory = context.strategic_number_inventory
                    if inventory is None:
                        raise ValueError(
                            "Strategic Number allocation requires an explicit AIRef inventory"
                        )
                    binding = StrategicNumberSlot(
                        id=sn_id,
                        role=request.role,
                        provenance_id=_provenance_id(request.request_id, sn_id),
                        inventory_sha=inventory.inventory_sha,
                    )
                    occupied_sn_ids.add(sn_id)
                else:
                    timer_id = self._next_free_timer(occupied_timer_ids)
                    binding = TimerSlot(
                        id=timer_id,
                        role=request.role,
                        provenance_id=_provenance_id(request.request_id, timer_id),
                        initialization_policy=request.initialization_policy,
                    )
                    occupied_timer_ids.add(timer_id)
            else:
                self._validate_existing_binding(
                    request,
                    binding,
                    strategic_number_inventory=context.strategic_number_inventory,
                )

            if isinstance(binding, (GoalSlot, GoalSpan)):
                interval = _binding_interval(binding)
                if any(interval.overlaps(other) for other in allocated_intervals):
                    if request.request_id not in existing:
                        raise ValueError(
                            f"binding collision for {request.request_id} at "
                            f"{interval.start}..{interval.end}"
                        )
                allocated_intervals.append(interval)
            records.append(BindingRecord(request.request_id, binding))
            if isinstance(request, StrategicNumberRequest):
                strategic_number_metadata.append(
                    _strategic_number_binding_metadata(request)
                )

        return BindingResult(
            tuple(records),
            strategic_number_metadata=tuple(
                sorted(
                    strategic_number_metadata,
                    key=lambda item: (
                        item.request_id.owner.source_unit,
                        item.request_id.owner.local_name,
                        item.request_id.purpose,
                        item.stability_key,
                    ),
                )
            ),
        )

    def _validate_existing_binding(
        self,
        request: StorageRequest,
        binding: Binding,
        *,
        strategic_number_inventory: StrategicNumberInventory | None = None,
    ) -> None:
        if isinstance(request, GoalSlotRequest):
            if not isinstance(binding, GoalSlot):
                raise ValueError(
                    f"existing binding storage kind mismatch for {request.request_id}"
                )
            if binding.role is not request.role:
                raise ValueError(f"existing binding role mismatch for {request.request_id}")
            if request.role is GoalRole.LIFECYCLE_STATE and binding.id.value > LIFECYCLE_GOAL_MAX:
                raise ValueError(
                    f"existing lifecycle GoalId {binding.id.value} leaves no room for lifecycle values"
                )
            return

        if isinstance(request, GoalSpanRequest):
            if not isinstance(binding, GoalSpan):
                raise ValueError(
                    f"existing binding storage kind mismatch for {request.request_id}"
                )
            _validate_span_request(request)
            if binding.role is not request.role:
                raise ValueError(f"existing binding role mismatch for {request.request_id}")
            if binding.width != request.width or binding.shape is not request.shape:
                raise ValueError(
                    f"existing binding shape mismatch for {request.request_id}"
                )
            if not request.start_min <= binding.start.value <= request.start_max:
                raise ValueError(
                    f"existing binding start {binding.start.value} is outside contract "
                    f"range {request.start_min}..{request.start_max}"
                )
            return

        if isinstance(request, StrategicNumberRequest):
            if not isinstance(binding, StrategicNumberSlot):
                raise ValueError(
                    f"existing binding storage kind mismatch for {request.request_id}"
                )
            if binding.role is not request.role:
                raise ValueError(f"existing binding role mismatch for {request.request_id}")
            if strategic_number_inventory is None:
                raise ValueError(
                    "Strategic Number binding reuse requires an explicit AIRef inventory"
                )
            if binding.id not in strategic_number_inventory.candidate_ids:
                raise ValueError(
                    f"existing Strategic Number {binding.id} is not approved by inventory "
                    f"{strategic_number_inventory.inventory_sha}"
                )
            if binding.inventory_sha != strategic_number_inventory.inventory_sha:
                raise ValueError(
                    f"existing Strategic Number {binding.id} provenance inventory mismatch"
                )
            if binding.id == 511:
                raise ValueError("Strategic Number 511 is not eligible for compiler allocation")
            return

        if not isinstance(binding, TimerSlot):
            raise ValueError(
                f"existing binding storage kind mismatch for {request.request_id}"
            )
        if binding.role is not request.role:
            raise ValueError(f"existing binding role mismatch for {request.request_id}")
        if binding.initialization_policy != request.initialization_policy:
            raise ValueError(
                f"existing binding initialization policy mismatch for {request.request_id}"
            )

    def _next_free_goal(
        self,
        occupied_ids: set[int],
        allocated_intervals: list[GoalInterval],
        *,
        max_goal: int = GOAL_ID_MAX,
    ) -> int:
        candidate = self._base_goal
        while candidate <= max_goal:
            interval = GoalInterval(candidate, candidate)
            if (
                candidate not in occupied_ids
                and not any(interval.overlaps(item) for item in allocated_intervals)
            ):
                return candidate
            candidate += 1
        if max_goal == LIFECYCLE_GOAL_MAX:
            raise ValueError(
                f"unable to allocate lifecycle GoalId; lifecycle GoalId must leave room "
                f"through GoalValue {GOAL_ID_MAX}; range {self._base_goal}..{max_goal}"
            )
        raise ValueError(
            f"unable to allocate GoalId in range "
            f"{self._base_goal}..{max_goal}"
        )

    def _next_free_span(
        self,
        request: GoalSpanRequest,
        occupied_ids: set[int],
        allocated_intervals: list[GoalInterval],
    ) -> int:
        _validate_span_request(request)
        start = request.start_min
        end = request.start_max
        while start <= end:
            interval = GoalInterval(start, start + request.width - 1)
            if (
                interval.end <= request.start_max
                and not any(
                    GoalInterval(value, value).overlaps(interval)
                    for value in occupied_ids
                )
                and not any(interval.overlaps(item) for item in allocated_intervals)
            ):
                return start
            start += 1
        raise ValueError(
            f"unable to allocate GoalSpan '{request.request_id.purpose}' "
            f"in range {request.start_min}..{request.start_max}"
        )


    def _next_free_strategic_number(
        self,
        request: StrategicNumberRequest,
        occupied_sn_ids: set[int],
        inventory: StrategicNumberInventory | None,
    ) -> int:
        if not request.why_not_goal.strip():
            raise ValueError(
                f"Strategic Number request {request.request_id} requires WHY_NOT_GOAL justification"
            )
        if inventory is None:
            raise ValueError(
                "Strategic Number allocation requires an explicit AIRef inventory"
            )
        for candidate in sorted(inventory.candidate_ids, reverse=True):
            if candidate == 511:
                continue
            if candidate not in occupied_sn_ids:
                return candidate
        raise ValueError("unable to allocate a Strategic Number from the supplied inventory")

    def _next_free_timer(self, occupied_timer_ids: set[int]) -> int:
        for candidate in range(TIMER_ID_MIN, TIMER_ID_MAX + 1):
            if candidate not in occupied_timer_ids:
                return candidate
        raise ValueError("unable to allocate TimerId in range 1..50")


class VolatileGoalPool:
    """Deterministic temporary Goal storage with explicit checkout/release."""

    def __init__(
        self,
        start: int,
        end: int,
        *,
        reserved: Iterable[int] = (),
    ) -> None:
        if start < GOAL_ID_MIN or end > GOAL_ID_MAX or start > end:
            raise ValueError("volatile Goal pool range is invalid")
        reserved_ids = set(reserved)
        for goal in reserved_ids:
            GoalId(goal)
            if goal < start or goal > end:
                raise ValueError(f"reserved GoalId {goal} is outside pool")
        self._range = (start, end)
        self._available = [goal for goal in range(start, end + 1) if goal not in reserved_ids]
        self._leased: set[int] = set()

    def checkout(self) -> GoalId:
        if not self._available:
            raise ValueError("volatile Goal pool is exhausted")
        value = self._available.pop(0)
        self._leased.add(value)
        return GoalId(value)

    def release(self, goal: GoalId) -> None:
        if not isinstance(goal, GoalId):
            raise TypeError("volatile Goal pool releases require GoalId")
        start, end = self._range
        if not start <= goal.value <= end:
            raise ValueError(f"GoalId {goal.value} is outside pool")
        if goal.value not in self._leased:
            raise ValueError(f"GoalId {goal.value} is not leased")
        self._leased.remove(goal.value)
        self._available.append(goal.value)
        self._available.sort()

    @contextmanager
    def using(self) -> Iterator[GoalId]:
        goal = self.checkout()
        try:
            yield goal
        finally:
            self.release(goal)


def _validate_span_request(request: GoalSpanRequest) -> None:
    if request.width <= 0:
        raise ValueError("GoalSpan request width must be positive")
    if request.start_min < GOAL_ID_MIN or request.start_max > GOAL_ID_MAX:
        raise ValueError("GoalSpan request bounds exceed native GoalId range")
    if request.start_min > request.start_max:
        raise ValueError("GoalSpan request start_min must not exceed start_max")
    expected = {
        GoalSpanKind.POINT_PAIR: 2,
        GoalSpanKind.EXTENDED_4: 4,
    }[request.shape]
    if request.width != expected:
        raise ValueError(
            f"GoalSpan shape {request.shape.value} requires width {expected}, got {request.width}"
        )
    if request.start_min + request.width - 1 > request.start_max:
        raise ValueError(
            f"GoalSpan request width {request.width} does not fit "
            f"{request.start_min}..{request.start_max}"
        )


def _binding_interval(binding: Binding) -> GoalInterval:
    if isinstance(binding, GoalSlot):
        return GoalInterval(binding.id.value, binding.id.value)
    return binding.interval


def _coerce_interval(value: tuple[int, int]) -> GoalInterval:
    if len(value) != 2:
        raise ValueError("occupied GoalInterval must be a (start, end) pair")
    return GoalInterval(int(value[0]), int(value[1]))


def _provenance_id(request_id: StorageRequestId, goal_id: int) -> str:
    material = (
        f"{request_id.owner.source_unit}|"
        f"{request_id.owner.local_name}|"
        f"{request_id.purpose}|"
        f"{goal_id}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
