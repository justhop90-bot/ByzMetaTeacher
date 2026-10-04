"""Native AI engine metadata kept separate from game/civilization facts."""
from __future__ import annotations

from dataclasses import dataclass

from .versioning import PatchId


@dataclass(frozen=True)
class NativeIdentifier:
    symbol: str
    native_kind: str
    numeric_id: int | None
    built_in: bool
    local_alias_required: bool
    introduced: PatchId
    removed: PatchId | None = None

    def usable_with_local_alias(self, local_aliases: frozenset[str]) -> bool:
        return self.built_in or not self.local_alias_required or self.symbol in local_aliases


@dataclass(frozen=True)
class NativeParameterContract:
    command: str
    parameter_index: int
    parameter_type: str
    direction: str
    version: PatchId


@dataclass(frozen=True)
class NativeEngineProfile:
    version: PatchId
    identifiers: tuple[NativeIdentifier, ...]
    parameters: tuple[NativeParameterContract, ...] = ()
    goal_range: tuple[int, int] = (1, 16000)
    strategic_number_range: tuple[int, int] = (0, 511)
    timer_range: tuple[int, int] = (1, 50)
    rule_element_limit: int = 32
    rule_limit: int = 10000
    source_line_limit: int = 255

    def identifier(self, symbol: str) -> NativeIdentifier:
        for item in self.identifiers:
            if item.symbol == symbol:
                return item
        raise KeyError(f"unknown native identifier: {symbol}")

    def require_symbol(
        self,
        symbol: str,
        *,
        local_aliases: set[str] | frozenset[str] = frozenset(),
    ) -> NativeIdentifier:
        identifier = self.identifier(symbol)
        if not identifier.usable_with_local_alias(frozenset(local_aliases)):
            raise ValueError(
                f"native identifier '{symbol}' requires an explicit local alias"
            )
        return identifier


def default_de_native_profile() -> NativeEngineProfile:
    patch = PatchId("AOE2DE", "185872", None, "2026-09-22")
    return NativeEngineProfile(
        version=patch,
        identifiers=(
            NativeIdentifier(
                symbol="ri-logistica",
                native_kind="TechId",
                numeric_id=61,
                built_in=False,
                local_alias_required=True,
                introduced=patch,
            ),
            NativeIdentifier(
                symbol="ri-elite-varangian-guard",
                native_kind="TechId",
                numeric_id=1454,
                built_in=False,
                local_alias_required=True,
                introduced=patch,
            ),
        ),
    )
