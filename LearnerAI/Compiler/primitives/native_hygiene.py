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


class CitationSemanticScope(str, Enum):
    GENERAL_NATIVE_FACT = "GENERAL_NATIVE_FACT"
    ORDINARY_PERSISTENT_GOAL_STORAGE = "ORDINARY_PERSISTENT_GOAL_STORAGE"
    EXTENDED_GOAL_SPAN = "EXTENDED_GOAL_SPAN"
    GOAL_ID_PARAMETER_RANGE = "GOAL_ID_PARAMETER_RANGE"


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


@dataclass(frozen=True)
class CitationCatalogAudit:
    unused: Tuple[str, ...] = ()
    duplicates: Tuple[Tuple[str, ...], ...] = ()
    stale: Tuple[str, ...] = ()
    weak: Tuple[str, ...] = ()

    @property
    def clean(self) -> bool:
        return not any((self.unused, self.duplicates, self.stale, self.weak))


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
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("native witness semantics require documented native facts")
        if self.comparator is not None:
            if self.comparator not in {"==", "!=", "<", "<=", ">", ">="}:
                raise ValueError("invalid native witness comparator")
            if self.value is None:
                raise ValueError("comparison witnesses require a value")
        if self.value is not None and self.comparator is None:
            raise ValueError("numeric witness values require a comparator")
        if self.state is not None and self.value is not None:
            raise ValueError("state and numeric value are mutually exclusive")
        if self.comparator is None and self.state is None:
            raise ValueError("native witness requires comparison or state evidence")
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
class NativeGoalStorageContract:
    identity: str
    minimum_id: int
    maximum_id: int
    provenance: Tuple[AIRefProvenance, ...]

    def __post_init__(self) -> None:
        if not self.identity or not self.provenance:
            raise ValueError("Goal storage contract identity and provenance are required")
        if self.minimum_id < 1 or self.maximum_id != 512 or self.minimum_id > self.maximum_id:
            raise ValueError("ordinary persistent Goal storage must be exactly 1..512")
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("Goal storage contracts require documented native facts")

    def validate_id(self, goal_id: int) -> None:
        if not self.minimum_id <= goal_id <= self.maximum_id:
            raise ValueError(
                f"Goal storage contract '{self.identity}' permits ids "
                f"{self.minimum_id}..{self.maximum_id}, got {goal_id}"
            )


@dataclass(frozen=True)
class NativeGoalSpanContract:
    identity: str
    storage_kind: NativeStorageKind
    width: int
    minimum_start: int
    maximum_start: int
    provenance: Tuple[AIRefProvenance, ...]

    def __post_init__(self) -> None:
        expected = {
            NativeStorageKind.POINT_GOAL_SPAN: (2, 15998),
            NativeStorageKind.COST_DATA_GOAL_SPAN: (4, 15996),
            NativeStorageKind.SEARCH_STATE_GOAL_SPAN: (4, 15996),
            NativeStorageKind.GUARD_STATE_GOAL_SPAN: (4, 15996),
        }
        if not self.identity or not self.provenance:
            raise ValueError("Goal span contract identity and provenance are required")
        if self.storage_kind not in expected:
            raise ValueError("Goal span contract requires an extended Goal span kind")
        expected_width, expected_max = expected[self.storage_kind]
        if self.width != expected_width or self.maximum_start != expected_max or self.minimum_start != 41:
            raise ValueError("Goal span contract does not match the documented native shape")
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("Goal span contracts require documented native facts")

    def validate_shape(self, start: int, end: int) -> None:
        if end - start + 1 != self.width:
            raise ValueError(
                f"Goal span contract '{self.identity}' requires width {self.width}"
            )
        if start < self.minimum_start or start > self.maximum_start:
            raise ValueError(
                f"Goal span contract '{self.identity}' permits starts "
                f"{self.minimum_start}..{self.maximum_start}, got {start}"
            )


