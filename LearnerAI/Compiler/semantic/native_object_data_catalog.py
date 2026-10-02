"""Authoritative native ObjectData value binding from the checked-in AIRef inventory."""
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
    / "airef-value-family-inventory.json"
)
_OBJECT_DATA_FAMILY = "32"


class NativeObjectDataError(ValueError):
    """Raised when a DUC ObjectData operand is not a documented native value."""


@lru_cache(maxsize=1)
def _object_data_ids() -> frozenset[int]:
    if not _INVENTORY.is_file():
        raise NativeObjectDataError(
            f"native ObjectData inventory is unavailable at {_INVENTORY}"
        )

    payload = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    family = payload.get("families", {}).get(_OBJECT_DATA_FAMILY)
    if not isinstance(family, dict):
        raise NativeObjectDataError(
            "native ObjectData value family 32 is missing from the checked-in inventory"
        )

    ids: set[int] = set()
    for entry in family.get("entries", ()):
        if not isinstance(entry, dict):
            continue
        value = entry.get("id")
        try:
            ids.add(int(str(value), 10))
        except (TypeError, ValueError):
            continue
    if not ids:
        raise NativeObjectDataError(
            "native ObjectData value family 32 contains no numeric entries"
        )
    return frozenset(ids)


def resolve_object_data_id(symbol: str) -> int:
    """Resolve one DUC ObjectData operand to its documented native numeric ID.

    DUC plans deliberately carry native arguments, not a second source-language
    enum surface. Symbolic ObjectData names therefore fail closed rather than
    being silently invented or emitted without a defconst.
    """
    token = symbol.strip().lower()
    if not token or not re.fullmatch(r"-?\d+", token):
        raise NativeObjectDataError(
            f"ObjectData operand '{symbol}' must be a numeric native ObjectData ID"
        )

    value = int(token, 10)
    if value not in _object_data_ids():
        raise NativeObjectDataError(
            f"ObjectData ID '{symbol}' is not present in the checked-in native inventory"
        )
    return value


__all__ = ["NativeObjectDataError", "resolve_object_data_id"]
