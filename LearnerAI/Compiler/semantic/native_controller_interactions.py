"""Typed native-controller interaction semantics.

This layer records causal, temporal, mutation, and performance relationships
between the native controller graph and its control surfaces. It is descriptive
and fail-closed: community evidence never becomes executable engine semantics by
proximity alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from ..primitives.native_hygiene import (
    AIRefVersionFamily,
    EngineVersionScope,
    PerformanceClass,
)
from .community_engine import EvidenceClass
from .native_controller import (
    NativeControllerCatalog,
    NativeControlSurfaceKind,
    default_native_controller_catalog,
)


class NativeInteractionEndpointKind(str, Enum):
    CONTROLLER = "CONTROLLER"
    CONTROL_SURFACE = "CONTROL_SURFACE"


class NativeControllerInteractionKind(str, Enum):
    CONTROLLED_BY = "CONTROLLED_BY"
    COUPLED_WITH = "COUPLED_WITH"
    GATES = "GATES"
    FEEDS = "FEEDS"
    FEEDBACK = "FEEDBACK"
    AUTO_MUTATES = "AUTO_MUTATES"
    REQUIRES_WORLD_STATE = "REQUIRES_WORLD_STATE"
    AFFECTS_TARGETING = "AFFECTS_TARGETING"
    AFFECTS_PLACEMENT = "AFFECTS_PLACEMENT"
    AFFECTS_ALLOCATION = "AFFECTS_ALLOCATION"
    AFFECTS_QUEUE_ADMISSION = "AFFECTS_QUEUE_ADMISSION"
    AFFECTS_ATTACK_STATE = "AFFECTS_ATTACK_STATE"
    OVERRIDES = "OVERRIDES"
    REASSESSES = "REASSESSES"
    COSTS = "COSTS"


class NativeInteractionLifetime(str, Enum):
    PERSISTENT = "PERSISTENT"
    TRANSIENT = "TRANSIENT"


class NativeInteractionVisibility(str, Enum):
    SAME_RULE = "SAME_RULE"
    SAME_PASS_LATER_RULE = "SAME_PASS_LATER_RULE"
    NEXT_PASS = "NEXT_PASS"
    RUNTIME_DEPENDENT = "RUNTIME_DEPENDENT"


class NativeInteractionMutationOwner(str, Enum):
    NONE = "NONE"
    ENGINE_AUTOMATIC = "ENGINE_AUTOMATIC"
    COMPILER_ACTION = "COMPILER_ACTION"
    RUNTIME_EXTERNAL = "RUNTIME_EXTERNAL"


class NativeInteractionSupportState(str, Enum):
    EVIDENCE_ONLY = "EVIDENCE_ONLY"
    ENGINE_SEMANTICS_MAPPED = "ENGINE_SEMANTICS_MAPPED"
    OPEN = "OPEN"


@dataclass(frozen=True)
class NativeInteractionEndpoint:
    kind: NativeInteractionEndpointKind
    identity: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native interaction endpoint identity is required")


@dataclass(frozen=True)
class NativeInteractionCardinality:
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if self.minimum < 0 or self.maximum < self.minimum:
            raise ValueError("invalid native interaction cardinality range")


@dataclass(frozen=True)
class NativeControllerInteraction:
    identity: str
    source: NativeInteractionEndpoint
    target: NativeInteractionEndpoint
    relation: NativeControllerInteractionKind
    evidence: EvidenceClass
    status: NativeInteractionSupportState
    lifetime: NativeInteractionLifetime
    visibility: NativeInteractionVisibility
    mutation_owner: NativeInteractionMutationOwner
    sources: tuple[str, ...]
    engine_version_scope: EngineVersionScope
    description: str
    performance_class: PerformanceClass | None = None
    cardinality: NativeInteractionCardinality | None = None

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native controller interaction identity is required")
        if self.source == self.target:
            raise ValueError("native controller interaction self-interactions are not supported")
        if not self.sources:
            raise ValueError(f"interaction '{self.identity}' requires evidence sources")
        if not self.description.strip():
            raise ValueError(f"interaction '{self.identity}' requires a description")


_DIRECTIONAL_RELATIONS = frozenset(
    {
        NativeControllerInteractionKind.GATES,
        NativeControllerInteractionKind.FEEDS,
        NativeControllerInteractionKind.REQUIRES_WORLD_STATE,
        NativeControllerInteractionKind.AFFECTS_TARGETING,
        NativeControllerInteractionKind.AFFECTS_PLACEMENT,
        NativeControllerInteractionKind.AFFECTS_ALLOCATION,
        NativeControllerInteractionKind.AFFECTS_QUEUE_ADMISSION,
        NativeControllerInteractionKind.AFFECTS_ATTACK_STATE,
        NativeControllerInteractionKind.OVERRIDES,
        NativeControllerInteractionKind.REASSESSES,
    }
)

_DEPENDENCY_RELATIONS = frozenset(_DIRECTIONAL_RELATIONS)


@dataclass(frozen=True)
class NativeControllerInteractionCatalog:
    interactions: tuple[NativeControllerInteraction, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interactions",
            tuple(sorted(self.interactions, key=self._sort_key)),
        )

    @staticmethod
    def _sort_key(
        item: NativeControllerInteraction,
    ) -> tuple[str, str, str, str]:
        return (
            item.identity,
            item.source.identity,
            item.target.identity,
            item.relation.value,
        )

    def resolve(self, interaction_id: str) -> NativeControllerInteraction:
        for item in self.interactions:
            if item.identity == interaction_id:
                return item
        raise KeyError(interaction_id)

    def _validate_endpoint(
        self,
        endpoint: NativeInteractionEndpoint,
        controller_catalog: NativeControllerCatalog,
    ) -> None:
        if endpoint.kind is NativeInteractionEndpointKind.CONTROLLER:
            controller_catalog.controller(endpoint.identity)
            return

        if endpoint.kind is NativeInteractionEndpointKind.CONTROL_SURFACE:
            if ":" in endpoint.identity:
                prefix, kind_value, native_identifier = endpoint.identity.split(":", 2)
                try:
                    kind = NativeControlSurfaceKind(kind_value.upper())
                except ValueError as exc:
                    raise ValueError(
                        f"unknown control-surface kind '{kind_value}' "
                        f"in endpoint '{endpoint.identity}'"
                    ) from exc
                surface = controller_catalog.resolve_surface(kind, native_identifier)
                if surface.identity != endpoint.identity:
                    raise ValueError(
                        f"control surface endpoint '{endpoint.identity}' has inconsistent identity"
                    )
                if surface.controller_id != prefix:
                    raise ValueError(
                        f"control surface endpoint '{endpoint.identity}' has inconsistent ownership"
                    )
                return

            for surface in controller_catalog.surfaces:
                if surface.identity == endpoint.identity:
                    return
            raise ValueError(
                f"unknown control-surface endpoint '{endpoint.identity}'"
            )

        raise ValueError(
            f"unsupported native interaction endpoint kind {endpoint.kind.value}"
        )

    def _validate_relation_shape(
        self,
        item: NativeControllerInteraction,
        controller_catalog: NativeControllerCatalog,
    ) -> None:
        source = item.source
        target = item.target
        relation = item.relation

        if relation is NativeControllerInteractionKind.CONTROLLED_BY:
            if (
                source.kind is not NativeInteractionEndpointKind.CONTROL_SURFACE
                or target.kind is not NativeInteractionEndpointKind.CONTROLLER
            ):
                raise ValueError("CONTROLLED_BY requires surface -> controller endpoints")
            _, kind_value, native_identifier = source.identity.split(":", 2)
            surface = controller_catalog.resolve_surface(
                NativeControlSurfaceKind(kind_value.upper()),
                native_identifier,
            )
            if surface.controller_id != target.identity:
                raise ValueError(
                    f"control surface '{surface.identity}' is owned by "
                    f"'{surface.controller_id}', not '{target.identity}'"
                )

        elif relation is NativeControllerInteractionKind.AUTO_MUTATES:
            if target.kind is not NativeInteractionEndpointKind.CONTROL_SURFACE:
                raise ValueError("AUTO_MUTATES requires a control-surface target")
            if item.mutation_owner is not NativeInteractionMutationOwner.ENGINE_AUTOMATIC:
                raise ValueError(
                    "AUTO_MUTATES requires ENGINE_AUTOMATIC mutation ownership"
                )

        elif relation in _DIRECTIONAL_RELATIONS or relation in {
            NativeControllerInteractionKind.COUPLED_WITH,
            NativeControllerInteractionKind.COSTS,
        }:
            if (
                source.kind is not NativeInteractionEndpointKind.CONTROLLER
                or target.kind is not NativeInteractionEndpointKind.CONTROLLER
            ):
                raise ValueError(
                    f"{relation.value} requires controller -> controller endpoints"
                )

        elif relation is NativeControllerInteractionKind.FEEDBACK:
            if (
                source.kind is not NativeInteractionEndpointKind.CONTROLLER
                or target.kind is not NativeInteractionEndpointKind.CONTROLLER
            ):
                raise ValueError("FEEDBACK requires controller -> controller endpoints")

    def validate(
        self,
        controller_catalog: NativeControllerCatalog,
        *,
        target_engine_families: tuple[AIRefVersionFamily, ...] = (
            AIRefVersionFamily.DE,
        ),
    ) -> None:
        controller_catalog.validate()

        identities = tuple(item.identity for item in self.interactions)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate native controller interaction identity")

        for item in self.interactions:
            self._validate_endpoint(item.source, controller_catalog)
            self._validate_endpoint(item.target, controller_catalog)
            self._validate_relation_shape(item, controller_catalog)

            if item.status is NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED:
                if item.evidence is not EvidenceClass.ENGINE_FACT:
                    raise ValueError(
                        f"interaction '{item.identity}' cannot be engine-semantics-mapped "
                        "without engine-fact evidence"
                    )
                if not set(item.engine_version_scope.engine_targets).intersection(
                    target_engine_families
                ):
                    raise ValueError(
                        f"interaction '{item.identity}' engine-version scope does not "
                        "cover target engine families"
                    )

        directional_keys: dict[
            tuple[NativeControllerInteractionKind, str, str],
            str,
        ] = {}
        for item in self.interactions:
            if item.relation not in _DIRECTIONAL_RELATIONS:
                continue
            reverse_key = (
                item.relation,
                item.target.identity,
                item.source.identity,
            )
            if reverse_key in directional_keys:
                raise ValueError(
                    f"contradictory reverse-direction interaction for "
                    f"{item.relation.value}: {directional_keys[reverse_key]} "
                    f"and {item.identity}"
                )
            directional_keys[
                (item.relation, item.source.identity, item.target.identity)
            ] = item.identity

    def dependency_edges(self) -> tuple[NativeControllerInteraction, ...]:
        return tuple(
            item
            for item in self.interactions
            if item.relation in _DEPENDENCY_RELATIONS
        )

    def require_engine_semantics_mapped(
        self,
        interaction_id: str,
    ) -> NativeControllerInteraction:
        item = self.resolve(interaction_id)
        if item.status is not NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED:
            raise ValueError(
                f"interaction '{interaction_id}' is not engine-semantics-mapped"
            )
        if item.evidence is not EvidenceClass.ENGINE_FACT:
            raise ValueError(
                f"interaction '{interaction_id}' lacks engine-fact evidence"
            )
        return item

    def fingerprint(self) -> str:
        payload = [
            {
                "identity": item.identity,
                "source": (item.source.kind.value, item.source.identity),
                "target": (item.target.kind.value, item.target.identity),
                "relation": item.relation.value,
                "evidence": item.evidence.value,
                "status": item.status.value,
                "lifetime": item.lifetime.value,
                "visibility": item.visibility.value,
                "mutation_owner": item.mutation_owner.value,
                "sources": item.sources,
                "engine_targets": tuple(
                    family.value
                    for family in item.engine_version_scope.engine_targets
                ),
                "performance": (
                    item.performance_class.value
                    if item.performance_class
                    else None
                ),
                "cardinality": (
                    (item.cardinality.minimum, item.cardinality.maximum)
                    if item.cardinality
                    else None
                ),
            }
            for item in self.interactions
        ]
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def default_native_controller_interaction_catalog(
    controller_catalog: NativeControllerCatalog | None = None,
) -> NativeControllerInteractionCatalog:
    controller_catalog = controller_catalog or default_native_controller_catalog()
    catalog = NativeControllerInteractionCatalog(())
    catalog.validate(controller_catalog)
    return catalog


__all__ = [
    "NativeControllerInteraction",
    "NativeControllerInteractionCatalog",
    "NativeControllerInteractionKind",
    "NativeInteractionCardinality",
    "NativeInteractionEndpoint",
    "NativeInteractionEndpointKind",
    "NativeInteractionLifetime",
    "NativeInteractionMutationOwner",
    "NativeInteractionSupportState",
    "NativeInteractionVisibility",
    "default_native_controller_interaction_catalog",
]