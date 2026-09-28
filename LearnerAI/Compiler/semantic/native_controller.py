"""Evidence-backed native AI controller semantics.

This module describes the native controller systems that .per state and commands
steer. It is intentionally descriptive: controller knowledge is not executable
engine semantics until a native contract explicitly promotes it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable

from .community_engine import EvidenceClass, PracticeStatus


class NativeControllerDomain(str, Enum):
    ECONOMY = "ECONOMY"
    EXPLORATION = "EXPLORATION"
    ATTACK = "ATTACK"
    DEFENSE = "DEFENSE"
    TARGETING = "TARGETING"
    RESOURCE_CONTROL = "RESOURCE_CONTROL"
    DUC = "DUC"


class NativeControlSurfaceKind(str, Enum):
    STRATEGIC_NUMBER = "STRATEGIC_NUMBER"
    TIMER = "TIMER"
    GOAL = "GOAL"
    COMMAND = "COMMAND"


class NativeControllerRelation(str, Enum):
    CONTROLLED_BY = "CONTROLLED_BY"
    COUPLED_WITH = "COUPLED_WITH"
    AUTO_MUTATES = "AUTO_MUTATES"
    FEEDS = "FEEDS"
    GATES = "GATES"
    OVERRIDES = "OVERRIDES"
    REASSESSES = "REASSESSES"
    COSTS = "COSTS"
    REQUIRES_EXPLORATION = "REQUIRES_EXPLORATION"
    AFFECTS_TARGETING = "AFFECTS_TARGETING"
    AFFECTS_PLACEMENT = "AFFECTS_PLACEMENT"


@dataclass(frozen=True)
class NativeController:
    identity: str
    domain: NativeControllerDomain
    evidence: EvidenceClass
    status: PracticeStatus
    sources: tuple[str, ...]
    description: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("native controller identity is required")
        if not self.sources:
            raise ValueError(f"controller '{self.identity}' requires evidence sources")
        if not self.description.strip():
            raise ValueError(f"controller '{self.identity}' requires a description")


@dataclass(frozen=True)
class NativeControlSurface:
    identity: str
    controller_id: str
    kind: NativeControlSurfaceKind
    native_identifier: str
    evidence: EvidenceClass
    status: PracticeStatus
    sources: tuple[str, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("control-surface identity is required")
        if not self.controller_id.strip():
            raise ValueError(f"surface '{self.identity}' requires a controller")
        if not self.native_identifier.strip():
            raise ValueError(f"surface '{self.identity}' requires a native identifier")
        if not self.sources:
            raise ValueError(f"surface '{self.identity}' requires evidence sources")

    @property
    def lookup_key(self) -> tuple[NativeControlSurfaceKind, str]:
        return self.kind, self.native_identifier


@dataclass(frozen=True)
class NativeControllerEdge:
    source_controller: str
    target_controller: str
    relation: NativeControllerRelation
    evidence: EvidenceClass
    status: PracticeStatus
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_controller.strip() or not self.target_controller.strip():
            raise ValueError("controller edge endpoints are required")
        if self.source_controller == self.target_controller:
            raise ValueError("native controller self-interactions are not supported")
        if not self.sources:
            raise ValueError("native controller edges require evidence sources")


@dataclass(frozen=True)
class NativeControllerCatalog:
    controllers: tuple[NativeController, ...]
    surfaces: tuple[NativeControlSurface, ...]
    edges: tuple[NativeControllerEdge, ...]

    def validate(self) -> None:
        controller_ids = tuple(item.identity for item in self.controllers)
        if len(controller_ids) != len(set(controller_ids)):
            raise ValueError("duplicate native controller identity")

        surface_ids = tuple(item.identity for item in self.surfaces)
        if len(surface_ids) != len(set(surface_ids)):
            raise ValueError("duplicate native control-surface identity")

        controller_set = set(controller_ids)
        lookup_keys: set[tuple[NativeControlSurfaceKind, str]] = set()
        for surface in self.surfaces:
            if surface.controller_id not in controller_set:
                raise ValueError(
                    f"control surface '{surface.identity}' references unknown controller "
                    f"'{surface.controller_id}'"
                )
            if surface.lookup_key in lookup_keys:
                raise ValueError(
                    f"duplicate native control surface lookup key "
                    f"{surface.kind.value}:{surface.native_identifier}"
                )
            lookup_keys.add(surface.lookup_key)

        edge_keys: set[tuple[str, NativeControllerRelation, str]] = set()
        for edge in self.edges:
            if edge.source_controller not in controller_set:
                raise ValueError(
                    f"edge references unknown source controller '{edge.source_controller}'"
                )
            if edge.target_controller not in controller_set:
                raise ValueError(
                    f"edge references unknown target controller '{edge.target_controller}'"
                )
            key = (edge.source_controller, edge.relation, edge.target_controller)
            if key in edge_keys:
                raise ValueError(
                    "duplicate native controller edge "
                    f"{edge.source_controller}:{edge.relation.value}:{edge.target_controller}"
                )
            edge_keys.add(key)

    def controller(self, controller_id: str) -> NativeController:
        for controller in self.controllers:
            if controller.identity == controller_id:
                return controller
        raise KeyError(controller_id)

    def resolve_surface(
        self,
        kind: NativeControlSurfaceKind,
        native_identifier: str,
    ) -> NativeControlSurface:
        for surface in self.surfaces:
            if surface.kind is kind and surface.native_identifier == native_identifier:
                return surface
        raise KeyError(f"{kind.value}:{native_identifier}")

    def require_executable_surface(
        self,
        kind: NativeControlSurfaceKind,
        native_identifier: str,
    ) -> NativeControlSurface:
        surface = self.resolve_surface(kind, native_identifier)
        controller = self.controller(surface.controller_id)
        if surface.status is not PracticeStatus.CONTRACTED:
            raise ValueError(
                f"control surface '{native_identifier}' is not executable: "
                f"surface status is {surface.status.value}"
            )
        if controller.status is not PracticeStatus.CONTRACTED:
            raise ValueError(
                f"control surface '{native_identifier}' is not executable: "
                f"controller status is {controller.status.value}"
            )
        if surface.evidence is not EvidenceClass.ENGINE_FACT:
            raise ValueError(
                f"control surface '{native_identifier}' is not executable: "
                "surface evidence is not an engine fact"
            )
        if controller.evidence is not EvidenceClass.ENGINE_FACT:
            raise ValueError(
                f"control surface '{native_identifier}' is not executable: "
                "controller evidence is not an engine fact"
            )
        return surface

    def surfaces_for_controller(
        self,
        controller_id: str,
    ) -> tuple[NativeControlSurface, ...]:
        self.controller(controller_id)
        return tuple(
            surface
            for surface in self.surfaces
            if surface.controller_id == controller_id
        )

    def fingerprint(self) -> str:
        self.validate()

        payload = {
            "controllers": [
                {
                    "identity": item.identity,
                    "domain": item.domain.value,
                    "evidence": item.evidence.value,
                    "status": item.status.value,
                    "sources": item.sources,
                    "description": item.description,
                }
                for item in self.controllers
            ],
            "surfaces": [
                {
                    "identity": item.identity,
                    "controller_id": item.controller_id,
                    "kind": item.kind.value,
                    "native_identifier": item.native_identifier,
                    "evidence": item.evidence.value,
                    "status": item.status.value,
                    "sources": item.sources,
                    "description": item.description,
                }
                for item in self.surfaces
            ],
            "edges": [
                {
                    "source_controller": item.source_controller,
                    "target_controller": item.target_controller,
                    "relation": item.relation.value,
                    "evidence": item.evidence.value,
                    "status": item.status.value,
                    "sources": item.sources,
                }
                for item in self.edges
            ],
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _surface(
    controller_id: str,
    kind: NativeControlSurfaceKind,
    native_identifier: str,
    *,
    sources: tuple[str, ...],
    description: str,
) -> NativeControlSurface:
    identity = f"{controller_id}:{kind.value.lower()}:{native_identifier}"
    return NativeControlSurface(
        identity=identity,
        controller_id=controller_id,
        kind=kind,
        native_identifier=native_identifier,
        evidence=EvidenceClass.ENGINE_FACT
        if kind is NativeControlSurfaceKind.STRATEGIC_NUMBER
        else EvidenceClass.COMMUNITY_PRACTICE,
        status=PracticeStatus.EVIDENCE_ONLY,
        sources=sources,
        description=description,
    )


def default_native_controller_catalog() -> NativeControllerCatalog:
    """Return the currently evidence-backed native controller corpus."""
    airef_sn = "https://airef.github.io/strategic-numbers/sn-index.html"
    airef_performance = (
        "https://airef.github.io/resources/articles/command-performance.html"
    )
    scripting = "https://userpatch.aiscripters.net/reference.html"
    aoe2ai = "https://github.com/lewisc64/aoe2ai"
    duke = "https://github.com/niektb/AI"
    economy_forum = (
        "https://forums.ageofempires.com/t/creating-simple-ai-scripts-for-your-custom-campaigns/210881"
    )
    attack_forum = (
        "https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476"
    )

    controller_sources = {
        "civilian-task-allocation": (airef_sn, economy_forum, duke, aoe2ai),
        "exploration-control": (airef_sn, scripting, aoe2ai),
        "attack-group-control": (airef_sn, attack_forum, duke, aoe2ai),
        "town-size-defense-targeting": (airef_sn, attack_forum, duke),
        "resource-escrow-control": (scripting, duke),
        "duc-search-state": (airef_performance, aoe2ai),
    }

    controllers = (
        NativeController(
            identity="attack-group-control",
            domain=NativeControllerDomain.ATTACK,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["attack-group-control"],
            description=(
                "Native military attack-group behavior controlled through persistent "
                "Strategic Numbers and attack commands."
            ),
        ),
        NativeController(
            identity="civilian-task-allocation",
            domain=NativeControllerDomain.ECONOMY,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["civilian-task-allocation"],
            description=(
                "Native civilian task allocation and gatherer-percentage behavior "
                "steered by Strategic Number control surfaces."
            ),
        ),
        NativeController(
            identity="duc-search-state",
            domain=NativeControllerDomain.DUC,
            evidence=EvidenceClass.ENGINE_FACT,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["duc-search-state"],
            description=(
                "Stateful Direct Unit Control search-list/session behavior including "
                "search, reset, and search-state observation."
            ),
        ),
        NativeController(
            identity="exploration-control",
            domain=NativeControllerDomain.EXPLORATION,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["exploration-control"],
            description=(
                "Native exploration/group discovery behavior that determines which "
                "world objects are available to downstream attack logic."
            ),
        ),
        NativeController(
            identity="resource-escrow-control",
            domain=NativeControllerDomain.RESOURCE_CONTROL,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["resource-escrow-control"],
            description=(
                "Transient native resource protection through escrow and release "
                "controls used by production and research scripts."
            ),
        ),
        NativeController(
            identity="town-size-defense-targeting",
            domain=NativeControllerDomain.DEFENSE,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=controller_sources["town-size-defense-targeting"],
            description=(
                "Town-size and response-distance controls that steer native defense "
                "and targeting behavior."
            ),
        ),
    )

    surfaces = (
        _surface(
            "attack-group-control",
            NativeControlSurfaceKind.COMMAND,
            "attack-now",
            sources=controller_sources["attack-group-control"],
            description="Immediate native attack-group activation command.",
        ),
        *(
            _surface(
                "attack-group-control",
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                identifier,
                sources=controller_sources["attack-group-control"],
                description="Persistent attack-group control Strategic Number.",
            )
            for identifier in (
                "sn-number-attack-groups",
                "sn-percent-attack-soldiers",
            )
        ),
        *(
            _surface(
                "civilian-task-allocation",
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                identifier,
                sources=controller_sources["civilian-task-allocation"],
                description="Persistent civilian allocation Strategic Number.",
            )
            for identifier in (
                "sn-food-gatherer-percentage",
                "sn-gold-gatherer-percentage",
                "sn-percent-civilian-builders",
                "sn-percent-civilian-explorers",
                "sn-percent-civilian-gatherers",
                "sn-stone-gatherer-percentage",
                "sn-wood-gatherer-percentage",
            )
        ),
        *(
            _surface(
                "duc-search-state",
                NativeControlSurfaceKind.COMMAND,
                identifier,
                sources=controller_sources["duc-search-state"],
                description="DUC search/session state command.",
            )
            for identifier in (
                "up-find-local",
                "up-find-remote",
                "up-full-reset-search",
                "up-get-search-state",
            )
        ),
        *(
            _surface(
                "exploration-control",
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                identifier,
                sources=controller_sources["exploration-control"],
                description="Persistent exploration control Strategic Number.",
            )
            for identifier in (
                "sn-initial-exploration-required",
                "sn-number-explore-groups",
                "sn-total-number-explorers",
            )
        ),
        *(
            _surface(
                "resource-escrow-control",
                NativeControlSurfaceKind.COMMAND,
                identifier,
                sources=controller_sources["resource-escrow-control"],
                description="Escrow lifecycle control command.",
            )
            for identifier in (
                "release-escrow",
                "set-escrow-percentage",
            )
        ),
        *(
            _surface(
                "town-size-defense-targeting",
                NativeControlSurfaceKind.STRATEGIC_NUMBER,
                identifier,
                sources=controller_sources["town-size-defense-targeting"],
                description="Persistent town-size/response-distance control Strategic Number.",
            )
            for identifier in (
                "sn-enemy-sighted-response-distance",
                "sn-maximum-town-size",
            )
        ),
    )

    edges = (
        NativeControllerEdge(
            source_controller="attack-group-control",
            target_controller="exploration-control",
            relation=NativeControllerRelation.REQUIRES_EXPLORATION,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=(attack_forum,),
        ),
        NativeControllerEdge(
            source_controller="town-size-defense-targeting",
            target_controller="attack-group-control",
            relation=NativeControllerRelation.AFFECTS_TARGETING,
            evidence=EvidenceClass.COMMUNITY_PRACTICE,
            status=PracticeStatus.EVIDENCE_ONLY,
            sources=(attack_forum, duke),
        ),
    )

    catalog = NativeControllerCatalog(
        controllers=tuple(sorted(controllers, key=lambda item: item.identity)),
        surfaces=tuple(
            sorted(
                surfaces,
                key=lambda item: (
                    item.controller_id,
                    item.kind.value,
                    item.native_identifier,
                ),
            )
        ),
        edges=tuple(
            sorted(
                edges,
                key=lambda item: (
                    item.source_controller,
                    item.relation.value,
                    item.target_controller,
                ),
            )
        ),
    )
    catalog.validate()
    return catalog


__all__ = [
    "NativeController",
    "NativeControllerCatalog",
    "NativeControllerDomain",
    "NativeControllerEdge",
    "NativeControllerRelation",
    "NativeControlSurface",
    "NativeControlSurfaceKind",
    "default_native_controller_catalog",
]
