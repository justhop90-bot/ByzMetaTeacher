"""Typed asynchronous production lifecycle observation IR."""
from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression
from .model import GoalRole, GoalSlotRequest




@dataclass(frozen=True)
class ProductionQueueStateObservation:
    """Typed current+queued production observation for one unit target."""

    primitive: str
    expression: Expression
    native_unit_id: int
    semantic_id: str

    def __post_init__(self) -> None:
        if self.primitive != "unit-type-count-total":
            raise ValueError(
                "production queue-state observation must use unit-type-count-total"
            )
        if self.expression.head != self.primitive:
            raise ValueError(
                "production queue-state observation expression must match its primitive"
            )
        if self.native_unit_id <= 0:
            raise ValueError(
                "production queue-state observation native_unit_id must be positive"
            )
        if (
            not self.expression.args
            or str(self.expression.args[0]) != str(self.native_unit_id)
        ):
            raise ValueError(
                f"production queue-state observation does not target "
                f"UnitId {self.native_unit_id}"
            )
        if self.semantic_id != "witness.unit.present.total":
            raise ValueError(
                "production queue-state observation must use "
                "witness.unit.present.total semantic mapping"
            )


@dataclass(frozen=True)
class ProductionProviderStateObservation:
    """Typed provider world-state observation for one production building."""

    primitive: str
    expression: Expression
    native_building_id: int
    semantic_id: str

    def __post_init__(self) -> None:
        if self.primitive != "building-type-count":
            raise ValueError(
                "production provider-state observation must use building-type-count"
            )
        if self.expression.head != self.primitive:
            raise ValueError(
                "production provider-state observation expression must match its primitive"
            )
        if self.native_building_id <= 0:
            raise ValueError(
                "production provider-state observation native_building_id must be positive"
            )
        if (
            not self.expression.args
            or str(self.expression.args[0]) != str(self.native_building_id)
        ):
            raise ValueError(
                f"production provider-state observation does not target "
                f"BuildingId {self.native_building_id}"
            )
        if self.semantic_id != "witness.building.present":
            raise ValueError(
                "production provider-state observation must use "
                "witness.building.present semantic mapping"
            )


@dataclass(frozen=True)
class ProductionLifecycle:
    """Native queue admission evidence for an asynchronous train action."""

    unit: str
    native_unit_id: int
    pending_fact: Expression
    completion_witness: Expression
    retry_barrier: GoalSlotRequest
    queue_state: ProductionQueueStateObservation | None = None
    provider_state: ProductionProviderStateObservation | None = None

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("production unit must be nonempty")
        if self.native_unit_id <= 0:
            raise ValueError("production native_unit_id must be positive")
        if self.pending_fact.head != "up-pending-objects":
            raise ValueError(
                "production pending fact must use up-pending-objects"
            )
        if self.completion_witness.head != "unit-type-count":
            raise ValueError(
                "production completion witness must use unit-type-count"
            )
        if (
            not self.completion_witness.args
            or str(self.completion_witness.args[0]) != self.unit
        ):
            raise ValueError(
                f"production completion witness must target unit '{self.unit}'"
            )
        if self.retry_barrier.request_id.purpose != "production-retry-barrier":
            raise ValueError(
                "production retry barrier must use the "
                "'production-retry-barrier' purpose"
            )
        if self.retry_barrier.role is not GoalRole.EXECUTION_MEMORY:
            raise ValueError(
                "production retry barrier must use EXECUTION_MEMORY role"
            )
        if (
            self.queue_state is not None
            and self.queue_state.native_unit_id != self.native_unit_id
        ):
            raise ValueError(
                "production queue-state observation must target the lifecycle unit"
            )


__all__ = [
    "ProductionLifecycle",
    "ProductionProviderStateObservation",
    "ProductionQueueStateObservation",
]