@dataclass(frozen=True)
class NativeGoalParameterRangeContract:
    identity: str
    parameter_type: str
    minimum: int
    maximum: int
    commands: Tuple[str, ...]
    provenance: Tuple[AIRefProvenance, ...]

    def __post_init__(self) -> None:
        if (
            not self.identity
            or not self.parameter_type
            or not self.commands
            or not self.provenance
        ):
            raise ValueError("GoalId parameter-range contract is incomplete")
        if self.parameter_type != "GoalId" or self.minimum != 1 or self.maximum != 16000:
            raise ValueError("GoalId parameter range must be exactly 1..16000")
        if len(self.commands) != len(set(self.commands)):
            raise ValueError("GoalId parameter-range commands must be unique")
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("GoalId parameter-range contracts require documented native facts")

    def validate_value(self, value: int) -> None:
        if not self.minimum <= value <= self.maximum:
            raise ValueError(
                f"parameter contract '{self.identity}' permits values "
                f"{self.minimum}..{self.maximum}, got {value}"
            )


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
    contract_id: Optional[str] = None


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
        if self.storage_class is NativeStorageClass.PERSISTENT_SCALAR and self.kind is NativeStorageKind.GOAL:
            if not 1 <= start <= 512 or start != end:
                raise ValueError(
                    f"native storage use '{self.identity}' requires ordinary Goal id 1..512, got {start}..{end}"
                )
        if self.storage_class is NativeStorageClass.GOAL_SPAN:
            if end - start + 1 != self.span_length:
                raise ValueError(f"native storage use '{self.identity}' requires width {self.span_length}, got {end - start + 1}")
            limits = {
                NativeStorageKind.POINT_GOAL_SPAN: (41, 15998),
                NativeStorageKind.COST_DATA_GOAL_SPAN: (41, 15996),
                NativeStorageKind.SEARCH_STATE_GOAL_SPAN: (41, 15996),
                NativeStorageKind.GUARD_STATE_GOAL_SPAN: (41, 15996),
            }
            minimum_start, maximum_start = limits[self.kind]
            if not minimum_start <= start <= maximum_start:
                raise ValueError(
                    f"native storage use '{self.identity}' requires span start {minimum_start}..{maximum_start}, got {start}"
                )
    def __post_init__(self) -> None:
        if not self.identity or not self.provenance:
            raise ValueError("storage identity and provenance are required")
        if self.span_length < 1 or self.access not in {"READ", "WRITE", "READ_WRITE"}:
            raise ValueError("invalid storage shape/access")
        if self.symbolic and self.request_purpose is None:
            raise ValueError("symbolic storage uses require request purpose")
        if any(p.evidence_kind is not EvidenceKind.DOCUMENTED_FACT for p in self.provenance):
            raise ValueError("native storage semantics require documented native facts")
        if self.storage_class is NativeStorageClass.PERSISTENT_SCALAR:
            if self.span_length != 1:
                raise ValueError("persistent scalar requires one slot")
            if self.base is None and not self.symbolic:
                raise ValueError("persistent scalar requires an explicit slot unless symbolic")
            if self.kind is NativeStorageKind.GOAL and self.contract_id not in {None, "ordinary-persistent-goal-storage"}:
                raise ValueError("ordinary Goal storage must use its dedicated storage contract")
            if self.base is not None:
                bounds = {
                    NativeStorageKind.GOAL: (1, 512),
                    NativeStorageKind.STRATEGIC_NUMBER: (0, 511),
                    NativeStorageKind.TIMER: (1, 50),
                }
                if self.kind in bounds and not bounds[self.kind][0] <= self.base <= bounds[self.kind][1]:
                    raise ValueError("storage slot is outside its native storage contract")
        elif self.storage_class is NativeStorageClass.GOAL_SPAN:
            expected = {
                NativeStorageKind.POINT_GOAL_SPAN: (2, 41, 15998),
                NativeStorageKind.COST_DATA_GOAL_SPAN: (4, 41, 15996),
                NativeStorageKind.SEARCH_STATE_GOAL_SPAN: (4, 41, 15996),
                NativeStorageKind.GUARD_STATE_GOAL_SPAN: (4, 41, 15996),
            }
            if self.kind not in expected or self.base is None:
                raise ValueError("invalid documented Goal span")
            width, minimum_start, maximum_start = expected[self.kind]
            if self.span_length != width:
                raise ValueError("Goal span width does not match its native command shape")
            if not minimum_start <= self.base <= maximum_start:
                raise ValueError("Goal span start is outside its native span contract")
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
        elif self.storage_class is NativeStorageClass.ENGINE_MANAGED_STATE:
            if self.base is not None or self.span_length != 1 or self.kind not in {
                NativeStorageKind.FLAG,
                NativeStorageKind.ESCROW,
            }:
                raise ValueError("invalid engine-managed state storage")
        else:
            raise ValueError("unsupported native storage class")


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


