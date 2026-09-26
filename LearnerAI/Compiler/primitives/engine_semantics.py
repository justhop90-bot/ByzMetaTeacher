"""Validated native engine-semantic mappings for executable compiler primitives.

The mapping catalog is deliberately separate from EnginePractice evidence records.
A mapping is executable only when the compiler has a complete, contracted semantic
description for the native primitive. Evidence-only identities may exist in the
catalog but can never promote a primitive to executable-safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EngineSemanticMappingStatus(str, Enum):
    CONTRACTED = "contracted"
    EVIDENCE_ONLY = "evidence-only"
    OPEN = "open"


@dataclass(frozen=True)
class EngineSemanticMapping:
    identity: str
    native_command: str | None
    native_kind: str | None
    status: EngineSemanticMappingStatus
    evidence_class: str
    evidence_sources: tuple[str, ...]
    state_effects: str
    lifetime: str
    ordering: str
    admission: str
    completion: str
    recovery: str


@dataclass(frozen=True)
class EngineSemanticMappingRegistry:
    mappings: tuple[EngineSemanticMapping, ...]

    def __post_init__(self) -> None:
        identities = [item.identity for item in self.mappings]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate engine semantic mapping identity")
        for item in self.mappings:
            if not item.identity:
                raise ValueError("engine semantic mapping identity must not be empty")
            if not item.evidence_class:
                raise ValueError(f"engine semantic mapping '{item.identity}' lacks evidence class")
            if not item.evidence_sources:
                raise ValueError(f"engine semantic mapping '{item.identity}' lacks evidence")
            for field_name in (
                "state_effects",
                "lifetime",
                "ordering",
                "admission",
                "completion",
                "recovery",
            ):
                if not getattr(item, field_name):
                    raise ValueError(
                        f"engine semantic mapping '{item.identity}' lacks {field_name}"
                    )
            if item.status is EngineSemanticMappingStatus.CONTRACTED:
                if not item.native_command or not item.native_kind:
                    raise ValueError(
                        f"contracted engine semantic mapping '{item.identity}' "
                        "must identify a native command and kind"
                    )
            elif item.native_command is not None or item.native_kind is not None:
                raise ValueError(
                    f"non-executable engine semantic mapping '{item.identity}' "
                    "must not masquerade as a native primitive contract"
                )

    def get(self, identity: str) -> EngineSemanticMapping | None:
        for item in self.mappings:
            if item.identity == identity:
                return item
        return None

    def require(self, identity: str) -> EngineSemanticMapping:
        item = self.get(identity)
        if item is None:
            raise KeyError(identity)
        return item

    def for_command(self, command: str) -> EngineSemanticMapping | None:
        matches = [item for item in self.mappings if item.native_command == command]
        if len(matches) > 1:
            raise ValueError(
                f"multiple engine semantic mappings registered for native command '{command}'"
            )
        return matches[0] if matches else None

    def validate_primitive(
        self,
        *,
        command: str,
        native_kind: str,
        identity: str,
    ) -> tuple[bool, str]:
        mapping = self.get(identity)
        if mapping is None:
            return False, f"engine semantic mapping '{identity}' is not registered"
        if mapping.status is EngineSemanticMappingStatus.EVIDENCE_ONLY:
            return False, (
                f"engine semantic mapping '{identity}' is evidence-only and cannot "
                "promote a native primitive"
            )
        if mapping.status is EngineSemanticMappingStatus.OPEN:
            return False, (
                f"engine semantic mapping '{identity}' is open/unknown and cannot "
                "promote a native primitive"
            )
        if mapping.native_command != command:
            return False, (
                f"engine semantic mapping '{identity}' targets "
                f"'{mapping.native_command}', not '{command}'"
            )
        if mapping.native_kind != native_kind:
            return False, (
                f"engine semantic mapping '{identity}' has native kind "
                f"'{mapping.native_kind}', expected '{native_kind}'"
            )
        return True, "engine semantic mapping is contracted and executable"


_AOERF = "https://airef.github.io/"
_AOERF_LIMITS = "https://airef.github.io/resources/articles/data-limits.html"
_AOERF_PER = "https://airef.github.io/resources/articles/intro-to-commands.html"
_AOE2AI = "https://github.com/lewisc64/aoe2ai"
_DUKE = "https://github.com/niektb/AI"

_OBSERVATION_SPECS = (
    ("current-age", "observation.age.current"),
    ("food-amount", "observation.resource.food"),
    ("wood-amount", "observation.resource.wood"),
    ("gold-amount", "observation.resource.gold"),
    ("stone-amount", "observation.resource.stone"),
    ("players-unit-type-count", "observation.threat.unit-count"),
    ("players-building-type-count", "observation.world.building-count"),
    ("game-time", "observation.timing.game-time"),
    ("dropsite-min-distance", "observation.placement.dropsite-distance"),
    ("unit-type-count", "observation.unit.count"),
)

_ADMISSIBILITY_SPECS = (
    ("building-available", "admissibility.building.available"),
    ("research-available", "admissibility.research.available"),
)

_ARBITRATION_SPECS = (
    ("can-afford-building", "arbitration.building.affordability"),
    ("can-afford-research", "arbitration.research.affordability"),
)

_FEASIBILITY_SPECS = (
    ("can-build", "execution.build.feasibility"),
    ("can-build-with-escrow", "execution.build.feasibility.escrow"),
    ("can-train", "execution.train.feasibility"),
    ("can-train-with-escrow", "execution.train.feasibility.escrow"),
    ("can-research", "execution.research.feasibility"),
    ("can-research-with-escrow", "execution.research.feasibility.escrow"),
)

_WITNESS_SPECS = (
    ("building-type-count", "witness.building.present"),
    ("building-type-count-total", "witness.building.present.total"),
    ("unit-type-count-total", "witness.unit.present.total"),
    ("research-completed", "witness.research.completed"),
)

_ACTION_SPECS = (
    ("build", "execution.build.request"),
    ("train", "execution.train.request"),
    ("research", "execution.research.request"),
)

_EXPLICIT_SPECS = (
    ("up-pending-objects", "execution.pending-objects"),
)


def _fact_mapping(command: str, identity: str, category: str) -> EngineSemanticMapping:
    if category == "OBSERVATION":
        state_effects = "reads native world state without persistent mutation"
        lifetime = "single fact evaluation; truth is re-evaluated on subsequent rule passes"
        ordering = "observation reflects native state at evaluation time; source order does not make it persistent"
        admission = "native fact evaluation"
        completion = "observation result is not an action-completion witness"
        recovery = "re-evaluate the fact; no retained compiler failure state"
        sources = (_AOERF, _AOERF_PER)
    elif category == "ADMISSIBILITY":
        state_effects = "reads native provider/research admissibility state without persistent mutation"
        lifetime = "single admissibility evaluation; availability may change between passes"
        ordering = "truth is determined from native state at evaluation time"
        admission = "native admissibility fact"
        completion = "admissibility is not completion evidence"
        recovery = "re-evaluate admissibility when the demand is reconsidered"
        sources = (_AOERF, _AOERF_LIMITS)
    elif category == "ARBITRATION":
        state_effects = "reads current resource-affordability state without owning strategic intent"
        lifetime = "transient feasibility observation"
        ordering = "truth is evaluated against current native resource state"
        admission = "native affordability/arbitration fact"
        completion = "affordability is not completion evidence"
        recovery = "re-evaluate when resources or competing claims change"
        sources = (_AOERF, _DUKE)
    elif category == "FEASIBILITY":
        state_effects = "reads native execution feasibility; does not issue the native action"
        lifetime = "transient admission predicate"
        ordering = "must be evaluated immediately before the associated action when used as an execution guard"
        admission = "native can-* execution admission"
        completion = "feasibility does not prove issuance or completion"
        recovery = "re-enter through the same native feasibility predicate after temporary blockage"
        sources = (_AOERF, _DUKE)
    elif category == "WITNESS":
        state_effects = "reads world-state evidence produced by native engine state"
        lifetime = "persistent world observation until the world state changes"
        ordering = "witness must be evaluated after the relevant world-state transition can exist"
        admission = "native observation/witness evaluation"
        completion = "proves the corresponding world-state condition, not merely a request"
        recovery = "reassess current world state; never infer completion from a timer or request"
        sources = (_AOERF, _DUKE)
    else:
        raise ValueError(category)
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT" if category in {"OBSERVATION", "ADMISSIBILITY", "WITNESS"} else "COMMUNITY PRACTICE",
        evidence_sources=sources,
        state_effects=state_effects,
        lifetime=lifetime,
        ordering=ordering,
        admission=admission,
        completion=completion,
        recovery=recovery,
    )


def _action_mapping(command: str, identity: str) -> EngineSemanticMapping:
    witness = {
        "build": "building-type-count-total",
        "train": "unit-type-count-total",
        "research": "research-completed",
    }[command]
    return EngineSemanticMapping(
        identity=identity,
        native_command=command,
        native_kind="Action",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOE2AI, _DUKE),
        state_effects="issues native engine work and may create asynchronous pending work",
        lifetime="request persists only as native engine state; completion occurs through later world observation",
        ordering="action executes in emitted order within its rule; later rules observe engine-persisted effects only after they exist",
        admission="native action command; caller must separately guard with can-* or equivalent admission semantics where required",
        completion=f"completion requires world-state witness '{witness}'",
        recovery="preserve strategic demand and reassess through native feasibility after temporary blockage or failure",
    )


def _pending_mapping() -> EngineSemanticMapping:
    return EngineSemanticMapping(
        identity="execution.pending-objects",
        native_command="up-pending-objects",
        native_kind="Fact",
        status=EngineSemanticMappingStatus.CONTRACTED,
        evidence_class="ENGINE FACT",
        evidence_sources=(_AOERF, _AOERF_LIMITS, _AOE2AI),
        state_effects="reads outstanding native build/train work without proving target birth",
        lifetime="pending engine work persists until admitted work progresses, completes, or disappears",
        ordering="pending state is observed after native admission/issuance and before world-state completion",
        admission="native pending-work fact",
        completion="pending state is never a completion witness",
        recovery="use pending evidence to suppress duplicate issuance, then re-evaluate feasibility and world-state witnesses",
    )


def default_engine_semantic_mapping_registry() -> EngineSemanticMappingRegistry:
    mappings: list[EngineSemanticMapping] = []
    for command, identity in _OBSERVATION_SPECS:
        mappings.append(_fact_mapping(command, identity, "OBSERVATION"))
    mappings.append(
        EngineSemanticMapping(
            identity="observation.unit.count",
            native_command="unit-type-count",
            native_kind="Fact",
            status=EngineSemanticMappingStatus.CONTRACTED,
            evidence_class="ENGINE FACT",
            evidence_sources=(_AOERF, _AOERF_PER),
            state_effects="reads native unit world-state count",
            lifetime="world-state observation at evaluation time",
            ordering="evaluated against current native unit state",
            admission="native observation fact",
            completion="count is evidence of existing units, not an issuance request",
            recovery="re-evaluate current unit state",
        )
    )
    for command, identity in _ADMISSIBILITY_SPECS:
        mappings.append(_fact_mapping(command, identity, "ADMISSIBILITY"))
    for command, identity in _ARBITRATION_SPECS:
        mappings.append(_fact_mapping(command, identity, "ARBITRATION"))
    for command, identity in _FEASIBILITY_SPECS:
        mappings.append(_fact_mapping(command, identity, "FEASIBILITY"))
    for command, identity in _WITNESS_SPECS:
        mappings.append(_fact_mapping(command, identity, "WITNESS"))
    mappings.append(
        EngineSemanticMapping(
            identity="execution.pending-objects",
            native_command="up-pending-objects",
            native_kind="Fact",
            status=EngineSemanticMappingStatus.CONTRACTED,
            evidence_class="ENGINE FACT",
            evidence_sources=(_AOERF, _AOERF_LIMITS, _AOE2AI),
            state_effects="reads outstanding native build/train work without proving target birth",
            lifetime="pending engine work persists until admitted work progresses, completes, or disappears",
            ordering="pending state is observed after native admission/issuance and before world-state completion",
            admission="native pending-work fact",
            completion="pending state is never a completion witness",
            recovery="use pending evidence to suppress duplicate issuance, then re-evaluate feasibility and world-state witnesses",
        )
    )
    mappings.extend(_action_mapping(command, identity) for command, identity in _ACTION_SPECS)
    mappings.extend(
        (
            EngineSemanticMapping(
                identity="duc.search-state-retained",
                native_command=None,
                native_kind=None,
                status=EngineSemanticMappingStatus.EVIDENCE_ONLY,
                evidence_class="ENGINE FACT",
                evidence_sources=(_AOERF, _AOERF_LIMITS),
                state_effects="retained DUC search state mutates engine search context",
                lifetime="retained across commands until reset or replacement",
                ordering="later DUC operations can observe retained search state",
                admission="not executable until DUC IR/lifetime mapping exists",
                completion="not a completion witness",
                recovery="unknown; evidence-only",
            ),
            EngineSemanticMapping(
                identity="attack.group-state-control",
                native_command=None,
                native_kind=None,
                status=EngineSemanticMappingStatus.EVIDENCE_ONLY,
                evidence_class="COMMUNITY PRACTICE",
                evidence_sources=("https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476",),
                state_effects="persistent attack-group control changes native attack behavior",
                lifetime="persists until native attack controls are changed",
                ordering="later control writes can override earlier attack state",
                admission="not executable until attack lifecycle semantics are mapped",
                completion="not a generic completion witness",
                recovery="unknown; evidence-only",
            ),
        )
    )
    registry = EngineSemanticMappingRegistry(tuple(mappings))
    registry.validate_exact_executable_commands(
        tuple(command for command, _identity in _OBSERVATION_SPECS)
        + tuple(command for command, _identity in _ADMISSIBILITY_SPECS)
        + tuple(command for command, _identity in _ARBITRATION_SPECS)
        + tuple(command for command, _identity in _FEASIBILITY_SPECS)
        + tuple(command for command, _identity in _WITNESS_SPECS)
        + ("up-pending-objects",)
        + tuple(command for command, _identity in _ACTION_SPECS)
    )
    return registry
