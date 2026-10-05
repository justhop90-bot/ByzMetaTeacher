"""Downstream client strategy semantics above generic execution IR."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import Enum, IntEnum
from typing import TYPE_CHECKING

from ..ast import DemandNode, SourceLocation
from .civ_profile import EffectiveCivData
from .game_data import Age, BuildingId, CivId, FactStatus, Resource
from .model import LifecycleState
from .versioning import EvidenceKind, EvidenceRef
from .strategic_number import StrategicNumberOrigin

if TYPE_CHECKING:
    from .military_composition import MilitaryCompositionPlan
    from .model import SemanticDemand
    from .counter_strategy import CounterPackage
    from .native_attack import NativeAttackLifecyclePlan
    from .native_duc import NativeDucPlan
    from .recurrent import TimerRequest
    from .strategic_number import StrategicNumberOrigin
    from .water import WaterExecutionPlan
    from .map_profile import MapProfile
    from .opening import OpeningSelectorPlan
    from .economic_control import EconomyControllerPlan
    from .camp_control import ByzantineCampControllerPlan
    from .role_separation import NativeRoleSeparationPlan
    from .endgame import EndgamePlan
    from ..semantic.policy_recipe import (
        PolicyOverride,
        PolicyRecipe,
        PolicyResolution,
    )


class StrategyPosture(str, Enum):
    FLUSH = "FLUSH"
    RUSH = "RUSH"
    BOOM = "BOOM"
    CASTLE_POWER = "CASTLE-POWER"

class StrategicNumberReassertionPolicy(str, Enum):
    ON_DRIFT = "ON_DRIFT"


_STRATEGY_POSTURE_STATE = "strategy-posture"
_STRATEGY_POSTURE_VALUES = {
    StrategyPosture.FLUSH: 1,
    StrategyPosture.RUSH: 2,
    StrategyPosture.BOOM: 3,
    StrategyPosture.CASTLE_POWER: 4,
}


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
    ECONOMIC_MULTIPLIER = 90
    DEFENSE = 80
    SUPPORT = 50
    OPTIONAL = 20


@dataclass(frozen=True)
class StrategyEnvelope:
    game_mode: str
    match_type: str
    maps: tuple[str, ...]


@dataclass(frozen=True)
class StrategicNumberMode:
    """Compiler-policy mode for one documented native Strategic Number."""

    identity: str
    native_strategic_number_id: int
    value: int
    minimum_age: Age = Age.DARK
    maximum_age: Age | None = None
    postures: tuple[StrategyPosture, ...] = ()
    reassertion_policy: StrategicNumberReassertionPolicy = (
        StrategicNumberReassertionPolicy.ON_DRIFT
    )
    priority: int = 0

    @property
    def state_name(self) -> str:
        # One physical native storage slot per exact native SN id. Multiple
        # age/posture modes are policy rules over that same persistent state.
        return f"sn-native-{self.native_strategic_number_id}"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", self.identity):
            raise ValueError(
                f"Strategic Number mode identity '{self.identity}' is not a valid .per identifier"
            )
        if not isinstance(self.native_strategic_number_id, int) or isinstance(
            self.native_strategic_number_id, bool
        ):
            raise ValueError("Strategic Number mode native id must be an integer")
        if not 0 <= self.native_strategic_number_id <= 511:
            raise ValueError(
                f"Strategic Number mode native id must be in range 0..511, got "
                f"{self.native_strategic_number_id}"
            )
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise ValueError("Strategic Number mode value must be an integer")
        if not -32768 <= self.value <= 32767:
            raise ValueError(
                f"Strategic Number mode value must be in native constant range -32768..32767, got {self.value}"
            )
        if self.maximum_age is not None:
            if _AGE_ORDER[self.maximum_age] < _AGE_ORDER[self.minimum_age]:
                raise ValueError(
                    "Strategic Number mode maximum_age must not precede minimum_age"
                )
        if len(self.postures) != len(set(self.postures)):
            raise ValueError("Strategic Number mode postures must be unique")


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
    escrow_release_resources: tuple[Resource, ...] = ()


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
    production_arbitration_group: str | None = None

    @property
    def persistent_intent(self) -> bool:
        return any(
            evidence.kind is StrategicEvidenceKind.PERSISTENT
            for evidence in self.reason
        )


@dataclass(frozen=True)
class CapabilityRecoveryContract:
    """Compiler-policy contract for temporary capability loss and recovery."""

    preserve_strategic_demand: bool = True
    preserve_opportunity_cost: bool = True
    reopen_on_recovery: bool = True

    def __post_init__(self) -> None:
        if not self.preserve_strategic_demand:
            raise ValueError(
                "capability recovery must preserve the original strategic demand"
            )
        if not self.reopen_on_recovery:
            raise ValueError(
                "capability recovery must reopen the original strategic demand"
            )


@dataclass(frozen=True)
class GoalStateAssertion:
    """One strategy-owned goal-state rule: when guard fires, set the state.

    Lowers to a NativeControlPlan state plus one guard rule through the
    existing persistent-control-plane channel (never through demands:
    set-goal is not a demand action primitive). Guards stay native Facts;
    same-pass write visibility and goal-ID collisions remain governed by
    the control-plane gate and the emitter, not by this type.
    """

    demand_id: str
    state_name: str
    guard_fact: str
    set_value: int

    def __post_init__(self) -> None:
        if not self.demand_id.strip():
            raise ValueError("goal state assertion demand identity must not be empty")
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", self.state_name):
            raise ValueError(
                f"goal state name '{self.state_name}' is not a valid .per identifier"
            )
        if not self.guard_fact.strip():
            raise ValueError("goal state assertion guard fact must not be empty")
        if not isinstance(self.set_value, int) or isinstance(self.set_value, bool):
            raise ValueError("goal state assertion value must be an integer")


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
    initial_state: LifecycleState = LifecycleState.ACTIVE
    additional_execution_demands: tuple[ExecutionDemandTemplate, ...] = ()
    goal_assertions: tuple[GoalStateAssertion, ...] = ()
    provenance: tuple[EvidenceRef, ...] = ()
    recovery: CapabilityRecoveryContract = CapabilityRecoveryContract()
    production_arbitration_group: str | None = None

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
class StrategicMilitaryComposition:
    """Strategy-level grouping of production demands under one military objective."""

    identity: str
    production_demands: tuple[str, ...]
    attack_objective: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("military composition identity must not be empty")
        if not self.production_demands:
            raise ValueError("military composition requires at least one production demand")
        if len(self.production_demands) != len(set(self.production_demands)):
            raise ValueError("military composition production demands must be unique")
        if any(not item.strip() for item in self.production_demands):
            raise ValueError("military composition production demand identities must not be empty")
        if not self.attack_objective.strip():
            raise ValueError("military composition attack objective must not be empty")


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
    military_compositions: tuple[StrategicMilitaryComposition, ...] = ()
    strategic_number_modes: tuple[StrategicNumberMode, ...] = ()
    policy_recipes: tuple["PolicyRecipe", ...] = ()
    counter_packages: tuple["CounterPackage", ...] = ()
    attack_plan: "NativeAttackLifecyclePlan | None" = None
    duc_plan: "NativeDucPlan | None" = None
    water_execution_plan: "WaterExecutionPlan | None" = None
    map_profile: tuple["MapProfile", ...] = ()
    opening_selector: "OpeningSelectorPlan | None" = None
    economy_controller: "EconomyControllerPlan | None" = None
    camp_controller: "ByzantineCampControllerPlan | None" = None
    role_separation_plan: "NativeRoleSeparationPlan | None" = None
    endgame_plan: "EndgamePlan | None" = None

    def demand(self, identity: str) -> StrategicDemandSpec:
        for item in self.demands:
            if item.identity == identity:
                return item
        raise KeyError(f"unknown strategic demand '{identity}'")

    def policy_recipe(self, identity: str) -> "PolicyRecipe":
        for item in self.policy_recipes:
            if item.identity == identity:
                return item
        raise KeyError(f"unknown policy recipe '{identity}'")

    def resolve_policy_recipe(
        self,
        identity: str,
        *,
        bindings: dict[str, str] | None = None,
        overrides: tuple["PolicyOverride", ...] = (),
    ) -> "PolicyResolution":
        from ..semantic.policy_recipe import resolve_policy_recipe

        return resolve_policy_recipe(
            self.policy_recipe(identity),
            bindings=bindings,
            overrides=overrides,
        )

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
    policy_resolutions: tuple["PolicyResolution", ...] = ()


@dataclass(frozen=True)
class StrategyCompilation:
    profile: StrategyProfile
    demands: tuple["SemanticDemand", ...]
    bindings: dict[str, StrategicBinding]
    escrow_plan: "NativeEscrowReleasePlan | None" = None
    control_plan: "NativeControlPlan | None" = None
    military_compositions: tuple["MilitaryCompositionPlan", ...] = ()
    attack_plan: "NativeAttackLifecyclePlan | None" = None
    duc_plan: "NativeDucPlan | None" = None
    water_execution_plan: "WaterExecutionPlan | None" = None
    map_profile: tuple["MapProfile", ...] = ()
    opening_selector: "OpeningSelectorPlan | None" = None
    economy_controller: "EconomyControllerPlan | None" = None
    camp_controller: "ByzantineCampControllerPlan | None" = None
    role_separation_plan: "NativeRoleSeparationPlan | None" = None
    endgame_plan: "EndgamePlan | None" = None


_AGE_ORDER = {
    Age.DARK: 0,
    Age.FEUDAL: 1,
    Age.CASTLE: 2,
    Age.IMPERIAL: 3,
}

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


def _validate_strategic_number_modes(
    profile: StrategyProfile,
    effective: EffectiveCivData,
) -> None:
    if not profile.strategic_number_modes:
        return

    from ..primitives.strategic_number_catalog import default_strategic_number_catalog

    catalog = default_strategic_number_catalog()
    identities: set[str] = set()
    posture_mode_present = False
    for mode in profile.strategic_number_modes:
        if mode.identity in identities:
            raise ValueError(
                f"duplicate Strategic Number mode '{mode.identity}'"
            )
        identities.add(mode.identity)
        if mode.native_strategic_number_id not in catalog.de_documented_ids:
            raise ValueError(
                f"Strategic Number mode '{mode.identity}' references native Strategic Number "
                f"{mode.native_strategic_number_id}, which is not DE-documented in catalog "
                f"{catalog.inventory.inventory_sha}"
            )
        if mode.postures:
            posture_mode_present = True

    if posture_mode_present and not profile.transitions:
        raise ValueError(
            "posture-driven Strategic Number modes require StrategyPosture transition control"
        )

    modes = tuple(profile.strategic_number_modes)
    for index, first in enumerate(modes):
        first_min = _AGE_ORDER[first.minimum_age]
        first_max = (
            _AGE_ORDER[first.maximum_age]
            if first.maximum_age is not None
            else _AGE_ORDER[Age.IMPERIAL]
        )
        first_postures = set(first.postures) if first.postures else set(StrategyPosture)
        for second in modes[index + 1:]:
            if first.native_strategic_number_id != second.native_strategic_number_id:
                continue
            second_min = _AGE_ORDER[second.minimum_age]
            second_max = (
                _AGE_ORDER[second.maximum_age]
                if second.maximum_age is not None
                else _AGE_ORDER[Age.IMPERIAL]
            )
            if first_max < second_min or second_max < first_min:
                continue
            second_postures = (
                set(second.postures) if second.postures else set(StrategyPosture)
            )
            if not first_postures.intersection(second_postures):
                continue
            raise ValueError(
                f"overlapping Strategic Number modes '{first.identity}' and "
                f"'{second.identity}' target native Strategic Number "
                f"{first.native_strategic_number_id}"
            )


def _validate_endgame_plan(
    profile: StrategyProfile,
) -> None:
    plan = profile.endgame_plan
    if plan is None:
        return
    from .endgame import validate_endgame_plan

    validate_endgame_plan(
        plan,
        observation_ids=tuple(item.identity for item in profile.observations),
        frontier_witness_provenance={
            item.identity: item.provenance
            for item in profile.observations
        },
    )


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
    from .counter_strategy import validate_counter_packages
    validate_counter_packages(profile)
    counter_package_demands = {
        demand_identity
        for package in profile.counter_packages
        for demand_identity in package.demand_identities
    }
    _validate_capability_observations(profile, effective)
    _validate_observation_specs(profile, effective)
    _validate_strategic_number_modes(profile, effective)

    _validate_endgame_plan(profile)

    for demand in profile.demands:
        if demand.identity in seen:
            raise ValueError(f"duplicate strategic demand '{demand.identity}'")
        seen.add(demand.identity)

        if not demand.owner:
            raise ValueError(
                f"strategic demand '{demand.identity}' needs a strategic owner"
            )
        if (
            not any(
                evidence.kind is StrategicEvidenceKind.PERSISTENT
                for evidence in demand.reason
            )
            and demand.identity not in counter_package_demands
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' needs persistent strategic evidence "
                "or an explicit counter-package activation owner"
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

        if not demand.recovery.preserve_strategic_demand:
            raise ValueError(
                f"strategic demand '{demand.identity}' must preserve intent across capability loss"
            )
        if not demand.recovery.reopen_on_recovery:
            raise ValueError(
                f"strategic demand '{demand.identity}' must reopen on capability recovery"
            )
        if demand.opportunity_cost is not None and not demand.recovery.preserve_opportunity_cost:
            raise ValueError(
                f"strategic demand '{demand.identity}' cannot release opportunity-cost protection "
                "merely because capability was temporarily lost"
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

    from ..semantic.policy_recipe import resolve_policy_recipes

    # Policy recipes carried by StrategyProfile form the reusable policy catalog.
    # Required bindings are resolved only when a concrete control instance supplies them.
    policy_resolutions = resolve_policy_recipes(profile.policy_recipes)

    return ResolvedStrategyProfile(
        profile_id=profile.profile_id,
        demand_ids=tuple(sorted(seen)),
        policy_resolutions=policy_resolutions,
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
    from ..ir.resource_control import (
        EscrowOperation,
        EscrowOperationKind,
        NATIVE_ESCROW_RELEASE_COMMAND,
        NATIVE_ESCROW_RELEASE_RESOURCES,
        NativeEscrowReleasePlan,
    )
    from ..ir.model import SemanticId

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
                production_arbitration_group=spec.production_arbitration_group,
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

    escrow_operations = []
    for demand_index, demand in enumerate(semantic_demands):
        spec = profile.demand(execution_owner[demand.name])
        selected_execution = next(
            execution
            for execution in spec.execution_demands
            if (
                spec.identity
                if len(spec.execution_demands) == 1 and execution.local_id == "primary"
                else f"{spec.identity}::{execution.local_id}"
            ) == demand.name
        )
        resources = tuple(
            resource.value.lower()
            for resource in selected_execution.escrow_release_resources
        )
        if not resources:
            continue
        if demand.action.expression.head != "research" or len(demand.action.expression.args) != 1:
            raise ValueError(
                f"strategic execution demand '{demand.name}' may use escrow release resources "
                "only with a one-argument research action"
            )
        technology = str(demand.action.expression.args[0])
        if not any(
            requirement.expression.head == "can-research-with-escrow"
            and len(requirement.expression.args) == 1
            and str(requirement.expression.args[0]) == technology
            for requirement in demand.requirements
        ):
            raise ValueError(
                f"strategic execution demand '{demand.name}' must require "
                "can-research-with-escrow for the same technology"
            )
        for resource_index, resource in enumerate(resources):
            if resource not in NATIVE_ESCROW_RELEASE_RESOURCES:
                raise ValueError(
                    f"unsupported strategy escrow release resource '{resource}'"
                )
            escrow_operations.append(
                EscrowOperation(
                    contract_identity=f"{demand.name}:escrow:{resource}",
                    owner=demand.identity,
                    target_demand=demand.identity,
                    kind=EscrowOperationKind.RELEASE,
                    resource=resource,
                    command=NATIVE_ESCROW_RELEASE_COMMAND,
                    rule_order=demand_index,
                    within_rule_order=resource_index,
                )
            )

    escrow_plan = (
        NativeEscrowReleasePlan(tuple(escrow_operations))
        if escrow_operations
        else None
    )

    from .military_composition import (
        MilitaryCompositionPlan,
        MilitaryCompositionUnitTarget,
    )

    military_compositions: list[MilitaryCompositionPlan] = []
    for spec in profile.military_compositions:
        composition_identity = SemanticId(profile.profile_id, spec.identity)
        targets: list[MilitaryCompositionUnitTarget] = []
        for strategic_identity in spec.production_demands:
            candidates = tuple(
                demand
                for demand in bound_demands
                if demand.strategic_binding is not None
                and demand.strategic_binding.strategic_id == strategic_identity
            )
            if not candidates:
                raise ValueError(
                    f"military composition '{spec.identity}' references unknown strategic demand "
                    f"'{strategic_identity}'"
                )
            if len(candidates) != 1:
                raise ValueError(
                    f"military composition '{spec.identity}' requires exactly one lowered execution demand "
                    f"for strategic demand '{strategic_identity}'"
                )
            demand = candidates[0]
            lifecycle = demand.production_lifecycle
            if lifecycle is None:
                raise ValueError(
                    f"military composition '{spec.identity}' production demand '{strategic_identity}' "
                    "must lower to a ProductionLifecycle"
                )
            target_minimum = profile.demand(strategic_identity).target.minimum
            if target_minimum is None or target_minimum < 1:
                raise ValueError(
                    f"military composition '{spec.identity}' production demand '{strategic_identity}' "
                    "requires a positive StrategicTarget minimum"
                )
            targets.append(
                MilitaryCompositionUnitTarget(
                    demand=demand.identity,
                    unit=lifecycle.unit,
                    native_unit_id=lifecycle.native_unit_id,
                    minimum=target_minimum,
                )
            )
        military_compositions.append(
            MilitaryCompositionPlan(
                identity=composition_identity,
                targets=tuple(targets),
                attack_objective=SemanticId(profile.profile_id, spec.attack_objective),
            )
        )

    return StrategyCompilation(
        profile=profile,
        demands=tuple(bound_demands),
        bindings=bindings,
        escrow_plan=escrow_plan,
        control_plan=_strategy_control_plan(profile),
        military_compositions=tuple(military_compositions),
        attack_plan=profile.attack_plan,
        duc_plan=profile.duc_plan,
        water_execution_plan=profile.water_execution_plan,
        map_profile=profile.map_profile,
        opening_selector=profile.opening_selector,
        economy_controller=profile.economy_controller,
        camp_controller=profile.camp_controller,
        role_separation_plan=profile.role_separation_plan,
        endgame_plan=profile.endgame_plan,
    )


def _age_token(age: Age) -> str:
    return {
        Age.DARK: "dark-age",
        Age.FEUDAL: "feudal-age",
        Age.CASTLE: "castle-age",
        Age.IMPERIAL: "imperial-age",
    }[age]


def _next_age(age: Age) -> Age:
    if age is Age.DARK:
        return Age.FEUDAL
    if age is Age.FEUDAL:
        return Age.CASTLE
    if age is Age.CASTLE:
        return Age.IMPERIAL
    raise ValueError("Imperial Age has no successor")


def _combine_binary_native_guards(head: str, parts: tuple[str, ...]) -> str:
    if not parts:
        raise ValueError(f"cannot combine empty native guard sequence with '{head}'")
    combined = parts[0]
    for part in parts[1:]:
        combined = f"({head} {combined} {part})"
    return combined


def _strategic_number_arbitration_control_plan(profile: StrategyProfile):
    """Build and lower the typed Strategic Number controller arbitration plan."""
    if not profile.strategic_number_modes:
        return None

    from ..primitives.strategic_number_catalog import (
        default_strategic_number_inventory,
    )
    from ..semantic.strategic_number_arbitration import (
        build_strategic_number_arbitration_plan,
        lower_strategic_number_arbitration,
    )

    inventory = default_strategic_number_inventory()
    arbitration_plan = build_strategic_number_arbitration_plan(profile)
    lowering = lower_strategic_number_arbitration(
        arbitration_plan,
        profile_id=profile.profile_id,
        documented_native_ids=inventory.documented_ids,
    )
    return lowering.control_plan



def _strategy_number_mode_control_plan(profile: StrategyProfile):
    """Lower explicit age/posture Strategic Number modes into native controls."""
    if not profile.strategic_number_modes:
        return None

    from ..ast import SourceLocation
    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from .recurrent import TimerRequest
    from ..semantic.analyzer import parse_expression
    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from .model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
    from .strategic_number import StrategicNumberOrigin

    states: dict[str, NativeControlState] = {}
    native_state_names: dict[int, str] = {}
    rules: list[NativeControlRule] = []

    if any(mode.postures for mode in profile.strategic_number_modes):
        posture_owner = SemanticId(profile.profile_id, _STRATEGY_POSTURE_STATE)
        states[_STRATEGY_POSTURE_STATE] = NativeControlState(
            _STRATEGY_POSTURE_STATE,
            GoalSlotRequest(
                StorageRequestId(
                    posture_owner,
                    "strategy-posture",
                ),
                role=GoalRole.PERSISTENT_STATE,
            ),
        )

    ordered = tuple(
        sorted(
            enumerate(profile.strategic_number_modes),
            key=lambda item: (
                -item[1].priority,
                item[1].native_strategic_number_id,
                _AGE_ORDER[item[1].minimum_age],
                _AGE_ORDER[item[1].maximum_age]
                if item[1].maximum_age is not None
                else _AGE_ORDER[Age.IMPERIAL],
                item[1].identity,
                item[0],
            ),
        )
    )

    for rule_index, (_profile_index, mode) in enumerate(ordered):
        state_name = native_state_names.setdefault(
            mode.native_strategic_number_id,
            mode.state_name,
        )
        if state_name not in states:
            owner = SemanticId(profile.profile_id, state_name)
            states[state_name] = NativeControlState(
                state_name,
                StrategicNumberRequest(
                    StorageRequestId(
                        owner,
                        f"strategy-sn-native:{mode.native_strategic_number_id}",
                    ),
                    why_not_goal=(
                        "This state is a compiler policy reference to a DE-documented "
                        "native Strategic Number; native per-SN effect semantics remain "
                        "evidence-bounded."
                    ),
                    stability_key=(
                        f"{profile.profile_id}:strategic-number:"
                        f"{mode.native_strategic_number_id}"
                    ),
                    origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                    native_strategic_number_id=mode.native_strategic_number_id,
                ),
            )

        guards: list[str] = []
        if mode.minimum_age is mode.maximum_age:
            guards.append(f"(current-age == {_age_token(mode.minimum_age)})")
        else:
            guards.append(f"(current-age >= {_age_token(mode.minimum_age)})")
            if mode.maximum_age is not None and mode.maximum_age is not Age.IMPERIAL:
                guards.append(
                    f"(current-age < {_age_token(_next_age(mode.maximum_age))})"
                )

        if mode.postures:
            posture_guards = tuple(
                f"(goal {_STRATEGY_POSTURE_STATE} {_STRATEGY_POSTURE_VALUES[posture]})"
                for posture in mode.postures
            )
            guards.append(
                _combine_binary_native_guards("or", posture_guards)
            )

        if mode.reassertion_policy is StrategicNumberReassertionPolicy.ON_DRIFT:
            guards.append(
                f"(up-compare-sn {state_name} != {mode.value})"
            )

        guard_source = _combine_binary_native_guards("and", tuple(guards))
        rules.append(
            NativeControlRule(
                f"sn-mode-{mode.identity}-{rule_index:03d}",
                facts=(parse_expression(guard_source, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-strategic-number {state_name} {mode.value})",
                        SourceLocation(1),
                    ),
                ),
            )
        )

    return NativeControlPlan(
        states=tuple(
            states[key]
            for key in sorted(states)
        ),
        rules=tuple(rules),
    )


def _counter_package_state_name(identity: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", identity.lower()).strip("-")
    if not slug:
        raise ValueError("counter package identity cannot produce an empty native state name")
    return f"counter-package-{slug}"


def _counter_package_control_plan(profile: StrategyProfile):
    """Lower counter arbitration into persistent native package-selection state.

    Each counter package gets one Goal latch. Selection is recomputed from the
    package's verified native trigger each pass, with higher-priority packages
    of the same threat class suppressing lower-priority packages. This mirrors
    runtime arbitration without inventing a second scheduler.
    """
    if not profile.counter_packages:
        return None

    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState

    ordered = tuple(sorted(profile.counter_packages, key=lambda item: (-item.priority, item.identity)))
    state_names: dict[str, str] = {}
    states: list[NativeControlState] = []
    by_threat: dict[object, list] = {}

    for package in ordered:
        state_name = _counter_package_state_name(package.identity)
        existing = next(
            (
                package_identity
                for package_identity, existing_name in state_names.items()
                if existing_name == state_name
            ),
            None,
        )
        if existing is not None and existing != package.identity:
            raise ValueError(
                f"counter package identities '{existing}' and '{package.identity}' "
                f"collide on native state '{state_name}'"
            )
        state_names[package.identity] = state_name
        states.append(
            NativeControlState(
                state_name,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(profile.profile_id, package.identity),
                        "counter-package-selection",
                    ),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            )
        )
        by_threat.setdefault(package.threat_class, []).append(package)

    reset_actions = tuple(
        parse_expression(
            f"(set-goal {state_names[package.identity]} 0)",
            SourceLocation(1),
        )
        for package in ordered
    )
    rules: list[NativeControlRule] = [
        NativeControlRule(
            "counter-package-selection-reset-000",
            facts=(parse_expression("(current-age >= dark-age)", SourceLocation(1)),),
            actions=reset_actions,
        )
    ]

    rule_index = 1
    for threat_class in sorted(by_threat, key=lambda item: item.value):
        candidates = tuple(sorted(by_threat[threat_class], key=lambda item: (-item.priority, item.identity)))
        for index, package in enumerate(candidates):
            observation = profile.observation(package.trigger.observation_ref)
            guard = observation.expression
            higher = candidates[:index]
            if higher:
                higher_guards = tuple(
                    profile.observation(item.trigger.observation_ref).expression
                    for item in higher
                )
                blocked = (
                    higher_guards[0]
                    if len(higher_guards) == 1
                    else "(or " + " ".join(higher_guards) + ")"
                )
                guard = f"(and {guard} (not {blocked}))"
            rules.append(
                NativeControlRule(
                    f"counter-package-selection-{rule_index:03d}-{package.identity.lower()}",
                    facts=(parse_expression(guard, SourceLocation(1)),),
                    actions=(
                        parse_expression(
                            f"(set-goal {state_names[package.identity]} 1)",
                            SourceLocation(1),
                        ),
                    ),
                )
            )
            rule_index += 1

    return NativeControlPlan(
        states=tuple(sorted(states, key=lambda item: item.identifier)),
        rules=tuple(rules),
    )


def _merge_native_control_plans(*plans):
    from .native_control import NativeControlPlan

    states = []
    seen_state_ids = set()
    state_by_id = {}
    rules = []
    for plan in plans:
        if plan is None:
            continue
        for state in plan.states:
            existing = state_by_id.get(state.identifier)
            if existing is not None:
                if existing != state:
                    raise ValueError(
                        f"native control state '{state.identifier}' has conflicting definitions"
                    )
                continue
            state_by_id[state.identifier] = state
            states.append(state)
        rules.extend(plan.rules)

    if not states and not rules:
        return None
    return NativeControlPlan(states=tuple(states), rules=tuple(rules))


def _byzantine_attack_lifecycle_control_plan(profile: StrategyProfile):
    """Lower the default Byzantine attack policy into explicit persistent phases.

    Phase values:
      0 READY
      1 PREPARE-CATAPHRACT
      2 ATTACK-CATAPHRACT
      3 PREPARE-KNIGHT
      4 ATTACK-KNIGHT
      5 REASSESS

    This is compiler policy, not a native attack acknowledgement. The native
    attack command remains issue-only; phase release is driven by an explicit
    observed pressure witness or a force-floor loss.
    """
    if profile.profile_id not in {
        "byzantine-land-castle-v1",
        "byzantine-stock-v1",
    } or profile.attack_plan is None:
        return None

    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
    from .strategic_number import StrategicNumberOrigin

    owner = SemanticId(profile.profile_id, "byzantine-attack-phase")
    state_name = "byzantine-attack-phase"
    state = NativeControlState(
        state_name,
        GoalSlotRequest(
            StorageRequestId(owner, state_name),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )

    current_age = "(current-age >= castle-age)"
    allocation = "(goal strategy-posture 4)"
    knight_pressure = "(players-unit-type-count any-enemy knight >= 3)"
    knight_clear = "(players-unit-type-count any-enemy knight < 3)"
    cataphract_floor = "(unit-type-count cataphract >= 2)"
    cataphract_lost = "(unit-type-count cataphract < 2)"
    infantry_pressure = "(players-unit-type-count any-enemy militia-line >= 5)"
    infantry_clear = "(players-unit-type-count any-enemy militia-line < 5)"
    knight_floor = "(unit-type-count knight >= 3)"
    knight_lost = "(unit-type-count knight < 3)"

    rules = (
        NativeControlRule(
            "byzantine-attack-phase-initialize",
            facts=(parse_expression(f"(goal {state_name} 0)", SourceLocation(1)),),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 0)",
                    SourceLocation(1),
                ),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-prepare-cataphract",
            facts=(
                parse_expression(f"(goal {state_name} 0)", SourceLocation(1)),
                parse_expression(
                    f"(and {current_age} (and {allocation} "
                    f"(and {knight_pressure} {cataphract_floor})))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 1)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-attack-cataphract",
            facts=(
                parse_expression(f"(goal {state_name} 1)", SourceLocation(1)),
                parse_expression(
                    f"(and {current_age} (and {allocation} "
                    f"(and {knight_pressure} {cataphract_floor})))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 2)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-prepare-knight",
            facts=(
                parse_expression(f"(goal {state_name} 0)", SourceLocation(1)),
                parse_expression(
                    f"(and {current_age} (and {allocation} "
                    f"(and {infantry_pressure} {knight_floor})))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 3)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-attack-knight",
            facts=(
                parse_expression(f"(goal {state_name} 3)", SourceLocation(1)),
                parse_expression(
                    f"(and {current_age} (and {allocation} "
                    f"(and {infantry_pressure} {knight_floor})))",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 4)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-complete-cataphract",
            facts=(
                parse_expression(f"(goal {state_name} 2)", SourceLocation(1)),
                parse_expression(knight_clear, SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 0)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-complete-knight",
            facts=(
                parse_expression(f"(goal {state_name} 4)", SourceLocation(1)),
                parse_expression(infantry_clear, SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 0)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-recover-cataphract",
            facts=(
                parse_expression(f"(goal {state_name} 2)", SourceLocation(1)),
                parse_expression(cataphract_lost, SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 5)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-recover-knight",
            facts=(
                parse_expression(f"(goal {state_name} 4)", SourceLocation(1)),
                parse_expression(knight_lost, SourceLocation(1)),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 5)",
                    SourceLocation(1),
                ),
            ),
        ),
        NativeControlRule(
            "byzantine-attack-phase-reassess",
            facts=(parse_expression(f"(goal {state_name} 5)", SourceLocation(1)),),
            actions=(
                parse_expression(
                    f"(set-goal {state_name} 0)",
                    SourceLocation(1),
                ),
            ),
        ),
    )
    return NativeControlPlan(states=(state,), rules=rules)


def _byzantine_endgame_push_control_plan(profile: StrategyProfile):
    """Lower the bounded Imperial attack-group lifecycle.

    The native group pulse is world-state driven and uses only the shared native
    Strategic Number slots. Frontier advancement is lowered only when the strategy
    provides a separately verified frontier witness observation. We do not infer
    target destruction from attack-soldier-count reaching zero.
    """
    if profile.profile_id not in {
        "byzantine-land-castle-v1",
        "byzantine-stock-v1",
    }:
        return None
    plan = profile.endgame_plan
    if plan is None or plan.push_contract is None:
        return None

    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
    from .recurrent import TimerRequest
    from .strategic_number import StrategicNumberOrigin

    push_state_name = "byzantine-endgame-push-state"
    push_timer_name = "byzantine-endgame-push-timer"
    push_owner = SemanticId(profile.profile_id, "byzantine-endgame-push")
    push_state = NativeControlState(
        push_state_name,
        GoalSlotRequest(
            StorageRequestId(push_owner, push_state_name),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )
    push_timer = NativeControlState(
        push_timer_name,
        TimerRequest(
            StorageRequestId(push_owner, f"timer:{push_timer_name}"),
            initialization_policy="DISABLE_BEFORE_FIRST_USE",
            stability_key=f"{profile.profile_id}:byzantine-endgame-push-timer",
        ),
    )

    def _native_sn_state(native_id: int) -> NativeControlState:
        state_name = f"sn-native-{native_id}"
        owner = SemanticId(profile.profile_id, state_name)
        return NativeControlState(
            state_name,
            StrategicNumberRequest(
                StorageRequestId(
                    owner,
                    f"strategy-sn-native:{native_id}",
                ),
                why_not_goal=(
                    "This state is a compiler policy reference to a DE-documented "
                    "native Strategic Number; native per-SN effect semantics remain "
                    "evidence-bounded."
                ),
                stability_key=(
                    f"{profile.profile_id}:strategic-number:"
                    f"{native_id}"
                ),
                origin=StrategicNumberOrigin.NATIVE_REFERENCE,
                native_strategic_number_id=native_id,
            ),
        )

    sn_states = tuple(_native_sn_state(native_id) for native_id in (16, 26))

    live_witness = profile.observation(
        plan.push_contract.live_witness_ref
    ).expression
    cleared_witness = profile.observation(
        plan.push_contract.cleared_witness_ref
    ).expression
    military_ready = (
        "(or (unit-type-count cataphract >= 4) "
        "(or (unit-type-count varangian-guard >= 6) "
        "(or (unit-type-count 492 >= 6) "
        "(unit-type-count halberdier >= 6))))"
    )
    siege_ready = (
        "(or (unit-type-count trebuchet >= 1) "
        "(or (unit-type-count bombard-cannon >= 1) "
        "(unit-type-count-total mangonel-line >= 1)))"
    )

    rules = [
        NativeControlRule(
            "byzantine-endgame-push-initialize",
            facts=(parse_expression("(goal byzantine-endgame-push-state 0)", SourceLocation(1)),),
            actions=(
                parse_expression("(set-goal byzantine-endgame-push-state 0)", SourceLocation(1)),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-imperial-ready",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 0)", SourceLocation(1)),
                parse_expression("(current-age >= imperial-age)", SourceLocation(1)),
            ),
            actions=(
                parse_expression("(set-strategic-number sn-native-16 6)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-26 40)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-36 0)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-227 75)", SourceLocation(1)),
                parse_expression(f"(disable-timer {push_timer_name})", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 1)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-admit",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 1)", SourceLocation(1)),
                parse_expression("(current-age >= imperial-age)", SourceLocation(1)),
                parse_expression("(attack-soldier-count <= 0)", SourceLocation(1)),
                parse_expression(military_ready, SourceLocation(1)),
                parse_expression(siege_ready, SourceLocation(1)),
                parse_expression("(strategic-number sn-native-16 >= 6)", SourceLocation(1)),
                parse_expression("(strategic-number sn-native-26 >= 40)", SourceLocation(1)),
            ),
            actions=(
                parse_expression(f"(set-strategic-number sn-native-36 {plan.push_contract.attack_group_count})", SourceLocation(1)),
                parse_expression(f"(set-strategic-number sn-native-227 {plan.push_contract.attack_soldier_percent})", SourceLocation(1)),
                parse_expression(f"(enable-timer {push_timer_name} {plan.push_contract.active_window_seconds})", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 2)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-live-witness",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 2)", SourceLocation(1)),
                parse_expression(live_witness, SourceLocation(1)),
            ),
            actions=(
                parse_expression("(set-strategic-number sn-native-36 0)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-227 75)", SourceLocation(1)),
                parse_expression(f"(disable-timer {push_timer_name})", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 3)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-pulse-expiry",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 2)", SourceLocation(1)),
                parse_expression(f"(timer-triggered {push_timer_name})", SourceLocation(1)),
            ),
            actions=(
                parse_expression(f"(disable-timer {push_timer_name})", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-36 0)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-227 75)", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 3)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-recover",
            facts=(
                parse_expression(
                    "(or (goal byzantine-endgame-push-state 1) "
                    "(or (goal byzantine-endgame-push-state 2) "
                    "(goal byzantine-endgame-push-state 3)))",
                    SourceLocation(1),
                ),
                parse_expression(f"(not {military_ready})", SourceLocation(1)),
            ),
            actions=(
                parse_expression("(set-strategic-number sn-native-36 0)", SourceLocation(1)),
                parse_expression("(set-strategic-number sn-native-227 75)", SourceLocation(1)),
                parse_expression(f"(disable-timer {push_timer_name})", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 5)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-release",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 3)", SourceLocation(1)),
                parse_expression(cleared_witness, SourceLocation(1)),
                parse_expression(military_ready, SourceLocation(1)),
            ),
            actions=(
                parse_expression(f"(disable-timer {push_timer_name})", SourceLocation(1)),
                parse_expression("(set-goal byzantine-endgame-push-state 1)", SourceLocation(1)),
            ),
        ),
        NativeControlRule(
            "byzantine-endgame-push-recovery-release",
            facts=(
                parse_expression("(goal byzantine-endgame-push-state 5)", SourceLocation(1)),
                parse_expression(military_ready, SourceLocation(1)),
            ),
            actions=(
                parse_expression("(set-goal byzantine-endgame-push-state 0)", SourceLocation(1)),
            ),
        ),
    ]

    endgame_mode = "byzantine-endgame-mode"
    endgame_win = "byzantine-endgame-win-condition"
    frontier_verified = "byzantine-endgame-frontier-verified"
    states = [push_state, push_timer, *sn_states]
    states.extend(
        (
            NativeControlState(
                frontier_verified,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(profile.profile_id, frontier_verified),
                        frontier_verified,
                    ),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            ),
            NativeControlState(
                endgame_mode,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(profile.profile_id, endgame_mode),
                        endgame_mode,
                    ),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            ),
            NativeControlState(
                endgame_win,
                GoalSlotRequest(
                    StorageRequestId(
                        SemanticId(profile.profile_id, endgame_win),
                        endgame_win,
                    ),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            ),
        )
    )
    verified_frontier_match = (
        "(or (and (goal byzantine-endgame-frontier 1) "
        "(goal byzantine-endgame-frontier-verified 1)) "
        "(or (and (goal byzantine-endgame-frontier 2) "
        "(goal byzantine-endgame-frontier-verified 2)) "
        "(and (goal byzantine-endgame-frontier 3) "
        "(goal byzantine-endgame-frontier-verified 3))))"
    )
    conversion_contract = plan.conversion_contract
    if conversion_contract is not None:
        for demand in profile.demands:
            if not demand.identity.startswith("imperial-forward-production-"):
                continue
            action = demand.execution.action.strip()
            if not action.startswith("(build ") or not action.endswith(")"):
                continue
            building_token = action[len("(build "):-1].strip()
            if not building_token:
                continue
            rules.append(
                NativeControlRule(
                    f"byzantine-endgame-conversion-admit-{demand.identity}",
                    facts=(
                        parse_expression(verified_frontier_match, SourceLocation(1)),
                        parse_expression(f"(goal demand-{demand.name} 0)", SourceLocation(1)),
                        parse_expression("(current-age >= imperial-age)", SourceLocation(1)),
                        parse_expression(f"(can-build {building_token})", SourceLocation(1)),
                    ),
                    actions=(
                        parse_expression(f"(set-goal demand-{demand.name} 1)", SourceLocation(1)),
                    ),
                )
            )

    rules.extend(
        (
            NativeControlRule(
                "byzantine-endgame-mode-recovery",
                facts=(
                    parse_expression(verified_frontier_match, SourceLocation(1)),
                    parse_expression("(goal byzantine-endgame-push-state 5)", SourceLocation(1)),
                ),
                actions=(
                    parse_expression(f"(set-goal {endgame_mode} 3)", SourceLocation(1)),
                    parse_expression(f"(set-goal {endgame_win} 3)", SourceLocation(1)),
                ),
            ),
            NativeControlRule(
                "byzantine-endgame-mode-resource-denial",
                facts=(
                    parse_expression(verified_frontier_match, SourceLocation(1)),
                    parse_expression(profile.observation("strategy-endgame-resource-denial").expression, SourceLocation(1)),
                    parse_expression(profile.observation("strategy-enemy-pressure").expression, SourceLocation(1)),
                ),
                actions=(
                    parse_expression(f"(set-goal {endgame_mode} 2)", SourceLocation(1)),
                    parse_expression(f"(set-goal {endgame_win} 1)", SourceLocation(1)),
                ),
            ),
            NativeControlRule(
                "byzantine-endgame-mode-attrition",
                facts=(
                    parse_expression(f"(goal {frontier_verified} 1)", SourceLocation(1)),
                    parse_expression("(or (goal byzantine-endgame-frontier 1) (goal byzantine-endgame-frontier 2) (goal byzantine-endgame-frontier 3))", SourceLocation(1)),
                    parse_expression(profile.observation("strategy-endgame-ground-conversion").expression, SourceLocation(1)),
                    parse_expression(profile.observation("strategy-imperial-spend-gold").expression, SourceLocation(1)),
                ),
                actions=(
                    parse_expression(f"(set-goal {endgame_mode} 1)", SourceLocation(1)),
                    parse_expression(f"(set-goal {endgame_win} 2)", SourceLocation(1)),
                ),
            ),
            NativeControlRule(
                "byzantine-endgame-mode-breakthrough",
                facts=(
                    parse_expression(verified_frontier_match, SourceLocation(1)),
                    parse_expression(profile.observation("strategy-imperial-spend-gold").expression, SourceLocation(1)),
                    parse_expression(profile.observation("strategy-enemy-castle").expression, SourceLocation(1)),
                ),
                actions=(
                    parse_expression(f"(set-goal {endgame_mode} 0)", SourceLocation(1)),
                    parse_expression(f"(set-goal {endgame_win} 0)", SourceLocation(1)),
                ),
            ),
        )
    )

    frontier_witness_ref = plan.push_contract.frontier_witness_ref
    target_control = plan.target_control
    conversion_contract = plan.conversion_contract
    if target_control is not None or frontier_witness_ref is not None:
        frontier_name = "byzantine-endgame-frontier"
        frontier_owner = SemanticId(profile.profile_id, "byzantine-endgame-frontier")
        states.append(
            NativeControlState(
                frontier_name,
                GoalSlotRequest(
                    StorageRequestId(frontier_owner, frontier_name),
                    role=GoalRole.PERSISTENT_STATE,
                ),
            )
        )
        rules.append(
            NativeControlRule(
                "byzantine-endgame-frontier-initialize",
                facts=(parse_expression(f"(goal {frontier_name} 0)", SourceLocation(1)),),
                actions=(
                    parse_expression(f"(set-goal {frontier_name} 0)", SourceLocation(1)),
                    parse_expression("(disable-self)", SourceLocation(1)),
                ),
            )
        )

    if frontier_witness_ref is not None:
        frontier_witness_name = "byzantine-endgame-frontier-witness"
        frontier_owner = SemanticId(profile.profile_id, "byzantine-endgame-frontier")
        states.append(
            NativeControlState(
                frontier_witness_name,
                GoalSlotRequest(
                    StorageRequestId(frontier_owner, frontier_witness_name),
                    role=GoalRole.EXECUTION_MEMORY,
                ),
            )
        )
        frontier_witness = profile.observation(frontier_witness_ref).expression
        rules.append(
            NativeControlRule(
                "byzantine-endgame-frontier-witness-initialize",
                facts=(parse_expression(f"(goal {frontier_witness_name} 0)", SourceLocation(1)),),
                actions=(
                    parse_expression(f"(set-goal {frontier_witness_name} 0)", SourceLocation(1)),
                    parse_expression("(disable-self)", SourceLocation(1)),
                ),
            )
        )
        frontier_steps = (
            ("byzantine-endgame-frontier-witness-defense", 0, 1),
            ("byzantine-endgame-frontier-witness-production", 1, 2),
            ("byzantine-endgame-frontier-witness-town-center", 2, 3),
        )
        for identity, current_value, next_value in frontier_steps:
            rules.append(
                NativeControlRule(
                    identity,
                    facts=(
                        parse_expression("(goal byzantine-endgame-push-state 3)", SourceLocation(1)),
                        parse_expression(f"(goal {frontier_name} {current_value})", SourceLocation(1)),
                        parse_expression(f"(goal {frontier_witness_name} 0)", SourceLocation(1)),
                        parse_expression(frontier_witness, SourceLocation(1)),
                    ),
                    actions=(
                        parse_expression(f"(set-goal {frontier_witness_name} {next_value})", SourceLocation(1)),
                    ),
                )
            )
        for identity, current_value, next_value in (
            ("byzantine-endgame-frontier-commit-defense", 0, 1),
            ("byzantine-endgame-frontier-commit-production", 1, 2),
            ("byzantine-endgame-frontier-commit-town-center", 2, 3),
        ):
            rules.append(
                NativeControlRule(
                    identity,
                    facts=(
                        parse_expression(f"(goal {frontier_name} {current_value})", SourceLocation(1)),
                        parse_expression(f"(goal {frontier_witness_name} {next_value})", SourceLocation(1)),
                    ),
                    actions=(
                        parse_expression(f"(set-goal {frontier_name} {next_value})", SourceLocation(1)),
                        parse_expression(f"(set-goal {frontier_verified} {next_value})", SourceLocation(1)),
                        parse_expression("(set-goal byzantine-endgame-push-state 4)", SourceLocation(1)),
                        parse_expression(f"(set-goal {frontier_witness_name} 0)", SourceLocation(1)),
                    ),
                )
            )

    if frontier_witness_ref is not None:
        rules.append(
            NativeControlRule(
                "byzantine-endgame-frontier-advance-release",
                facts=(
                    parse_expression("(goal byzantine-endgame-push-state 4)", SourceLocation(1)),
                ),
                actions=(
                    parse_expression("(set-goal byzantine-endgame-push-state 1)", SourceLocation(1)),
                ),
            )
        )

    return NativeControlPlan(states=tuple(states), rules=tuple(rules))

def _strategy_control_plan(profile: StrategyProfile):
    """Lower posture transitions, SN modes, and explicit Goal assertions through one control plane."""
    posture_plan = _posture_transition_control_plan(profile)
    mode_plan = _strategic_number_arbitration_control_plan(profile)
    assertion_plan = _goal_state_control_plan(profile)
    attack_lifecycle_plan = _byzantine_attack_lifecycle_control_plan(profile)
    endgame_push_plan = _byzantine_endgame_push_control_plan(profile)
    water_plan = None
    if profile.water_execution_plan is not None:
        from .water import lower_water_execution_plan
        water_plan = lower_water_execution_plan(
            profile.water_execution_plan,
            profile,
        )
    opening_plan = None
    if profile.opening_selector is not None:
        from .opening import lower_opening_selector
        opening_plan = lower_opening_selector(profile.opening_selector, profile)
    economy_plan = None
    if profile.economy_controller is not None:
        from .economic_control import lower_economy_controller
        economy_plan = lower_economy_controller(profile.economy_controller, profile)

    camp_plan = None
    if profile.camp_controller is not None:
        from .camp_control import lower_byzantine_camp_controller
        camp_plan = lower_byzantine_camp_controller(profile.camp_controller, profile)

    relic_plan = _byzantine_relic_control_plan(profile.profile_id)

    if any(
        state.identifier == _STRATEGY_POSTURE_STATE
        for state in (assertion_plan.states if assertion_plan is not None else ())
    ):
        raise ValueError(
            f"native strategy state '{_STRATEGY_POSTURE_STATE}' is reserved by posture transitions"
        )
    if posture_plan is not None and mode_plan is not None:
        mode_posture_state = mode_plan.state(_STRATEGY_POSTURE_STATE) if _STRATEGY_POSTURE_STATE in {
            state.identifier for state in mode_plan.states
        } else None
        if mode_posture_state is not None and mode_posture_state != posture_plan.state(
            _STRATEGY_POSTURE_STATE
        ):
            raise ValueError(
                f"native strategy state '{_STRATEGY_POSTURE_STATE}' conflicts with posture transition storage"
            )



    return _merge_native_control_plans(
        posture_plan,
        mode_plan,
        assertion_plan,
        attack_lifecycle_plan,
        endgame_push_plan,
        water_plan,
        opening_plan,
        economy_plan,
        camp_plan,
        relic_plan,
    )


def _posture_transition_control_plan(profile: StrategyProfile):
    """Lower the StrategyProfile posture FSM into native Goal control rules.

    Transition evidence is always read from verified StrategyObservationSpec
    references. Native same-pass Goal visibility remains engine-ordered, so
    this synthesis establishes deterministic policy/lowering without claiming
    an unproven runtime firing order.
    """
    if not profile.transitions:
        return None

    labels = {transition.label for transition in profile.transitions}
    if len(labels) != len(profile.transitions):
        raise ValueError("duplicate posture transition label")

    transitions = profile.transitions
    for index, first in enumerate(transitions):
        for second in transitions[index + 1 :]:
            if first.priority != second.priority or first.to_posture is second.to_posture:
                continue
            if set(first.from_postures).intersection(second.from_postures):
                raise ValueError(
                    f"equal-priority posture transitions '{first.label}' and '{second.label}' "
                    "have incompatible destinations"
                )
            if not first.from_postures and not second.from_postures:
                raise ValueError(
                    f"equal-priority initial posture transitions '{first.label}' and '{second.label}' "
                    "have incompatible destinations"
                )

    from ..ast import SourceLocation
    from ..runtime_binding import GoalSlotRequest
    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState

    owner = SemanticId(profile.profile_id, _STRATEGY_POSTURE_STATE)
    state = NativeControlState(
        _STRATEGY_POSTURE_STATE,
        GoalSlotRequest(
            StorageRequestId(owner, _STRATEGY_POSTURE_STATE),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )

    rules = [
        NativeControlRule(
            f"{_STRATEGY_POSTURE_STATE}-initialize-000",
            facts=(
                parse_expression(
                    f"(goal {_STRATEGY_POSTURE_STATE} 0)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression(
                    f"(set-goal {_STRATEGY_POSTURE_STATE} 0)",
                    SourceLocation(1),
                ),
                parse_expression("(disable-self)", SourceLocation(1)),
            ),
        )
    ]

    ordered = tuple(
        sorted(
            enumerate(profile.transitions),
            key=lambda item: (-item[1].priority, item[1].label, item[0]),
        )
    )
    for rule_index, (_profile_index, transition) in enumerate(ordered, start=1):
        guard_sources: list[str] = []
        if transition.from_postures:
            posture_guards = tuple(
                f"(goal {_STRATEGY_POSTURE_STATE} {_STRATEGY_POSTURE_VALUES[posture]})"
                for posture in transition.from_postures
            )
            guard_sources.append(
                posture_guards[0]
                if len(posture_guards) == 1
                else "(or " + " ".join(posture_guards) + ")"
            )
        else:
            # Empty from_postures means "initial posture only" in the runtime
            # model. Encode the same boundary in native persistent state so an
            # initial transition cannot reassert forever after initialization.
            guard_sources.append(f"(goal {_STRATEGY_POSTURE_STATE} 0)")
        for evidence in transition.evidence:
            if evidence.observation_ref is None:
                raise ValueError(
                    f"posture transition '{transition.label}' requires observation-backed evidence"
                )
            guard_sources.append(profile.observation(evidence.observation_ref).expression)

        guard_source = guard_sources[0] if len(guard_sources) == 1 else f"(and {' '.join(guard_sources)})"
        target_value = _STRATEGY_POSTURE_VALUES[transition.to_posture]
        rules.append(
            NativeControlRule(
                f"{_STRATEGY_POSTURE_STATE}-transition-{rule_index:03d}",
                facts=(parse_expression(guard_source, SourceLocation(1)),),
                actions=(
                    parse_expression(
                        f"(set-goal {_STRATEGY_POSTURE_STATE} {target_value})",
                        SourceLocation(1),
                    ),
                ),
            )
        )

    return NativeControlPlan(states=(state,), rules=tuple(rules))


def _goal_state_control_plan(profile: StrategyProfile):
    """Lower strategy-owned goal assertions to a NativeControlPlan.

    Returns None when no demand declares assertions, preserving existing
    behavior exactly. States dedupe by (name, owner); rules stay
    one-per-assertion in profile order.
    """
    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, GoalSlotRequest, SemanticId, StorageRequestId
    from .native_control import (
        NativeControlPlan,
        NativeControlRule,
        NativeControlState,
    )

    states: dict[tuple[str, SemanticId], NativeControlState] = {}
    rules: list[NativeControlRule] = []
    for spec in profile.demands:
        for assertion in spec.goal_assertions:
            if assertion.demand_id != spec.identity:
                raise ValueError(
                    f"goal state assertion '{assertion.state_name}' is owned by "
                    f"'{assertion.demand_id}', not by strategic demand "
                    f"'{spec.identity}'"
                )
            owner = SemanticId(profile.profile_id, assertion.demand_id)
            key = (assertion.state_name, owner)
            if key not in states:
                states[key] = NativeControlState(
                    assertion.state_name,
                    GoalSlotRequest(
                        StorageRequestId(
                            owner,
                            f"strategy-goal:{assertion.state_name}",
                        ),
                        role=GoalRole.PERSISTENT_STATE,
                    ),
                )
            try:
                guard = parse_expression(
                    assertion.guard_fact, SourceLocation(1)
                )
                action = parse_expression(
                    f"(set-goal {assertion.state_name} {assertion.set_value})",
                    SourceLocation(1),
                )
            except ValueError as exc:
                raise ValueError(
                    f"goal state assertion '{assertion.state_name}' has an "
                    f"unparsable native expression: {exc}"
                ) from exc
            rules.append(
                NativeControlRule(
                    f"{assertion.state_name}-assert-{len(rules):03d}",
                    facts=(guard,),
                    actions=(action,),
                )
            )
    for name in sorted({state for state, _ in states}):
        owners = sorted(
            {owner.local_name for state, owner in states if state == name}
        )
        if len(owners) > 1:
            raise ValueError(
                f"goal state '{name}' is claimed by multiple demand owners: "
                f"{', '.join(owners)}"
            )
    if not rules:
        return None
    return NativeControlPlan(
        states=tuple(
            states[key]
            for key in sorted(states, key=lambda item: (item[0], item[1].local_name))
        ),
        rules=tuple(rules),
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
            "enemy-feudal-mounted-pressure",
            "(and (current-age == feudal-age) (players-unit-type-count any-enemy scout-cavalry-line >= 3))",
            provenance=effective.unit_line("scout-cavalry-line").provenance,
        ),
        StrategicObservationSpec(
            "enemy-ranged-pressure",
            "(and (current-age == feudal-age) (players-unit-type-count any-enemy archer-line >= 3))",
            provenance=effective.unit_line("archer-line").provenance,
        ),
        StrategicObservationSpec(
            "enemy-mounted-commitment-feudal",
            "(and (current-age == feudal-age) "
            "(and (players-building-type-count any-enemy stable >= 1) "
            "(players-unit-type-count any-enemy scout-cavalry-line < 3)))",
            provenance=tuple(
                dict.fromkeys(
                    (
                        *effective.building(101).provenance,
                        *effective.unit_line("scout-cavalry-line").provenance,
                    )
                )
            ),
        ),
        StrategicObservationSpec(
            "enemy-ranged-commitment-feudal",
            "(and (current-age == feudal-age) "
            "(and (players-building-type-count any-enemy archery-range >= 1) "
            "(players-unit-type-count any-enemy archer-line < 3)))",
            provenance=tuple(
                dict.fromkeys(
                    (
                        *effective.building(87).provenance,
                        *effective.unit_line("archer-line").provenance,
                    )
                )
            ),
        ),
        StrategicObservationSpec(
            "enemy-infantry-pressure",
            "(and (current-age >= castle-age) (players-unit-type-count any-enemy militia-line >= 5))",
            provenance=effective.unit_line("militia-line").provenance,
        ),
        StrategicObservationSpec(
            "enemy-siege-pressure",
            "(and (current-age >= castle-age) (players-unit-type-count any-enemy mangonel-line >= 2))",
            provenance=effective.unit_line("mangonel-line").provenance,
        ),
        StrategicObservationSpec(
            "castle-complete",
            "(and (current-age >= castle-age) (building-type-count-total castle >= 1))",
            provenance=castle_complete_provenance,
        ),
        StrategicObservationSpec(
            "byz-logistica-complete",
            "(research-completed 61)",
            provenance=effective.tech(61).provenance,
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
    castle_age = effective.age_advance(Age.CASTLE)
    castle_age_cost = effective.cost_of_age_advance(Age.CASTLE)

    castle_policy = OpportunityCostPolicy(
        owner="castle-trajectory",
        protected_floors=(
            ProtectedResourceFloor(Resource.STONE, 650),
        ),
        emergency_override_postures=(StrategyPosture.FLUSH, StrategyPosture.RUSH),
    )

    castle_age_policy = OpportunityCostPolicy(
        owner="age-transition",
        protected_floors=(
            ProtectedResourceFloor(Resource.FOOD, castle_age_cost.food),
            ProtectedResourceFloor(Resource.GOLD, castle_age_cost.gold),
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
                    "(unit-type-count-total villager >= 21)",
                    "(can-research-with-escrow feudal-age)",
                ),
                action="(research feudal-age)",
                witness="(current-age >= feudal-age)",
                release="(current-age >= feudal-age)",
                escrow_release_resources=(Resource.FOOD, Resource.GOLD),
            ),
        ),
        StrategicDemandSpec(
            identity="castle-age-transition",
            owner="age-transition",
            posture=StrategyPosture.BOOM,
            priority=StrategicPriority.CORE,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Reach Castle as the selected Feudal trajectory without allowing optional Feudal purchases to starve the age bank",
                    observation_ref="current-feudal-age",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle transition remains admissible until Castle Age is witnessed",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle transition is obsolete after Imperial Age",
                    observation_ref="current-imperial-age",
                ),
            ),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.AGE_ADVANCE,
                "age-advance",
                "castle-age",
                castle_age.provider_building,
            ),
            target=StrategicTarget(
                StrategicTargetKind.EXACT,
                "age-advance",
                "castle-age",
            ),
            opportunity_cost=castle_age_policy,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age == feudal-age)",
                    "(unit-type-count-total villager >= 28)",
                    "(building-type-count-total blacksmith >= 1)",
                    "(building-type-count-total market >= 1)",
                    "(can-research-with-escrow castle-age)",
                ),
                action="(research castle-age)",
                witness="(current-age >= castle-age)",
                release="(current-age >= castle-age)",
                escrow_release_resources=(Resource.FOOD, Resource.GOLD),
            ),
        ),
        StrategicDemandSpec(
            identity="early-defensive-spears",
            owner="defense",
            production_arbitration_group="defense",
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




def _byzantine_relic_control_plan(profile_id: str):
    """Lower relic acquisition state into the shared persistent-control plane."""
    if profile_id != "byzantine-stock-v1":
        return None

    from ..runtime_binding import GoalSlotRequest, StrategicNumberRequest
    from ..semantic.analyzer import parse_expression
    from .model import GoalRole, SemanticId, StorageRequestId
    from .native_control import NativeControlPlan, NativeControlRule, NativeControlState
    from .recurrent import TimerRequest
    from .strategic_number import StrategicNumberOrigin

    owner = SemanticId(profile_id, "byzantine-relic-control")
    state_name = "byzantine-relic-control-state"
    timer_name = "byzantine-relic-control-timer"
    state = NativeControlState(
        state_name,
        GoalSlotRequest(
            StorageRequestId(owner, "relic-control-state"),
            role=GoalRole.PERSISTENT_STATE,
        ),
    )
    timer = NativeControlState(
        timer_name,
        TimerRequest(
            StorageRequestId(owner, f"timer:{timer_name}"),
            initialization_policy="DISABLE_BEFORE_FIRST_USE",
            stability_key=f"{profile_id}:byzantine-relic-control-timer",
        ),
    )
    focus_player = NativeControlState(
        "sn-focus-player-number",
        StrategicNumberRequest(
            StorageRequestId(owner, "sn-focus-player-number"),
            why_not_goal=(
                "Native DUC focus-player selector used to make the remote relic "
                "search operate against Gaia. SN 251 is DE-documented."
            ),
            stability_key=f"{profile_id}:strategic-number:251",
            origin=StrategicNumberOrigin.NATIVE_REFERENCE,
            native_strategic_number_id=251,
        ),
    )

    def expr(source: str):
        return parse_expression(source, SourceLocation(1))

    acquire_guard = (
        expr("(current-age >= castle-age)"),
        expr(f"(goal {state_name} 0)"),
        expr("(building-type-count-total 104 >= 1)"),
        expr("(unit-type-count-total 125 >= 1)"),
        expr("(unit-type-count-total 286 < 1)"),
        expr(
            f"(or "
            f"(up-timer-status {timer_name} c:== timer-disabled) "
            f"(up-timer-status {timer_name} c:== timer-triggered))"
        ),
    )

    rules = (
        NativeControlRule(
            "byzantine-relic-control-initialize",
            facts=(expr(f"(goal {state_name} -1)"),),
            actions=(
                expr(f"(set-goal {state_name} 0)"),
                expr(f"(disable-timer {timer_name})"),
                expr("(set-strategic-number sn-focus-player-number 0)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-focus-gaia",
            facts=(
                expr(f"(goal {state_name} 0)"),
            ),
            actions=(
                expr("(set-strategic-number sn-focus-player-number 0)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-mark-dispatch",
            facts=acquire_guard,
            actions=(
                expr(f"(set-goal {state_name} 1)"),
                expr(f"(enable-timer {timer_name} 45)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-pickup-witness",
            facts=(
                expr(f"(goal {state_name} 1)"),
                expr("(unit-type-count-total 286 >= 1)"),
            ),
            actions=(
                expr(f"(set-goal {state_name} 2)"),
                expr(f"(disable-timer {timer_name})"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-resume-carrier",
            facts=(
                expr(f"(goal {state_name} 0)"),
                expr("(unit-type-count-total 286 >= 1)"),
            ),
            actions=(
                expr(f"(set-goal {state_name} 2)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-start-return",
            facts=(
                expr(f"(goal {state_name} 2)"),
                expr("(unit-type-count-total 286 >= 1)"),
                expr("(building-type-count-total 104 >= 1)"),
                expr(f"(up-timer-status {timer_name} c:== timer-disabled)"),
            ),
            actions=(
                expr(f"(enable-timer {timer_name} 45)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-carrier-loss-recovery",
            facts=(
                expr(f"(goal {state_name} 2)"),
                expr("(unit-type-count-total 286 < 1)"),
            ),
            actions=(
                expr(f"(disable-timer {timer_name})"),
                expr(f"(set-goal {state_name} 0)"),
            ),
        ),
        NativeControlRule(
            "byzantine-relic-control-expiry",
            facts=(
                expr(
                    f"(or "
                    f"(goal {state_name} 1) "
                    f"(goal {state_name} 2))"
                ),
                expr(f"(timer-triggered {timer_name})"),
            ),
            actions=(
                expr(f"(disable-timer {timer_name})"),
                expr(f"(set-goal {state_name} 0)"),
            ),
        ),
    )
    return NativeControlPlan(
        states=(state, timer, focus_player),
        rules=rules,
    )

def _default_byzantine_duc_plan(
    profile_id: str,
    *,
    target_control=None,
) -> "NativeDucPlan":
    """Default Castle-age Byzantine enemy-target discovery/reacquisition substrate.

    Strategy policy selects only decision-grade observed pressure. DUC then
    rebuilds the remote search list and records the native object identity.
    Runtime object liveness and attack-controller consumption remain separate
    boundaries.
    """
    from ..semantic.analyzer import parse_expression
    from ..runtime_binding import GoalSlotRequest
    from .model import GoalRole, SemanticId, StorageRequestId
    from .native_duc import (
        NativeDucLifecycleStage,
        NativeDucOutputRequest,
        NativeDucPlan,
        NativeDucRule,
    )

    target_specs = (
        (
            "byzantine-castle-target-knight",
            "(players-unit-type-count any-enemy knight >= 3)",
            "38",
            "knight",
        ),
        (
            "byzantine-castle-target-infantry",
            "(players-unit-type-count any-enemy militia-line >= 5)",
            "74",
            "militia-line",
        ),
    )

    rules = []
    outputs = []
    for order, (identity, pressure_fact, search_unit, purpose) in enumerate(
        target_specs
    ):
        output = GoalSlotRequest(
            StorageRequestId(
                SemanticId(profile_id, identity),
                "up-get-object-data",
            ),
            role=GoalRole.NATIVE_OUTPUT,
        )
        rules.append(
            NativeDucRule(
                identity=identity,
                order=order,
                facts=(
                    parse_expression("(current-age >= castle-age)", SourceLocation(1)),
                    parse_expression("(up-compare-sn 227 >= 75)", SourceLocation(1)),
                    parse_expression(pressure_fact, SourceLocation(1)),
                ),
                actions=(
                    parse_expression("(up-full-reset-search)", SourceLocation(1)),
                    parse_expression(
                        f"(up-find-remote c: {search_unit} c: 1)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        "(up-set-target-object search-remote c: 0)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        "(up-get-object-data id 0)",
                        SourceLocation(1),
                    ),
                ),
            )
        )
        outputs.append(
            NativeDucOutputRequest(
                rule_identity=identity,
                section="ACTION",
                expression_index=3,
                request=output,
                command="up-get-object-data",
                argument_index=1,
            )
        )

    if profile_id != "byzantine-stock-v1":
        return NativeDucPlan(
            rules=tuple(rules),
            output_requests=tuple(outputs),
        )

    if target_control is not None:
        from .endgame import EndgameFrontierState, EndgameTargetQueryKind
        from .model import GoalRole

        frontier_values = {
            EndgameFrontierState.SIEGE: 0,
            EndgameFrontierState.DEFENSE: 1,
            EndgameFrontierState.PRODUCTION: 2,
            EndgameFrontierState.TOWN_CENTER: 3,
        }
        target_base = len(rules)
        for offset, candidate in enumerate(target_control.candidates):
            frontier_value = frontier_values[candidate.frontier]
            query_kind = candidate.query_kind
            if query_kind not in {
                EndgameTargetQueryKind.OBJECT_TYPE,
                EndgameTargetQueryKind.OBJECT_CLASS,
            }:
                raise ValueError(
                    f"unsupported endgame target query kind '{query_kind}'"
                )
            identity = f"byzantine-endgame-target-{target_base + offset:03d}-{candidate.identity}"
            output = GoalSlotRequest(
                StorageRequestId(
                    SemanticId(profile_id, f"endgame-target:{candidate.identity}"),
                    "up-get-object-data",
                ),
                role=GoalRole.NATIVE_OUTPUT,
            )
            rules.append(
                NativeDucRule(
                    identity=identity,
                    order=target_base + offset,
                    facts=(
                        parse_expression(
                            "(current-age >= imperial-age)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(goal byzantine-endgame-push-state 1)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            f"(goal byzantine-endgame-frontier {frontier_value})",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(goal byzantine-offensive-objective-claim 0)",
                            SourceLocation(1),
                        ),
                    ),
                    actions=(
                        parse_expression(
                            "(up-full-reset-search)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            f"(up-set-target-point {target_control.anchor_goal})",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            f"(up-filter-distance c: -1 c: {target_control.search_radius})",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            f"(up-find-remote c: {candidate.native_id} c: 1)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(up-set-target-object search-remote c: 0)",
                            SourceLocation(1),
                        ),
                        parse_expression(
                            "(up-get-object-data id 0)",
                            SourceLocation(1),
                        ),
                    ),
                    lifecycle=(
                        NativeDucLifecycleStage.ADMISSIBILITY,
                        NativeDucLifecycleStage.TARGET,
                    ),
                )
            )
            outputs.append(
                NativeDucOutputRequest(
                    rule_identity=identity,
                    section="ACTION",
                    expression_index=5,
                    request=output,
                    command="up-get-object-data",
                    argument_index=1,
                )
            )

    relic_base = len(rules)
    from .native_duc import NativeDucLifecycleStage

    lifecycle_rules = (
        NativeDucRule(
            identity="byzantine-relic-control-acquire",
            order=relic_base + 0,
            facts=(
                parse_expression("(current-age >= castle-age)", SourceLocation(1)),
                parse_expression("(goal byzantine-relic-control-state 0)", SourceLocation(1)),
                parse_expression("(building-type-count-total 104 >= 1)", SourceLocation(1)),
                parse_expression("(unit-type-count-total 125 >= 1)", SourceLocation(1)),
                parse_expression("(unit-type-count-total 286 < 1)", SourceLocation(1)),
                parse_expression("(up-gaia-type-count-total c: 285 > 0)", SourceLocation(1)),
                parse_expression(
                    "(up-timer-status byzantine-relic-control-timer c:== timer-disabled)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression("(up-full-reset-search)", SourceLocation(1)),
                parse_expression("(up-find-remote c: 285 c: 1)", SourceLocation(1)),
                parse_expression("(up-set-target-object search-remote c: 0)", SourceLocation(1)),
                parse_expression("(up-find-local c: 125 c: 1)", SourceLocation(1)),
                parse_expression(
                    "(up-target-objects 0 0 -1 stance-defensive)",
                    SourceLocation(1),
                ),
            ),
            lifecycle=(
                NativeDucLifecycleStage.ADMISSIBILITY,
                NativeDucLifecycleStage.TARGET,
                NativeDucLifecycleStage.DISPATCH,
            ),
        ),
        NativeDucRule(
            identity="byzantine-relic-control-pickup-witness",
            order=relic_base + 1,
            facts=(parse_expression("(goal byzantine-relic-control-state 1)", SourceLocation(1)),),
            actions=(
                parse_expression("(up-find-local c: 286 c: 1)", SourceLocation(1)),
            ),
            lifecycle=(NativeDucLifecycleStage.PICKUP_WITNESS,),
        ),
        NativeDucRule(
            identity="byzantine-relic-control-return",
            order=relic_base + 2,
            facts=(
                parse_expression("(goal byzantine-relic-control-state 2)", SourceLocation(1)),
                parse_expression("(unit-type-count-total 286 >= 1)", SourceLocation(1)),
                parse_expression("(building-type-count-total 104 >= 1)", SourceLocation(1)),
                parse_expression(
                    "(up-timer-status byzantine-relic-control-timer c:== timer-disabled)",
                    SourceLocation(1),
                ),
            ),
            actions=(
                parse_expression("(up-full-reset-search)", SourceLocation(1)),
                parse_expression("(up-find-local c: 104 c: 1)", SourceLocation(1)),
                parse_expression("(up-set-target-object search-local c: 0)", SourceLocation(1)),
                parse_expression("(up-find-local c: 286 c: 1)", SourceLocation(1)),
                parse_expression(
                    "(up-target-objects 0 0 -1 stance-defensive)",
                    SourceLocation(1),
                ),
            ),
            lifecycle=(NativeDucLifecycleStage.RETURN,),
        ),
        NativeDucRule(
            identity="byzantine-relic-control-release-witness",
            order=relic_base + 3,
            facts=(
                parse_expression("(goal byzantine-relic-control-state 2)", SourceLocation(1)),
                parse_expression("(up-gaia-type-count-total c: 285 == 0)", SourceLocation(1)),
            ),
            actions=(
                parse_expression("(up-full-reset-search)", SourceLocation(1)),
            ),
            lifecycle=(NativeDucLifecycleStage.RELEASE_WITNESS,),
        ),
        NativeDucRule(
            identity="byzantine-relic-control-recovery",
            order=relic_base + 4,
            facts=(
                parse_expression("(goal byzantine-relic-control-state 2)", SourceLocation(1)),
                parse_expression("(up-gaia-type-count-total c: 285 >= 1)", SourceLocation(1)),
            ),
            actions=(
                parse_expression("(up-full-reset-search)", SourceLocation(1)),
            ),
            lifecycle=(NativeDucLifecycleStage.RECOVERY,),
        ),
    )
    return NativeDucPlan(
        rules=tuple((*rules, *lifecycle_rules)),
        output_requests=tuple(outputs),
    )


def _byzantine_attack_phase_request(profile_id: str):
    from ..runtime_binding import GoalSlotRequest
    from .model import GoalRole, SemanticId, StorageRequestId

    owner = SemanticId(profile_id, "byzantine-attack-phase")
    return GoalSlotRequest(
        StorageRequestId(owner, "byzantine-attack-phase"),
        role=GoalRole.PERSISTENT_STATE,
    )


def _byzantine_attack_phase_request(profile_id: str):
    from ..runtime_binding import GoalSlotRequest
    from .model import GoalRole, SemanticId, StorageRequestId

    owner = SemanticId(profile_id, "byzantine-attack-phase")
    return GoalSlotRequest(
        StorageRequestId(owner, "byzantine-attack-phase"),
        role=GoalRole.PERSISTENT_STATE,
    )


def _default_byzantine_attack_plan(profile_id: str) -> "NativeAttackLifecyclePlan":
    """Default Castle-age Byzantine attack issue actuator gated by lifecycle phase."""

    from ..semantic.analyzer import parse_expression
    from .native_attack import (
        AttackLifecycleObservation,
        NativeAttackGoalInputRequest,
        NativeAttackLifecyclePlan,
        NativeAttackRule,
    )

    lifecycle = (
        AttackLifecycleObservation.ADMISSION_REQUIRED,
        AttackLifecycleObservation.ISSUE,
        AttackLifecycleObservation.COMPLETION_UNOBSERVED,
        AttackLifecycleObservation.REASSESS_REQUIRED,
    )
    phase_request = _byzantine_attack_phase_request(profile_id)
    common_facts = (
        parse_expression("(current-age == castle-age)", SourceLocation(1)),
        parse_expression("(up-compare-sn 227 >= 75)", SourceLocation(1)),
        parse_expression(
            "(or (goal byzantine-army-role-state byzantine-army-role-committed) "
            "(goal byzantine-army-role-state byzantine-army-role-raid-split))",
            SourceLocation(1),
        ),
    )
    return NativeAttackLifecyclePlan(
        rules=(
            NativeAttackRule(
                identity="byzantine-castle-attack-now-cataphract",
                order=100,
                facts=(
                    *common_facts,
                    parse_expression(
                        "(unit-type-count cataphract >= 2)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        "(goal byzantine-attack-phase 2)",
                        SourceLocation(1),
                    ),
                ),
                actions=(parse_expression("(attack-now)", SourceLocation(1)),),
                lifecycle=lifecycle,
            ),
            NativeAttackRule(
                identity="byzantine-castle-attack-now-knight",
                order=110,
                facts=(
                    *common_facts,
                    parse_expression(
                        "(unit-type-count knight >= 3)",
                        SourceLocation(1),
                    ),
                    parse_expression(
                        "(goal byzantine-attack-phase 4)",
                        SourceLocation(1),
                    ),
                ),
                actions=(parse_expression("(attack-now)", SourceLocation(1)),),
                lifecycle=lifecycle,
            ),
        ),
        goal_input_requests=(
            NativeAttackGoalInputRequest(
                identity="byzantine-attack-phase-cataphract-input",
                rule_identity="byzantine-castle-attack-now-cataphract",
                section="FACT",
                expression_index=4,
                argument_index=0,
                request=phase_request,
            ),
            NativeAttackGoalInputRequest(
                identity="byzantine-attack-phase-knight-input",
                rule_identity="byzantine-castle-attack-now-knight",
                section="FACT",
                expression_index=4,
                argument_index=0,
                request=phase_request,
            ),
        ),
    )

def _byzantine_strategic_number_modes() -> tuple[StrategicNumberMode, ...]:
    return (
        StrategicNumberMode(
            "civilian-builders-dark",
            native_strategic_number_id=4,
            value=3,
            minimum_age=Age.DARK,
            maximum_age=Age.DARK,
        ),
        StrategicNumberMode(
            "civilian-builders-feudal",
            native_strategic_number_id=4,
            value=5,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.FEUDAL,
        ),
        StrategicNumberMode(
            "civilian-builders-castle",
            native_strategic_number_id=4,
            value=8,
            minimum_age=Age.CASTLE,
            maximum_age=Age.CASTLE,
        ),
        StrategicNumberMode(
            "civilian-builders-imperial",
            native_strategic_number_id=4,
            value=12,
            minimum_age=Age.IMPERIAL,
            maximum_age=Age.IMPERIAL,
        ),
        StrategicNumberMode(
            "attack-allocation-flush",
            native_strategic_number_id=227,
            value=50,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.CASTLE,
            postures=(StrategyPosture.FLUSH,),
        ),
        StrategicNumberMode(
            "attack-allocation-rush",
            native_strategic_number_id=227,
            value=50,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.CASTLE,
            postures=(StrategyPosture.RUSH,),
        ),
        StrategicNumberMode(
            "attack-allocation-boom",
            native_strategic_number_id=227,
            value=75,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.CASTLE,
            postures=(StrategyPosture.BOOM,),
        ),
        StrategicNumberMode(
            "attack-allocation-castle-power",
            native_strategic_number_id=227,
            value=75,
            minimum_age=Age.FEUDAL,
            maximum_age=Age.CASTLE,
            postures=(StrategyPosture.CASTLE_POWER,),
        ),
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


def _byzantine_counter_demands() -> tuple[StrategicDemandSpec, ...]:
    return (
        StrategicDemandSpec(
            identity="expected-mounted-spears",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.SUPPORT,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Enemy stable commitment without confirmed scout mass justifies a small predicted anti-mounted floor",
                    observation_ref="enemy-mounted-commitment-feudal",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Feudal age admits the predicted anti-mounted floor",
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
                    "(and (players-building-type-count any-enemy stable >= 1) (players-unit-type-count any-enemy scout-cavalry-line < 3))",
                    "(can-train-with-escrow spearman-line)",
                    "(unit-type-count-total spearman-line < 2)",
                ),
                action="(train spearman-line)",
                witness="(unit-type-count spearman-line >= 2)",
                release="(unit-type-count spearman-line >= 2)",
            ),
        ),
        StrategicDemandSpec(
            identity="expected-ranged-skirmishers",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.SUPPORT,
            reason=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Enemy archery commitment without confirmed archer mass justifies a small predicted anti-ranged floor",
                    observation_ref="enemy-ranged-commitment-feudal",
                ),
            ),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Feudal age admits the predicted anti-ranged floor",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "skirmisher-line",
                BuildingId(87),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "skirmisher-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(and (players-building-type-count any-enemy archery-range >= 1) (players-unit-type-count any-enemy archer-line < 3))",
                    "(can-train-with-escrow skirmisher-line)",
                    "(unit-type-count-total skirmisher-line < 2)",
                ),
                action="(train skirmisher-line)",
                witness="(unit-type-count skirmisher-line >= 2)",
                release="(unit-type-count skirmisher-line >= 2)",
            ),
        ),
        StrategicDemandSpec(
            identity="counter-mounted-spears",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.DEFENSE,
            reason=(),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Feudal anti-mounted counter demand is admissible",
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
                minimum=4,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-train-with-escrow spearman-line)",
                    "(unit-type-count-total spearman-line < 4)",
                ),
                action="(train spearman-line)",
                witness="(unit-type-count spearman-line >= 4)",
                release="(unit-type-count spearman-line >= 4)",
            ),
        ),
        StrategicDemandSpec(
            identity="counter-ranged-skirmishers",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.FLUSH,
            priority=StrategicPriority.DEFENSE,
            reason=(),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Feudal anti-ranged counter demand is admissible",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "skirmisher-line",
                BuildingId(87),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "skirmisher-line",
                minimum=4,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= feudal-age)",
                    "(can-train-with-escrow skirmisher-line)",
                    "(unit-type-count-total skirmisher-line < 4)",
                ),
                action="(train skirmisher-line)",
                witness="(unit-type-count skirmisher-line >= 4)",
                release="(unit-type-count skirmisher-line >= 4)",
            ),
        ),
        StrategicDemandSpec(
            identity="counter-castle-camels",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.DEFENSE,
            reason=(),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle anti-mounted counter demand is admissible",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "camel-rider-line",
                BuildingId(101),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "camel-rider-line",
                minimum=3,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(can-train-with-escrow 329)",
                    "(unit-type-count-total camel-rider-line < 3)",
                ),
                action="(train 329)",
                witness="(unit-type-count 329 >= 3)",
                release="(unit-type-count 329 >= 3)",
            ),
        ),
        StrategicDemandSpec(
            identity="counter-castle-cataphracts",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.DEFENSE,
            reason=(),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle anti-infantry counter demand is admissible",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "cataphract-line",
                BuildingId(82),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "cataphract-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(can-train-with-escrow cataphract)",
                    "(unit-type-count-total cataphract-line < 2)",
                ),
                action="(train cataphract)",
                witness="(unit-type-count cataphract >= 2)",
                release="(unit-type-count cataphract >= 2)",
            ),
        ),
        StrategicDemandSpec(
            identity="counter-castle-siege-response",
            owner="defense",
            production_arbitration_group="defense",
            posture=StrategyPosture.CASTLE_POWER,
            priority=StrategicPriority.DEFENSE,
            reason=(),
            admissibility=(
                StrategicEvidence(
                    StrategicEvidenceKind.PERSISTENT,
                    None,
                    "Castle anti-siege counter demand is admissible",
                    observation_ref="current-feudal-age",
                ),
            ),
            invalidation=(),
            capability_intent=CapabilityIntent(
                CapabilityIntentKind.TRAIN,
                "unit-line",
                "knight-line",
                BuildingId(101),
            ),
            target=StrategicTarget(
                StrategicTargetKind.CURRENT_QUEUED,
                "unit-line",
                "knight-line",
                minimum=2,
            ),
            opportunity_cost=None,
            execution=ExecutionDemandTemplate(
                requirements=(
                    "(current-age >= castle-age)",
                    "(can-train-with-escrow knight-line)",
                    "(unit-type-count-total knight-line < 2)",
                ),
                action="(train knight-line)",
                witness="(unit-type-count knight-line >= 2)",
                release="(unit-type-count knight-line >= 2)",
            ),
        ),
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
    from ..semantic.policy_recipe import default_byzantine_policy_recipes
    from .counter_strategy import default_byzantine_counter_packages

    counter_demands = _byzantine_counter_demands()
    return replace(
        profile,
        demands=(*demands, *counter_demands),
        transitions=transitions,
        provenance=(*profile.provenance, *meta_provenance),
        capability_observations=_byzantine_capability_observations(effective),
        strategic_number_modes=_byzantine_strategic_number_modes(),
        policy_recipes=default_byzantine_policy_recipes(),
        counter_packages=default_byzantine_counter_packages(effective),
        attack_plan=_default_byzantine_attack_plan(profile.profile_id),
        duc_plan=_default_byzantine_duc_plan(profile.profile_id),
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

def build_byzantine_stock_strategy(
    effective: EffectiveCivData,
    *,
    include_water_continuity: bool = True,
) -> StrategyProfile:
    """Return the broader community-derived Byzantine stock strategy profile."""
    from .community_strategy_packs import build_byzantine_stock_strategy as _build

    return _build(
        effective,
        include_water_continuity=include_water_continuity,
    )


def build_byzantine_strategy(
    effective: EffectiveCivData,
    *,
    include_water_continuity: bool = True,
) -> StrategyProfile:
    """Canonical Byzantine strategy entry point for normal compiler clients."""
    return build_byzantine_stock_strategy(
        effective,
        include_water_continuity=include_water_continuity,
    )
