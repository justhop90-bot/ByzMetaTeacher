"""Typed asynchronous production lifecycle observation IR."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..ast import Expression
from .model import GoalRole, GoalSlotRequest






class ProductionFactDisposition(str, Enum):
    SUPPORTED = "SUPPORTED"
    OPEN = "OPEN"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ProductionTargetAdmission:
    """Typed native feasibility fact that admits one production target."""

    disposition: ProductionFactDisposition
    primitive: str
    expression: Expression
    native_unit_id: int
    semantic_id: str

    def __post_init__(self) -> None:
        if self.disposition is not ProductionFactDisposition.SUPPORTED:
            raise ValueError("production target admission must be SUPPORTED")
        if self.primitive not in {"can-train", "can-train-with-escrow"}:
            raise ValueError(
                "production target admission must use can-train or "
                "can-train-with-escrow"
            )
        if self.expression.head != self.primitive:
            raise ValueError(
                "production target admission expression must match its primitive"
            )
        if self.native_unit_id <= 0:
            raise ValueError(
                "production target admission native_unit_id must be positive"
            )
        if (
            not self.expression.args
            or str(self.expression.args[0]) != str(self.native_unit_id)
        ):
            raise ValueError(
                f"production target admission does not target UnitId "
                f"{self.native_unit_id}"
            )
        expected_semantic_id = {
            "can-train": "execution.train.feasibility",
            "can-train-with-escrow": "execution.train.feasibility.escrow",
        }[self.primitive]
        if self.semantic_id != expected_semantic_id:
            raise ValueError(
                f"production target admission '{self.primitive}' must use "
                f"{expected_semantic_id} semantic mapping"
            )


@dataclass(frozen=True)
class ProductionQueueProtection:
    """Typed anti-duplication protection for one production target."""

    disposition: ProductionFactDisposition
    pending_fact: Expression
    native_unit_id: int

    def __post_init__(self) -> None:
        if self.disposition is not ProductionFactDisposition.SUPPORTED:
            raise ValueError("production queue protection must be SUPPORTED")
        if self.pending_fact.head != "up-pending-objects":
            raise ValueError(
                "production queue protection must use up-pending-objects"
            )
        if self.native_unit_id <= 0:
            raise ValueError(
                "production queue protection native_unit_id must be positive"
            )
        if (
            len(self.pending_fact.args) < 2
            or str(self.pending_fact.args[1]) != str(self.native_unit_id)
        ):
            raise ValueError(
                f"production queue protection does not target UnitId "
                f"{self.native_unit_id}"
            )

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
class ProductionQueueCapacityEvidence:
    """Open evidence source for queue-capacity semantics."""

    disposition: ProductionFactDisposition
    expression: Expression
    native_unit_id: int
    source_semantic_id: str

    def __post_init__(self) -> None:
        if self.disposition is not ProductionFactDisposition.OPEN:
            raise ValueError("production queue-capacity evidence must remain OPEN")
        if self.expression.head != "unit-type-count-total":
            raise ValueError(
                "production queue-capacity evidence must use unit-type-count-total"
            )
        if self.native_unit_id <= 0:
            raise ValueError(
                "production queue-capacity evidence native_unit_id must be positive"
            )
        if (
            not self.expression.args
            or str(self.expression.args[0]) != str(self.native_unit_id)
        ):
            raise ValueError(
                f"production queue-capacity evidence does not target UnitId "
                f"{self.native_unit_id}"
            )
        if self.source_semantic_id != "witness.unit.present.total":
            raise ValueError(
                "production queue-capacity evidence must retain the source "
                "semantic mapping witness.unit.present.total"
            )


@dataclass(frozen=True)
class ProductionProviderAvailabilityEvidence:
    """Open evidence source for provider availability semantics."""

    disposition: ProductionFactDisposition
    expression: Expression
    native_building_id: int
    source_semantic_id: str

    def __post_init__(self) -> None:
        if self.disposition is not ProductionFactDisposition.OPEN:
            raise ValueError(
                "production provider-availability evidence must remain OPEN"
            )
        if self.expression.head != "building-type-count":
            raise ValueError(
                "production provider-availability evidence must use "
                "building-type-count"
            )
        if self.native_building_id <= 0:
            raise ValueError(
                "production provider-availability evidence native_building_id "
                "must be positive"
            )
        if (
            not self.expression.args
            or str(self.expression.args[0]) != str(self.native_building_id)
        ):
            raise ValueError(
                f"production provider-availability evidence does not target "
                f"BuildingId {self.native_building_id}"
            )
        if self.source_semantic_id != "witness.building.present":
            raise ValueError(
                "production provider-availability evidence must retain the source "
                "semantic mapping witness.building.present"
            )


@dataclass(frozen=True)
class ProductionQueueCapacityControlEvidence:
    """Open native control evidence for the DE training queue capacity."""

    disposition: ProductionFactDisposition
    expression: Expression
    native_strategic_number_id: int
    configured_additional_queue_slots: int
    documented_total_capacity: int
    semantic_id: str

    def __post_init__(self) -> None:
        if self.disposition is not ProductionFactDisposition.OPEN:
            raise ValueError(
                "production queue-capacity control evidence must remain OPEN"
            )
        if self.expression.head != "up-compare-sn":
            raise ValueError(
                "production queue-capacity control evidence must use up-compare-sn"
            )
        if len(self.expression.args) != 3:
            raise ValueError(
                "production queue-capacity control evidence requires "
                "SnId, compareOp, and value"
            )
        if str(self.expression.args[0]) != str(self.native_strategic_number_id):
            raise ValueError(
                "production queue-capacity control evidence must target "
                f"Strategic Number {self.native_strategic_number_id}"
            )
        if str(self.expression.args[1]) != "==":
            raise ValueError(
                "production queue-capacity control evidence must use exact equality"
            )
        if not 0 <= self.configured_additional_queue_slots <= 15:
            raise ValueError(
                "production queue-capacity control evidence additional queue "
                "slots must be in 0..15"
            )
        if (
            self.documented_total_capacity
            != self.configured_additional_queue_slots + 1
        ):
            raise ValueError(
                "production queue-capacity control evidence total capacity must "
                "equal additional queue slots plus one active training slot"
            )
        if str(self.expression.args[2]) != str(
            self.configured_additional_queue_slots
        ):
            raise ValueError(
                "production queue-capacity control evidence value does not match "
                "configured additional queue slots"
            )
        if self.semantic_id != "controller.production.queue-capacity.sn264":
            raise ValueError(
                "production queue-capacity control evidence must use the "
                "controller.production.queue-capacity.sn264 semantic mapping"
            )


@dataclass(frozen=True)
class ProductionLifecycle:

    """Separated target-admission and queue-protection contract for train."""

    unit: str
    native_unit_id: int
    target_admission: ProductionTargetAdmission
    completion_witness: Expression
    retry_barrier: GoalSlotRequest
    queue_protection: ProductionQueueProtection
    queue_state: ProductionQueueStateObservation | None = None
    provider_state: ProductionProviderStateObservation | None = None
    queue_capacity_evidence: ProductionQueueCapacityEvidence | None = None
    provider_availability_evidence: ProductionProviderAvailabilityEvidence | None = None
    queue_capacity_control: ProductionQueueCapacityControlEvidence | None = None

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("production unit must be nonempty")
        if self.native_unit_id <= 0:
            raise ValueError("production native_unit_id must be positive")
        if self.target_admission.native_unit_id != self.native_unit_id:
            raise ValueError(
                "production target admission must target the lifecycle unit"
            )
        if self.queue_protection.native_unit_id != self.native_unit_id:
            raise ValueError(
                "production queue protection must target the lifecycle unit"
            )
        if (
            self.queue_state is not None
            and self.queue_state.native_unit_id != self.native_unit_id
        ):
            raise ValueError(
                "production queue-state observation must target the lifecycle unit"
            )
        if (
            self.queue_capacity_evidence is not None
            and self.queue_capacity_evidence.native_unit_id != self.native_unit_id
        ):
            raise ValueError(
                "production queue-capacity evidence must target the lifecycle unit"
            )
        if (
            self.provider_state is not None
            and self.provider_state.native_building_id <= 0
        ):
            raise ValueError(
                "production provider-state observation native_building_id must be positive"
            )
        if (
            self.provider_availability_evidence is not None
            and self.provider_availability_evidence.native_building_id <= 0
        ):
            raise ValueError(
                "production provider-availability evidence native_building_id "
                "must be positive"
            )
        if (
            self.completion_witness.head != "unit-type-count"
        ):
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

    @property
    def pending_fact(self) -> Expression:
        return self.queue_protection.pending_fact


__all__ = [
    "ProductionFactDisposition",
    "ProductionLifecycle",
    "ProductionQueueCapacityEvidence",
    "ProductionQueueProtection",
    "ProductionTargetAdmission",
    "ProductionProviderAvailabilityEvidence",
    "ProductionQueueCapacityControlEvidence",
    "ProductionProviderStateObservation",
    "ProductionQueueStateObservation",
]
