"""Typed strategic semantics above EffectiveCivData and below execution IR."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum, IntEnum
from typing import TYPE_CHECKING

from ..ast import DemandNode, SourceLocation
from .civ_profile import EffectiveCivData
from .game_data import Age, BuildingId, CivId, FactStatus, Resource
from .versioning import EvidenceKind, EvidenceRef

if TYPE_CHECKING:
    from .model import SemanticDemand


class StrategyPosture(str, Enum):
    FLUSH = "FLUSH"
    RUSH = "RUSH"
    BOOM = "BOOM"
    CASTLE_POWER = "CASTLE-POWER"


class StrategicEvidenceKind(str, Enum):
    PERSISTENT = "PERSISTENT"
    EXECUTION = "EXECUTION"
    TIMING = "TIMING"


class StrategicEvidenceSource(str, Enum):
    AUTHORING = "AUTHORING"
    COMMUNITY_META = "COMMUNITY_META"


class StrategicCapabilityObservationKind(str, Enum):
    EXECUTION_FEASIBILITY = "EXECUTION_FEASIBILITY"
    PROVIDER_WORLD_STATE = "PROVIDER_WORLD_STATE"


class StrategicTargetKind(str, Enum):
    EXACT = "EXACT"
    STANDING_FLOOR = "STANDING_FLOOR"
    CURRENT_QUEUED = "CURRENT_QUEUED"
    BOUNDED_PACKAGE = "BOUNDED_PACKAGE"


class CapabilityIntentKind(str, Enum):
    BUILD = "BUILD"
    TRAIN = "TRAIN"
    RESEARCH = "RESEARCH"
    AGE_ADVANCE = "AGE_ADVANCE"
    ECONOMIC = "ECONOMIC"
    MILITARY = "MILITARY"


class StrategicPriority(IntEnum):
    CORE = 100
    DEFENSE = 80
    SUPPORT = 50
    OPTIONAL = 20


@dataclass(frozen=True)
class StrategyEnvelope:
    game_mode: str
    match_type: str
    maps: tuple[str, ...]


@dataclass(frozen=True)
class StrategicEvidence:
    kind: StrategicEvidenceKind
    expression: str | None
    label: str
    source: StrategicEvidenceSource = StrategicEvidenceSource.AUTHORING
    provenance: tuple[EvidenceRef, ...] = ()
    observation_ref: str | None = None


@dataclass(frozen=True)
class StrategicTarget:
    kind: StrategicTargetKind
    entity_type: str
    entity_id: int | str
    minimum: int | None = None
    maximum: int | None = None
    package_members: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityIntent:
    kind: CapabilityIntentKind
    entity_type: str
    entity_id: int | str
    provider_building: BuildingId | None = None


@dataclass(frozen=True)
class ProtectedResourceFloor:
    resource: Resource
    minimum: int


@dataclass(frozen=True)
class OpportunityCostPolicy:
    owner: str
    protected_floors: tuple[ProtectedResourceFloor, ...] = ()
    emergency_override_postures: tuple[StrategyPosture, ...] = ()
    release_on_completion: bool = True
    release_on_invalidation: bool = True


@dataclass(frozen=True)
class ExecutionDemandTemplate:
    requirements: tuple[str, ...]
    action: str
    witness: str
    release: str
    invalidate: str | None = None
    local_id: str = "primary"
    capability_intent: CapabilityIntent | None = None


@dataclass(frozen=True)
class StrategicBinding:
    strategic_id: str
    owner: str
    posture: StrategyPosture
    priority: StrategicPriority
    reason: tuple[StrategicEvidence, ...]
    target: StrategicTarget
    capability_intent: CapabilityIntent
    opportunity_cost: OpportunityCostPolicy | None

    @property
    def persistent_intent(self) -> bool:
        return any(
            evidence.kind is StrategicEvidenceKind.PERSISTENT
            for evidence in self.reason
        )


@dataclass(frozen=True)
class StrategicDemandSpec:
    identity: str
    owner: str
    posture: StrategyPosture
    priority: StrategicPriority
    reason: tuple[StrategicEvidence, ...]
    admissibility: tuple[StrategicEvidence, ...]
    invalidation: tuple[StrategicEvidence, ...]
    capability_intent: CapabilityIntent
    target: StrategicTarget
    opportunity_cost: OpportunityCostPolicy | None
    execution: ExecutionDemandTemplate
    additional_execution_demands: tuple[ExecutionDemandTemplate, ...] = ()
    provenance: tuple[EvidenceRef, ...] = ()

    @property
    def execution_demands(self) -> tuple[ExecutionDemandTemplate, ...]:
        return (self.execution, *self.additional_execution_demands)

    def with_overrides(
        self,
        *,
        reason: tuple[StrategicEvidence, ...] | None = None,
        capability_entity_id: int | str | None = None,
        opportunity_cost_owner: str | None = None,
        additional_execution_demands: tuple[ExecutionDemandTemplate, ...] | None = None,
    ) -> "StrategicDemandSpec":
        intent = self.capability_intent
        if capability_entity_id is not None:
            intent = replace(intent, entity_id=capability_entity_id)
        policy = self.opportunity_cost
        if policy is not None and opportunity_cost_owner is not None:
            policy = replace(policy, owner=opportunity_cost_owner)
        return replace(
            self,
            reason=self.reason if reason is None else reason,
            capability_intent=intent,
            opportunity_cost=policy,
            additional_execution_demands=(
                self.additional_execution_demands
                if additional_execution_demands is None
                else additional_execution_demands
            ),
        )


@dataclass(frozen=True)
class PostureTransition:
    from_postures: tuple[StrategyPosture, ...]
    to_posture: StrategyPosture
    evidence: tuple[StrategicEvidence, ...]
    label: str
    priority: int = 0


@dataclass(frozen=True)
class StrategicCapabilityObservation:
    identity: str
    capability: CapabilityIntent
    expression: str
    source: StrategicEvidenceSource = StrategicEvidenceSource.AUTHORING
    provenance: tuple[EvidenceRef, ...] = ()
    observation_kind: StrategicCapabilityObservationKind = (
        StrategicCapabilityObservationKind.EXECUTION_FEASIBILITY
    )


@dataclass(frozen=True)
class StrategicObservationSpec:
    identity: str
    expression: str
    source: StrategicEvidenceSource = StrategicEvidenceSource.AUTHORING
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class StrategyProfile:
    profile_id: str
    civ_id: CivId
    patch_key: str
    effective_snapshot_fingerprint: str
    envelope: StrategyEnvelope
    postures: tuple[StrategyPosture, ...]
    demands: tuple[StrategicDemandSpec, ...]
    transitions: tuple[PostureTransition, ...]
    provenance: tuple[EvidenceRef, ...]
    capability_observations: tuple[StrategicCapabilityObservation, ...] = ()
    observations: tuple[StrategicObservationSpec, ...] = ()

    def demand(self, identity: str) -> StrategicDemandSpec:
        for item in self.demands:
            if item.identity == identity:
                return item
        raise KeyError(f"unknown strategic demand '{identity}'")

    def observation(self, identity: str) -> StrategicObservationSpec:
        for item in self.observations:
            if item.identity == identity:
                return item
        raise KeyError(f"unknown strategic observation '{identity}'")

    @property
    def community_meta_evidence(self) -> tuple[StrategicEvidence, ...]:
        evidence: list[StrategicEvidence] = []
        for demand in self.demands:
            evidence.extend(demand.reason)
            evidence.extend(demand.admissibility)
            evidence.extend(demand.invalidation)
        for transition in self.transitions:
            evidence.extend(transition.evidence)
        return tuple(
            item for item in evidence
            if item.source is StrategicEvidenceSource.COMMUNITY_META
        )

    def with_demand_override(self, identity: str, **kwargs) -> "StrategyProfile":
        target = self.demand(identity)
        updated = target.with_overrides(**kwargs)
        demands = tuple(
            updated if item.identity == identity else item
            for item in self.demands
        )
        return replace(self, demands=demands)


@dataclass(frozen=True)
class ResolvedStrategyProfile:
    profile_id: str
    demand_ids: tuple[str, ...]


@dataclass(frozen=True)
class StrategyCompilation:
    profile: StrategyProfile
    demands: tuple["SemanticDemand", ...]
    bindings: dict[str, StrategicBinding]


def _validate_evidence_attribution(
    evidence: StrategicEvidence,
    effective: EffectiveCivData | None = None,
) -> None:
    if evidence.source is not StrategicEvidenceSource.COMMUNITY_META:
        return
    if evidence.kind is not StrategicEvidenceKind.PERSISTENT:
        raise ValueError(
            f"community meta evidence '{evidence.label}' must be PERSISTENT"
        )
    if not any(
        ref.kind is EvidenceKind.COMMUNITY_REFERENCE
        for ref in evidence.provenance
    ):
        raise ValueError(
            f"community meta evidence '{evidence.label}' requires COMMUNITY_REFERENCE provenance"
        )
    if effective is not None and any(
        ref.patch != effective.patch for ref in evidence.provenance
    ):
        raise ValueError(
            f"community meta evidence '{evidence.label}' has provenance for a different patch"
        )


def _validate_capability_observations(
    profile: StrategyProfile,
    effective: EffectiveCivData,
) -> None:
    identities: set[str] = set()
    for observation in profile.capability_observations:
        if observation.identity in identities:
            raise ValueError(
                f"duplicate strategic capability observation '{observation.identity}'"
            )
        identities.add(observation.identity)

        if observation.source is StrategicEvidenceSource.COMMUNITY_META:
            raise ValueError(
                f"community meta cannot define factual capability '{observation.identity}'"
            )
        if observation.capability.kind is not CapabilityIntentKind.TRAIN:
            raise ValueError(
                f"strategic capability observation '{observation.identity}' must use TRAIN intent"
            )
        if observation.capability.entity_type != "unit":
            raise ValueError(
                f"strategic capability observation '{observation.identity}' must target a unit"
            )
        unit_id = int(observation.capability.entity_id)
        status = effective.factual_status("unit", unit_id)
        if status is not FactStatus.VERIFIED:
            raise ValueError(
                f"strategic capability observation '{observation.identity}' requires "
                f"factual status VERIFIED for unit {unit_id}; status is {status.value}"
            )
        if observation.capability.provider_building is not None:
            effective.building(observation.capability.provider_building)
        if not observation.provenance:
            raise ValueError(
                f"strategic capability observation '{observation.identity}' requires factual provenance"
            )

        unit = effective.unit(unit_id)
        aliases = {
            str(unit_id),
            unit.name.lower().replace(" ", "-"),
        }
        from_expression = observation.expression.strip().lower()
        if observation.observation_kind is StrategicCapabilityObservationKind.EXECUTION_FEASIBILITY:
            if not from_expression.startswith("(can-train"):
                raise ValueError(
                    f"strategic capability observation '{observation.identity}' must use a can-train native primitive"
                )
            if not any(alias in from_expression for alias in aliases):
                raise ValueError(
                    f"strategic capability observation '{observation.identity}' does not bind its declared unit"
                )
        elif observation.observation_kind is StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE:
            provider = observation.capability.provider_building
            if provider is None:
                raise ValueError(
                    f"provider-state capability observation '{observation.identity}' requires a provider building"
                )
            provider_item = effective.building(provider)
            provider_aliases = {
                str(int(provider_item.id)),
                provider_item.name.lower().replace(" ", "-"),
            }
            if not from_expression.startswith("(building-type-count"):
                raise ValueError(
                    f"provider-state capability observation '{observation.identity}' must use building-type-count"
                )
            if not any(alias in from_expression for alias in provider_aliases):
                raise ValueError(
                    f"provider-state capability observation '{observation.identity}' does not bind its provider building"
                )
        else:
            raise ValueError(
                f"strategic capability observation '{observation.identity}' has unsupported observation kind "
                f"'{observation.observation_kind.value}'"
            )


def _validate_observation_specs(
    profile: StrategyProfile,
    effective: EffectiveCivData,
) -> None:
    identities: set[str] = set()
    for observation in profile.observations:
        if observation.identity in identities:
            raise ValueError(
                f"duplicate strategic observation '{observation.identity}'"
            )
        identities.add(observation.identity)
        if observation.source is StrategicEvidenceSource.COMMUNITY_META:
            raise ValueError(
                f"community meta cannot define native observation '{observation.identity}'"
            )
        if not observation.expression:
            raise ValueError(
                f"strategic observation '{observation.identity}' requires a native expression"
            )
        if not observation.provenance:
            raise ValueError(
                f"strategic observation '{observation.identity}' requires native provenance"
            )
        if any(ref.patch != effective.patch for ref in observation.provenance):
            raise ValueError(
                f"strategic observation '{observation.identity}' has provenance for a different patch"
            )



def _validate_factual_coverage(
    demand: StrategicDemandSpec,
    effective: EffectiveCivData,
) -> None:
    intents = (demand.capability_intent,) + tuple(
        execution.capability_intent
        for execution in demand.execution_demands
        if execution.capability_intent is not None
    )
    for intent in intents:
        effective.require_coverage(intent.entity_type, intent.entity_id)


def resolve_strategy_profile(
    profile: StrategyProfile,
    effective: EffectiveCivData,
) -> ResolvedStrategyProfile:
    if profile.civ_id != effective.civ_id:
        raise ValueError("strategy profile civilization does not match EffectiveCivData")
    if profile.patch_key != effective.patch.key:
        raise ValueError("strategy profile patch does not match EffectiveCivData")
    if profile.effective_snapshot_fingerprint != effective.fingerprint:
        raise ValueError("strategy profile snapshot fingerprint does not match EffectiveCivData")

    seen: set[str] = set()
    _validate_capability_observations(profile, effective)
    _validate_observation_specs(profile, effective)

    for demand in profile.demands:
        if demand.identity in seen:
            raise ValueError(f"duplicate strategic demand '{demand.identity}'")
        seen.add(demand.identity)

        if not demand.owner:
            raise ValueError(
                f"strategic demand '{demand.identity}' needs a strategic owner"
            )
        if not any(
            evidence.kind is StrategicEvidenceKind.PERSISTENT
            for evidence in demand.reason
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' needs persistent strategic evidence"
            )
        for evidence in (*demand.reason, *demand.admissibility, *demand.invalidation):
            _validate_evidence_attribution(evidence, effective)
            if evidence.observation_ref is None:
                raise ValueError(
                    f"strategic evidence '{evidence.label}' must reference a verified native observation"
                )
            if evidence.expression is not None:
                raise ValueError(
                    f"strategic evidence '{evidence.label}' must not override its native observation expression"
                )
            if evidence.observation_ref not in {item.identity for item in profile.observations}:
                raise ValueError(
                    f"unknown strategic observation reference '{evidence.observation_ref}'"
                )
            if evidence.kind is StrategicEvidenceKind.TIMING and evidence.expression:
                if all(
                    other.kind is StrategicEvidenceKind.TIMING
                    for other in (*demand.reason, *demand.admissibility, *demand.invalidation)
                ):
                    raise ValueError(
                        f"strategic demand '{demand.identity}' cannot use timing as strategic truth"
                    )

        _validate_factual_coverage(demand, effective)
        _validate_capability_intent(demand, effective)
        for execution in demand.execution_demands:
            if execution.capability_intent is not None:
                _validate_capability_intent_value(
                    demand,
                    execution.capability_intent,
                    effective,
                )
        if len(demand.execution_demands) > 1 and any(
            execution.local_id == "primary"
            for execution in demand.execution_demands
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' has multiple execution demands; "
                "each must have a distinct local_id"
            )
        _validate_target(demand, effective)

        if demand.opportunity_cost is not None:
            if demand.opportunity_cost.owner != demand.owner:
                raise ValueError(
                    f"strategic demand '{demand.identity}' opportunity-cost owner "
                    f"must equal the strategic owner"
                )
            _validate_resource_policy(demand, effective)

    for transition in profile.transitions:
        for evidence in transition.evidence:
            _validate_evidence_attribution(evidence, effective)
            if evidence.observation_ref is None:
                raise ValueError(
                    f"strategic evidence '{evidence.label}' must reference a verified native observation"
                )
            if evidence.expression is not None:
                raise ValueError(
                    f"strategic evidence '{evidence.label}' must not override its native observation expression"
                )
            if evidence.observation_ref not in {item.identity for item in profile.observations}:
                raise ValueError(
                    f"unknown strategic observation reference '{evidence.observation_ref}'"
                )
        if not transition.evidence:
            raise ValueError(
                f"posture transition '{transition.label}' needs evidence"
            )
        if all(
            evidence.kind is StrategicEvidenceKind.TIMING
            for evidence in transition.evidence
        ):
            raise ValueError(
                f"posture transition '{transition.label}' is timer-only and cannot be strategic"
            )

    return ResolvedStrategyProfile(
        profile_id=profile.profile_id,
        demand_ids=tuple(sorted(seen)),
    )


def lower_strategy_profile(
    profile: StrategyProfile,
    effective: EffectiveCivData,
) -> StrategyCompilation:
    resolve_strategy_profile(profile, effective)

    # Import these only when lowering so StrategyProfile remains a domain IR
    # rather than depending on the execution lifecycle at module import time.
    from ..primitives import default_de_registry
    from ..semantic.analyzer import analyze

    nodes = []
    execution_owner: dict[str, str] = {}
    for spec in profile.demands:
        execution_demands = spec.execution_demands
        if len(execution_demands) > 1 and any(
            execution.local_id == "primary"
            for execution in execution_demands
        ):
            raise ValueError(
                f"strategic demand '{spec.identity}' has multiple execution demands; "
                "each must have a distinct local_id"
            )
        for execution in execution_demands:
            execution_name = (
                spec.identity
                if len(execution_demands) == 1 and execution.local_id == "primary"
                else f"{spec.identity}::{execution.local_id}"
            )
            if execution_name in execution_owner:
                raise ValueError(
                    f"duplicate lowered execution demand '{execution_name}'"
                )
            execution_owner[execution_name] = spec.identity
            nodes.append(
                DemandNode(
                    name=execution_name,
                    requirements=execution.requirements,
                    action=execution.action,
                    witness=execution.witness,
                    release=execution.release,
                    location=SourceLocation(1),
                    invalidate=execution.invalidate,
                )
            )
    semantic_demands = analyze(
        nodes,
        default_de_registry(),
        source_unit=profile.profile_id,
    )

    bindings: dict[str, StrategicBinding] = {}
    bound_demands: list[SemanticDemand] = []
    from dataclasses import replace as dc_replace

    for demand in semantic_demands:
        spec = profile.demand(execution_owner[demand.name])
        base_binding = bindings.get(spec.identity)
        if base_binding is None:
            base_binding = StrategicBinding(
                strategic_id=spec.identity,
                owner=spec.owner,
                posture=spec.posture,
                priority=spec.priority,
                reason=spec.reason,
                target=spec.target,
                capability_intent=spec.capability_intent,
                opportunity_cost=spec.opportunity_cost,
            )
            bindings[spec.identity] = base_binding

        selected_execution = next(
            execution
            for execution in spec.execution_demands
            if (
                spec.identity
                if len(spec.execution_demands) == 1 and execution.local_id == "primary"
                else f"{spec.identity}::{execution.local_id}"
            ) == demand.name
        )
        selected_intent = (
            selected_execution.capability_intent
            or spec.capability_intent
        )
        execution_binding = dc_replace(
            base_binding,
            capability_intent=selected_intent,
        )
        bound_demands.append(
            dc_replace(
                demand,
                strategic_binding=execution_binding,
            )
        )

    return StrategyCompilation(
        profile=profile,
        demands=tuple(bound_demands),
        bindings=bindings,
    )


def _land_castle_observations(
    effective: EffectiveCivData,
) -> tuple[StrategicObservationSpec, ...]:
    feudal = effective.age_advance(Age.FEUDAL).provenance
    dark = next(
        (
            advance.provenance
            for advance in effective.age_advances
            if advance.age is Age.DARK
        ),
        feudal,
    )
    castle = effective.age_advance(Age.CASTLE).provenance
    imperial = effective.age_advance(Age.IMPERIAL).provenance
    knight = effective.unit(38).provenance
    castle_building = effective.building(82).provenance
    castle_complete_provenance = tuple(dict.fromkeys((*castle, *castle_building)))
    return (
        StrategicObservationSpec(
            "current-dark-age",
            "(current-age == dark-age)",
            provenance=dark,
        ),
        StrategicObservationSpec(
            "current-feudal-age",
            "(current-age >= feudal-age)",
            provenance=feudal,
        ),
        StrategicObservationSpec(
            "current-imperial-age",
            "(current-age >= imperial-age)",
            provenance=imperial,
        ),
        StrategicObservationSpec(
            "enemy-knight-pressure",
            "(players-unit-type-count any-enemy knight >= 3)",
            provenance=knight,
        ),
        StrategicObservationSpec(
            "enemy-knight-pressure-cleared",
            "(players-unit-type-count any-enemy knight < 3)",
            provenance=knight,
        ),
        StrategicObservationSpec(
            "castle-complete",
            "(and (current-age >= castle-age) (building-type-count-total castle >= 1))",
            provenance=castle_complete_provenance,
        ),
    )


def build_land_castle_strategy(
    effective: EffectiveCivData,
    *,
    profile_id: str = "land-castle-v1",
) -> StrategyProfile:
    castle_reason = (
        StrategicEvidence(
            StrategicEvidenceKind.PERSISTENT,
            None,
            "Castle-capability trajectory remains strategically intended",
            observation_ref="current-feudal-age",
        ),
    )

    castle_policy = OpportunityCostPolicy(
        owner="castle-trajectory",
        protected_floors=(
            ProtectedResourceFloor(Resource.STONE, 650),
        ),
        emergency_override_postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH),
    )

    demands = (
        StrategicDemandSpec(
            identity="feudal-transition",
            owner="age-transition",
            posture=StrategyPosture.BOOM,
            priority=StrategicPriority.CORE,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Reach Feudal so the intended Byzantine development path can continue",
                    observation_ref="current-dark-age",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Dark Age transition remains admissible until it completes",
                    observation_ref="current-dark-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.AGE_ADVANCE,
                "age-advance",
                "feudal-age",
                BuildingId(109),
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "age-advance",
                "feudal-age",
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age == dark-age)",
                    "(can-research-with-escrow feudal-age)",
                ),
                action="(research feudal-age)",
                witness="(current-age >= feudal-age)",
                release="(current-age >= feudal-age)",
            ),
        ),
        StrategicDemandSpec(
            identity="early-defensive-spears",
            owner="defense",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.DEFENSE,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Maintain a minimum cheap defensive military floor",
                    observation_ref="current-feudal-age",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "The Feudal defensive package remains admissible",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "spearman-line",
                BuildingId(12),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "spearman-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-train-with-escrow spearman-line)",
                    "(unit-type-count-total spearman-line < 2)",
                ),
                action="(train spearman-line)",
                witness="(unit-type-count spearman-line >= 2)",
                release="(unit-type-count spearman-line >= 2)",
            ),
        ),
        StrategicDemandSpec(
            identity="feudal-infrastructure",
            owner="economy",
            posture=StrategyPosture.BOOM,
            priority=StrategicPriority.SUPPORT,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Maintain core Feudal infrastructure needed by the selected trajectory",
                    observation_ref="current-feudal-age",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Blacksmith remains an admissible core Feudal provider",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.BUILD,
                "building",
                103,
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "building",
                103,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-build blacksmith)",
                ),
                action="(build blacksmith)",
                witness="(building-type-count blacksmith > 0)",
                release="(building-type-count blacksmith > 0)",
            ),
        ),
        StrategicDemandSpec(
            identity="castle-commitment",
            owner="castle-trajectory",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.CORE,
            reason=castle_reason,
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle is the selected next strategic capability",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle commitment is obsolete once Imperial Age is reached without the strategic Castle path",
                    observation_ref="current-imperial-age",
                ),
            ),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.BUILD,
                "building",
                82,
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "building",
                82,
            ),
            opportunity_cost=castle_policy,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(building-available castle)",
                    "(can-afford-building castle)",
                    "(can-build castle)",
                ),
                action="(build castle)",
                witness="(building-type-count castle > 0)",
                release="(building-type-count castle > 0)",
                invalidate="(current-age >= imperial-age)",
            ),
        ),
    )

    transitions = (
        PostureTransition(
            from_postures=(),
            to_posture=StrategyPosture.BOOM,
            evidence=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Dark Age opens the baseline economic trajectory",
                    observation_ref="current-dark-age",
                ),
            ),
            label="opening-dark-boom",
            priority=10,
        ),
        PostureTransition(
            from_postures=(),
            to_posture=StrategyPosture.BOOM,
            evidence=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Existing Feudal state begins on the economic trajectory",
                    observation_ref="current-feudal-age",
                ),
            ),
            label="opening-feudal-boom",
            priority=10,
        ),
        PostureTransition(
            from_postures=(StrategyPosture.BOOM, StrategyPosture.CASTLE_POWER),
            to_posture=StrategyPosture.FLUSH,
            evidence=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Sustained mounted pressure changes the active defensive posture",
                    observation_ref="enemy-knight-pressure",
                ),
            ),
            label="enemy-mounted-pressure",
            priority=80,
        ),
        PostureTransition(
            from_postures=(StrategyPosture.FLUSH,),
            to_posture=StrategyPosture.BOOM,
            evidence=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Mounted pressure has cleared enough to resume the economic trajectory",
                    observation_ref="enemy-knight-pressure-cleared",
                ),
            ),
            label="pressure-cleared",
            priority=40,
        ),
        PostureTransition(
            from_postures=(StrategyPosture.FLUSH, StrategyPosture.BOOM),
            to_posture=StrategyPosture.CASTLE_POWER,
            evidence=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle completion materially changes the strategic posture",
                    observation_ref="castle-complete",
                ),
            ),
            label="castle-complete-reassessment",
            priority=100,
        ),
    )

    return StrategyProfile(
        profile_id=profile_id,
        civ_id=effective.civ_id,
        patch_key=effective.patch.key,
        effective_snapshot_fingerprint=effective.fingerprint,
        envelope=StrategyEnvelope(
            game_mode="STANDARD_LAND",
            match_type="1v1",
            maps=("ARABIA", "ARENA", "STANDARD_LAND"),
        ),
        postures=(
            StrategyPosture.FLUSH,
            StrategyPosture.RUSH,
            StrategyPosture.BOOM,
            StrategyPosture.CASTLE_POWER,
        ),
        demands=demands,
        transitions=transitions,
        provenance=(),
        observations=_land_castle_observations(effective),
    )


def _byzantine_capability_observations(
    effective: EffectiveCivData,
) -> tuple[StrategicCapabilityObservation, ...]:
    return tuple(
        StrategicCapabilityObservation(
            identity=identity,
            capability=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit",
                unit_id,
                provider_building=provider_building,
            ),
            expression=f"(can-train-with-escrow {token})",
            provenance=effective.unit(unit_id).provenance,
        )
        for identity, unit_id, token, provider_building in (
            ("cataphract-capability", 40, "cataphract", BuildingId(82)),
            ("varangian-guard-capability", 2703, "varangian-guard", BuildingId(12)),
            (
                "elite-varangian-guard-capability",
                2704,
                "elite-varangian-guard",
                BuildingId(12),
            ),
        )
    )


def build_byzantine_castle_strategy(
    effective: EffectiveCivData,
) -> StrategyProfile:
    profile = build_land_castle_strategy(
        effective,
        profile_id="byzantine-land-castle-v1",
    )
    community_meta = EvidenceRef(
        EvidenceKind.COMMUNITY_REFERENCE,
        "https://www.reddit.com/r/aoe2/comments/1trs47f/",
        "2026-05-30",
        "current community discussion of Byzantine defensive posture, Spear/Skirmisher pressure, and transition choices",
        effective.patch,
        verification="contextual-strategy",
    )
    supporting_meta = EvidenceRef(
        EvidenceKind.COMMUNITY_REFERENCE,
        "https://www.reddit.com/r/aoe2/comments/1va13b/",
        "2026-07-29",
        "current community discussion of Byzantine defensive counter-unit use",
        effective.patch,
        verification="contextual-strategy",
    )
    meta_provenance = (community_meta, supporting_meta)
    meta_labels = {
        "Castle-capability trajectory remains strategically intended",
        "Maintain a minimum cheap defensive military floor",
        "Sustained mounted pressure changes the active defensive posture",
        "Mounted pressure has cleared enough to resume the economic trajectory",
        "Castle commitment is obsolete once Imperial Age is reached without the strategic Castle path",
        "Castle completion materially changes the strategic posture",
    }

    def annotate_meta(evidence: StrategicEvidence) -> StrategicEvidence:
        if evidence.label in meta_labels:
            return replace(
                evidence,
                source=StrategicEvidenceSource.COMMUNITY_META,
                provenance=meta_provenance,
            )
        return evidence

    demands = tuple(
        replace(
            demand,
            reason=tuple(annotate_meta(evidence) for evidence in demand.reason),
            admissibility=tuple(annotate_meta(evidence) for evidence in demand.admissibility),
            invalidation=tuple(annotate_meta(evidence) for evidence in demand.invalidation),
        )
        for demand in profile.demands
    )
    transitions = tuple(
        replace(
            transition,
            evidence=tuple(
                replace(
                    evidence,
                    source=StrategicEvidenceSource.COMMUNITY_META,
                    provenance=meta_provenance,
                )
                if evidence.label in meta_labels
                else evidence
                for evidence in transition.evidence
            ),
        )
        for transition in profile.transitions
    )
    return replace(
        profile,
        demands=demands,
        transitions=transitions,
        provenance=(*profile.provenance, *meta_provenance),
        capability_observations=_byzantine_capability_observations(effective),
    )

def _validate_capability_intent(
    demand: StrategicDemandSpec,
    effective: EffectiveCivData,
) -> None:
    _validate_capability_intent_value(demand, demand.capability_intent, effective)


def _validate_capability_intent_value(
    demand: StrategicDemandSpec,
    intent: CapabilityIntent,
    effective: EffectiveCivData,
) -> None:
    if intent.kind is CapabilityIntentKind.BUILD:
        if int(intent.entity_id) not in effective.available_buildings:
            raise ValueError(
                f"strategic demand '{demand.identity}' references unknown building {intent.entity_id}"
            )
        if intent.provider_building is not None:
            effective.building(int(intent.provider_building))
    elif intent.kind is CapabilityIntentKind.TRAIN:
        if intent.entity_type == "unit-line":
            effective.unit_line(str(intent.entity_id))
        elif int(intent.entity_id) not in effective.available_units:
            raise ValueError(
                f"strategic demand '{demand.identity}' references unknown unit {intent.entity_id}"
            )
        if intent.provider_building is not None:
            effective.building(int(intent.provider_building))
    elif intent.kind is CapabilityIntentKind.RESEARCH:
        if int(intent.entity_id) not in effective.available_technologies:
            raise ValueError(
                f"strategic demand '{demand.identity}' references unknown technology {intent.entity_id}"
            )
    elif intent.kind is CapabilityIntentKind.AGE_ADVANCE:
        age = _age_from_advance_id(str(intent.entity_id))
        effective.age_advance(age)
    else:
        raise ValueError(
            f"strategic demand '{demand.identity}' has unsupported capability intent {intent.kind.value}"
        )


def _validate_target(
    demand: StrategicDemandSpec,
    effective: EffectiveCivData,
) -> None:
    target = demand.target
    if target.kind is StrategicTargetKind.EXACT:
        if target.entity_type == "building":
            effective.building(int(target.entity_id))
        elif target.entity_type == "unit-line":
            effective.unit_line(str(target.entity_id))
        elif target.entity_type == "age-advance":
            effective.age_advance(_age_from_advance_id(str(target.entity_id)))
        elif target.entity_type == "technology":
            effective.tech(int(target.entity_id))
        else:
            raise ValueError(
                f"strategic demand '{demand.identity}' has unknown exact target type {target.entity_type}"
            )
    elif target.kind in (
        StrategicTargetKind.STANDING_FLOOR,
        StrategicTargetKind.CURRENT_QUEUED,
    ):
        if target.minimum is None or target.minimum < 1:
            raise ValueError(
                f"strategic demand '{demand.identity}' needs a positive target floor"
            )
        if target.entity_type == "unit-line":
            effective.unit_line(str(target.entity_id))
        else:
            raise ValueError(
                f"strategic demand '{demand.identity}' has unsupported floor target type"
            )
    elif target.kind is StrategicTargetKind.BOUNDED_PACKAGE:
        if not target.package_members:
            raise ValueError(
                f"strategic demand '{demand.identity}' bounded package cannot be empty"
            )


def _validate_resource_policy(
    demand: StrategicDemandSpec,
    effective: EffectiveCivData,
) -> None:
    policy = demand.opportunity_cost
    assert policy is not None
    if demand.capability_intent.kind is CapabilityIntentKind.BUILD:
        cost = effective.cost_of(f"building:{int(demand.capability_intent.entity_id)}")
        required = {
            Resource.FOOD: cost.food,
            Resource.WOOD: cost.wood,
            Resource.GOLD: cost.gold,
            Resource.STONE: cost.stone,
        }
        for floor in policy.protected_floors:
            if floor.minimum < required[floor.resource]:
                raise ValueError(
                    f"strategic demand '{demand.identity}' resource floor for "
                    f"{floor.resource.value} is below the target's factual cost"
                )


def _age_from_advance_id(value: str) -> Age:
    mapping = {
        "dark-age": Age.DARK,
        "feudal-age": Age.FEUDAL,
        "castle-age": Age.CASTLE,
        "imperial-age": Age.IMPERIAL,
    }
    try:
        return mapping[value]
    except KeyError as exc:
        raise ValueError(f"unknown age advance '{value}'") from exc
