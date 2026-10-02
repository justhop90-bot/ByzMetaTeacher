"""Authoritative native BuildingId binding from the checked-in engine catalog."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re


_CATALOG_ROOT = Path(__file__).resolve().parents[3] / "docs" / "reference" / "engine" / "catalog"
_DETAIL_RE = re.compile(r"^- Detail: Object (\d+) - ", re.MULTILINE)


class NativeBuildingIdError(ValueError):
    """Raised when a build target cannot be bound to a native BuildingId."""


# The DE build action uses the completed building name "town-center", while
# the construction lifecycle's pending foundation/object identity is 621.
# This is a deliberate source-target/native-observation split, not a second
# public BuildingId symbol. The checked-in Byzantine object manifest records
# object 621 as the Castle-Age Town Center object used for expansion.
_CANONICAL_BUILDING_ID_OVERRIDES = {
    # The checked-in Byzantine factual snapshot supplies these native object
    # identities. Their engine catalog detail pages are absent from the current
    # catalog tree, so these symbols remain explicit and auditable here rather
    # than silently disappearing from the compiler's build vocabulary.
    "town-center": 621,
    "stable": 101,
    "siege-workshop": 49,
    "university": 209,
    "outpost": 598,
    "watch-tower": 79,
    "stone-wall": 117,
}


@lru_cache(maxsize=1)
def _building_ids() -> dict[str, int]:
    if not _CATALOG_ROOT.is_dir():
        raise NativeBuildingIdError(
            f"native engine catalog is unavailable at {_CATALOG_ROOT}"
        )

    result: dict[str, int] = {}
    for path in sorted(_CATALOG_ROOT.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "- Kind: `object`" not in text:
            continue
        if not re.search(r"^Class: `building-class\b", text, re.MULTILINE):
            continue
        match = _DETAIL_RE.search(text)
        if match is None:
            continue
        token = path.stem.lower()
        object_id = int(match.group(1))
        previous = result.get(token)
        if previous is not None and previous != object_id:
            raise NativeBuildingIdError(
                f"native building symbol '{token}' maps to both {previous} and {object_id}"
            )
        result[token] = object_id

    return result


def resolve_building_id(symbol: str) -> int:
    """Resolve one source build target to its native numeric BuildingId."""
    token = symbol.strip().lower()
    if token.isdigit():
        object_id = int(token)
        if object_id not in _building_ids().values():
            raise NativeBuildingIdError(
                f"numeric BuildingId '{symbol}' is not a known DE building"
            )
        return object_id

    if not token or not re.fullmatch(r"[a-z][a-z0-9_-]*", token):
        raise NativeBuildingIdError(
            f"invalid BuildingId symbol '{symbol}'"
        )

    override = _CANONICAL_BUILDING_ID_OVERRIDES.get(token)
    if override is not None:
        return override

    try:
        return _building_ids()[token]
    except KeyError as exc:
        raise NativeBuildingIdError(
            f"unknown native BuildingId symbol '{symbol}'"
        ) from exc


__all__ = ["NativeBuildingIdError", "resolve_building_id"]