def default_native_goal_storage_contracts() -> Tuple[NativeGoalStorageContract, ...]:
    return (
        NativeGoalStorageContract(
            identity="ordinary-persistent-goal-storage",
            minimum_id=1,
            maximum_id=512,
            provenance=(
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:goal-storage",
                ),
            ),
        ),
    )


def default_native_goal_span_contracts() -> Tuple[NativeGoalSpanContract, ...]:
    provenance_point = (
        AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.HIGH,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            citation_id="airef:extended-goal-span-point",
        ),
    )
    provenance_four = (
        AIRefProvenance(
            evidence_kind=EvidenceKind.DOCUMENTED_FACT,
            confidence=ConfidenceLevel.HIGH,
            confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
            citation_id="airef:extended-goal-span-4",
        ),
    )
    return (
        NativeGoalSpanContract(
            "point-goal-span",
            NativeStorageKind.POINT_GOAL_SPAN,
            2,
            41,
            15998,
            provenance_point,
        ),
        NativeGoalSpanContract(
            "extended-4-goal-span",
            NativeStorageKind.SEARCH_STATE_GOAL_SPAN,
            4,
            41,
            15996,
            provenance_four,
        ),
        NativeGoalSpanContract(
            "cost-data-4-goal-span",
            NativeStorageKind.COST_DATA_GOAL_SPAN,
            4,
            41,
            15996,
            provenance_four,
        ),
        NativeGoalSpanContract(
            "guard-state-4-goal-span",
            NativeStorageKind.GUARD_STATE_GOAL_SPAN,
            4,
            41,
            15996,
            provenance_four,
        ),
    )


def default_native_goal_parameter_ranges() -> Tuple[NativeGoalParameterRangeContract, ...]:
    return (
        NativeGoalParameterRangeContract(
            "goal-id-parameter-range",
            "GoalId",
            1,
            16000,
            ("goal", "set-goal"),
            (
                AIRefProvenance(
                    evidence_kind=EvidenceKind.DOCUMENTED_FACT,
                    confidence=ConfidenceLevel.HIGH,
                    confidence_basis=ConfidenceBasis.EXPLICIT_AIREf_TEXT,
                    citation_id="airef:goal-id-parameter-range",
                ),
            ),
        ),
    )


