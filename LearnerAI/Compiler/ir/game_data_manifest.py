"""Authoritative Byzantine manifest parsing and factual coverage accounting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from .civ_profile import EffectiveCivData


class ManifestNodeKind(str, Enum):
    BUILDING = "BUILDING"
    UNIT = "UNIT"
    TECHNOLOGY = "TECHNOLOGY"


class ManifestNodeStatus(str, Enum):
    DECLARED = "DECLARED"
    VERIFIED_UNAVAILABLE = "VERIFIED_UNAVAILABLE"


@dataclass(frozen=True)
class ManifestNode:
    id: int
    name: str
    kind: ManifestNodeKind
    status: ManifestNodeStatus
    age: str
    provider_building: int | None
    link_id: int | None
    trigger_id: int | None
    manifest_section: str

    def __post_init__(self) -> None:
        if self.id < 0:
            raise ValueError("manifest node id must be non-negative")
        if not self.name.strip():
            raise ValueError("manifest node name must not be empty")
        if not self.age.strip():
            raise ValueError("manifest node age must not be empty")
        if self.provider_building is not None and self.provider_building < 0:
            raise ValueError("manifest provider building id must be non-negative")
        if self.link_id is not None and self.link_id < 0:
            raise ValueError("manifest link id must be non-negative")
        if self.trigger_id is not None and self.trigger_id < 0:
            raise ValueError("manifest trigger id must be non-negative")


@dataclass(frozen=True)
class ByzantineManifest:
    building_count: int
    unit_tech_count: int
    nodes: tuple[ManifestNode, ...]

    def __post_init__(self) -> None:
        if self.building_count < 0 or self.unit_tech_count < 0:
            raise ValueError("manifest declared counts must be non-negative")
        keys = [(node.kind, node.id) for node in self.nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate Byzantine manifest node identity")
        building_rows = [node for node in self.nodes if node.manifest_section == "BUILDINGS"]
        unit_tech_rows = [
            node for node in self.nodes if node.manifest_section == "UNIT_TECH"
        ]
        if len(building_rows) != self.building_count:
            raise ValueError(
                "declared building count does not match manifest rows: "
                f"declared={self.building_count}, rows={len(building_rows)}"
            )
        if len(unit_tech_rows) != self.unit_tech_count:
            raise ValueError(
                "declared unit/tech count does not match manifest rows: "
                f"declared={self.unit_tech_count}, rows={len(unit_tech_rows)}"
            )
        if len(self.nodes) != self.building_count + self.unit_tech_count:
            raise ValueError("manifest node total does not match declared section counts")


@dataclass(frozen=True)
class ByzantineManifestCoverage:
    modeled_count: int
    verified_unavailable_count: int
    unmodeled_count: int
    modeled_nodes: tuple[ManifestNode, ...] = ()
    verified_unavailable_nodes: tuple[ManifestNode, ...] = ()
    unmodeled_nodes: tuple[ManifestNode, ...] = ()

    def __post_init__(self) -> None:
        if min(
            self.modeled_count,
            self.verified_unavailable_count,
            self.unmodeled_count,
        ) < 0:
            raise ValueError("manifest coverage counts must be non-negative")
        if self.modeled_count != len(self.modeled_nodes):
            raise ValueError("modeled coverage count does not match nodes")
        if self.verified_unavailable_count != len(self.verified_unavailable_nodes):
            raise ValueError("unavailable coverage count does not match nodes")
        if self.unmodeled_count != len(self.unmodeled_nodes):
            raise ValueError("unmodeled coverage count does not match nodes")


_NODE_RE = re.compile(
    r"^(?P<id>\d+) \| (?P<name>.*?) \| TYPE=(?P<type>.*?) "
    r"\| USE=(?P<use>.*?) \| STATUS=(?P<status>.*?) \| AGE=(?P<age>.*?) "
    r"\| BUILDING=(?P<building>.*?) \| LINK=(?P<link>.*?) \| TRIGGER=(?P<trigger>.*?)$"
)


def _optional_int(value: str) -> int | None:
    value = value.strip()
    if value in {"", "<MISSING>"}:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"manifest numeric field is invalid: '{value}'") from exc


def _node_kind(use: str) -> ManifestNodeKind:
    use = use.strip()
    if use == "Building":
        return ManifestNodeKind.BUILDING
    if use == "Unit":
        return ManifestNodeKind.UNIT
    if use == "Tech":
        return ManifestNodeKind.TECHNOLOGY
    raise ValueError(f"unsupported manifest node USE '{use}'")


def _node_status(status: str) -> ManifestNodeStatus:
    status = status.strip()
    if status == "NotAvailable":
        return ManifestNodeStatus.VERIFIED_UNAVAILABLE
    if status in {"ResearchRequired", "ResearchedCompleted"}:
        return ManifestNodeStatus.DECLARED
    raise ValueError(f"unsupported manifest node STATUS '{status}'")


def parse_byzantine_manifest(text: str) -> ByzantineManifest:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Byzantine manifest text must not be empty")

    building_match = re.search(r"^Buildings:\s*(\d+)\s*$", text, re.MULTILINE)
    unit_tech_match = re.search(
        r"^Units/tech nodes:\s*(\d+)\s*$",
        text,
        re.MULTILINE,
    )
    if building_match is None or unit_tech_match is None:
        raise ValueError("Byzantine manifest is missing declared node counts")

    lines = text.splitlines()
    section: str | None = None
    nodes: list[ManifestNode] = []
    for raw in lines:
        line = raw.strip()
        if line == "BUILDINGS":
            section = "BUILDINGS"
            continue
        if line == "AVAILABLE UNIT / TECH NODES":
            section = "UNIT_TECH"
            continue
        if line == "NOT AVAILABLE UNIT / TECH NODES":
            section = "UNIT_TECH"
            continue
        match = _NODE_RE.match(line)
        if match is None or section is None:
            continue

        use = match.group("use").strip()
        kind = _node_kind(use)
        nodes.append(
            ManifestNode(
                id=int(match.group("id")),
                name=match.group("name").strip(),
                kind=kind,
                status=_node_status(match.group("status")),
                age=match.group("age").strip(),
                provider_building=_optional_int(match.group("building")),
                link_id=_optional_int(match.group("link")),
                trigger_id=_optional_int(match.group("trigger")),
                manifest_section=section,
            )
        )

    return ByzantineManifest(
        building_count=int(building_match.group(1)),
        unit_tech_count=int(unit_tech_match.group(1)),
        nodes=tuple(nodes),
    )


def _modeled_ids(effective: EffectiveCivData) -> dict[ManifestNodeKind, frozenset[int]]:
    age_advance_tech_ids = frozenset(
        int(item.native_tech_id)
        for item in effective.age_advances
        if item.native_tech_id is not None
    )
    return {
        ManifestNodeKind.BUILDING: frozenset(int(item.id) for item in effective.buildings),
        ManifestNodeKind.UNIT: frozenset(int(item.id) for item in effective.units),
        ManifestNodeKind.TECHNOLOGY: frozenset(
            int(item.id) for item in effective.technologies
        ) | age_advance_tech_ids,
    }


def classify_byzantine_manifest_coverage(
    manifest: ByzantineManifest,
    effective: EffectiveCivData,
) -> ByzantineManifestCoverage:
    modeled_ids = _modeled_ids(effective)
    modeled: list[ManifestNode] = []
    unavailable: list[ManifestNode] = []
    unmodeled: list[ManifestNode] = []

    for node in manifest.nodes:
        if node.status is ManifestNodeStatus.VERIFIED_UNAVAILABLE:
            unavailable.append(node)
            continue
        if node.id in modeled_ids[node.kind]:
            modeled.append(node)
        else:
            unmodeled.append(node)

    return ByzantineManifestCoverage(
        modeled_count=len(modeled),
        verified_unavailable_count=len(unavailable),
        unmodeled_count=len(unmodeled),
        modeled_nodes=tuple(modeled),
        verified_unavailable_nodes=tuple(unavailable),
        unmodeled_nodes=tuple(unmodeled),
    )


__all__ = [
    "ByzantineManifest",
    "ByzantineManifestCoverage",
    "ManifestNode",
    "ManifestNodeKind",
    "ManifestNodeStatus",
    "classify_byzantine_manifest_coverage",
    "parse_byzantine_manifest",
]
