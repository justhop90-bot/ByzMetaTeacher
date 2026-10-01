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


@dataclass(frozen=True)
class ActiveSNSeed:
    """Authored evidence input for one active Strategic Number.

    Prevalence counts are checked-in research data (Promisory/Naga corpus
    hits measured against the pinned inventory names), not a live
    filesystem scan: the loader never touches the game install, so record
    building stays deterministic on any machine.
    """

    sn_id: int
    prevalence: tuple[tuple[str, int], ...]
    semantic_role: str
    unknown_boundary: str


_UNMAPPED_SN_ROLE = "UNMAPPED"

_COMMON_UNKNOWN_TAIL = (
    " Per-SN engine effect unmodeled; no AUTO_MUTATES target is proven "
    "for any SN; compiler reads/writes carry syntax only."
)

ACTIVE_SN_SEEDS: tuple[ActiveSNSeed, ...] = (
    ActiveSNSeed(
        sn_id=0,
        prevalence=(("naga", 46), ("promisory", 41)),
        semantic_role="civilian-task-allocation",
        unknown_boundary=(
            "AIRef default 34 with required range 0 to 100 verbatim."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=1,
        prevalence=(("naga", 2), ("promisory", 2)),
        semantic_role="civilian-task-allocation",
        unknown_boundary=(
            "AIRef effective=0 despite descriptive controller surfacing; "
            "not executable proof."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=2,
        prevalence=(("naga", 8), ("promisory", 8)),
        semantic_role="civilian-task-allocation",
        unknown_boundary=(
            "AIRef effective=0 despite descriptive controller surfacing; "
            "not executable proof."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=18,
        prevalence=(("naga", 54), ("promisory", 49)),
        semantic_role="exploration-control",
        unknown_boundary=(
            "Required range -1 to Max verbatim; upper-bound authority OPEN."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=20,
        prevalence=(("naga", 14), ("promisory", 18)),
        semantic_role="town-size-defense-targeting",
        unknown_boundary="AIRef default 25 with required range 0 to 50 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=36,
        prevalence=(("naga", 26), ("promisory", 25)),
        semantic_role="attack-group-control",
        unknown_boundary=(
            "Required range 0 to Max verbatim; upper-bound authority OPEN."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=42,
        prevalence=(("naga", 52), ("promisory", 52)),
        semantic_role="exploration-control",
        unknown_boundary=(
            "Required range 0 to Max verbatim; upper-bound authority OPEN."
            + _COMMON_UNKNOWN_TAIL
        ),
    ),
    ActiveSNSeed(
        sn_id=74,
        prevalence=(("naga", 169), ("promisory", 187)),
        semantic_role="town-size-defense-targeting",
        unknown_boundary="AIRef default 20 with required range 0 to 255 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=117,
        prevalence=(("naga", 193), ("promisory", 170)),
        semantic_role="civilian-task-allocation",
        unknown_boundary="AIRef default 0 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=118,
        prevalence=(("naga", 216), ("promisory", 171)),
        semantic_role="civilian-task-allocation",
        unknown_boundary="AIRef default 0 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=119,
        prevalence=(("naga", 175), ("promisory", 141)),
        semantic_role="civilian-task-allocation",
        unknown_boundary="AIRef default 0 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=120,
        prevalence=(("naga", 202), ("promisory", 176)),
        semantic_role="civilian-task-allocation",
        unknown_boundary="AIRef default 0 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=167,
        prevalence=(("naga", 1), ("promisory", 3)),
        semantic_role="exploration-control",
        unknown_boundary="AIRef default 2 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=227,
        prevalence=(("naga", 36), ("promisory", 36)),
        semantic_role="attack-group-control",
        unknown_boundary="AIRef default 75 with required range 0 to 100 verbatim."
        + _COMMON_UNKNOWN_TAIL,
    ),
    ActiveSNSeed(
        sn_id=264,
        prevalence=(("naga", 3), ("promisory", 36)),
        semantic_role=_UNMAPPED_SN_ROLE,
        unknown_boundary=(
            "OPEN queue-capacity evidence, not a controller surface: "
            "exact-equality up-compare-sn reads only; DE enforcement, "
            "provider busy/queued behavior, and birth/queue-exit timing OPEN."
        ),
    ),
)


@dataclass(frozen=True)
class ActiveSNRecord:
    """Evidence-closed record for one actively used Strategic Number.

    Carries the pinned AIRef facts verbatim (never synthesized) plus the
    checked-in community-prevalence and compiler-role evidence. The
    evidence hash covers the canonical record so tampering fails closed.
    Per-SN engine effects, auto-mutation, and version deltas stay in
    `unknown_boundary`: this record proves evidence status, never native
    behavior.
    """

    sn_id: int
    canonical_name: str
    version: str
    supported_versions: tuple[str, ...]
    default: int | None
    required_range: str
    effective: int
    auto_mutation: str
    prevalence: tuple[tuple[str, int], ...]
    semantic_role: str
    evidence_hash: str
    unknown_boundary: str

    def __post_init__(self) -> None:
        if self.sn_id not in SN_NAMESPACE:
            raise ValueError(f"active SN id {self.sn_id} is outside 0..511")
        if not self.canonical_name.strip():
            raise ValueError("active SN canonical name must not be empty")
        if "DE" not in self.supported_versions:
            raise ValueError(
                f"active SN {self.sn_id} is not covered by a DE version scope"
            )
        if self.default is not None and (
            not isinstance(self.default, int)
            or isinstance(self.default, bool)
        ):
            raise ValueError(f"active SN {self.sn_id} default must be an integer")
        if not self.required_range.strip():
            raise ValueError(f"active SN {self.sn_id} required range must not be empty")
        if self.effective not in (0, 1):
            raise ValueError(f"active SN {self.sn_id} effective status must be 0 or 1")
        if self.auto_mutation != "UNKNOWN":
            raise ValueError(
                f"active SN {self.sn_id} auto-mutation '{self.auto_mutation}' is "
                "unproven: only UNKNOWN is admissible"
            )
        if not self.prevalence:
            raise ValueError(f"active SN {self.sn_id} prevalence must not be empty")
        sources = tuple(source for source, _ in self.prevalence)
        if tuple(sorted(sources)) != sources:
            raise ValueError(
                f"active SN {self.sn_id} prevalence sources must be sorted for determinism"
            )
        for source, hits in self.prevalence:
            if not source.strip() or not isinstance(hits, int) or isinstance(hits, bool) or hits < 0:
                raise ValueError(
                    f"active SN {self.sn_id} prevalence entries must be named sources "
                    "with non-negative hit counts"
                )
        if not self.semantic_role.strip():
            raise ValueError(f"active SN {self.sn_id} semantic role must not be empty")
        if not self.unknown_boundary.strip():
            raise ValueError(f"active SN {self.sn_id} UNKNOWN boundary must not be empty")
        if self.evidence_hash != _active_sn_evidence_hash(self._canonical_payload()):
            raise ValueError(
                f"active SN {self.sn_id} evidence hash does not match its canonical payload"
            )

    def _canonical_payload(self) -> dict:
        return {
            "sn_id": self.sn_id,
            "canonical_name": self.canonical_name,
            "version": self.version,
            "supported_versions": sorted(self.supported_versions),
            "default": self.default,
            "required_range": self.required_range,
            "effective": self.effective,
            "auto_mutation": self.auto_mutation,
            "prevalence": [list(entry) for entry in self.prevalence],
            "semantic_role": self.semantic_role,
            "unknown_boundary": self.unknown_boundary,
        }

    @property
    def prevalence_total(self) -> int:
        return sum(hits for _, hits in self.prevalence)


def _active_sn_evidence_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_active_sn_records(
    path: Path | None = None,
    *,
    seeds: tuple[ActiveSNSeed, ...] = ACTIVE_SN_SEEDS,
) -> tuple[ActiveSNRecord, ...]:
    """Build evidence records for the active SN subset from the pinned inventory.

    Fails closed: unknown ids, name drift, non-DE scope, and any proven
    auto-mutation claim all raise. Records return sorted by SN id.
    """
    source_path = path or _DEFAULT_INVENTORY_PATH
    payload = json.loads(source_path.read_bytes().decode("utf-8"))
    records = payload.get("strategic_numbers")
    if not isinstance(records, list):
        raise ValueError("Strategic Number inventory records are invalid")
    by_id = {}
    for record in records:
        if not isinstance(record, dict) or record.get("de") != 1:
            continue
        by_id[int(record["sn_id"])] = record

    built: list[ActiveSNRecord] = []
    for seed in sorted(seeds, key=lambda item: item.sn_id):
        record = by_id.get(seed.sn_id)
        if record is None:
            raise ValueError(
                f"active SN {seed.sn_id} is not a DE-documented inventory record"
            )
        supported = tuple(str(item) for item in record.get("supported_versions", ()))
        if "DE" not in supported:
            raise ValueError(
                f"active SN {seed.sn_id} is not covered by a DE version scope"
            )
        default = record.get("default_value")
        if default is not None:
            default = int(default)
        fields = {
            "sn_id": seed.sn_id,
            "canonical_name": str(record["name"]),
            "version": str(record["version"]),
            "supported_versions": supported,
            "default": default,
            "required_range": str(record["required_range"]),
            "effective": int(record["effective"]),
            "auto_mutation": "UNKNOWN",
            "prevalence": seed.prevalence,
            "semantic_role": seed.semantic_role,
            "unknown_boundary": seed.unknown_boundary,
        }
        evidence_hash = _active_sn_evidence_hash(
            {
                **fields,
                "supported_versions": sorted(supported),
                "prevalence": [list(entry) for entry in seed.prevalence],
            }
        )
        built.append(ActiveSNRecord(evidence_hash=evidence_hash, **fields))
    return tuple(built)


_default_catalog: StrategicNumberCatalog | None = None


def default_strategic_number_catalog() -> StrategicNumberCatalog:
    global _default_catalog
    if _default_catalog is None:
        _default_catalog = load_strategic_number_catalog()
    return _default_catalog


def default_strategic_number_inventory() -> StrategicNumberInventory:
    return default_strategic_number_catalog().inventory
