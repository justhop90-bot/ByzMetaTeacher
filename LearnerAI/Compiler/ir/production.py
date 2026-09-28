"""Typed asynchronous production lifecycle observation IR."""
from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression


@dataclass(frozen=True)
class ProductionLifecycle:
    """Native queue admission evidence for an asynchronous train action."""

    unit: str
    native_unit_id: int
    pending_fact: Expression

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("production unit must be nonempty")
        if self.native_unit_id <= 0:
            raise ValueError("production native_unit_id must be positive")
        if self.pending_fact.head != "up-pending-objects":
            raise ValueError(
                "production pending fact must use up-pending-objects"
            )


__all__ = ["ProductionLifecycle"]
