"""Typed native research lifecycle observation."""
from __future__ import annotations

from dataclasses import dataclass

from ..ast import Expression


@dataclass(frozen=True)
class ResearchLifecycle:
    """Native in-progress observation for an asynchronous research action."""

    technology: str
    pending_fact: Expression

    def __post_init__(self) -> None:
        if not self.technology:
            raise ValueError("research technology must be nonempty")
        if self.pending_fact.head != "up-research-status":
            raise ValueError("research pending fact must use up-research-status")
        if self.pending_fact.args[-1] != "research-pending":
            raise ValueError(
                "research pending fact must compare against research-pending"
            )


__all__ = ["ResearchLifecycle"]
