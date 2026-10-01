"""Downstream client strategic evidence binding and posture evaluation."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Iterable, Mapping

from ..ast import Expression
from ..primitives import PrimitiveRegistry, default_de_registry
from ..primitives.native_schema import NativeParameterSpec
from ..semantic.community_engine import CapabilityTransition, classify_capability_transition
from .civ_profile import EffectiveCivData
from .counter_strategy import (
    CompositionUpgradeRequirement,
    CounterPackage,
    CounterThreatClass,
)
from .game_data import canonical_fingerprint
from .strategy import (
    CapabilityIntentKind,
    StrategicCapabilityObservation,
    StrategicCapabilityObservationKind,
    StrategicDemandSpec,
    StrategicEvidence,
    StrategicObservationSpec,
    StrategicEvidenceKind,
    StrategicEvidenceSource,
    StrategyPosture,
    StrategyProfile,
)
from .versioning import EvidenceRef


class StrategicObservationType(str, Enum):
    CURRENT_AGE = "CURRENT_AGE"
    RESOURCE_AMOUNT = "RESOURCE_AMOUNT"
    BUILDING_COUNT = "BUILDING_COUNT"
    UNIT_CURRENT_COUNT = "UNIT_CURRENT_COUNT"
    UNIT_QUEUED_COUNT = "UNIT_QUEUED_COUNT"
    UNIT_CURRENT_PLUS_QUEUED = "UNIT_CURRENT_PLUS_QUEUED"
    ENEMY_UNIT_COUNT = "ENEMY_UNIT_COUNT"
    ENEMY_BUILDING_COUNT = "ENEMY_BUILDING_COUNT"
    ENEMY_COMPOSITION = "ENEMY_COMPOSITION"
    MAP_PROFILE = "MAP_PROFILE"
    OPENING_STATE = "OPENING_STATE"
    PRESSURE_STATE = "PRESSURE_STATE"
    CAPABILITY_STATE = "CAPABILITY_STATE"
    UNIT_CAPABILITY = "UNIT_CAPABILITY"
    RESEARCH_STATE = "RESEARCH_STATE"
    DUC_SEARCH_AVAILABILITY = "DUC_SEARCH_AVAILABILITY"
    ESCROW_CAPABILITY = "ESCROW_CAPABILITY"
    PERSISTENT_CONTROL_STATE = "PERSISTENT_CONTROL_STATE"
    PRODUCTION_QUEUE_CAPACITY_CONTROL = "PRODUCTION_QUEUE_CAPACITY_CONTROL"
    EXPLORATION_GROUP_CONTROL = "EXPLORATION_GROUP_CONTROL"
    BOAT_EXPLORATION_GROUP_CONTROL = "BOAT_EXPLORATION_GROUP_CONTROL"
    TOTAL_EXPLORER_CAP = "TOTAL_EXPLORER_CAP"
    CIVILIAN_EXPLORER_CAP = "CIVILIAN_EXPLORER_CAP"
    ATTACK_GROUP_CONTROL = "ATTACK_GROUP_CONTROL"
    ATTACK_SOLDIER_PERCENT_CONTROL = "ATTACK_SOLDIER_PERCENT_CONTROL"
    TOWN_SIZE_CONTROL = "TOWN_SIZE_CONTROL"
    TRAIN_PROVIDER_READINESS = "TRAIN_PROVIDER_READINESS"
    TIMING = "TIMING"


class EvidenceTruth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class StrategicDemandRuntimeState(str, Enum):
    STRATEGIC_INACTIVE = "STRATEGIC_INACTIVE"
    STRATEGIC_ACTIVE_EXECUTABLE = "STRATEGIC_ACTIVE_EXECUTABLE"
    STRATEGIC_ACTIVE_BLOCKED = "STRATEGIC_ACTIVE_BLOCKED"
    STRATEGIC_INVALIDATED = "STRATEGIC_INVALIDATED"
    STRATEGIC_COMPLETE = "STRATEGIC_COMPLETE"


class OpportunityCostRuntimeState(str, Enum):
    PROTECTED_ACTIVE = "PROTECTED_ACTIVE"
    OVERRIDDEN = "OVERRIDDEN"
    RELEASED = "RELEASED"


class CounterArbitrationMode(str, Enum):
    NONE = "NONE"
    SINGLE = "SINGLE"
    MIXED = "MIXED"


class CompositionUpgradeReadiness(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CompositionUpgradeRequirementState:
    requirement: CompositionUpgradeRequirement
    truth: EvidenceTruth


@dataclass(frozen=True)
class CompositionUpgradeReadinessState:
    status: CompositionUpgradeReadiness
    selected_packages: tuple[str, ...]
    requirements: tuple[CompositionUpgradeRequirementState, ...]


def aggregate_composition_upgrade_readiness(
    selected_packages: tuple[str, ...],
    package_requirements: Mapping[str, tuple[CompositionUpgradeRequirement, ...]],
    requirement_truths: Mapping[str, EvidenceTruth],
) -> CompositionUpgradeReadinessState:
    """Aggregate selected-package upgrade witnesses using deterministic tri-state semantics.

    Selected package order does not affect requirement ordering. Requirements are
    deduplicated by semantic identity; conflicting definitions are structural
    errors, while absent runtime evidence is UNKNOWN and therefore fail-closed.
    """
    canonical_packages = tuple(sorted(set(selected_packages)))
    unknown_packages = sorted(
        package_id for package_id in canonical_packages if package_id not in package_requirements
    )
    if unknown_packages:
        raise ValueError(
            "upgrade readiness selected unknown package(s): "
            + ", ".join(unknown_packages)
        )

    union: dict[str, CompositionUpgradeRequirement] = {}
    for package_id in canonical_packages:
        for requirement in package_requirements[package_id]:
            prior = union.get(requirement.identity)
            if prior is None:
                union[requirement.identity] = requirement
                continue
            if (
                prior.observation_ref != requirement.observation_ref
                or prior.technology_id != requirement.technology_id
            ):
                raise ValueError(
                    f"conflicting composition upgrade requirement '{requirement.identity}'"
                )

    ordered_requirements = tuple(
        sorted(
            union.values(),
            key=lambda item: (
                item.technology_id,
                item.identity,
                item.observation_ref,
            ),
        )
    )
    states = tuple(
        CompositionUpgradeRequirementState(
            requirement=requirement,
            truth=requirement_truths.get(requirement.identity, EvidenceTruth.UNKNOWN),
        )
        for requirement in ordered_requirements
    )

    truths = tuple(item.truth for item in states)
    if any(truth is EvidenceTruth.UNKNOWN for truth in truths):
        status = CompositionUpgradeReadiness.UNKNOWN
    elif any(truth is EvidenceTruth.FALSE for truth in truths):
        status = CompositionUpgradeReadiness.BLOCKED
    else:
        status = CompositionUpgradeReadiness.READY

    return CompositionUpgradeReadinessState(
        status=status,
        selected_packages=canonical_packages,
        requirements=states,
    )


def evaluate_composition_upgrade_readiness(
    profile: StrategyProfile,
    effective: EffectiveCivData,
    snapshot: RuntimeObservationSnapshot,
    registry: PrimitiveRegistry,
    arbitration: CounterArbitrationDecision,
) -> CompositionUpgradeReadinessState:
    """Evaluate research-completion witnesses for the arbitrated package union."""
    packages = {package.identity: package for package in profile.counter_packages}
    selected = arbitration.active_packages
    package_requirements = {
        package_id: packages[package_id].upgrade_requirements
        for package_id in selected
    }
    truths: dict[str, EvidenceTruth] = {}
    for requirements in package_requirements.values():
        for requirement in requirements:
            if requirement.identity in truths:
                continue
            evidence = StrategicEvidence(
                kind=StrategicEvidenceKind.EXECUTION,
                expression=None,
                label=f"composition-upgrade:{requirement.identity}",
                source=StrategicEvidenceSource.AUTHORING,
                observation_ref=requirement.observation_ref,
            )
            binding = bind_observation_reference(
                evidence,
                profile,
                effective,
                registry,
            )
            truths[requirement.identity] = evaluate_binding(binding, snapshot)
    return aggregate_composition_upgrade_readiness(
        selected,
        package_requirements,
        truths,
    )


class ReassessmentReason(str, Enum):
    POSTURE_CHANGE = "POSTURE_CHANGE"
    DEMAND_ACTIVATION = "DEMAND_ACTIVATION"
    COUNTER_PACKAGE_CHANGE = "COUNTER_PACKAGE_CHANGE"
    DEMAND_INVALIDATION = "DEMAND_INVALIDATION"
    CAPABILITY_COMPLETION = "CAPABILITY_COMPLETION"
    CAPABILITY_LOSS = "CAPABILITY_LOSS"
    CAPABILITY_RECOVERY = "CAPABILITY_RECOVERY"
    UPGRADE_READINESS_CHANGE = "UPGRADE_READINESS_CHANGE"
    ENEMY_COMPOSITION_CHANGE = "ENEMY_COMPOSITION_CHANGE"
    AGE_TRANSITION = "AGE_TRANSITION"
    MAP_OPENING_CHANGE = "MAP_OPENING_CHANGE"


@dataclass(frozen=True)
class StrategicObservation:
    identity: str
    semantic_type: StrategicObservationType
    primitive: str
    native_parameter_contracts: tuple[NativeParameterSpec, ...]
    expression: Expression
    evidence_class: StrategicEvidenceKind
    evidence_source: StrategicEvidenceSource
    provenance: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class StrategicPredicate:
    expression: Expression
    observations: tuple[StrategicObservation, ...]
    timing_primitives: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObservationReferenceBinding:
    reference: str
    observation: StrategicObservationSpec


@dataclass(frozen=True)
class StrategicEvidenceBinding:
    evidence: StrategicEvidence
    predicate: StrategicPredicate
    fingerprint: str
    observation_reference: ObservationReferenceBinding | None = None

    @property
    def observations(self) -> tuple[StrategicObservation, ...]:
        return self.predicate.observations


@dataclass(frozen=True)
class RuntimeObservationSnapshot:
    fact_results: tuple[tuple[str, bool], ...] = ()
    completed_demands: frozenset[str] = frozenset()
    previous_posture: StrategyPosture | None = None
    previous_demand_states: tuple[tuple[str, StrategicDemandRuntimeState], ...] = ()
    previous_counter_package_states: tuple[tuple[str, EvidenceTruth], ...] = ()
    previous_capability_observations: tuple[tuple[str, bool | None], ...] = ()
    previous_composition_upgrade_readiness: CompositionUpgradeReadinessState | None = None
    reassessment_signals: frozenset[ReassessmentReason] = frozenset()

    def result_for(self, expression: Expression) -> EvidenceTruth:
        for key, result in self.fact_results:
            if key == expression.source:
                return EvidenceTruth.TRUE if result else EvidenceTruth.FALSE
        return EvidenceTruth.UNKNOWN


@dataclass(frozen=True)
class CounterPackageRuntimeState:
    identity: str
    threat_class: CounterThreatClass
    truth: EvidenceTruth
    priority: int
    demand_identities: tuple[str, ...]
    policy_recipe_identity: str | None = None


@dataclass(frozen=True)
class CounterArbitrationDecision:
    mode: CounterArbitrationMode
    primary_package: str | None
    supporting_packages: tuple[str, ...]
    suppressed_packages: tuple[str, ...]
    active_threat_classes: tuple[CounterThreatClass, ...]

    @property
    def active_packages(self) -> tuple[str, ...]:
        packages = (
            (self.primary_package,) if self.primary_package is not None else ()
        )
        return packages + self.supporting_packages


@dataclass(frozen=True)
class StrategyRuntimeState:
    current_posture: StrategyPosture | None
    previous_posture: StrategyPosture | None
    demand_states: tuple[tuple[str, StrategicDemandRuntimeState], ...]
    opportunity_cost_states: tuple[tuple[str, OpportunityCostRuntimeState], ...]
    evaluated_evidence: tuple[tuple[str, EvidenceTruth], ...]
    active_strategic_demands: tuple[str, ...]
    strategically_blocked_demands: tuple[str, ...]
    strategically_invalidated_demands: tuple[str, ...]
    strategically_complete_demands: tuple[str, ...]
    reassessment_reasons: tuple[ReassessmentReason, ...]
    runtime_storage_requests: tuple[object, ...]
    fingerprint: str
    counter_package_states: tuple[CounterPackageRuntimeState, ...] = ()
    counter_arbitration: CounterArbitrationDecision | None = None
    _owners: tuple[tuple[str, str], ...] = ()
    evaluated_meta_evidence: tuple[
        tuple[str, EvidenceTruth, tuple[EvidenceRef, ...]],
        ...
    ] = ()
    evaluated_capability_observations: tuple[tuple[str, EvidenceTruth], ...] = ()
    capability_transitions: tuple[tuple[str, CapabilityTransition], ...] = ()
    composition_upgrade_readiness: CompositionUpgradeReadinessState | None = None

    @property
    def active_or_blocked_demands(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.active_strategic_demands) | set(self.strategically_blocked_demands)))

    def demand_state(self, identity: str) -> StrategicDemandRuntimeState:
        for key, state in self.demand_states:
            if key == identity:
                return state
        raise KeyError(identity)

    @property
    def active_counter_packages(self) -> tuple[str, ...]:
        if self.counter_arbitration is not None:
            return self.counter_arbitration.active_packages
        return tuple(
            item.identity
            for item in self.counter_package_states
            if item.truth is EvidenceTruth.TRUE
        )

    @property
    def counter_package_primary(self) -> str | None:
        return self.counter_arbitration.primary_package if self.counter_arbitration else None

    def counter_package_state(self, identity: str) -> CounterPackageRuntimeState:
        for item in self.counter_package_states:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def strategic_owner(self, identity: str) -> str:
        for key, owner in self._owners:
            if key == identity:
                return owner
        raise KeyError(identity)

    def opportunity_cost_state(self, identity: str) -> OpportunityCostRuntimeState | None:
        for key, state in self.opportunity_cost_states:
            if key == identity:
                return state
        return None


def bind_strategic_capability_observation(
    observation: StrategicCapabilityObservation,
    effective: EffectiveCivData,
    registry: PrimitiveRegistry | None = None,
) -> StrategicEvidenceBinding:
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
    if status.value != "VERIFIED":
        raise ValueError(
            f"strategic capability observation '{observation.identity}' requires "
            f"factual status VERIFIED for unit {unit_id}; status is {status.value}"
        )
    evidence = StrategicEvidence(
        StrategicEvidenceKind.EXECUTION,
        observation.expression,
        observation.identity,
        source=observation.source,
        provenance=observation.provenance,
    )
    binding = bind_strategic_evidence(evidence, effective, registry)
    unit = effective.unit(unit_id)
    aliases = {
        str(unit_id),
        unit.name.lower().replace(" ", "-"),
    }
    observation_expression = binding.observations[0].expression
    if observation.observation_kind is StrategicCapabilityObservationKind.EXECUTION_FEASIBILITY:
        if not observation_expression.args or str(observation_expression.args[0]).lower() not in aliases:
            raise ValueError(
                f"strategic capability observation '{observation.identity}' does not bind its declared unit"
            )
        if not any(
            item.semantic_type is StrategicObservationType.UNIT_CAPABILITY
            for item in binding.observations
        ):
            raise ValueError(
                f"strategic capability observation '{observation.identity}' did not bind to UNIT_CAPABILITY"
            )
    elif observation.observation_kind is StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE:
        if not any(
            item.semantic_type is StrategicObservationType.BUILDING_COUNT
            for item in binding.observations
        ):
            raise ValueError(
                f"provider-state capability observation '{observation.identity}' did not bind to BUILDING_COUNT"
            )
    else:
        raise ValueError(
            f"strategic capability observation '{observation.identity}' has unsupported observation kind "
            f"'{observation.observation_kind.value}'"
        )
    return binding


def bind_observation_reference(
    evidence: StrategicEvidence,
    profile: StrategyProfile,
    effective: EffectiveCivData,
    registry: PrimitiveRegistry | None = None,
) -> StrategicEvidenceBinding:
    reference = evidence.observation_ref
    if not reference:
        raise ValueError(
            f"strategic evidence '{evidence.label}' requires an observation reference"
        )
    try:
        observation = profile.observation(reference)
    except KeyError as exc:
        raise ValueError(
            f"unknown strategic observation reference '{reference}'"
        ) from exc
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
    if evidence.expression is not None:
        raise ValueError(
            f"strategic evidence '{evidence.label}' must not override its native observation expression"
        )
    resolved = replace(
        evidence,
        expression=observation.expression,
        observation_ref=None,
    )
    binding = bind_strategic_evidence(resolved, effective, registry)
    reference_binding = ObservationReferenceBinding(reference, observation)
    return replace(
        binding,
        observation_reference=reference_binding,
        fingerprint=canonical_fingerprint(
            {
                "binding": binding.fingerprint,
                "observation_reference": reference_binding,
            }
        ),
    )


_OBSERVATION_PRIMITIVES: dict[str, StrategicObservationType] = {
    "current-age": StrategicObservationType.CURRENT_AGE,
    "food-amount": StrategicObservationType.RESOURCE_AMOUNT,
    "wood-amount": StrategicObservationType.RESOURCE_AMOUNT,
    "gold-amount": StrategicObservationType.RESOURCE_AMOUNT,
    "stone-amount": StrategicObservationType.RESOURCE_AMOUNT,
    "building-type-count": StrategicObservationType.BUILDING_COUNT,
    "building-type-count-total": StrategicObservationType.BUILDING_COUNT,
    "unit-type-count": StrategicObservationType.UNIT_CURRENT_COUNT,
    "unit-type-count-total": StrategicObservationType.UNIT_CURRENT_PLUS_QUEUED,
    "players-unit-type-count": StrategicObservationType.ENEMY_UNIT_COUNT,
    "players-building-type-count": StrategicObservationType.ENEMY_BUILDING_COUNT,
    "research-completed": StrategicObservationType.RESEARCH_STATE,
    "research-available": StrategicObservationType.RESEARCH_STATE,
    "up-can-search": StrategicObservationType.DUC_SEARCH_AVAILABILITY,
    "up-compare-sn": StrategicObservationType.PERSISTENT_CONTROL_STATE,
    "up-train-site-ready": StrategicObservationType.TRAIN_PROVIDER_READINESS,
    "building-available": StrategicObservationType.CAPABILITY_STATE,
    "can-afford-building": StrategicObservationType.CAPABILITY_STATE,
    "can-afford-building-with-escrow": StrategicObservationType.ESCROW_CAPABILITY,
    "can-afford-unit": StrategicObservationType.CAPABILITY_STATE,
    "can-afford-unit-with-escrow": StrategicObservationType.ESCROW_CAPABILITY,
    "can-afford-research": StrategicObservationType.CAPABILITY_STATE,
    "can-afford-research-with-escrow": StrategicObservationType.ESCROW_CAPABILITY,
    "can-build": StrategicObservationType.CAPABILITY_STATE,
    "can-build-with-escrow": StrategicObservationType.ESCROW_CAPABILITY,
    "can-train": StrategicObservationType.UNIT_CAPABILITY,
    "can-train-with-escrow": StrategicObservationType.UNIT_CAPABILITY,
    "can-research": StrategicObservationType.CAPABILITY_STATE,
    "can-research-with-escrow": StrategicObservationType.ESCROW_CAPABILITY,
    "dropsite-min-distance": StrategicObservationType.MAP_PROFILE,
    "game-time": StrategicObservationType.TIMING,
}
_COMPARE_OPS = {"==", "!=", ">", ">=", "<", "<="}
_PLAYER_VALUES = {
    "self",
    "focus-player",
    "target-player",
    "any",
    "every",
    "any-enemy",
    "every-enemy",
}


def _lookup_token(token: str, values: Iterable[str]) -> bool:
    return token.lower() in {value.lower() for value in values}


def _building_tokens(effective: EffectiveCivData) -> set[str]:
    return {
        token
        for item in effective.buildings
        for token in (str(int(item.id)), item.name.lower().replace(" ", "-"))
    }


def _unit_tokens(effective: EffectiveCivData) -> set[str]:
    tokens = {
        token
        for item in effective.units
        for token in (str(int(item.id)), item.name.lower().replace(" ", "-"))
    }
    tokens.update(str(item.id).lower() for item in effective.unit_lines)
    return tokens


def _tech_tokens(effective: EffectiveCivData) -> set[str]:
    return {
        token
        for item in effective.technologies
        for token in (
            str(int(item.id)),
            item.name.lower().replace(" ", "-"),
            f"ri-{item.name.lower().replace(' ', '-')}",
        )
    }


def _validate_native_operand(
    parameter: NativeParameterSpec,
    token: object,
    effective: EffectiveCivData,
) -> None:
    if not isinstance(token, str):
        raise ValueError(
            f"native parameter family '{parameter.name or parameter.type}' received non-string operand"
        )
    value = token.lower()
    family = parameter.name.lower() or parameter.type.lower()

    if family == "searchsource":
        if value not in {"search-local", "search-remote"}:
            raise ValueError(
                f"native parameter family SearchSource does not accept '{token}'"
            )
        return
    if family == "compareop":
        if value not in _COMPARE_OPS:
            raise ValueError(f"native parameter family compareOp does not accept '{token}'")
        return
    if family == "age":
        if value not in {"dark-age", "feudal-age", "castle-age", "imperial-age"}:
            raise ValueError(
                f"native parameter family Age does not accept '{token}': "
                f"unresolved Age '{token}'"
            )
        return
    if family == "buildingid":
        if not _lookup_token(token, _building_tokens(effective)):
            raise ValueError(f"unresolved BuildingId '{token}'")
        return
    if family == "unitid":
        if not _lookup_token(token, _unit_tokens(effective)):
            raise ValueError(f"unresolved UnitId '{token}'")
        return
    if family == "techid":
        if not _lookup_token(token, _tech_tokens(effective)) and token not in {
            "ri-logistica",
            "ri-elite-varangian-guard",
        }:
            raise ValueError(f"unresolved TechId '{token}'")
        return
    if family == "resourcetype" or family == "resourceid":
        if value not in {"food", "wood", "gold", "stone"}:
            raise ValueError(f"native parameter family ResourceId does not accept '{token}'")
        return
    if family == "playernumber":
        if value in _PLAYER_VALUES:
            return
        try:
            int(value)
        except ValueError as exc:
            raise ValueError(
                f"native parameter family PlayerNumber does not accept '{token}'"
            ) from exc
        return
    if family == "value":
        try:
            int(value)
        except ValueError as exc:
            raise ValueError(
                f"native parameter family Value does not accept '{token}'"
            ) from exc
        return


def _validate_expression(
    expression: Expression,
    effective: EffectiveCivData,
    registry: PrimitiveRegistry,
    evidence: StrategicEvidence,
    observations: list[StrategicObservation],
    timing_primitives: list[str],
    ordinal: list[int],
) -> None:
    logical_arity = {"and": 2, "or": 2, "nand": 2, "nor": 2, "xor": 2, "xnor": 2, "not": 1}
    if expression.head in logical_arity:
        expected = logical_arity[expression.head]
        if len(expression.args) != expected:
            raise ValueError(f"logical operator '{expression.head}' requires {expected} operands")
        for child in expression.args:
            if not isinstance(child, Expression):
                raise ValueError(f"logical operator '{expression.head}' needs expression operands")
            _validate_expression(
                child, effective, registry, evidence, observations, timing_primitives, ordinal
            )
        return

    primitive = registry.get(expression.head)
    native = registry.native(expression.head)

    if primitive is None and native is not None and native.command_type in {"Action", "Fact/Action"}:
        raise ValueError(f"unsupported strategic native primitive '{expression.head}'")
    if primitive is None and expression.head == "up-can-search":
        registry.bind_duc_command(expression.head)
        registry.validate_native_signature(expression.head, len(expression.args))
        semantic_type = StrategicObservationType.DUC_SEARCH_AVAILABILITY
        for parameter, argument in zip(native.parameters, expression.args):
            _validate_native_operand(parameter, argument, effective)
        ordinal[0] += 1
        observations.append(
            StrategicObservation(
                identity=f"{evidence.label}:observation:{ordinal[0]}",
                semantic_type=semantic_type,
                primitive=expression.head,
                native_parameter_contracts=native.parameters,
                expression=expression,
                evidence_class=evidence.kind,
                evidence_source=evidence.source,
                provenance=evidence.provenance,
            )
        )
        return

    if primitive is None or native is None:
        raise ValueError(f"unsupported strategic native primitive '{expression.head}'")
    registry.validate_native_signature(expression.head, len(expression.args))
    registry.validate_adapter_contract(primitive)

    if primitive.kind == "ACTION":
        raise ValueError(f"strategic evidence cannot use action primitive '{expression.head}'")

    semantic_type = _OBSERVATION_PRIMITIVES.get(expression.head)
    if semantic_type is None:
        raise ValueError(f"native primitive '{expression.head}' has no strategic observation binding")

    if expression.head == "up-train-site-ready":
        if len(expression.args) != 2 or str(expression.args[0]) != "c:":
            raise ValueError(
                "up-train-site-ready requires literal c: typeOp"
            )

    if expression.head == "up-compare-sn":
        try:
            sn_id = int(str(expression.args[0]))
        except (IndexError, ValueError, TypeError):
            sn_id = None
        if sn_id == 264:
            compare_operator = str(expression.args[1]).removeprefix("c:")
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if compare_operator != "==" or configured_value is None or not 0 <= configured_value <= 15:
                raise ValueError(
                    "SN 264 sn-enable-training-queue requires equality against a value in 0..15"
                )
            semantic_type = StrategicObservationType.PRODUCTION_QUEUE_CAPACITY_CONTROL
        elif sn_id == 42:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or configured_value < 0:
                raise ValueError(
                    "SN 42 sn-number-explore-groups requires a comparison value in 0..Max"
                )
            semantic_type = StrategicObservationType.EXPLORATION_GROUP_CONTROL
        elif sn_id == 61:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or configured_value < 0:
                raise ValueError(
                    "SN 61 sn-number-boat-explore-groups requires a comparison value in 0..Max"
                )
            semantic_type = StrategicObservationType.BOAT_EXPLORATION_GROUP_CONTROL
        elif sn_id == 18:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or configured_value < -1:
                raise ValueError(
                    "SN 18 sn-total-number-explorers requires a comparison value in -1..Max"
                )
            semantic_type = StrategicObservationType.TOTAL_EXPLORER_CAP
        elif sn_id == 3:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or configured_value < -1:
                raise ValueError(
                    "SN 3 sn-cap-civilian-explorers requires a comparison value in -1..Max"
                )
            semantic_type = StrategicObservationType.CIVILIAN_EXPLORER_CAP
        elif sn_id == 36:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or configured_value < 0:
                raise ValueError(
                    "SN 36 sn-number-attack-groups requires a comparison value in 0..Max"
                )
            semantic_type = StrategicObservationType.ATTACK_GROUP_CONTROL
        elif sn_id == 227:
            try:
                configured_value = int(str(expression.args[2]))
            except (IndexError, ValueError, TypeError):
                configured_value = None
            if configured_value is None or not 0 <= configured_value <= 100:
                raise ValueError(
                    "SN 227 sn-percent-attack-soldiers requires a comparison value in 0..100"
                )
            semantic_type = StrategicObservationType.ATTACK_SOLDIER_PERCENT_CONTROL
        elif sn_id == 74:
            semantic_type = StrategicObservationType.TOWN_SIZE_CONTROL

    if evidence.kind is StrategicEvidenceKind.PERSISTENT and primitive.role in {
        "ACTION",
        "FEASIBILITY",
        "TIMING",
    } and expression.head != "up-compare-sn":
        raise ValueError(
            f"persistent strategic evidence cannot be based on {primitive.role.lower()} primitive "
            f"'{expression.head}'"
        )
    if evidence.kind is not StrategicEvidenceKind.EXECUTION and primitive.role == "TIMING":
        raise ValueError(
            f"timing primitive '{expression.head}' cannot be promoted to strategic truth"
        )
    if evidence.kind is StrategicEvidenceKind.TIMING and primitive.role != "TIMING":
        raise ValueError(
            f"timing evidence '{evidence.label}' must use a timing primitive"
        )

    if expression.head == "up-compare-sn":
        try:
            sn_id = int(str(expression.args[0]))
        except (IndexError, ValueError, TypeError):
            sn_id = None
        if sn_id is None or not 0 <= sn_id <= 511:
            raise ValueError(
                f"up-compare-sn requires a numeric Strategic Number id in 0..511; got "
                f"'{expression.args[0] if expression.args else None}'"
            )
        compare_operator = str(expression.args[1]).removeprefix("c:")
        if compare_operator not in _COMPARE_OPS:
            raise ValueError(
                f"up-compare-sn comparison operator '{compare_operator}' is unsupported"
            )

    for parameter, argument in zip(native.parameters, expression.args):
        _validate_native_operand(parameter, argument, effective)

    ordinal[0] += 1
    observations.append(
        StrategicObservation(
            identity=f"{evidence.label}:observation:{ordinal[0]}",
            semantic_type=semantic_type,
            primitive=expression.head,
            native_parameter_contracts=native.parameters,
            expression=expression,
            evidence_class=evidence.kind,
            evidence_source=evidence.source,
            provenance=evidence.provenance,
        )
    )
    if semantic_type is StrategicObservationType.TIMING:
        timing_primitives.append(expression.head)


def bind_strategic_evidence(
    evidence: StrategicEvidence,
    effective: EffectiveCivData,
    registry: PrimitiveRegistry | None = None,
) -> StrategicEvidenceBinding:
    from ..semantic.analyzer import parse_expression
    from .strategy import _validate_evidence_attribution

    if evidence.observation_ref is not None:
        raise ValueError(
            f"strategic evidence '{evidence.label}' must use bind_observation_reference"
        )
    if evidence.expression is None:
        raise ValueError(
            f"strategic evidence '{evidence.label}' requires a native expression"
        )

    _validate_evidence_attribution(evidence, effective)
    registry = registry or default_de_registry()
    expression = parse_expression(evidence.expression)
    observations: list[StrategicObservation] = []
    timing_primitives: list[str] = []
    _validate_expression(
        expression,
        effective,
        registry,
        evidence,
        observations,
        timing_primitives,
        [0],
    )
    predicate = StrategicPredicate(
        expression=expression,
        observations=tuple(observations),
        timing_primitives=tuple(timing_primitives),
    )
    return StrategicEvidenceBinding(
        evidence=evidence,
        predicate=predicate,
        fingerprint=canonical_fingerprint(
            {
                "label": evidence.label,
                "kind": evidence.kind,
                "source": evidence.source,
                "provenance": evidence.provenance,
                "expression": evidence.expression,
                "observations": observations,
            }
        ),
    )


def _truth_and(values: tuple[EvidenceTruth, ...]) -> EvidenceTruth:
    if any(value is EvidenceTruth.FALSE for value in values):
        return EvidenceTruth.FALSE
    if all(value is EvidenceTruth.TRUE for value in values):
        return EvidenceTruth.TRUE
    return EvidenceTruth.UNKNOWN


def _truth_or(values: tuple[EvidenceTruth, ...]) -> EvidenceTruth:
    if any(value is EvidenceTruth.TRUE for value in values):
        return EvidenceTruth.TRUE
    if all(value is EvidenceTruth.FALSE for value in values):
        return EvidenceTruth.FALSE
    return EvidenceTruth.UNKNOWN


def _evaluate_expression(expression: Expression, snapshot: RuntimeObservationSnapshot) -> EvidenceTruth:
    if expression.head in {"and", "or", "nand", "nor", "xor", "xnor", "not"}:
        children = tuple(
            _evaluate_expression(child, snapshot)
            for child in expression.args
            if isinstance(child, Expression)
        )
        if expression.head == "and":
            return _truth_and(children)
        if expression.head == "or":
            return _truth_or(children)
        if expression.head in {"nand", "nor"}:
            truth = _truth_and(children) if expression.head == "nand" else _truth_or(children)
            if truth is EvidenceTruth.UNKNOWN:
                return EvidenceTruth.UNKNOWN
            return EvidenceTruth.FALSE if truth is EvidenceTruth.TRUE else EvidenceTruth.TRUE
        if expression.head == "not":
            truth = children[0]
            if truth is EvidenceTruth.UNKNOWN:
                return EvidenceTruth.UNKNOWN
            return EvidenceTruth.FALSE if truth is EvidenceTruth.TRUE else EvidenceTruth.TRUE
        if any(value is EvidenceTruth.UNKNOWN for value in children):
            return EvidenceTruth.UNKNOWN
        true_count = sum(value is EvidenceTruth.TRUE for value in children)
        result = true_count == 1
        if expression.head == "xnor":
            result = not result
        return EvidenceTruth.TRUE if result else EvidenceTruth.FALSE
    return snapshot.result_for(expression)


def evaluate_binding(
    binding: StrategicEvidenceBinding,
    snapshot: RuntimeObservationSnapshot,
) -> EvidenceTruth:
    return _evaluate_expression(binding.predicate.expression, snapshot)


def _all_bindings(
    evidences: tuple[StrategicEvidence, ...],
    profile: StrategyProfile,
    effective: EffectiveCivData,
    registry: PrimitiveRegistry,
) -> tuple[StrategicEvidenceBinding, ...]:
    return tuple(
        bind_observation_reference(evidence, profile, effective, registry)
        if evidence.observation_ref is not None
        else bind_strategic_evidence(evidence, effective, registry)
        for evidence in evidences
    )


def _all_true(values: tuple[EvidenceTruth, ...]) -> bool:
    return bool(values) and all(value is EvidenceTruth.TRUE for value in values)


def _transition_candidates(
    profile: StrategyProfile,
    effective: EffectiveCivData,
    snapshot: RuntimeObservationSnapshot,
    registry: PrimitiveRegistry,
) -> tuple[tuple[int, str, StrategyPosture], ...]:
    applicable = []
    for transition in profile.transitions:
        if snapshot.previous_posture is None:
            if transition.from_postures:
                continue
        elif snapshot.previous_posture not in transition.from_postures:
            continue
        if _all_true(tuple(
            evaluate_binding(binding, snapshot)
            for binding in _all_bindings(transition.evidence, profile, effective, registry)
        )):
            applicable.append((transition.priority, transition.label, transition.to_posture))
    return tuple(applicable)


def _validate_transition_conflicts(profile: StrategyProfile) -> None:
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
                    f"equal-priority posture transitions '{first.label}' and '{second.label}' have incompatible destinations"
                )
            if not first.from_postures and not second.from_postures:
                raise ValueError(
                    f"equal-priority initial posture transitions '{first.label}' and '{second.label}' have incompatible destinations"
                )


def _evaluate_counter_packages(
    profile: StrategyProfile,
    effective: EffectiveCivData,
    snapshot: RuntimeObservationSnapshot,
    registry: PrimitiveRegistry,
) -> tuple[tuple[CounterPackageRuntimeState, ...], dict[str, tuple[str, ...]]]:
    states: list[CounterPackageRuntimeState] = []
    demand_sources: dict[str, list[str]] = {}

    for package in profile.counter_packages:
        binding = bind_observation_reference(
            package.trigger,
            profile,
            effective,
            registry,
        )
        truth = evaluate_binding(binding, snapshot)
        states.append(
            CounterPackageRuntimeState(
                identity=package.identity,
                threat_class=package.threat_class,
                truth=truth,
                priority=package.priority,
                demand_identities=package.demand_identities,
                policy_recipe_identity=package.policy_recipe_identity,
            )
        )
        if truth is EvidenceTruth.TRUE:
            for demand_identity in package.demand_identities:
                demand_sources.setdefault(demand_identity, []).append(package.identity)

    return (
        tuple(
            sorted(states, key=lambda item: (-item.priority, item.identity))
        ),
        {identity: tuple(sorted(sources)) for identity, sources in demand_sources.items()},
    )

def arbitrate_counter_packages(
    states: tuple[CounterPackageRuntimeState, ...],
) -> CounterArbitrationDecision:
    active = tuple(
        state
        for state in states
        if state.truth is EvidenceTruth.TRUE
    )
    if not active:
        return CounterArbitrationDecision(
            mode=CounterArbitrationMode.NONE,
            primary_package=None,
            supporting_packages=(),
            suppressed_packages=(),
            active_threat_classes=(),
        )

    selected: list[CounterPackageRuntimeState] = []
    suppressed: list[str] = []
    for threat_class in CounterThreatClass:
        candidates = tuple(
            state
            for state in active
            if state.threat_class is threat_class
        )
        if not candidates:
            continue
        winner = min(
            candidates,
            key=lambda item: (-item.priority, item.identity),
        )
        selected.append(winner)
        suppressed.extend(
            item.identity
            for item in candidates
            if item.identity != winner.identity
        )

    selected.sort(key=lambda item: (-item.priority, item.identity))
    primary = selected[0]
    supporting = tuple(item.identity for item in selected[1:])
    mode = (
        CounterArbitrationMode.SINGLE
        if len(selected) == 1
        else CounterArbitrationMode.MIXED
    )
    return CounterArbitrationDecision(
        mode=mode,
        primary_package=primary.identity,
        supporting_packages=supporting,
        suppressed_packages=tuple(sorted(suppressed)),
        active_threat_classes=tuple(
            sorted(
                {item.threat_class for item in selected},
                key=lambda item: item.value,
            )
        ),
    )


def _evaluate_demand(
    demand: StrategicDemandSpec,
    profile: StrategyProfile,
    effective: EffectiveCivData,
    snapshot: RuntimeObservationSnapshot,
    registry: PrimitiveRegistry,
    counter_package_sources: tuple[str, ...] = (),
) -> tuple[StrategicDemandRuntimeState, tuple[tuple[str, EvidenceTruth], ...]]:
    evaluated: list[tuple[str, EvidenceTruth]] = []
    reason_bindings = _all_bindings(demand.reason, profile, effective, registry)
    reason_truths = tuple(evaluate_binding(binding, snapshot) for binding in reason_bindings)
    evaluated.extend(
        (f"{demand.identity}:reason:{binding.evidence.label}", truth)
        for binding, truth in zip(reason_bindings, reason_truths)
    )
    evaluated.extend(
        (f"{demand.identity}:counter-package:{package_identity}", EvidenceTruth.TRUE)
        for package_identity in counter_package_sources
    )

    if demand.identity in snapshot.completed_demands:
        return StrategicDemandRuntimeState.STRATEGIC_COMPLETE, tuple(evaluated)

    invalidation_bindings = _all_bindings(demand.invalidation, profile, effective, registry)
    invalidation_truths = tuple(evaluate_binding(binding, snapshot) for binding in invalidation_bindings)
    evaluated.extend(
        (f"{demand.identity}:invalidation:{binding.evidence.label}", truth)
        for binding, truth in zip(invalidation_bindings, invalidation_truths)
    )
    if any(value is EvidenceTruth.TRUE for value in invalidation_truths):
        return StrategicDemandRuntimeState.STRATEGIC_INVALIDATED, tuple(evaluated)

    if not counter_package_sources and not _all_true(reason_truths):
        return StrategicDemandRuntimeState.STRATEGIC_INACTIVE, tuple(evaluated)

    admissibility_bindings = _all_bindings(demand.admissibility, profile, effective, registry)
    admissibility_truths = tuple(evaluate_binding(binding, snapshot) for binding in admissibility_bindings)
    evaluated.extend(
        (f"{demand.identity}:admissibility:{binding.evidence.label}", truth)
        for binding, truth in zip(admissibility_bindings, admissibility_truths)
    )

    execution_truths: list[EvidenceTruth] = []
    for execution in demand.execution_demands:
        for index, expression in enumerate(execution.requirements):
            binding = bind_strategic_evidence(
                StrategicEvidence(
                    StrategicEvidenceKind.EXECUTION,
                    expression,
                    f"{demand.identity}:execution:{index}",
                ),
                effective,
                registry,
            )
            execution_truths.append(evaluate_binding(binding, snapshot))

    if not _all_true(admissibility_truths) or not _all_true(tuple(execution_truths)):
        return StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED, tuple(evaluated)
    return StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE, tuple(evaluated)


def _validate_capability_recovery_outcome(
    demand: StrategicDemandSpec,
    state: StrategicDemandRuntimeState,
    evaluated: tuple[tuple[str, EvidenceTruth], ...],
    transition: CapabilityTransition,
    opportunity_state: OpportunityCostRuntimeState | None,
) -> None:
    if transition is CapabilityTransition.LOST:
        invalidation_true = any(
            key.startswith(f"{demand.identity}:invalidation:")
            and truth is EvidenceTruth.TRUE
            for key, truth in evaluated
        )
        if demand.recovery.preserve_strategic_demand and (
            state is StrategicDemandRuntimeState.STRATEGIC_INVALIDATED
            and not invalidation_true
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' cannot be invalidated "
                "by capability loss without explicit invalidation evidence"
            )
        if (
            demand.recovery.preserve_opportunity_cost
            and demand.opportunity_cost is not None
            and state
            not in {
                StrategicDemandRuntimeState.STRATEGIC_INVALIDATED,
                StrategicDemandRuntimeState.STRATEGIC_COMPLETE,
            }
            and opportunity_state is OpportunityCostRuntimeState.RELEASED
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' cannot release "
                "opportunity-cost protection on capability loss"
            )

    if transition is CapabilityTransition.RECOVERED and demand.recovery.reopen_on_recovery:
        reason_truths = tuple(
            truth
            for key, truth in evaluated
            if key.startswith(f"{demand.identity}:reason:")
        )
        invalidation_true = any(
            key.startswith(f"{demand.identity}:invalidation:")
            and truth is EvidenceTruth.TRUE
            for key, truth in evaluated
        )
        if (
            reason_truths
            and all(truth is EvidenceTruth.TRUE for truth in reason_truths)
            and not invalidation_true
            and state is StrategicDemandRuntimeState.STRATEGIC_INACTIVE
        ):
            raise ValueError(
                f"strategic demand '{demand.identity}' failed to reopen "
                "after capability recovery"
            )


def evaluate_strategy_runtime(
    profile: StrategyProfile,
    effective: EffectiveCivData,
    snapshot: RuntimeObservationSnapshot,
    registry: PrimitiveRegistry | None = None,
) -> StrategyRuntimeState:
    from .strategy import resolve_strategy_profile

    resolve_strategy_profile(profile, effective)
    registry = registry or default_de_registry()
    _validate_transition_conflicts(profile)

    candidates = _transition_candidates(profile, effective, snapshot, registry)
    if candidates:
        top_priority = max(item[0] for item in candidates)
        top = tuple(item for item in candidates if item[0] == top_priority)
        if len({item[2] for item in top}) > 1:
            raise ValueError("equal-priority posture candidates have incompatible destinations")
        current_posture = sorted(top, key=lambda item: item[1])[0][2]
    else:
        current_posture = snapshot.previous_posture
        if current_posture is None:
            raise ValueError("no reachable posture for current runtime evidence")

    demand_states: list[tuple[str, StrategicDemandRuntimeState]] = []
    evaluated: list[tuple[str, EvidenceTruth]] = []
    evaluated_meta_evidence: list[
        tuple[str, EvidenceTruth, tuple[EvidenceRef, ...]]
    ] = []
    for evidence in profile.community_meta_evidence:
        binding = (
            bind_observation_reference(evidence, profile, effective, registry)
            if evidence.observation_ref is not None
            else bind_strategic_evidence(evidence, effective, registry)
        )
        evaluated_meta_evidence.append(
            (
                evidence.label,
                evaluate_binding(binding, snapshot),
                evidence.provenance,
            )
        )

    evaluated_capability_observations: list[tuple[str, EvidenceTruth]] = []
    capability_transitions: list[tuple[str, CapabilityTransition]] = []
    previous_capability_observations = dict(snapshot.previous_capability_observations)
    for capability_observation in profile.capability_observations:
        binding = bind_strategic_capability_observation(
            capability_observation,
            effective,
            registry,
        )
        truth = evaluate_binding(binding, snapshot)
        evaluated_capability_observations.append(
            (
                capability_observation.identity,
                truth,
            )
        )
        if (
            capability_observation.observation_kind
            is not StrategicCapabilityObservationKind.PROVIDER_WORLD_STATE
        ):
            continue
        current_bool = (
            True if truth is EvidenceTruth.TRUE
            else False if truth is EvidenceTruth.FALSE
            else None
        )
        transition = classify_capability_transition(
            previous_capability_observations.get(capability_observation.identity),
            current_bool,
        )
        capability_transitions.append(
            (capability_observation.identity, transition)
        )

    counter_package_states, counter_package_sources = _evaluate_counter_packages(
        profile,
        effective,
        snapshot,
        registry,
    )
    counter_arbitration = arbitrate_counter_packages(counter_package_states)
    composition_upgrade_readiness = evaluate_composition_upgrade_readiness(
        profile,
        effective,
        snapshot,
        registry,
        counter_arbitration,
    )
    selected_package_ids = set(counter_arbitration.active_packages)
    counter_package_sources = {
        demand_identity: tuple(
            package_identity
            for package_identity in package_ids
            if package_identity in selected_package_ids
        )
        for demand_identity, package_ids in counter_package_sources.items()
    }

    owners: list[tuple[str, str]] = []
    active: list[str] = []
    blocked: list[str] = []
    invalidated: list[str] = []
    complete: list[str] = []
    opportunity: list[tuple[str, OpportunityCostRuntimeState]] = []

    reasons = set(snapshot.reassessment_signals)
    previous_counter_states = dict(snapshot.previous_counter_package_states)
    current_counter_states = {
        item.identity: item.truth
        for item in counter_package_states
    }
    if current_counter_states != previous_counter_states:
        reasons.add(ReassessmentReason.COUNTER_PACKAGE_CHANGE)

    if (
        snapshot.previous_composition_upgrade_readiness is not None
        and snapshot.previous_composition_upgrade_readiness != composition_upgrade_readiness
    ):
        reasons.add(ReassessmentReason.UPGRADE_READINESS_CHANGE)

    if snapshot.previous_posture is not None and snapshot.previous_posture is not current_posture:
        reasons.add(ReassessmentReason.POSTURE_CHANGE)

    previous_states = dict(snapshot.previous_demand_states)
    for demand in profile.demands:
        owners.append((demand.identity, demand.owner))
        state, evidence = _evaluate_demand(
            demand,
            profile,
            effective,
            snapshot,
            registry,
            counter_package_sources.get(demand.identity, ()),
        )
        demand_states.append((demand.identity, state))
        evaluated.extend(evidence)

        if state is StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE:
            active.append(demand.identity)
        elif state is StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED:
            blocked.append(demand.identity)
        elif state is StrategicDemandRuntimeState.STRATEGIC_INVALIDATED:
            invalidated.append(demand.identity)
        elif state is StrategicDemandRuntimeState.STRATEGIC_COMPLETE:
            complete.append(demand.identity)

        prior = previous_states.get(demand.identity)
        if prior is None and state in {
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_EXECUTABLE,
            StrategicDemandRuntimeState.STRATEGIC_ACTIVE_BLOCKED,
        }:
            reasons.add(ReassessmentReason.DEMAND_ACTIVATION)
        elif prior is not None and prior != state and state is StrategicDemandRuntimeState.STRATEGIC_INVALIDATED:
            reasons.add(ReassessmentReason.DEMAND_INVALIDATION)
        elif prior is not None and prior != state and state is StrategicDemandRuntimeState.STRATEGIC_COMPLETE:
            reasons.add(ReassessmentReason.CAPABILITY_COMPLETION)

        matched_capabilities = {
            observation.identity
            for observation in profile.capability_observations
            if observation.capability == demand.capability_intent
        }
        matched_transitions = tuple(
            transition
            for capability_identity, transition in capability_transitions
            if capability_identity in matched_capabilities
        )
        for transition in matched_transitions:
            if transition is CapabilityTransition.LOST:
                reasons.add(ReassessmentReason.CAPABILITY_LOSS)
            elif transition is CapabilityTransition.RECOVERED:
                reasons.add(ReassessmentReason.CAPABILITY_RECOVERY)

        demand_opportunity_state: OpportunityCostRuntimeState | None = None
        if demand.opportunity_cost is not None:
            if state is StrategicDemandRuntimeState.STRATEGIC_COMPLETE and demand.opportunity_cost.release_on_completion:
                demand_opportunity_state = OpportunityCostRuntimeState.RELEASED
            elif state is StrategicDemandRuntimeState.STRATEGIC_INVALIDATED and demand.opportunity_cost.release_on_invalidation:
                demand_opportunity_state = OpportunityCostRuntimeState.RELEASED
            elif current_posture in demand.opportunity_cost.emergency_override_postures:
                demand_opportunity_state = OpportunityCostRuntimeState.OVERRIDDEN
            else:
                demand_opportunity_state = OpportunityCostRuntimeState.PROTECTED_ACTIVE
            opportunity.append((demand.identity, demand_opportunity_state))

        for transition in matched_transitions:
            _validate_capability_recovery_outcome(
                demand,
                state,
                tuple(evaluated),
                transition,
                demand_opportunity_state,
            )

    fingerprint = canonical_fingerprint(
        {
            "current_posture": current_posture,
            "previous_posture": snapshot.previous_posture,
            "counter_package_states": counter_package_states,
            "counter_arbitration": counter_arbitration,
            "composition_upgrade_readiness": composition_upgrade_readiness,
            "demand_states": demand_states,
            "opportunity": opportunity,
            "recovery_contracts": {
                demand.identity: {
                    "preserve_strategic_demand": demand.recovery.preserve_strategic_demand,
                    "preserve_opportunity_cost": demand.recovery.preserve_opportunity_cost,
                    "reopen_on_recovery": demand.recovery.reopen_on_recovery,
                }
                for demand in profile.demands
            },
            "evaluated": evaluated,
            "active": active,
            "blocked": blocked,
            "invalidated": invalidated,
            "complete": complete,
            "reassessment": sorted(reason.value for reason in reasons),
            "evaluated_meta_evidence": evaluated_meta_evidence,
            "evaluated_capability_observations": evaluated_capability_observations,
            "capability_transitions": capability_transitions,
        }
    )

    return StrategyRuntimeState(
        current_posture=current_posture,
        previous_posture=snapshot.previous_posture,
        demand_states=tuple(sorted(demand_states)),
        counter_package_states=tuple(counter_package_states),
        counter_arbitration=counter_arbitration,
        composition_upgrade_readiness=composition_upgrade_readiness,
        opportunity_cost_states=tuple(sorted(opportunity)),
        evaluated_evidence=tuple(sorted(evaluated)),
        active_strategic_demands=tuple(sorted(active)),
        strategically_blocked_demands=tuple(sorted(blocked)),
        strategically_invalidated_demands=tuple(sorted(invalidated)),
        strategically_complete_demands=tuple(sorted(complete)),
        reassessment_reasons=tuple(sorted(reasons, key=lambda item: item.value)),
        runtime_storage_requests=(),
        fingerprint=fingerprint,
        _owners=tuple(sorted(owners)),
        evaluated_meta_evidence=tuple(
            sorted(
                evaluated_meta_evidence,
                key=lambda item: (item[0], item[2][0].stable_key() if item[2] else ""),
            )
        ),
        evaluated_capability_observations=tuple(
            sorted(evaluated_capability_observations)
        ),
        capability_transitions=tuple(
            sorted(capability_transitions, key=lambda item: item[0])
        ),
    )
