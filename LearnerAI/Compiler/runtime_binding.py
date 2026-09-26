"""Typed semantic-to-native runtime storage binding.

The semantic compiler requests storage symbolically. This module is the only
place in the compiler that resolves lifecycle storage to native GoalIds.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib


GOAL_ID_MIN = 1
GOAL_ID_MAX = 16_000


class StorageKind(str, Enum):
    GOAL_SLOT = "GOAL_SLOT"


class GoalStorageShape(str, Enum):
    SCALAR = "SCALAR"
    POINT_PAIR = "POINT_PAIR"
    EXTENDED_4 = "EXTENDED_4"


class GoalRole(str, Enum):
    LIFECYCLE_STATE = "LIFECYCLE_STATE"
    PERSISTENT_STATE = "PERSISTENT_STATE"
    DERIVED_SCALAR = "DERIVED_SCALAR"
    NATIVE_OUTPUT = "NATIVE_OUTPUT"
    EXECUTION_MEMORY = "EXECUTION_MEMORY"


class NativeParameterKind(str, Enum):
    CONSTANT = "CONSTANT"
    GOAL_ID = "GOAL_ID"
    GOAL_VALUE = "GOAL_VALUE"
    GOAL_SPAN_START = "GOAL_SPAN_START"
    SN_ID = "SN_ID"
    TIMER_ID = "TIMER_ID"


@dataclass(frozen=True, order=True)
class SemanticId:
    source_unit: str
    local_name: str


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

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("GoalSpan width must be positive")
        if self.start.value + self.width - 1 > GOAL_ID_MAX:
            raise ValueError("GoalSpan exceeds the native GoalId range")


@dataclass(frozen=True)
class LifecycleEncoding:
    released: GoalValue
    active: GoalValue
    pending: GoalValue
    complete: GoalValue

    @staticmethod
    def for_goal_slot(slot: GoalSlot) -> "LifecycleEncoding":
        goal = slot.id.value
        return LifecycleEncoding(
            released=GoalValue(0),
            active=GoalValue(1),
            pending=GoalValue(goal + 1),
            complete=GoalValue(goal + 2),
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


@dataclass(frozen=True)
class BindingContext:
    occupied_goal_ids: frozenset[int] = frozenset()
    existing_bindings: tuple[tuple[StorageRequestId, GoalSlot], ...] = ()


@dataclass(frozen=True)
class BindingRecord:
    request_id: StorageRequestId
    binding: GoalSlot


@dataclass(frozen=True)
class BindingResult:
    records: tuple[BindingRecord, ...]

    def binding_for(self, request_id: StorageRequestId) -> GoalSlot:
        for record in self.records:
            if record.request_id == request_id:
                return record.binding
        raise KeyError(f"no binding for storage request {request_id}")


class RuntimeBinder:
    """Deterministically bind symbolic lifecycle storage to Goal slots."""

    def __init__(
        self,
        base_goal: int = 1000,
        *,
        occupied_goal_ids: frozenset[int] = frozenset(),
        existing_bindings: tuple[tuple[StorageRequestId, GoalSlot], ...] = (),
    ) -> None:
        if not GOAL_ID_MIN <= base_goal <= GOAL_ID_MAX:
            raise ValueError(
                f"GoalId base must be in range {GOAL_ID_MIN}..{GOAL_ID_MAX}, got {base_goal}"
            )
        self._base_goal = base_goal
        self._occupied = set(occupied_goal_ids)
        self._existing = dict(existing_bindings)

        for value in self._occupied:
            GoalId(value)
        for request_id, slot in self._existing.items():
            if slot.id.value in self._occupied:
                raise ValueError(
                    f"existing binding {request_id} conflicts with occupied GoalId "
                    f"{slot.id.value}"
                )

    def bind(self, requests: tuple[GoalSlotRequest, ...]) -> BindingResult:
        ordered = tuple(
            sorted(
                requests,
                key=lambda request: (
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
        newly_bound_ids: set[int] = set()

        for request in ordered:
            existing = self._existing.get(request.request_id)
            if existing is not None:
                if existing.role is not request.role:
                    raise ValueError(
                        f"existing binding role mismatch for {request.request_id}"
                    )
                if existing.id.value in newly_bound_ids:
                    raise ValueError(
                        f"existing binding collision on GoalId {existing.id.value}"
                    )
                records.append(BindingRecord(request.request_id, existing))
                newly_bound_ids.add(existing.id.value)
                continue

            goal_id = self._next_free_goal(newly_bound_ids)
            provenance_id = _provenance_id(request.request_id, goal_id)
            slot = GoalSlot(
                id=GoalId(goal_id),
                role=request.role,
                provenance_id=provenance_id,
            )
            records.append(BindingRecord(request.request_id, slot))
            newly_bound_ids.add(goal_id)

        return BindingResult(tuple(records))

    def _next_free_goal(self, newly_bound_ids: set[int]) -> int:
        candidate = self._base_goal
        while candidate <= GOAL_ID_MAX:
            if candidate not in self._occupied and candidate not in newly_bound_ids:
                return candidate
            candidate += 1
        raise ValueError(
            f"unable to allocate lifecycle GoalId in range "
            f"{self._base_goal}..{GOAL_ID_MAX}"
        )


def _provenance_id(request_id: StorageRequestId, goal_id: int) -> str:
    material = (
        f"{request_id.owner.source_unit}|"
        f"{request_id.owner.local_name}|"
        f"{request_id.purpose}|"
        f"{goal_id}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
