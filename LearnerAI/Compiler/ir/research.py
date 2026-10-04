"""Typed native research lifecycle observation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..ast import Expression


class ResearchState(IntEnum):
    """Native ResearchState value family from the pinned AIRef inventory."""

    DISABLED = -1
    UNAVAILABLE = 0
    AVAILABLE = 1
    PENDING = 2
    COMPLETE = 3
    QUEUED = 4


@dataclass(frozen=True)
class ResearchLifecycle:
    """Native in-progress observation for an asynchronous research action."""

    technology: str
    native_tech_id: int
    pending_fact: Expression
    pending_state: ResearchState = ResearchState.PENDING

    def __post_init__(self) -> None:
        if not self.technology:
            raise ValueError("research technology must be nonempty")
        if self.native_tech_id < 0:
            raise ValueError("research native_tech_id must be non-negative")
        if self.pending_state is not ResearchState.PENDING:
            raise ValueError(
                "research lifecycle pending_state must remain ResearchState.PENDING"
            )
        if self.pending_fact.head != "up-research-status":
            raise ValueError("research pending fact must use up-research-status")
        if len(self.pending_fact.args) != 4:
            raise ValueError(
                "research pending fact must have typeOp, TechId, compareOp, and ResearchState"
            )
        type_op, tech_id, comparator, state_value = self.pending_fact.args
        if type_op != "c:":
            raise ValueError("research pending fact must use c: for TechId")
        if not isinstance(tech_id, str) or not tech_id.startswith("ri-"):
            raise ValueError(
                "research pending fact must use a runtime-native TechId symbol"
            )
        if comparator != ">=":
            raise ValueError(
                "research pending fact must compare ResearchState with >="
            )
        if state_value != "research-pending":
            raise ValueError(
                "research pending fact must use runtime-native research-pending state"
            )


__all__ = ["ResearchLifecycle", "ResearchState"]
