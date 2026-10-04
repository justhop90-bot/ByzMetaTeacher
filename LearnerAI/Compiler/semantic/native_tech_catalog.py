"""Authoritative native technology-id binding from the checked-in AIRef tech inventory."""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re


_INVENTORY = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "reference"
    / "inventories"
    / "airef-tech-inventory.json"
)

# Current DE engine supplements not represented with AIRef ai_name values.
# These are explicitly anchored by the native metadata profile.
_NATIVE_TECH_SYMBOL_OVERRIDES = {
    61: "ri-logistica",
    1454: "ri-elite-varangian-guard",
}


class NativeTechIdError(ValueError):
    """Raised when a research target cannot be bound to a native TechId."""


def _aliases(value: str) -> tuple[str, ...]:
    return tuple(
        token.strip().lower()
        for token in value.split(",")
        if token.strip()
    )


def _canonical_alias(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])[- _]+(?=[a-z0-9])", "", value.lower())


@lru_cache(maxsize=1)
def _techs() -> tuple[dict, ...]:
    if not _INVENTORY.is_file():
        raise NativeTechIdError(
            f"native AIRef tech inventory is unavailable at {_INVENTORY}"
        )

    payload = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    return tuple(
        entry
        for entry in payload.get("techs", ())
        if isinstance(entry, dict)
        and isinstance(entry.get("tech_id"), int)
        and (entry.get("versions") or {}).get("de") == 1
    )


def _matches(token: str) -> tuple[int, ...]:
    exact: set[int] = set()
    canonical: set[int] = set()
    canonical_token = _canonical_alias(token)

    for entry in _techs():
        ai_name = entry.get("ai_name")
        display_name = entry.get("name")

        ai_aliases = _aliases(ai_name) if isinstance(ai_name, str) else ()
        display_aliases = _aliases(display_name) if isinstance(display_name, str) else ()

        if token in ai_aliases or token in display_aliases:
            exact.add(entry["tech_id"])
            continue

        all_aliases = ai_aliases + display_aliases
        if canonical_token in {
            _canonical_alias(alias) for alias in all_aliases
        }:
            canonical.add(entry["tech_id"])

    matches = exact or canonical
    return tuple(sorted(set(matches)))


def _resolve_entry(symbol: str) -> dict:
    token = symbol.strip().lower()
    for tech_id, runtime_symbol in _NATIVE_TECH_SYMBOL_OVERRIDES.items():
        if token == runtime_symbol:
            return {"tech_id": tech_id, "ai_name": runtime_symbol}
    if not token or not re.fullmatch(r"[a-z][a-z0-9_ -]*|[0-9]+", token):
        raise NativeTechIdError(f"invalid TechId symbol '{symbol}'")
    if token.isdigit():
        tech_id = int(token)
        if tech_id in _NATIVE_TECH_SYMBOL_OVERRIDES:
            return {
                "tech_id": tech_id,
                "ai_name": _NATIVE_TECH_SYMBOL_OVERRIDES[tech_id],
            }
        for entry in _techs():
            if entry["tech_id"] == tech_id:
                return entry
        raise NativeTechIdError(
            f"numeric TechId '{symbol}' is not a known DE technology"
        )

    matches = _matches(token)
    if not matches:
        raise NativeTechIdError(
            f"unknown native TechId symbol '{symbol}'"
        )
    if len(matches) > 1:
        raise NativeTechIdError(
            f"native TechId symbol '{symbol}' maps to multiple DE technologies: "
            + ", ".join(str(item) for item in matches)
        )
    tech_id = matches[0]
    for entry in _techs():
        if entry["tech_id"] == tech_id:
            return entry
    raise NativeTechIdError(
        f"native TechId '{tech_id}' is missing from the DE technology inventory"
    )


def resolve_tech_id(symbol: str) -> int:
    """Resolve a source research target to one deterministic native TechId."""
    return int(_resolve_entry(symbol)["tech_id"])


def resolve_tech_symbol(symbol: str) -> str:
    """Resolve a source research target to its runtime-native AI TechId symbol."""
    entry = _resolve_entry(symbol)
    ai_name = entry.get("ai_name")
    if not isinstance(ai_name, str):
        raise NativeTechIdError(
            f"native TechId '{entry['tech_id']}' has no runtime AI symbol"
        )
    symbols = tuple(
        token.strip()
        for token in ai_name.split(",")
        if token.strip()
    )
    if not symbols:
        raise NativeTechIdError(
            f"native TechId '{entry['tech_id']}' has no runtime AI symbol"
        )
    return symbols[0]


__all__ = ["NativeTechIdError", "resolve_tech_id", "resolve_tech_symbol"]
