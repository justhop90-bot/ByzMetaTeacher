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


class NativeInteractionEndpointRole(str, Enum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"


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
            try:
                controller_catalog.controller(endpoint.identity)
            except KeyError as exc:
                raise ValueError(
                    f"unknown controller endpoint '{endpoint.identity}'"
                ) from exc
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

            if not set(item.engine_version_scope.engine_targets).intersection(
                target_engine_families
            ):
                raise ValueError(
                    f"interaction '{item.identity}' engine-version scope does not "
                    "cover target engine families"
                )

            if item.status is NativeInteractionSupportState.ENGINE_SEMANTICS_MAPPED:
                if item.evidence is not EvidenceClass.ENGINE_FACT:
                    raise ValueError(
                        f"interaction '{item.identity}' cannot be engine-semantics-mapped "
                        "without engine-fact evidence"
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


@dataclass(frozen=True)
class NativeControllerInteractionBinding:
    access_identifier: str
    controller_id: str
    interaction_id: str
    relation: NativeControllerInteractionKind
    endpoint_role: NativeInteractionEndpointRole
    status: NativeInteractionSupportState
    rule_order: int
    within_rule_order: int


def bind_strategic_number_interactions(
    bindings: tuple[object, ...],
    interaction_catalog: NativeControllerInteractionCatalog | None = None,
) -> tuple[NativeControllerInteractionBinding, ...]:
    catalog = interaction_catalog or default_native_controller_interaction_catalog()
    output: list[NativeControllerInteractionBinding] = []
    for binding in bindings:
        for interaction in catalog.interactions:
            if (
                interaction.source.kind is NativeInteractionEndpointKind.CONTROLLER
                and interaction.source.identity == binding.controller_id
            ):
                output.append(
                    NativeControllerInteractionBinding(
                        access_identifier=binding.access_identifier,
                        controller_id=binding.controller_id,
                        interaction_id=interaction.identity,
                        relation=interaction.relation,
                        endpoint_role=NativeInteractionEndpointRole.SOURCE,
                        status=interaction.status,
                        rule_order=binding.rule_order,
                        within_rule_order=binding.within_rule_order,
                    )
                )
            if (
                interaction.target.kind is NativeInteractionEndpointKind.CONTROLLER
                and interaction.target.identity == binding.controller_id
            ):
                output.append(
                    NativeControllerInteractionBinding(
                        access_identifier=binding.access_identifier,
                        controller_id=binding.controller_id,
                        interaction_id=interaction.identity,
                        relation=interaction.relation,
                        endpoint_role=NativeInteractionEndpointRole.TARGET,
                        status=interaction.status,
                        rule_order=binding.rule_order,
                        within_rule_order=binding.within_rule_order,
                    )
                )
    return tuple(
        sorted(
            output,
            key=lambda item: (
                item.rule_order,
                item.within_rule_order,
                item.access_identifier,
                item.interaction_id,
                item.endpoint_role.value,
            ),
        )
    )


def _scope(
    *,
    source_families: tuple[AIRefVersionFamily, ...] = (AIRefVersionFamily.DE,),
) -> EngineVersionScope:
    return EngineVersionScope(
        source_families=source_families,
        engine_targets=(AIRefVersionFamily.DE,),
        introduced_family=source_families[-1],
    )


def _controller(identifier: str) -> NativeInteractionEndpoint:
    return NativeInteractionEndpoint(
        NativeInteractionEndpointKind.CONTROLLER,
        identifier,
    )


def _surface(identifier: str) -> NativeInteractionEndpoint:
    return NativeInteractionEndpoint(
        NativeInteractionEndpointKind.CONTROL_SURFACE,
        identifier,
    )


def default_native_controller_interaction_catalog(
    controller_catalog: NativeControllerCatalog | None = None,
) -> NativeControllerInteractionCatalog:
    controller_catalog = controller_catalog or default_native_controller_catalog()

    airef_command = "https://airef.github.io/commands/commands-details.html"
    airef_limits = "https://airef.github.io/resources/articles/data-limits.html"
    performance = "https://airef.github.io/resources/articles/command-performance.html"
    patch_notes = "https://airef.github.io/tables/up-patch-notes.html"
    attack_forum = (
        "https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476"
    )
    economy_forum = (
        "https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881"
    )
    scripting = "https://userpatch.aiscripters.net/reference.html"
    aoe2ai = "https://github.com/lewisc64/aoe2ai"
    duke = "https://github.com/niektb/AI"

    interactions = (
        NativeControllerInteraction(
            identity="attack-groups-gated-by-exploration",
            source=_controller("attack-group-control"),
            target=_controller("exploration-control"),
            relation=NativeControllerInteractionKind.GATES,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(attack_forum, scripting, aoe2ai, duke),
            engine_version_scope=_scope(),
            description=(
                "Community attack-group patterns require explored enemy state before "
                "the attack machinery has usable targets."
            ),
        ),
        NativeControllerInteraction(
            identity="town-size-affects-attack-targeting",
            source=_controller("town-size-defense-targeting"),
            target=_controller("attack-group-control"),
            relation=NativeControllerInteractionKind.AFFECTS_TARGETING,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(attack_forum, duke),
            engine_version_scope=_scope(),
            description=(
                "Town-size and enemy-response controls are adjusted with attack-state "
                "rules and timers in mature community attack scripts."
            ),
        ),
        NativeControllerInteraction(
            identity="civilian-allocation-coupled-with-resource-escrow",
            source=_controller("civilian-task-allocation"),
            target=_controller("resource-escrow-control"),
            relation=NativeControllerInteractionKind.COUPLED_WITH,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(economy_forum, duke),
            engine_version_scope=_scope(),
            description=(
                "Community economy scripts coordinate civilian allocation with "
                "resource-protection and spending-control state; the evidence does "
                "not establish a universal causal direction."
            ),
        ),
        NativeControllerInteraction(
            identity="escrow-gates-production-admission",
            source=_controller("resource-escrow-control"),
            target=_controller("production-admission"),
            relation=NativeControllerInteractionKind.GATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(f"{airef_command}#release-escrow", f"{airef_command}#can-train"),
            engine_version_scope=_scope(),
            description=(
                "Escrow-aware native production feasibility distinguishes resources "
                "available in normal stockpiles from resources explicitly admitted "
                "through escrow-aware production predicates."
            ),
        ),
        NativeControllerInteraction(
            identity="escrow-gates-research-admission",
            source=_controller("resource-escrow-control"),
            target=_controller("research-admission"),
            relation=NativeControllerInteractionKind.GATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(f"{airef_command}#release-escrow", f"{airef_command}#can-research"),
            engine_version_scope=_scope(),
            description=(
                "Escrow-aware native research feasibility distinguishes resources "
                "available to ordinary research from explicitly escrow-enabled research."
            ),
        ),
        NativeControllerInteraction(
            identity="duc-local-search-feeds-target-control",
            source=_controller("duc-search-state"),
            target=_controller("duc-target-control"),
            relation=NativeControllerInteractionKind.FEEDS,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(f"{airef_command}#up-find-local", performance, patch_notes, aoe2ai),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.WK, AIRefVersionFamily.DE)),
            performance_class=PerformanceClass.MEDIUM,
            cardinality=NativeInteractionCardinality(0, 240),
            description=(
                "Local DUC search results feed later selected-target operations; "
                "AIRef benchmark evidence shows cost varies materially with list "
                "cardinality and the searched object population."
            ),
        ),
        NativeControllerInteraction(
            identity="duc-remote-search-feeds-target-control",
            source=_controller("duc-search-state"),
            target=_controller("duc-target-control"),
            relation=NativeControllerInteractionKind.FEEDS,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.RUNTIME_DEPENDENT,
            mutation_owner=NativeInteractionMutationOwner.NONE,
            sources=(f"{airef_command}#up-find-remote", performance, patch_notes, aoe2ai),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.WK, AIRefVersionFamily.DE)),
            performance_class=PerformanceClass.FAST,
            cardinality=NativeInteractionCardinality(0, 40),
            description=(
                "Remote DUC search results feed later selected-target operations; "
                "remote-list capacity and benchmark cost are explicitly bounded."
            ),
        ),
        NativeControllerInteraction(
            identity="duc-filter-include-auto-resets-local-index",
            source=_surface("duc-search-state:command:up-filter-include"),
            target=_surface("duc-search-state:duc_search_index:local"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets local search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-filter-include-auto-resets-remote-index",
            source=_surface("duc-search-state:command:up-filter-include"),
            target=_surface("duc-search-state:duc_search_index:remote"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets remote search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-filter-exclude-auto-resets-local-index",
            source=_surface("duc-search-state:command:up-filter-exclude"),
            target=_surface("duc-search-state:duc_search_index:local"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets local search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-filter-exclude-auto-resets-remote-index",
            source=_surface("duc-search-state:command:up-filter-exclude"),
            target=_surface("duc-search-state:duc_search_index:remote"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets remote search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-filter-range-auto-resets-local-index",
            source=_surface("duc-search-state:command:up-filter-range"),
            target=_surface("duc-search-state:duc_search_index:local"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets local search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-filter-range-auto-resets-remote-index",
            source=_surface("duc-search-state:command:up-filter-range"),
            target=_surface("duc-search-state:duc_search_index:remote"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Changing DUC filters resets remote search cursor state for subsequent searches.",
        ),
        NativeControllerInteraction(
            identity="duc-reset-filters-auto-resets-local-index",
            source=_surface("duc-search-state:command:up-reset-filters"),
            target=_surface("duc-search-state:duc_search_index:local"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Resetting retained DUC filters resets local search cursor state.",
        ),
        NativeControllerInteraction(
            identity="duc-reset-filters-auto-resets-remote-index",
            source=_surface("duc-search-state:command:up-reset-filters"),
            target=_surface("duc-search-state:duc_search_index:remote"),
            relation=NativeControllerInteractionKind.AUTO_MUTATES,
            evidence=EvidenceClass.ENGINE_FACT,
            status=NativeInteractionSupportState.EVIDENCE_ONLY,
            lifetime=NativeInteractionLifetime.PERSISTENT,
            visibility=NativeInteractionVisibility.SAME_RULE,
            mutation_owner=NativeInteractionMutationOwner.ENGINE_AUTOMATIC,
            sources=(patch_notes, scripting),
            engine_version_scope=_scope(source_families=(AIRefVersionFamily.UP, AIRefVersionFamily.DE)),
            description="Resetting retained DUC filters resets remote search cursor state.",
        ),
    )

    catalog = NativeControllerInteractionCatalog(interactions)
    catalog.validate(controller_catalog)
    return catalog


__all__ = [
    "NativeControllerInteraction",
    "NativeControllerInteractionBinding",
    "NativeControllerInteractionCatalog",
    "NativeControllerInteractionKind",
    "NativeInteractionCardinality",
    "NativeInteractionEndpoint",
    "NativeInteractionEndpointRole",
    "NativeInteractionEndpointKind",
    "NativeInteractionLifetime",
    "NativeInteractionMutationOwner",
    "NativeInteractionSupportState",
    "NativeInteractionVisibility",
    "default_native_controller_interaction_catalog",
    "bind_strategic_number_interactions",
]