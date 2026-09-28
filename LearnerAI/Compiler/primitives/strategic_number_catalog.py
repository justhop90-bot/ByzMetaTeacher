"""Versioned Strategic Number catalog backed by the pinned AIRef inventory."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from ..runtime_binding import StrategicNumberInventory

STRATEGIC_NUMBER_CATALOG_VERSION = "airef-de-2026-04-29-v1"
SN_NAMESPACE = frozenset(range(512))
COMPILER_RESERVED_SN_IDS = frozenset({511})

_DEFAULT_INVENTORY_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "reference"
    / "inventories"
    / "airef-strategic-number-inventory.json"
)


@dataclass(frozen=True)
class StrategicNumberCatalog:
    version: str
    source_sha256: str
    source_url: str
    de_documented_ids: frozenset[int]
    compiler_candidate_ids: frozenset[int]
    all_ids: frozenset[int]
    inventory: StrategicNumberInventory

    def record_name(self, sn_id: int) -> str | None:
        return self._names.get(sn_id)

    _names: dict[int, str] = None  # replaced by loader; frozen public payload


def load_strategic_number_catalog(
    path: Path | None = None,
) -> StrategicNumberCatalog:
    source_path = path or _DEFAULT_INVENTORY_PATH
    content = source_path.read_bytes()
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Strategic Number inventory must be a JSON object")

    metadata = payload.get("metadata")
    records = payload.get("strategic_numbers")
    if not isinstance(metadata, dict) or not isinstance(records, list):
        raise ValueError("Strategic Number inventory metadata/records are invalid")
    if metadata.get("version_filter") != "de == 1":
        raise ValueError("Strategic Number inventory is not the expected DE-filtered snapshot")

    documented: set[int] = set()
    names: dict[int, str] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Strategic Number inventory record must be an object")
        if record.get("de") != 1:
            continue
        sn_id = int(record["sn_id"])
        name = str(record["name"])
        if sn_id not in SN_NAMESPACE:
            raise ValueError(f"Strategic Number id {sn_id} is outside 0..511")
        if sn_id in documented:
            raise ValueError(f"duplicate documented Strategic Number id {sn_id}")
        if name in names.values():
            raise ValueError(f"duplicate Strategic Number name '{name}'")
        documented.add(sn_id)
        names[sn_id] = name

    expected_documented = metadata.get("strategic_number_count")
    if expected_documented is not None and len(documented) != int(expected_documented):
        raise ValueError(
            f"Strategic Number inventory expected {expected_documented} DE records, "
            f"found {len(documented)}"
        )

    candidates = SN_NAMESPACE - documented - COMPILER_RESERVED_SN_IDS
    inventory_sha = hashlib.sha256(content).hexdigest()
    inventory = StrategicNumberInventory(
        inventory_sha=inventory_sha,
        documented_ids=frozenset(documented),
        candidate_ids=frozenset(candidates),
    )
    return StrategicNumberCatalog(
        version=STRATEGIC_NUMBER_CATALOG_VERSION,
        source_sha256=inventory_sha,
        source_url=str(metadata.get("source", "")),
        de_documented_ids=frozenset(documented),
        compiler_candidate_ids=frozenset(candidates),
        all_ids=SN_NAMESPACE,
        inventory=inventory,
        _names=names,
    )


_default_catalog: StrategicNumberCatalog | None = None


def default_strategic_number_catalog() -> StrategicNumberCatalog:
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = load_strategic_number_catalog()
    return _default_catalog


def default_strategic_number_inventory() -> StrategicNumberInventory:
    return default_strategic_number_catalog().inventory
