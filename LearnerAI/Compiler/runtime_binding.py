"""Typed semantic-to-native runtime storage binding."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib

from .ir import GoalRole, GoalSlotRequest, StorageRequestId


GOAL_ID_MIN = 1
GOAL_ID_MAX = 16_000


class StorageKind(str, Enum):
    GOAL_SLOT = "GOAL_SLOT"


class GoalStorageShape(str, Enum):
    SCALAR = "SCALAR"
    POINT_PAIR = "POINT_PAIR"
    EXTENDED_4 = "EXTENDED_4"


class NativeParameterKind(str, Enum):
    CONSTANT = "CONSTANT"
    GOAL_ID = "GOAL_ID"
    GOAL_VALUE = "GOAL_VALUE"
    GOAL_SPAN_START = "GOAL_SPAN_START"
    SN_ID = "SN_ID"
    TIMER_ID = "TIMER_ID"


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
    """Deterministically bind symbolic lifecycle storage to native Goal slots."""

    def __init__(self, base_goal: int = 1000) -> None:
        if not GOAL_ID_MIN <= base_goal <= GOAL_ID_MAX:
            raise ValueError(
                f"GoalId base must be in range {GOAL_ID_MIN}..{GOAL_ID_MAX}, got {base_goal}"
            )
        self._base_goal = base_goal

    def bind(
        self,
        requests: tuple[GoalSlotRequest, ...],
        context: BindingContext = BindingContext(),
    ) -> BindingResult:
        occupied = set(context.occupied_goal_ids)
        for value in occupied:
            GoalId(value)

        existing = dict(context.existing_bindings)
        for request_id, slot in existing.items():
            if slot.id.value in occupied:
                raise ValueError(
                    f"existing binding {request_id} conflicts with occupied GoalId "
                    f"{slot.id.value}"
                )

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
        allocated: set[int] = set()

        for request in ordered:
            slot = existing.get(request.request_id)
            if slot is None:
                goal_id = self._next_free_goal(occupied, allocated)
                slot = GoalSlot(
                    id=GoalId(goal_id),
                    role=request.role,
                    provenance_id=_provenance_id(request.request_id, goal_id),
                )
            elif slot.role is not request.role:
                raise ValueError(
                    f"existing binding role mismatch for {request.request_id}"
                )

            if slot.id.value in allocated:
                raise ValueError(
                    f"binding collision on GoalId {slot.id.value}"
                )
            allocated.add(slot.id.value)
            records.append(BindingRecord(request.request_id, slot))

        return BindingResult(tuple(records))

    def _next_free_goal(
        self,
        occupied: set[int],
        allocated: set[int],
    ) -> int:
        candidate = self._base_goal
        while candidate <= GOAL_ID_MAX:
            if candidate not in occupied and candidate not in allocated:
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
