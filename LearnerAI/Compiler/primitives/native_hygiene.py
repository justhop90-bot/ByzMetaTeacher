"""Native evidence and community-meta hygiene contracts for the .per compiler."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Optional, Tuple


class EvidenceKind(str, Enum):
    DOCUMENTED_FACT = "DOCUMENTED_FACT"
    INFERRED_MAPPING = "INFERRED_MAPPING"
    BENCHMARK_OBSERVATION = "BENCHMARK_OBSERVATION"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConfidenceBasis(str, Enum):
    EXPLICIT_AIREf_TEXT = "EXPLICIT_AIREf_TEXT"
    EXPLICIT_AIREf_TABLE = "EXPLICIT_AIREf_TABLE"
    EXPLICIT_AIREf_PATCH_NOTE = "EXPLICIT_AIREf_PATCH_NOTE"
    MECHANICAL_DERIVATION = "MECHANICAL_DERIVATION"
    CONTEXTUAL_BENCHMARK = "CONTEXTUAL_BENCHMARK"


class AIRefVersionFamily(str, Enum):
    AOK = "AOK"
    TC = "TC"
    WK = "WK"
    DE = "DE"
    UP = "UP"


class PerformanceClass(str, Enum):
    VERY_FAST = "VERY_FAST"
    FAST = "FAST"
    MEDIUM = "MEDIUM"
    SLOW = "SLOW"
    VERY_SLOW = "VERY_SLOW"


class NativeWitnessKind(str, Enum):
    GOAL_VALUE = "GOAL_VALUE"
    STRATEGIC_NUMBER_VALUE = "STRATEGIC_NUMBER_VALUE"
    TIMER_STATE = "TIMER_STATE"
    UNIT_COUNT = "UNIT_COUNT"
    UNIT_COUNT_TOTAL = "UNIT_COUNT_TOTAL"
    OBJECT_COUNT = "OBJECT_COUNT"
    OBJECT_COUNT_TOTAL = "OBJECT_COUNT_TOTAL"
    PENDING_OBJECTS = "PENDING_OBJECTS"
    RESEARCH_STATUS = "RESEARCH_STATUS"
    SEARCH_STATE = "SEARCH_STATE"
    GROUP_STATE = "GROUP_STATE"
    POINT_STATE = "POINT_STATE"
    ESCROW_STATE = "ESCROW_STATE"


class NativeStorageClass(str, Enum):
    PERSISTENT_SCALAR = "PERSISTENT_SCALAR"
    GOAL_SPAN = "GOAL_SPAN"
    ENGINE_MANAGED_LIST = "ENGINE_MANAGED_LIST"
    ENGINE_MANAGED_GROUP = "ENGINE_MANAGED_GROUP"
    ENGINE_MANAGED_STATE = "ENGINE_MANAGED_STATE"


class NativeStorageKind(str, Enum):
    GOAL = "GOAL"
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"
    FLAG = "FLAG"
    POINT_GOAL_SPAN = "POINT_GOAL_SPAN"
    COST_DATA_GOAL_SPAN = "COST_DATA_GOAL_SPAN"
    SEARCH_STATE_GOAL_SPAN = "SEARCH_STATE_GOAL_SPAN"
    GUARD_STATE_GOAL_SPAN = "GUARD_STATE_GOAL_SPAN"
    DUC_LOCAL_LIST = "DUC_LOCAL_LIST"
    DUC_REMOTE_LIST = "DUC_REMOTE_LIST"
    DUC_GROUP = "DUC_GROUP"
    ESCROW = "ESCROW"


class PassConstraintScope(str, Enum):
    RULE_PASS = "RULE_PASS"


class PassFailureMode(str, Enum):
    REJECTED = "REJECTED"
    NO_EFFECT = "NO_EFFECT"
    UNDEFINED = "UNDEFINED"


class ExcerptKind(str, Enum):
    FACT = "FACT"
    PARAMETER = "PARAMETER"
    EXAMPLE = "EXAMPLE"
    PATCH_NOTE = "PATCH_NOTE"
    TABLE_ENTRY = "TABLE_ENTRY"
    PERFORMANCE_RESULT = "PERFORMANCE_RESULT"
    DERIVATION_INPUT = "DERIVATION_INPUT"


class LocatorType(str, Enum):
    COMMAND = "COMMAND"
    PARAMETER = "PARAMETER"
    TABLE_ENTRY = "TABLE_ENTRY"
    PATCH_RELEASE = "PATCH_RELEASE"
    HEADING = "HEADING"
    SEARCH_TERM = "SEARCH_TERM"


class CitationState(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    PINNED = "PINNED"
    VERIFIED_SOURCE_CHANGED = "VERIFIED_SOURCE_CHANGED"
    VERIFIED_LOCATOR_CHANGED = "VERIFIED_LOCATOR_CHANGED"
    VERIFIED_URL_CHANGED = "VERIFIED_URL_CHANGED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BROKEN = "BROKEN"
    UNAVAILABLE = "UNAVAILABLE"
    SUPERSEDED = "SUPERSEDED"


class PromotionState(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    ELIGIBLE = "ELIGIBLE"
    EXISTING_PROMOTION_RETAINED = "EXISTING_PROMOTION_RETAINED"
    PROMOTION_BLOCKED = "PROMOTION_BLOCKED"


class ExcerptMatchKind(str, Enum):
    EXACT = "EXACT"
    NORMALIZED = "NORMALIZED"
    NONE = "NONE"
    AMBIGUOUS = "AMBIGUOUS"


class RevalidationResult(str, Enum):
    VERIFIED_UNCHANGED = "VERIFIED_UNCHANGED"
    SOURCE_CHANGED_EXCERPT_MATCHED = "SOURCE_CHANGED_EXCERPT_MATCHED"
    LOCATOR_CHANGED_EXCERPT_MATCHED = "LOCATOR_CHANGED_EXCERPT_MATCHED"
    URL_CHANGED_EXCERPT_MATCHED = "URL_CHANGED_EXCERPT_MATCHED"
    EXCERPT_CHANGED = "EXCERPT_CHANGED"
    SOURCE_CHANGED_EXCERPT_BROKEN = "SOURCE_CHANGED_EXCERPT_BROKEN"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    REDIRECTED_AND_VERIFIED = "REDIRECTED_AND_VERIFIED"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"


class RevalidationTrigger(str, Enum):
    SCHEDULED = "SCHEDULED"
    ON_USE = "ON_USE"
    MANUAL = "MANUAL"
    SOURCE_FETCH = "SOURCE_FETCH"
    URL_REDIRECT = "URL_REDIRECT"
    HASH_MISMATCH = "HASH_MISMATCH"


class CitationChangeKind(str, Enum):
    NONE = "NONE"
    URL_CHANGED = "URL_CHANGED"
    LOCATOR_CHANGED = "LOCATOR_CHANGED"
    EXCERPT_CHANGED = "EXCERPT_CHANGED"
    SOURCE_HASH_CHANGED = "SOURCE_HASH_CHANGED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


@dataclass(frozen=True)
class AIRefVersion:
    family: AIRefVersionFamily
    major: int
    minor: Optional[int] = None
    patch: Optional[int] = None
    release: Optional[str] = None

    def __post_init__(self) -> None:
        if any(v is not None and v < 0 for v in (self.major, self.minor, self.patch)):
            raise ValueError("AIRef version components must be non-negative")

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        return self.major, self.minor or 0, self.patch or 0, self.release or ""

    def precedes(self, other: "AIRefVersion") -> bool:
        if self.family is not other.family:
            raise ValueError("cannot order different AIRef version families")
        return self.sort_key < other.sort_key


@dataclass(frozen=True)
class AIRefProvenance:
    evidence_kind: EvidenceKind
    confidence: ConfidenceLevel
    confidence_basis: ConfidenceBasis
    citation_id: str
    parent_evidence: Tuple[str, ...] = ()
    derivation: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.citation_id:
            raise ValueError("citation_id is required")
        allowed_bases = {
            EvidenceKind.DOCUMENTED_FACT: {
                ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                ConfidenceBasis.EXPLICIT_AIREf_TABLE,
                ConfidenceBasis.EXPLICIT_AIREf_PATCH_NOTE,
            },
            EvidenceKind.INFERRED_MAPPING: {
                ConfidenceBasis.MECHANICAL_DERIVATION,
            },
            EvidenceKind.BENCHMARK_OBSERVATION: {
                ConfidenceBasis.CONTEXTUAL_BENCHMARK,
            },
        }
        if self.confidence_basis not in allowed_bases[self.evidence_kind]:
            raise ValueError(
                f"{self.evidence_kind.value} requires an appropriate confidence basis"
            )
        if self.evidence_kind is EvidenceKind.INFERRED_MAPPING:
            if not self.parent_evidence or not self.derivation:
                raise ValueError("inferred mappings require parents and derivation")
        if self.evidence_kind is EvidenceKind.BENCHMARK_OBSERVATION and self.parent_evidence:
            raise ValueError("benchmark observations cannot claim derivation parents")


@dataclass(frozen=True)
class SourceContentHash:
    algorithm: str
    digest: str
    representation: str
    normalization_version: Optional[str] = None

    def __post_init__(self) -> None:
        if self.algorithm.lower() != "sha256" or len(self.digest) != 64:
            raise ValueError("source hash must be sha256")
        int(self.digest, 16)
        if self.representation not in {"RAW_BYTES", "CANONICAL_TEXT"}:
            raise ValueError("invalid hash representation")
        if self.representation == "CANONICAL_TEXT" and not self.normalization_version:
            raise ValueError("canonical text hashes require normalization_version")


@dataclass(frozen=True)
class SourceExcerpt:
    text: str
    kind: ExcerptKind
    heading_path: Tuple[str, ...] = ()
    locator_text: Optional[str] = None
    exact_sha256: Optional[str] = None
    normalized_sha256: Optional[str] = None
    normalization_version: str = "1"

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("excerpt text is required")

    @staticmethod
    def normalize(text: str) -> str:
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    @classmethod
    def capture(cls, text: str, kind: ExcerptKind, **kwargs) -> "SourceExcerpt":
        return cls(
            text=text,
            kind=kind,
            exact_sha256=sha256(text.encode()).hexdigest(),
            normalized_sha256=sha256(cls.normalize(text).encode()).hexdigest(),
            **kwargs,
        )


@dataclass(frozen=True)
class VersionScope:
    introduced_in: Optional[AIRefVersion] = None
    supported_families: Tuple[AIRefVersionFamily, ...] = ()
    excluded_families: Tuple[AIRefVersionFamily, ...] = ()
    behavior_change_at: Tuple[AIRefVersion, ...] = ()
    provenance: Tuple[AIRefProvenance, ...] = ()
    scope_confidence: ConfidenceLevel = ConfidenceLevel.HIGH

    def __post_init__(self) -> None:
        if set(self.supported_families) & set(self.excluded_families):
            raise ValueError("supported/excluded version families overlap")
        if not self.provenance:
            raise ValueError("VersionScope requires provenance")
        if any(p.evidence_kind is EvidenceKind.BENCHMARK_OBSERVATION for p in self.provenance):
            raise ValueError("benchmarks cannot establish version scope")
        if self.introduced_in:
            for change in self.behavior_change_at:
                if change.family is not self.introduced_in.family or change.precedes(self.introduced_in):
                    raise ValueError("invalid behavior-change version")


@dataclass(frozen=True)
class PerformanceEvidence:
    identity: str
    command: str
    performance_class: PerformanceClass
    benchmark_context: str
    tested_cardinality: Optional[int] = None
    loops_for_lag: Optional[int] = None
    lag_fraction: Optional[float] = None
    version_context: Optional[str] = None
    map_context: Optional[str] = None
    speed_context: Optional[str] = None
    setup_context: Optional[str] = None
    provenance: Tuple[AIRefProvenance, ...] = ()
    observation_confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    generalization_confidence: ConfidenceLevel = ConfidenceLevel.LOW

    def __post_init__(self) -> None:
        if not self.identity or not self.command or not self.benchmark_context.strip():
            raise ValueError("performance identity, command, and context are required")
        if self.tested_cardinality is not None and self.tested_cardinality < 0:
            raise ValueError("tested cardinality must be non-negative")
        if self.loops_for_lag is not None and self.loops_for_lag <= 0:
            raise ValueError("loops_for_lag must be positive")
        if self.lag_fraction is not None and not 0 < self.lag_fraction <= 1:
            raise ValueError("lag_fraction must be within (0,1]")
        if not self.provenance:
            raise ValueError("performance evidence requires provenance")
        if any(p.evidence_kind is not EvidenceKind.BENCHMARK_OBSERVATION for p in self.provenance):
            raise ValueError("performance provenance must be benchmark observations")


@dataclass(frozen=True)
class NativeWitness:
    identity: str
    kind: NativeWitnessKind
    primitive: str
    subject: Optional[str] = None
    comparator: Optional[str] = None
    value: Optional[int] = None
    state: Optional[str] = None
    provenance: Tuple[AIRefProvenance, ...] = ()

    def __post_init__(self) -> None:
        if not self.identity or not self.primitive or not self.provenance:
            raise ValueError("native witness identity, primitive, and provenance are required")
        if self.comparator is not None and self.value is None:
            raise ValueError("comparison witnesses require a value")
        if self.state is not None and self.value is not None:
            raise ValueError("state and numeric value are mutually exclusive")
        if self.kind in {
            NativeWitnessKind.UNIT_COUNT,
            NativeWitnessKind.UNIT_COUNT_TOTAL,
            NativeWitnessKind.OBJECT_COUNT,
            NativeWitnessKind.OBJECT_COUNT_TOTAL,
            NativeWitnessKind.PENDING_OBJECTS,
        } and self.subject is None:
            raise ValueError("count witnesses require subject")
        if self.kind is NativeWitnessKind.RESEARCH_STATUS and (
            self.subject is None or (self.state is None and self.value is None)
        ):
            raise ValueError("research witnesses require subject and state/value")
        if self.kind in {
            NativeWitnessKind.GOAL_VALUE,
            NativeWitnessKind.STRATEGIC_NUMBER_VALUE,
        } and self.subject is None:
            raise ValueError("Goal/SN witnesses require subject")
        if any(p.evidence_kind is EvidenceKind.BENCHMARK_OBSERVATION for p in self.provenance):
            raise ValueError("benchmarks cannot define native witness semantics")


@dataclass(frozen=True)
class NativeStorageUse:
    identity: str
    storage_class: NativeStorageClass
    kind: NativeStorageKind
    base: Optional[int] = None
    span_length: int = 1
    access: str = "READ"
    command_family: Optional[str] = None
    maximum_cardinality: Optional[int] = None
    request_purpose: Optional[str] = None
    symbolic: bool = False
    provenance: Tuple[AIRefProvenance, ...] = ()


    def validate_binding_shape(
        self,
        *,
        binding_kind: str,
        start: int,
        end: int,
    ) -> None:
        expected = {
            (NativeStorageClass.PERSISTENT_SCALAR, NativeStorageKind.GOAL): "GOAL_SLOT",
            (NativeStorageClass.PERSISTENT_SCALAR, NativeStorageKind.STRATEGIC_NUMBER): "STRATEGIC_NUMBER",
            (NativeStorageClass.PERSISTENT_SCALAR, NativeStorageKind.TIMER): "TIMER",
            (NativeStorageClass.GOAL_SPAN, NativeStorageKind.POINT_GOAL_SPAN): "GOAL_SPAN",
            (NativeStorageClass.GOAL_SPAN, NativeStorageKind.COST_DATA_GOAL_SPAN): "GOAL_SPAN",
            (NativeStorageClass.GOAL_SPAN, NativeStorageKind.SEARCH_STATE_GOAL_SPAN): "GOAL_SPAN",
            (NativeStorageClass.GOAL_SPAN, NativeStorageKind.GUARD_STATE_GOAL_SPAN): "GOAL_SPAN",
            (NativeStorageClass.ENGINE_MANAGED_LIST, NativeStorageKind.DUC_LOCAL_LIST): "DUC_LOCAL_LIST",
            (NativeStorageClass.ENGINE_MANAGED_LIST, NativeStorageKind.DUC_REMOTE_LIST): "DUC_REMOTE_LIST",
            (NativeStorageClass.ENGINE_MANAGED_GROUP, NativeStorageKind.DUC_GROUP): "DUC_GROUP",
            (NativeStorageClass.ENGINE_MANAGED_STATE, NativeStorageKind.FLAG): "ENGINE_MANAGED_STATE",
            (NativeStorageClass.ENGINE_MANAGED_STATE, NativeStorageKind.ESCROW): "ENGINE_MANAGED_STATE",
        }.get((self.storage_class, self.kind))
        if binding_kind != expected:
            raise ValueError(
                f"native storage use '{self.identity}' requires {expected}, got {binding_kind}"
            )
        if start > end:
            raise ValueError("native storage binding start must not exceed end")
        if self.base is not None and start != self.base:
            raise ValueError(f"native storage use '{self.identity}' requires start {self.base}, got {start}")
        if self.storage_class is NativeStorageClass.GOAL_SPAN:
            if end - start + 1 != self.span_length:
                raise ValueError(f"native storage use '{self.identity}' requires width {self.span_length}, got {end - start + 1}")
    def __post_init__(self) -> None:
        if not self.identity or not self.provenance:
            raise ValueError("storage identity and provenance are required")
        if self.span_length < 1 or self.access not in {"READ", "WRITE", "READ_WRITE"}:
            raise ValueError("invalid storage shape/access")
        if self.storage_class is NativeStorageClass.PERSISTENT_SCALAR:
            if self.span_length != 1:
                raise ValueError("persistent scalar requires one slot")
            if self.base is None and not self.symbolic:
                raise ValueError("persistent scalar requires an explicit slot unless symbolic")
            if self.base is not None:
                bounds = {
                    NativeStorageKind.GOAL: (1, 16000),
                    NativeStorageKind.STRATEGIC_NUMBER: (0, 511),
                    NativeStorageKind.TIMER: (1, 50),
                }
                if self.kind in bounds and not bounds[self.kind][0] <= self.base <= bounds[self.kind][1]:
                    raise ValueError("storage slot is outside AIRef documented range")
        elif self.storage_class is NativeStorageClass.GOAL_SPAN:
            if self.kind not in {
                NativeStorageKind.POINT_GOAL_SPAN,
                NativeStorageKind.COST_DATA_GOAL_SPAN,
                NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
                NativeStorageKind.GUARD_STATE_GOAL_SPAN,
            } or self.base is None or self.span_length < 2:
                raise ValueError("invalid documented Goal span")
            if self.base < 41 or self.base + self.span_length - 1 > 508:
                raise ValueError("documented multi-Goal span is outside safe range")
        elif self.storage_class is NativeStorageClass.ENGINE_MANAGED_LIST:
            if self.base is not None or self.span_length != 1:
                raise ValueError("engine-managed lists do not use Goal slots")
            limits = {
                NativeStorageKind.DUC_LOCAL_LIST: 240,
                NativeStorageKind.DUC_REMOTE_LIST: 40,
            }
            if self.kind not in limits:
                raise ValueError("engine-managed list must be a DUC list")
            if self.maximum_cardinality not in (None, limits[self.kind]):
                raise ValueError("invalid DUC list cardinality")
        elif self.storage_class is NativeStorageClass.ENGINE_MANAGED_GROUP:
            if self.base is not None or self.span_length != 1 or self.kind is not NativeStorageKind.DUC_GROUP:
                raise ValueError("invalid DUC group storage")


@dataclass(frozen=True)
class PassExecutionConstraint:
    identity: str
    command: str
    scope: PassConstraintScope
    maximum_successes: Optional[int] = None
    failure_mode: Optional[PassFailureMode] = None
    requires_next_pass: bool = False
    provenance: Tuple[AIRefProvenance, ...] = ()

    def __post_init__(self) -> None:
        if not self.identity or not self.command or not self.provenance:
            raise ValueError("pass constraint identity, command, and provenance are required")
        if self.maximum_successes is not None and self.maximum_successes < 1:
            raise ValueError("maximum_successes must be positive")
        if self.maximum_successes is not None and self.failure_mode is None:
            raise ValueError("bounded pass constraints require failure mode")
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("hard pass constraints require documented native facts")


@dataclass(frozen=True)
class NativeContractCatalog:
    witnesses: Tuple[NativeWitness, ...] = ()
    storage_uses: Tuple[NativeStorageUse, ...] = ()
    pass_constraints: Tuple[PassExecutionConstraint, ...] = ()

    def __post_init__(self) -> None:
        for values, label in (
            (self.witnesses, "native witness"),
            (self.storage_uses, "native storage use"),
            (self.pass_constraints, "pass execution constraint"),
        ):
            identities = [item.identity for item in values]
            if len(identities) != len(set(identities)):
                raise ValueError(f"duplicate {label} identity")
        purposes = [
            item.request_purpose
            for item in self.storage_uses
            if item.request_purpose is not None
        ]
        if len(purposes) != len(set(purposes)):
            raise ValueError("duplicate native storage request purpose")
        commands = [item.command for item in self.pass_constraints]
        if len(commands) != len(set(commands)):
            raise ValueError("duplicate native pass constraint command")

    def witness(self, identity: str) -> NativeWitness:
        for item in self.witnesses:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def storage(self, identity: str) -> NativeStorageUse:
        for item in self.storage_uses:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def storage_for_purpose(self, purpose: str) -> NativeStorageUse:
        for item in self.storage_uses:
            if item.request_purpose == purpose:
                return item
        raise KeyError(purpose)

    def pass_constraint(self, identity: str) -> PassExecutionConstraint:
        for item in self.pass_constraints:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def pass_constraints_for(self, command: str) -> Tuple[PassExecutionConstraint, ...]:
        return tuple(item for item in self.pass_constraints if item.command == command)


@dataclass(frozen=True)
class SourceRetrieval:
    retrieved_at_utc: str
    canonical_url: str
    final_url: str
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.retrieved_at_utc or not self.canonical_url or not self.final_url:
            raise ValueError("retrieval timestamp and URLs are required")
        if self.http_status is not None and not 100 <= self.http_status <= 599:
            raise ValueError("HTTP status must be within 100..599")


@dataclass(frozen=True)
class CitationRecord:
    citation_id: str
    canonical_url: str
    final_url: str
    locator_type: LocatorType
    locator: str
    excerpt: Optional[SourceExcerpt] = None
    source_hash: Optional[SourceContentHash] = None
    retrieval: Optional[SourceRetrieval] = None
    state: CitationState = CitationState.CANDIDATE
    revalidation_events: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.citation_id or not self.canonical_url or not self.final_url or not self.locator.strip():
            raise ValueError("citation identity, URLs, and locator are required")
        verified = {
            CitationState.VERIFIED,
            CitationState.PINNED,
            CitationState.VERIFIED_SOURCE_CHANGED,
            CitationState.VERIFIED_LOCATOR_CHANGED,
            CitationState.VERIFIED_URL_CHANGED,
        }
        if self.state in verified and self.excerpt is None:
            raise ValueError("verified citations require excerpt")
        if self.state is CitationState.PINNED and self.source_hash is None:
            raise ValueError("pinned citations require source hash")
        if self.state is CitationState.PINNED and self.retrieval is None:
            raise ValueError("pinned citations require retrieval metadata")


@dataclass(frozen=True)
class CitationRevalidationEvent:
    event_id: str
    evidence_id: str
    trigger: RevalidationTrigger
    previous_citation_id: str
    current_citation_id: Optional[str]
    previous_url: str
    current_url: Optional[str]
    previous_locator: str
    current_locator: Optional[str]
    changes: Tuple[CitationChangeKind, ...]
    previous_source_hash: Optional[str]
    current_source_hash: Optional[str]
    previous_excerpt_hash: Optional[str]
    current_excerpt_hash: Optional[str]
    excerpt_match: ExcerptMatchKind
    result: RevalidationResult
    source_available: bool

    def __post_init__(self) -> None:
        if not self.event_id or not self.evidence_id or not self.previous_citation_id:
            raise ValueError("revalidation identity is required")
        if not self.previous_url or not self.previous_locator:
            raise ValueError("revalidation requires the previous citation location")
        if not self.source_available and self.result is not RevalidationResult.SOURCE_UNAVAILABLE:
            raise ValueError("unavailable source requires SOURCE_UNAVAILABLE")
        if self.source_available and self.result is RevalidationResult.SOURCE_UNAVAILABLE:
            raise ValueError("SOURCE_UNAVAILABLE requires source_available=False")

def compare_excerpts(stored: SourceExcerpt, current_text: str) -> ExcerptMatchKind:
    if stored.exact_sha256 == sha256(current_text.encode()).hexdigest():
        return ExcerptMatchKind.EXACT
    if stored.normalized_sha256 == sha256(SourceExcerpt.normalize(current_text).encode()).hexdigest():
        return ExcerptMatchKind.NORMALIZED
    return ExcerptMatchKind.NONE


def classify_revalidation(
    *,
    url_changed: bool,
    locator_changed: bool,
    source_hash_changed: bool,
    excerpt_match: ExcerptMatchKind,
    source_available: bool,
    redirected: bool = False,
) -> RevalidationResult:
    if not source_available:
        return RevalidationResult.SOURCE_UNAVAILABLE
    if excerpt_match is ExcerptMatchKind.AMBIGUOUS:
        return RevalidationResult.AMBIGUOUS_MATCH
    if excerpt_match is ExcerptMatchKind.NONE:
        return (
            RevalidationResult.SOURCE_CHANGED_EXCERPT_BROKEN
            if source_hash_changed
            else RevalidationResult.EXCERPT_CHANGED
        )
    if redirected and excerpt_match is ExcerptMatchKind.EXACT:
        return RevalidationResult.REDIRECTED_AND_VERIFIED
    if url_changed:
        return RevalidationResult.URL_CHANGED_EXCERPT_MATCHED
    if locator_changed:
        return RevalidationResult.LOCATOR_CHANGED_EXCERPT_MATCHED
    if source_hash_changed:
        return RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED
    return RevalidationResult.VERIFIED_UNCHANGED


def next_citation_state(
    current: CitationState,
    result: RevalidationResult,
) -> CitationState:
    verified = {
        CitationState.VERIFIED,
        CitationState.PINNED,
        CitationState.VERIFIED_SOURCE_CHANGED,
        CitationState.VERIFIED_LOCATOR_CHANGED,
        CitationState.VERIFIED_URL_CHANGED,
    }

    if current is CitationState.SUPERSEDED:
        raise ValueError("superseded citations are terminal")

    if result is RevalidationResult.SOURCE_UNAVAILABLE:
        return CitationState.UNAVAILABLE

    if result is RevalidationResult.VERIFIED_UNCHANGED:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified}:
            return CitationState.PINNED if current is CitationState.PINNED else CitationState.VERIFIED
        raise ValueError(f"cannot verify unchanged citation from {current.value}")

    if result is RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified}:
            return CitationState.VERIFIED_SOURCE_CHANGED
        raise ValueError(f"invalid source-change transition from {current.value}")

    if result is RevalidationResult.LOCATOR_CHANGED_EXCERPT_MATCHED:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified}:
            return CitationState.VERIFIED_LOCATOR_CHANGED
        raise ValueError(f"invalid locator-change transition from {current.value}")

    if result in {
        RevalidationResult.URL_CHANGED_EXCERPT_MATCHED,
        RevalidationResult.REDIRECTED_AND_VERIFIED,
    }:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified}:
            return CitationState.VERIFIED_URL_CHANGED
        raise ValueError(f"invalid URL-change transition from {current.value}")

    if result in {RevalidationResult.AMBIGUOUS_MATCH, RevalidationResult.EXCERPT_CHANGED}:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified, CitationState.REVIEW_REQUIRED}:
            return CitationState.REVIEW_REQUIRED
        raise ValueError(f"invalid review transition from {current.value}")

    if result is RevalidationResult.SOURCE_CHANGED_EXCERPT_BROKEN:
        if current in {CitationState.CANDIDATE, CitationState.UNAVAILABLE, *verified, CitationState.REVIEW_REQUIRED}:
            return CitationState.BROKEN
        raise ValueError(f"invalid broken-citation transition from {current.value}")

    raise ValueError(f"unsupported revalidation result: {result}")


def promotion_state(citation: CitationRecord, *, already_promoted: bool) -> PromotionState:
    if citation.state in {
        CitationState.VERIFIED,
        CitationState.PINNED,
        CitationState.VERIFIED_SOURCE_CHANGED,
        CitationState.VERIFIED_LOCATOR_CHANGED,
        CitationState.VERIFIED_URL_CHANGED,
    }:
        return PromotionState.ELIGIBLE
    if citation.state is CitationState.UNAVAILABLE:
        return (
            PromotionState.EXISTING_PROMOTION_RETAINED
            if already_promoted
            else PromotionState.NOT_ELIGIBLE
        )
    if citation.state in {CitationState.REVIEW_REQUIRED, CitationState.BROKEN}:
        return (
            PromotionState.EXISTING_PROMOTION_RETAINED
            if already_promoted
            else PromotionState.PROMOTION_BLOCKED
        )
    if citation.state is CitationState.SUPERSEDED:
        return PromotionState.EXISTING_PROMOTION_RETAINED
    return PromotionState.NOT_ELIGIBLE


def validate_goal_span_non_overlap(uses: Tuple[NativeStorageUse, ...]) -> None:
    spans = []
    for use in uses:
        if use.storage_class is NativeStorageClass.GOAL_SPAN:
            assert use.base is not None
            spans.append((use.base, use.base + use.span_length - 1, use.identity))
    for index, left in enumerate(spans):
        for right in spans[index + 1:]:
            if max(left[0], right[0]) <= min(left[1], right[1]):
                raise ValueError(f"overlapping Goal spans: {left[2]} and {right[2]}")


__all__ = [name for name in globals() if not name.startswith("_")]
