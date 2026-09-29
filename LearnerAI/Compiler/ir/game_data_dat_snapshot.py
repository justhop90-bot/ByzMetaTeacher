"""Deterministic import boundary for DAT-derived technology metadata."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any

from .game_data import GameData, ResourceCost, TechId, TechnologyDef
from .versioning import EvidenceKind, EvidenceRef, PatchId


@dataclass(frozen=True)
class DatTechnologyRecord:
    tech_id: TechId
    name: str
    native_civ: int
    base_cost: ResourceCost
    research_time_seconds: int
    research_location: int | None
    effect_id: int
    required_tech_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("DAT technology name must not be empty")
        if self.native_civ < -1:
            raise ValueError("DAT technology civ must be -1 or a non-negative civ id")
        if self.research_time_seconds < 0:
            raise ValueError("DAT research time must be non-negative")
        if self.research_location is not None and self.research_location < 0:
            raise ValueError("DAT research location must be non-negative")
        if self.effect_id < -1:
            raise ValueError("DAT effect id must be -1 or non-negative")
        if any(value < 0 for value in self.required_tech_ids):
            raise ValueError("DAT required technology ids must be non-negative")
        if len(set(self.required_tech_ids)) != len(self.required_tech_ids):
            raise ValueError("DAT required technology ids must be unique")


@dataclass(frozen=True)
class DatTechnologySnapshot:
    patch: PatchId
    evidence: EvidenceRef
    records: tuple[DatTechnologyRecord, ...]

    def __post_init__(self) -> None:
        if self.evidence.kind is not EvidenceKind.ENGINE_DATA:
            raise ValueError("DAT technology snapshots require ENGINE_DATA provenance")
        if self.evidence.patch != self.patch:
            raise ValueError("DAT snapshot evidence patch must match snapshot patch")
        if not self.evidence.content_hash:
            raise ValueError("DAT technology snapshots require immutable content_hash provenance")

        ids = [record.tech_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate DAT technology id")
        if tuple(ids) != tuple(sorted(ids)):
            raise ValueError("DAT technology records must be sorted by TechId")


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"DAT technology field '{field}' must be an integer")
    return value


def _parse_cost(raw: Any) -> ResourceCost:
    if raw is None:
        return ResourceCost()
    if not isinstance(raw, dict):
        raise ValueError("DAT technology cost must be an object")
    allowed = {"food", "wood", "gold", "stone"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"DAT technology cost has unknown resources: {unknown}")
    values = {name: _require_int(raw.get(name, 0), f"cost.{name}") for name in allowed}
    return ResourceCost(**values)


def parse_dat_technologies_json(
    text: str,
    *,
    source: str,
    revision: str,
    patch: PatchId,
    content_hash: str,
    extraction_version: str = "dat-technology-json-v1",
) -> DatTechnologySnapshot:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid DAT technologies JSON: {exc}") from exc

    records_payload = payload.get("technologies") if isinstance(payload, dict) else payload
    if not isinstance(records_payload, list):
        raise ValueError("DAT technologies JSON must be a list or an object with 'technologies'")

    records: list[DatTechnologyRecord] = []
    for raw in records_payload:
        if not isinstance(raw, dict):
            raise ValueError("each DAT technology entry must be an object")

        tech_id = TechId(_require_int(raw.get("id"), "id"))
        required = raw.get("required_techs")
        if required is None:
            singular = raw.get("required_tech")
            required = [] if singular is None or singular < 0 else [singular]
        if not isinstance(required, list):
            raise ValueError("DAT required_techs must be a list")

        records.append(
            DatTechnologyRecord(
                tech_id=tech_id,
                name=str(raw.get("name", "")).strip(),
                native_civ=_require_int(raw.get("civ", -1), "civ"),
                base_cost=_parse_cost(raw.get("cost", {})),
                research_time_seconds=_require_int(
                    raw.get("research_time", 0),
                    "research_time",
                ),
                research_location=(
                    None
                    if raw.get("research_location") is None
                    else _require_int(raw["research_location"], "research_location")
                ),
                effect_id=_require_int(raw.get("effect_id", -1), "effect_id"),
                required_tech_ids=tuple(
                    _require_int(value, "required_techs[]") for value in required
                ),
            )
        )

    evidence = EvidenceRef(
        EvidenceKind.ENGINE_DATA,
        source,
        revision,
        "technologies.json",
        patch,
        content_hash=content_hash,
        extraction_version=extraction_version,
    )
    return DatTechnologySnapshot(
        patch=patch,
        evidence=evidence,
        records=tuple(sorted(records, key=lambda record: record.tech_id)),
    )


def enrich_game_data_from_dat_snapshot(
    data: GameData,
    snapshot: DatTechnologySnapshot,
) -> GameData:
    if snapshot.patch != data.patch:
        raise ValueError(
            f"DAT snapshot patch {snapshot.patch.key} does not exactly match "
            f"GameData patch {data.patch.key}"
        )

    snapshot_by_id = {record.tech_id: record for record in snapshot.records}
    enriched: list[TechnologyDef] = []

    for technology in data.technologies:
        record = snapshot_by_id.get(technology.id)
        if record is None:
            enriched.append(technology)
            continue

        if record.name != technology.name:
            raise ValueError(
                f"DAT technology name mismatch for TechId {int(technology.id)}: "
                f"GameData='{technology.name}', DAT='{record.name}'"
            )

        provenance = technology.provenance
        if snapshot.evidence not in provenance:
            provenance = provenance + (snapshot.evidence,)

        enriched.append(
            replace(
                technology,
                base_cost=(
                    technology.base_cost
                    if technology.base_cost is not None
                    else record.base_cost
                ),
                research_time_seconds=(
                    technology.research_time_seconds
                    if technology.research_time_seconds is not None
                    else record.research_time_seconds
                ),
                provenance=provenance,
            )
        )

    unknown_ids = sorted(
        int(record.tech_id)
        for record in snapshot.records
        if record.tech_id not in {technology.id for technology in data.technologies}
    )
    if unknown_ids:
        raise ValueError(
            f"DAT snapshot contains technology ids absent from GameData: {unknown_ids}"
        )

    return replace(data, technologies=tuple(enriched))


__all__ = [
    "DatTechnologyRecord",
    "DatTechnologySnapshot",
    "enrich_game_data_from_dat_snapshot",
    "parse_dat_technologies_json",
]
