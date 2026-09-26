"""Compiler diagnostics."""
from __future__ import annotations

from typing import Iterable


class CompileError(ValueError):
    """Semantic compilation failure with deterministic diagnostics."""

    def __init__(
        self,
        message: str,
        *,
        diagnostics: Iterable[object] = (),
    ) -> None:
        super().__init__(message)
        self.diagnostics = tuple(diagnostics)
