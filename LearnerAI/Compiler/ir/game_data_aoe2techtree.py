"""Immutable adapters for machine-readable aoe2techtree civilization-tree snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from .game_data import Age
from .versioning import EvidenceKind, EvidenceRef, PatchId


class Aoe2TechTreeNodeKind(str, Enum):
    BUILDING = "Building"
    UNIT = "Unit"
    TECHNOLOGY = "Tech"


class Aoe2TechTreeNodeStatus(str, Enum):
    RESEARCHED_COMPLETED = "ResearchedCompleted"
    RESEARCH_REQUIRED = "ResearchRequired"
    NOT_AVAILABLE = "NotAvailable"


@dataclass(frozen=True)
class Aoe2TechTreeNode:
    kind: Aoe2TechTreeNodeKind
    node_id: int
    name: str
    age: Age
    building_id: int
    link_id: int | None
    status: Aoe2TechTreeNodeStatus
    node_type: str
    use_type: Aoe2TechTreeNodeKind
    provenance: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if self.node_id < 0:
            raise ValueError("aoe2techtree node id must be non-negative")
        if not self.name.strip():
            raise ValueError("aoe2techtree node name must not be empty")
        if self.building_id < 0:
            raise ValueError("aoe2techtree building id must be non-negative")
        if self.link_id is not None and self.link_id < 0:
            raise ValueError("aoe2techtree link id must be non-negative")
        if not self.node_type.strip():
            raise ValueError("aoe2techtree node type must not be empty")
        if self.use_type is not self.kind:
            raise ValueError("aoe2techtree use_type must match node kind")
        if not self.provenance:
            raise ValueError("aoe2techtree nodes require provenance")


@dataclass(frozen=True)
class Aoe2TechTreeSnapshot:
    civ_name: str
    patch: PatchId
    evidence: EvidenceRef
    buildings: tuple[Aoe2TechTreeNode, ...]
    units_techs: tuple[Aoe2TechTreeNode, ...]

    def __post_init__(self) -> None:
        if not self.civ_name.strip():
            raise ValueError("aoe2techtree civilization name must not be empty")
        if self.evidence.kind is not EvidenceKind.ENGINE_DATA:
            raise ValueError("aoe2techtree snapshots require ENGINE_DATA provenance")
        if self.evidence.patch != self.patch:
            raise ValueError("aoe2techtree snapshot evidence patch must match snapshot patch")

        nodes = self.buildings + self.units_techs
        keys = [(node.kind, node.node_id) for node in nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate aoe2techtree node identity")

        if any(node not in self.buildings and node.kind is Aoe2TechTreeNodeKind.BUILDING for node in nodes):
            raise ValueError("building node stored outside buildings collection")
        if any(node not in self.units_techs and node.kind is not Aoe2TechTreeNodeKind.BUILDING for node in nodes):
            raise ValueError("unit/technology node stored outside units_techs collection")

    def node(self, kind: Aoe2TechTreeNodeKind, node_id: int) -> Aoe2TechTreeNode:
        source = self.buildings if kind is Aoe2TechTreeNodeKind.BUILDING else self.units_techs
        for node in source:
            if node.kind is kind and node.node_id == node_id:
                return node
        raise KeyError(f"unknown aoe2techtree node {kind.value}:{node_id}")


def _age(raw: Any) -> Age:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError("aoe2techtree age_id must be an integer")
    mapping = {
        1: Age.DARK,
        2: Age.FEUDAL,
        3: Age.CASTLE,
        4: Age.IMPERIAL,
    }
    try:
        return mapping[raw]
    except KeyError as exc:
        raise ValueError(f"unsupported aoe2techtree age_id {raw}") from exc


def _status(raw: Any) -> Aoe2TechTreeNodeStatus:
    try:
        return Aoe2TechTreeNodeStatus(str(raw))
    except ValueError as exc:
        raise ValueError(f"unsupported aoe2techtree node_status {raw!r}") from exc


def _kind(raw: Any) -> Aoe2TechTreeNodeKind:
    try:
        return Aoe2TechTreeNodeKind(str(raw))
    except ValueError as exc:
        raise ValueError(f"unsupported aoe2techtree use_type {raw!r}") from exc


def _node(raw: Any, kind: Aoe2TechTreeNodeKind, evidence: EvidenceRef) -> Aoe2TechTreeNode:
    if not isinstance(raw, dict):
        raise ValueError("aoe2techtree node entries must be objects")

    use_type = _kind(raw.get("use_type"))
    if use_type is not kind:
        raise ValueError(
            f"aoe2techtree node use_type {use_type.value} does not match collection {kind.value}"
        )

    node_id = raw.get("node_id")
    building_id = raw.get("building_id")
    if isinstance(node_id, bool) or not isinstance(node_id, int):
        raise ValueError("aoe2techtree node_id must be an integer")
    if isinstance(building_id, bool) or not isinstance(building_id, int):
        raise ValueError("aoe2techtree building_id must be an integer")

    link_id = raw.get("link_id")
    if link_id is not None and (isinstance(link_id, bool) or not isinstance(link_id, int)):
        raise ValueError("aoe2techtree link_id must be an integer or null")

    return Aoe2TechTreeNode(
        kind=kind,
        node_id=node_id,
        name=str(raw.get("name", "")).strip(),
        age=_age(raw.get("age_id")),
        building_id=building_id,
        link_id=link_id,
        status=_status(raw.get("node_status")),
        node_type=str(raw.get("node_type", "")).strip(),
        use_type=use_type,
        provenance=(evidence,),
    )


def parse_aoe2techtree_byzantine_tree_json(
    text: str,
    *,
    source: str,
    revision: str,
    patch: PatchId,
    content_hash: str,
    extraction_version: str = "aoe2techtree-civ-tree-v1",
) -> Aoe2TechTreeSnapshot:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid aoe2techtree civilization tree JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("aoe2techtree civilization tree JSON root must be an object")

    buildings_raw = payload.get("buildings")
    units_techs_raw = payload.get("units_techs")
    if not isinstance(buildings_raw, list) or not isinstance(units_techs_raw, list):
        raise ValueError(
            "aoe2techtree civilization tree JSON requires 'buildings' and 'units_techs' lists"
        )

    evidence = EvidenceRef(
        EvidenceKind.ENGINE_DATA,
        source,
        revision,
        "data/trees/BYZANTINES.json",
        patch,
        content_hash=content_hash,
        extraction_version=extraction_version,
    )

    buildings = tuple(
        sorted(
            (_node(raw, Aoe2TechTreeNodeKind.BUILDING, evidence) for raw in buildings_raw),
            key=lambda node: node.node_id,
        )
    )
    units_techs = tuple(
        sorted(
            (
                _node(
                    raw,
                    Aoe2TechTreeNodeKind.UNIT
                    if raw.get("use_type") == "Unit"
                    else Aoe2TechTreeNodeKind.TECHNOLOGY,
                    evidence,
                )
                for raw in units_techs_raw
            ),
            key=lambda node: (node.kind.value, node.node_id),
        )
    )

    return Aoe2TechTreeSnapshot(
        civ_name="Byzantines",
        patch=patch,
        evidence=evidence,
        buildings=buildings,
        units_techs=units_techs,
    )


__all__ = [
    "Aoe2TechTreeNode",
    "Aoe2TechTreeNodeKind",
    "Aoe2TechTreeNodeStatus",
    "Aoe2TechTreeSnapshot",
    "parse_aoe2techtree_byzantine_tree_json",
]