@dataclass(frozen=True)
class NativeContractCatalog:
    witnesses: Tuple[NativeWitness, ...] = ()
    storage_uses: Tuple[NativeStorageUse, ...] = ()
    pass_constraints: Tuple[PassExecutionConstraint, ...] = ()
    goal_storage_contracts: Tuple[NativeGoalStorageContract, ...] = ()
    goal_span_contracts: Tuple[NativeGoalSpanContract, ...] = ()
    parameter_ranges: Tuple[NativeGoalParameterRangeContract, ...] = ()
    citation_catalog: Optional[CitationRecordCatalog] = None

    def __post_init__(self) -> None:
        if not self.goal_storage_contracts:
            object.__setattr__(self, "goal_storage_contracts", default_native_goal_storage_contracts())
        if not self.goal_span_contracts:
            object.__setattr__(self, "goal_span_contracts", default_native_goal_span_contracts())
        if not self.parameter_ranges:
            object.__setattr__(self, "parameter_ranges", default_native_goal_parameter_ranges())
        for values, label in (
            (self.witnesses, "native witness"),
            (self.storage_uses, "native storage use"),
            (self.pass_constraints, "pass execution constraint"),
            (self.goal_storage_contracts, "Goal storage contract"),
            (self.goal_span_contracts, "Goal span contract"),
            (self.parameter_ranges, "GoalId parameter-range contract"),
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
        validate_goal_span_non_overlap(self.storage_uses)

        goal_storage_ids = {contract.identity for contract in self.goal_storage_contracts}
        goal_span_ids = {contract.identity for contract in self.goal_span_contracts}
        parameter_range_ids = {contract.identity for contract in self.parameter_ranges}
        if any(
            storage.kind is NativeStorageKind.GOAL
            for storage in self.storage_uses
        ) and not goal_storage_ids:
            raise ValueError("Goal storage uses require an ordinary Goal storage contract")
        if any(
            storage.storage_class is NativeStorageClass.GOAL_SPAN
            for storage in self.storage_uses
        ) and not goal_span_ids:
            raise ValueError("Goal span uses require an extended Goal span contract")

        for storage in self.storage_uses:
            if storage.kind is NativeStorageKind.GOAL:
                if storage.contract_id not in goal_storage_ids:
                    raise ValueError(f"Goal storage '{storage.identity}' references an unknown Goal storage contract")
            if storage.storage_class is NativeStorageClass.GOAL_SPAN:
                if storage.contract_id not in goal_span_ids:
                    raise ValueError(f"Goal span '{storage.identity}' references an unknown Goal span contract")
                span_contract = self.goal_span_contract(storage.contract_id)
                if span_contract.storage_kind is not storage.kind:
                    raise ValueError(
                        f"Goal span '{storage.identity}' references contract "
                        f"for {span_contract.storage_kind.value}, not {storage.kind.value}"
                    )

        citation_catalog = self.citation_catalog or default_native_citation_catalog()
        object.__setattr__(self, "citation_catalog", citation_catalog)
        self.validate_all_provenance()

    def citation_ids(self) -> Tuple[str, ...]:
        ids = {
            provenance.citation_id
            for provenance in (
                *(
                    provenance
                    for witness in self.witnesses
                    for provenance in witness.provenance
                ),
                *(
                    provenance
                    for storage in self.storage_uses
                    for provenance in storage.provenance
                ),
                *(
                    provenance
                    for constraint in self.pass_constraints
                    for provenance in constraint.provenance
                ),
                *(
                    provenance
                    for contract in self.goal_storage_contracts
                    for provenance in contract.provenance
                ),
                *(
                    provenance
                    for contract in self.goal_span_contracts
                    for provenance in contract.provenance
                ),
                *(
                    provenance
                    for contract in self.parameter_ranges
                    for provenance in contract.provenance
                ),
            )
        }
        return tuple(sorted(ids))

    def goal_storage_contract(self, identity: str) -> NativeGoalStorageContract:
        for item in self.goal_storage_contracts:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def goal_span_contract(self, identity: str) -> NativeGoalSpanContract:
        for item in self.goal_span_contracts:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def parameter_range(self, identity: str) -> NativeGoalParameterRangeContract:
        for item in self.parameter_ranges:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def parameter_ranges_for(self, command: str, parameter: str) -> Tuple[NativeGoalParameterRangeContract, ...]:
        return tuple(
            item
            for item in self.parameter_ranges
            if command in item.commands and parameter == "GoalId"
        )

    def validate_all_provenance(self) -> None:
        for owner, provenance, expected_scope in (
            *(
                (witness.identity, witness.provenance, CitationSemanticScope.GENERAL_NATIVE_FACT)
                for witness in self.witnesses
            ),
            *(
                (
                    storage.identity,
                    storage.provenance,
                    (
                        CitationSemanticScope.ORDINARY_PERSISTENT_GOAL_STORAGE
                        if storage.kind is NativeStorageKind.GOAL
                        else CitationSemanticScope.EXTENDED_GOAL_SPAN
                        if storage.storage_class is NativeStorageClass.GOAL_SPAN
                        else CitationSemanticScope.GENERAL_NATIVE_FACT
                    ),
                )
                for storage in self.storage_uses
            ),
            *(
                (constraint.identity, constraint.provenance, CitationSemanticScope.GENERAL_NATIVE_FACT)
                for constraint in self.pass_constraints
            ),
            *(
                (
                    contract.identity,
                    contract.provenance,
                    CitationSemanticScope.ORDINARY_PERSISTENT_GOAL_STORAGE,
                )
                for contract in self.goal_storage_contracts
            ),
            *(
                (
                    contract.identity,
                    contract.provenance,
                    CitationSemanticScope.EXTENDED_GOAL_SPAN,
                )
                for contract in self.goal_span_contracts
            ),
            *(
                (
                    contract.identity,
                    contract.provenance,
                    CitationSemanticScope.GOAL_ID_PARAMETER_RANGE,
                )
                for contract in self.parameter_ranges
            ),
        ):
            try:
                self.citation_catalog.validate_provenance(
                    provenance,
                    require_promotable=True,
                    expected_scope=expected_scope,
                )
            except ValueError as exc:
                raise ValueError(
                    f"native contract '{owner}' has invalid citation provenance: {exc}"
                ) from exc

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
    semantic_scope: CitationSemanticScope = CitationSemanticScope.GENERAL_NATIVE_FACT
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
        if self.semantic_scope is CitationSemanticScope.ORDINARY_PERSISTENT_GOAL_STORAGE:
            if self.locator_type is not LocatorType.TABLE_ENTRY or self.locator != "Goals: 1 to 512":
                raise ValueError("ordinary Goal storage citations must identify the 1..512 Goal table entry")
        elif self.semantic_scope is CitationSemanticScope.EXTENDED_GOAL_SPAN:
            if self.locator_type is not LocatorType.COMMAND:
                raise ValueError("extended Goal span citations must identify a native command")
        elif self.semantic_scope is CitationSemanticScope.GOAL_ID_PARAMETER_RANGE:
            if self.locator_type is not LocatorType.COMMAND or "GoalId" not in self.locator:
                raise ValueError("GoalId parameter citations must identify a GoalId command parameter")


@dataclass(frozen=True)
class CitationRecordCatalog:
    records: Tuple[CitationRecord, ...] = ()

    def __post_init__(self) -> None:
        identities = [record.citation_id for record in self.records]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate CitationRecord citation_id")

    def get(self, citation_id: str) -> Optional[CitationRecord]:
        for record in self.records:
            if record.citation_id == citation_id:
                return record
        return None

    def resolve(self, citation_id: str) -> CitationRecord:
        record = self.get(citation_id)
        if record is None:
            raise ValueError(f"unresolved citation '{citation_id}'")
        return record

    def validate_provenance(
        self,
        provenance: Tuple[AIRefProvenance, ...],
        *,
        require_promotable: bool,
        expected_scope: Optional[CitationSemanticScope] = None,
    ) -> None:
        for evidence in provenance:
            record = self.resolve(evidence.citation_id)
            if expected_scope is not None and record.semantic_scope is not expected_scope:
                raise ValueError(
                    f"citation '{evidence.citation_id}' has scope "
                    f"{record.semantic_scope.value}, expected {expected_scope.value}"
                )
            if require_promotable:
                state = promotion_state(record, already_promoted=False)
                if state is not PromotionState.ELIGIBLE:
                    raise ValueError(
                        f"citation '{evidence.citation_id}' is not promotable "
                        f"(state={record.state.value})"
                    )

    def audit(self, used_citation_ids: Tuple[str, ...]) -> CitationCatalogAudit:
        used = set(used_citation_ids)
        unused = tuple(
            sorted(record.citation_id for record in self.records if record.citation_id not in used)
        )

        locations: dict[tuple[str, str, LocatorType, str], list[str]] = {}
        for record in self.records:
            key = (
                record.canonical_url,
                record.final_url,
                record.locator_type,
                record.locator,
            )
            locations.setdefault(key, []).append(record.citation_id)
        duplicates = tuple(
            sorted(tuple(sorted(ids)) for ids in locations.values() if len(ids) > 1)
        )

        stale_states = {
            CitationState.CANDIDATE,
            CitationState.REVIEW_REQUIRED,
            CitationState.BROKEN,
            CitationState.UNAVAILABLE,
            CitationState.SUPERSEDED,
        }
        stale = tuple(
            sorted(
                record.citation_id
                for record in self.records
                if record.state in stale_states
            )
        )

        weak: list[str] = []
        for record in self.records:
            if record.locator_type is LocatorType.COMMAND:
                expected_suffix = f"#{record.locator}"
                if not record.final_url.endswith(expected_suffix):
                    weak.append(record.citation_id)
            elif record.locator_type is LocatorType.HEADING:
                if record.excerpt is None or not record.excerpt.heading_path:
                    weak.append(record.citation_id)
            elif record.locator_type is LocatorType.TABLE_ENTRY:
                if (
                    record.excerpt is None
                    or (
                        record.locator.strip() not in record.excerpt.text.strip()
                        and record.excerpt.locator_text != record.locator
                    )
                ):
                    weak.append(record.citation_id)

        return CitationCatalogAudit(
            unused=unused,
            duplicates=duplicates,
            stale=stale,
            weak=tuple(sorted(weak)),
        )

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

        actual_changes = {
            CitationChangeKind.URL_CHANGED: self.current_url is not None and self.current_url != self.previous_url,
            CitationChangeKind.LOCATOR_CHANGED: self.current_locator is not None and self.current_locator != self.previous_locator,
            CitationChangeKind.SOURCE_HASH_CHANGED: self.current_source_hash != self.previous_source_hash,
            CitationChangeKind.EXCERPT_CHANGED: self.current_excerpt_hash != self.previous_excerpt_hash,
        }
        if CitationChangeKind.NONE in self.changes and any(actual_changes.values()):
            raise ValueError("NONE cannot accompany an actual citation change")
        for change, changed in actual_changes.items():
            if changed != (change in self.changes):
                raise ValueError(f"citation change set disagrees with observed {change.value}")

        required_change = {
            RevalidationResult.SOURCE_CHANGED_EXCERPT_MATCHED: CitationChangeKind.SOURCE_HASH_CHANGED,
            RevalidationResult.LOCATOR_CHANGED_EXCERPT_MATCHED: CitationChangeKind.LOCATOR_CHANGED,
            RevalidationResult.URL_CHANGED_EXCERPT_MATCHED: CitationChangeKind.URL_CHANGED,
            RevalidationResult.REDIRECTED_AND_VERIFIED: CitationChangeKind.URL_CHANGED,
            RevalidationResult.EXCERPT_CHANGED: CitationChangeKind.EXCERPT_CHANGED,
            RevalidationResult.SOURCE_CHANGED_EXCERPT_BROKEN: CitationChangeKind.EXCERPT_CHANGED,
        }.get(self.result)
        if required_change is not None and required_change not in self.changes:
            raise ValueError(f"{self.result.value} requires {required_change.value}")
        if self.result is RevalidationResult.VERIFIED_UNCHANGED and any(actual_changes.values()):
            raise ValueError("VERIFIED_UNCHANGED cannot claim citation changes")
        if self.result not in {RevalidationResult.SOURCE_UNAVAILABLE, RevalidationResult.VERIFIED_UNCHANGED, RevalidationResult.AMBIGUOUS_MATCH} and self.current_citation_id is None:
            raise ValueError("available revalidation results require current citation id")

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


def default_native_citation_catalog() -> CitationRecordCatalog:
    airef_commands = "https://airef.github.io/commands/commands-details.html"
    return CitationRecordCatalog(
        records=(
            CitationRecord(
                "airef:building-type-count",
                f"{airef_commands}#building-type-count",
                f"{airef_commands}#building-type-count",
                LocatorType.COMMAND,
                "building-type-count",
                excerpt=SourceExcerpt.capture(
                    "(building-type-count <BuildingId> <compareOp> <Value>)",
                    ExcerptKind.FACT,
                ),
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:unit-type-count",
                f"{airef_commands}#unit-type-count",
                f"{airef_commands}#unit-type-count",
                LocatorType.COMMAND,
                "unit-type-count",
                excerpt=SourceExcerpt.capture(
                    "(unit-type-count <UnitId> <compareOp> <Value>)",
                    ExcerptKind.FACT,
                ),
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:research-completed",
                f"{airef_commands}#research-completed",
                f"{airef_commands}#research-completed",
                LocatorType.COMMAND,
                "research-completed",
                excerpt=SourceExcerpt.capture(
                    "(research-completed <TechId>)",
                    ExcerptKind.FACT,
                ),
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:goal-storage",
                "https://airef.github.io/resources/articles/data-limits.html",
                "https://airef.github.io/resources/articles/data-limits.html",
                LocatorType.TABLE_ENTRY,
                "Goals: 1 to 512",
                excerpt=SourceExcerpt.capture(
                    "AI scripts has 512 different goals they can use to store different values, which are numbered from 1 to 512.",
                    ExcerptKind.TABLE_ENTRY,
                    locator_text="Goals: 1 to 512",
                ),
                semantic_scope=CitationSemanticScope.ORDINARY_PERSISTENT_GOAL_STORAGE,
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:extended-goal-span-point",
                f"{airef_commands}#up-get-point",
                f"{airef_commands}#up-get-point",
                LocatorType.COMMAND,
                "up-get-point Point: 41 to 15998, 2 consecutive goals",
                excerpt=SourceExcerpt.capture(
                    "an extended GoalId from 41 to 15998; the first of 2 consecutive goals to store the (x,y) pair.",
                    ExcerptKind.PARAMETER,
                ),
                semantic_scope=CitationSemanticScope.EXTENDED_GOAL_SPAN,
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:extended-goal-span-4",
                f"{airef_commands}#up-get-search-state",
                f"{airef_commands}#up-get-search-state",
                LocatorType.COMMAND,
                "up-get-search-state OutputGoalId: 41 to 15996, 4 consecutive goals",
                excerpt=SourceExcerpt.capture(
                    "an extended GoalId from 41 to 15996",
                    ExcerptKind.PARAMETER,
                ),
                semantic_scope=CitationSemanticScope.EXTENDED_GOAL_SPAN,
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:goal-id-parameter-range",
                f"{airef_commands}#goal",
                f"{airef_commands}#goal",
                LocatorType.COMMAND,
                "goal GoalId: 1 to 16000",
                excerpt=SourceExcerpt.capture(
                    "A valid GoalId, from 1 to 16000.",
                    ExcerptKind.PARAMETER,
                ),
                semantic_scope=CitationSemanticScope.GOAL_ID_PARAMETER_RANGE,
                state=CitationState.VERIFIED,
            ),
            CitationRecord(
                "airef:build-pass-limit",
                "https://airef.github.io/tables/up-patch-notes.html",
                "https://airef.github.io/tables/up-patch-notes.html",
                LocatorType.PATCH_RELEASE,
                "20120416-093415",
                excerpt=SourceExcerpt.capture(
                    "only 1 build/up-build command is allowed to succeed per AI rule pass.",
                    ExcerptKind.PATCH_NOTE,
                ),
                state=CitationState.VERIFIED,
            ),
        )
    )


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
