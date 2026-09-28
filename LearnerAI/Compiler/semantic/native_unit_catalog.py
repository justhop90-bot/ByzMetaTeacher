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
def _unit_ids() -> dict[str, int]:
    if not _INVENTORY.is_file():
        raise NativeUnitIdError(
            f"native AIRef object inventory is unavailable at {_INVENTORY}"
        )

    payload = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    result: dict[str, int] = {}
    for entry in payload.get("objects", ()):
        object_id = entry.get("object_id")
        ai_name = entry.get("ai_name")
        versions = entry.get("versions") or {}
        if not isinstance(object_id, int) or versions.get("de") != 1:
            continue
        if not isinstance(ai_name, str):
            continue
        for alias in _aliases(ai_name):
            previous = result.get(alias)
            if previous is not None and previous != object_id:
                raise NativeUnitIdError(
                    f"native unit symbol '{alias}' maps to both "
                    f"{previous} and {object_id}"
                )
            result[alias] = object_id
    return result


def resolve_unit_id(symbol: str) -> int:
    """Resolve one concrete source train target to its native numeric UnitId."""
    token = symbol.strip().lower()
    if not token or not re.fullmatch(r"[a-z][a-z0-9_-]*|[0-9]+", token):
        raise NativeUnitIdError(f"invalid UnitId symbol '{symbol}'")
    if token.isdigit():
        unit_id = int(token)
        if unit_id not in _unit_ids().values():
            raise NativeUnitIdError(
                f"numeric UnitId '{symbol}' is not a known DE unit"
            )
        return unit_id
    try:
        return _unit_ids()[token]
    except KeyError as exc:
        raise NativeUnitIdError(
            f"unknown native UnitId symbol '{symbol}'"
        ) from exc


__all__ = ["NativeUnitIdError", "resolve_unit_id"]
