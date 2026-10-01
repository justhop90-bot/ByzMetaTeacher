"""Typed threat-to-counter package data for the strategy layer.

Counter packages are policy data. They reuse the existing StrategicEvidence
binding and StrategicDemand lifecycle; they do not schedule actions themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .civ_profile import EffectiveCivData
    from .strategy import StrategyProfile, StrategicEvidence


class CounterThreatClass(str, Enum):
    MOUNTED = "MOUNTED"
    RANGED = "RANGED"
    INFANTRY = "INFANTRY"
    SIEGE = "SIEGE"
    MIXED = "MIXED"


@dataclass(frozen=True)
class CounterPackage:
    identity: str
    threat_class: CounterThreatClass
    priority: int
    trigger: "StrategicEvidence"
    demand_identities: tuple[str, ...]
    policy_recipe_identity: str | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("counter package identity must not be empty")
        if self.priority < 0:
            raise ValueError("counter package priority must not be negative")
        if not self.demand_identities:
            raise ValueError(
                f"counter package '{self.identity}' requires at least one demand"
            )
        if len(self.demand_identities) != len(set(self.demand_identities)):
            raise ValueError(
                f"counter package '{self.identity}' has duplicate demand identities"
            )
        if any(not item.strip() for item in self.demand_identities):
            raise ValueError(
                f"counter package '{self.identity}' contains an empty demand identity"
            )
        if not self.rationale.strip():
            raise ValueError(
                f"counter package '{self.identity}' requires a rationale"
            )


def validate_counter_packages(profile: "StrategyProfile") -> None:
    identities = [package.identity for package in profile.counter_packages]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate counter package identity")

    for package in profile.counter_packages:
        for demand_identity in package.demand_identities:
            profile.demand(demand_identity)
        if package.policy_recipe_identity is not None:
            profile.policy_recipe(package.policy_recipe_identity)
        if package.trigger.kind.value != "PERSISTENT":
            raise ValueError(
                f"counter package '{package.identity}' requires PERSISTENT trigger evidence"
            )
        if package.trigger.observation_ref is None:
            raise ValueError(
                f"counter package '{package.identity}' requires a native observation reference"
            )


def default_byzantine_counter_packages(
    effective: "EffectiveCivData",
) -> tuple[CounterPackage, ...]:
    from .strategy import (
        StrategicEvidence,
        StrategicEvidenceKind,
        StrategicEvidenceSource,
    )

    scout_provenance = effective.unit_line("scout-cavalry-line").provenance
    archer_provenance = effective.unit_line("archer-line").provenance
    knight_provenance = effective.unit_line("knight-line").provenance
    militia_provenance = effective.unit_line("militia-line").provenance

    return (
        CounterPackage(
            identity="MOUNTED_PRESSURE_FEUDAL",
            threat_class=CounterThreatClass.MOUNTED,
            priority=100,
            trigger=StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                None,
                "Feudal mounted pressure detected",
                source=StrategicEvidenceSource.AUTHORING,
                provenance=scout_provenance,
                observation_ref="enemy-feudal-mounted-pressure",
            ),
            demand_identities=("counter-mounted-spears",),
            policy_recipe_identity=None,
            rationale="Build the cheapest credible anti-mounted screen when mounted pressure is decision-grade.",
        ),
        CounterPackage(
            identity="RANGED_PRESSURE_FEUDAL",
            threat_class=CounterThreatClass.RANGED,
            priority=95,
            trigger=StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                None,
                "Feudal ranged pressure detected",
                source=StrategicEvidenceSource.AUTHORING,
                provenance=archer_provenance,
                observation_ref="enemy-ranged-pressure",
            ),
            demand_identities=("counter-ranged-skirmishers",),
            policy_recipe_identity="RANGED_HOLD",
            rationale="Use the discounted ranged counter before upgrading the package into a premium composition.",
        ),
        CounterPackage(
            identity="MOUNTED_PRESSURE_CASTLE",
            threat_class=CounterThreatClass.MOUNTED,
            priority=110,
            trigger=StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                None,
                "Castle mounted pressure detected",
                source=StrategicEvidenceSource.AUTHORING,
                provenance=knight_provenance,
                observation_ref="enemy-knight-pressure",
            ),
            demand_identities=("counter-castle-camels",),
            policy_recipe_identity=None,
            rationale="Escalate the anti-mounted response after sustained Castle cavalry commitment.",
        ),
        CounterPackage(
            identity="INFANTRY_PRESSURE_CASTLE",
            threat_class=CounterThreatClass.INFANTRY,
            priority=105,
            trigger=StrategicEvidence(
                StrategicEvidenceKind.PERSISTENT,
                None,
                "Castle infantry pressure detected",
                source=StrategicEvidenceSource.AUTHORING,
                provenance=militia_provenance,
                observation_ref="enemy-infantry-pressure",
            ),
            demand_identities=("counter-castle-cataphracts",),
            policy_recipe_identity=None,
            rationale="Use the premium anti-infantry transition when a real infantry mass justifies it.",
        ),
    )


__all__ = [
    "CounterPackage",
    "CounterThreatClass",
    "default_byzantine_counter_packages",
    "validate_counter_packages",
]
