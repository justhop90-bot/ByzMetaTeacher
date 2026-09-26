"""Syntax-level AST for the Basilisk compiler."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SourceLocation:
    line: int
    column: int = 1

@dataclass(frozen=True)
class DemandNode:
    name: str
    requirements: tuple[str, ...]
    action: str
    witness: str
    release: str
    location: SourceLocation
    invalidate: str | None = None

@dataclass(frozen=True)
class Expression:
    source: str
    head: str
    args: tuple[object, ...]
    location: Optional[SourceLocation] = None
