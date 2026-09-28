"""Syntax-level AST for the AoE2 .per compiler."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int = 1
    source_unit: str = "<source>"


@dataclass(frozen=True)
class DemandNode:
    name: str
    requirements: tuple[str, ...]
    action: str
    witness: str
    release: str
    location: SourceLocation
    invalidate: str | None = None
    requirement_locations: tuple[SourceLocation, ...] = ()
    action_location: SourceLocation | None = None
    witness_location: SourceLocation | None = None
    release_location: SourceLocation | None = None
    invalidate_location: SourceLocation | None = None
    strategic_number_states: tuple[tuple[str, int, SourceLocation], ...] = ()
    timer_states: tuple[tuple[str, SourceLocation], ...] = ()


@dataclass(frozen=True)
class Expression:
    source: str
    head: str
    args: tuple[object, ...]
    location: Optional[SourceLocation] = None
