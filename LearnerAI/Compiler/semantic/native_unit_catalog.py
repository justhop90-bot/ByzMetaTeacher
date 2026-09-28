"""Authoritative native unit-id binding from the checked-in AIRef object inventory."""
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
    / "airef-object-inventory.json"
)


class NativeUnitIdError(ValueError):
    """Raised when a train target cannot be bound to a native UnitId."""


def _aliases(value: str) -> tuple[str, ...]:
    return tuple(
        token.strip().lower()
        for token in value.split(",")
        if token.strip()
    )


@lru_cache(maxsize=1)
def _objects() -> tuple[dict, ...]:
    if not _INVENTORY.is_file():
        raise NativeUnitIdError(
            f"native AIRef object inventory is unavailable at {_INVENTORY}"
        )

    payload = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    return tuple(
        entry
        for entry in payload.get("objects", ())
        if isinstance(entry, dict)
        and isinstance(entry.get("object_id"), int)
        and (entry.get("versions") or {}).get("de") == 1
    )


def _unit_ids_for(token: str) -> tuple[int, ...]:
    ids: set[int] = set()
    for entry in _objects():
        ai_name = entry.get("ai_name")
        if not isinstance(ai_name, str):
            continue
        if token in _aliases(ai_name):
            ids.add(entry["object_id"])
    return tuple(sorted(ids))


def resolve_unit_id(symbol: str) -> int:
    """Resolve one concrete source train target to its native numeric UnitId."""
    token = symbol.strip().lower()
    if not token or not re.fullmatch(r"[a-z][a-z0-9_-]*|[0-9]+", token):
        raise NativeUnitIdError(f"invalid UnitId symbol '{symbol}'")
    if token.isdigit():
        unit_id = int(token)
        known_ids = {entry["object_id"] for entry in _objects()}
        if unit_id not in known_ids:
            raise NativeUnitIdError(
                f"numeric UnitId '{symbol}' is not a known DE unit"
            )
        return unit_id

    matches = _unit_ids_for(token)
    if not matches:
        raise NativeUnitIdError(
            f"unknown native UnitId symbol '{symbol}'"
        )
    if len(matches) > 1:
        raise NativeUnitIdError(
            f"native UnitId symbol '{symbol}' maps to multiple DE objects: "
            + ", ".join(str(item) for item in matches)
        )
    return matches[0]


__all__ = ["NativeUnitIdError", "resolve_unit_id"]
