"""Evidence-backed native AoE2 .per engine semantics.

This module is deliberately descriptive rather than a second scripting language.
It records the engine/community contracts that a typed compiler needs to preserve:
state persistence, recurrent rule passes, asynchronous work, resource arbitration,
DUC/attack lifetimes, and recovery without inventing hidden runtime machinery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EvidenceClass(str, Enum):
    ENGINE_FACT = "ENGINE FACT"
    COMMUNITY_PRACTICE = "COMMUNITY PRACTICE"
    COMPILER_POLICY = "COMPILER POLICY"
    OPEN_UNKNOWN = "OPEN / UNKNOWN"


class PracticeStatus(str, Enum):
    CONTRACTED = "CONTRACTED"
    PARTIAL = "PARTIAL"
    EVIDENCE_ONLY = "EVIDENCE_ONLY"
    OPEN = "OPEN"


class CapabilityTransition(str, Enum):
    UNKNOWN = "UNKNOWN"
    NO_CHANGE = "NO_CHANGE"
    LOST = "LOST"
    RECOVERED = "RECOVERED"


class LifecyclePhase(str, Enum):
    ADMISSIBLE = "ADMISSIBLE"
    ISSUED = "ISSUED"
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"


def classify_capability_transition(
    previous: Optional[bool],
    current: Optional[bool],
) -> CapabilityTransition:
    """Classify a capability edge without inventing an engine failure channel."""
    if previous is True and current is False:
        return CapabilityTransition.LOST
    if previous is False and current is True:
        return CapabilityTransition.RECOVERED
    if previous is None or current is None:
        return CapabilityTransition.UNKNOWN
    return CapabilityTransition.NO_CHANGE


def capability_loss_preserves_demand(transition: CapabilityTransition) -> bool:
    """Temporary capability loss preserves the original strategic identity."""
    return transition is CapabilityTransition.LOST


@dataclass(frozen=True)
class EnginePractice:
    identity: str
    domain: str
    rule: str
    evidence: EvidenceClass
    status: PracticeStatus
    sources: tuple[str, ...]
    compiler_action: str
    runtime_truth: str


@dataclass(frozen=True)
class EngineLifecycleContract:
    action: str
    feasibility_fact: str
    pending_fact: str | None
    completion_witness: str
    pending_is_completion: bool = False
    temporary_failure_preserves_intent: bool = True


@dataclass(frozen=True)
class CommunityEngineSemanticsRegistry:
    practices: tuple[EnginePractice, ...]
    lifecycle_contracts: tuple[EngineLifecycleContract, ...]

    def practice(self, identity: str) -> EnginePractice:
        for item in self.practices:
            if item.identity == identity:
                return item
        raise KeyError(identity)

    def lifecycle(self, action: str) -> EngineLifecycleContract:
        for item in self.lifecycle_contracts:
            if item.action == action:
                return item
        raise KeyError(action)

    def validate(self) -> None:
        identities = [item.identity for item in self.practices]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate community engine practice identity")
        actions = [item.action for item in self.lifecycle_contracts]
        if len(actions) != len(set(actions)):
            raise ValueError("duplicate engine lifecycle contract")
        for practice in self.practices:
            if not practice.sources:
                raise ValueError(f"practice '{practice.identity}' has no evidence source")
            if not practice.compiler_action or not practice.runtime_truth:
                raise ValueError(f"practice '{practice.identity}' lacks an explicit contract")
        for contract in self.lifecycle_contracts:
            if contract.pending_is_completion:
                raise ValueError(
                    f"lifecycle contract '{contract.action}' incorrectly treats pending as completion"
                )


def default_community_engine_registry() -> CommunityEngineSemanticsRegistry:
    """Return the current evidence-backed community engine contract catalog."""
    airef = "https://airef.github.io/"
    limits = "https://airef.github.io/resources/articles/data-limits.html"
    performance = "https://airef.github.io/resources/articles/command-performance.html"
    duke = "https://github.com/niektb/AI"
    scripting = "https://userpatch.aiscripters.net/reference.html"
    aoe2ai = "https://github.com/lewisc64/aoe2ai"
    forum_attack = "https://forums.ageofempires.com/t/three-ways-to-get-the-ai-to-attack/205476"

    practices = (
        EnginePractice(
            "state.goal.persistent",
            "persistent-state",
            "Goal values survive rule passes; later writes replace the stored value.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.CONTRACTED,
            (limits, scripting, aoe2ai),
            "Treat Goal reads/writes as engine-backed persistent state; never model them as a same-rule-only latch.",
            "A Goal remains readable in later passes until another action changes it.",
        ),
        EnginePractice(
            "state.sn.engine-control",
            "persistent-state",
            "Strategic Numbers are persistent engine control surfaces, not generic integers with uniform semantics.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.PARTIAL,
            (limits, scripting),
            "Bind SN storage with an explicit semantic ID and native SN contract; do not assign generic behavior to an unknown SN.",
            "An SN write can alter built-in engine behavior and may have civ/patch-specific meaning.",
        ),
        EnginePractice(
            "state.timer.explicit-rearm",
            "timing-state",
            "Timers are explicit engine state: enable/rearm, test timer-triggered, then disable or rearm deliberately.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.CONTRACTED,
            (scripting,),
            "Treat timer state as timing/control state, never as strategic truth or completion evidence.",
            "A disabled timer does not satisfy timer-triggered; elapsed intervals do not prove world-state completion.",
        ),
        EnginePractice(
            "rules.recurrent-pass-order",
            "rule-order",
            "Rules are evaluated repeatedly; separate rules form pass boundaries while actions within one rule remain sequential.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.CONTRACTED,
            (scripting, airef),
            "Record emitted rule order and within-rule order separately; do not invent an asynchronous boundary inside one rule.",
            "A later rule sees engine-backed state produced by an earlier rule/pass, subject to native execution timing.",
        ),
        EnginePractice(
            "actions.request-not-completion",
            "lifecycle",
            "A native action requests work; a later world-state witness proves completion.",
            EvidenceClass.COMPILER_POLICY,
            PracticeStatus.CONTRACTED,
            (airef, duke),
            "Keep action issuance, pending state, and completion witnesses distinct.",
            "There is no generic native Boolean action-return channel to substitute for a witness.",
        ),
        EnginePractice(
            "pending.work-queue-guard",
            "lifecycle",
            "Pending objects represent outstanding engine work and are commonly used to suppress duplicate build requests.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.CONTRACTED,
            (aoe2ai, duke),
            "Use pending facts as anti-duplication execution guards, never as completion witnesses.",
            "A pending foundation/queue entry can exist before the requested world object is complete.",
        ),
        EnginePractice(
            "build.can-pending-witness",
            "lifecycle",
            "Community build rules commonly pair can-build with pending-object guards and a world-state count witness.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.CONTRACTED,
            (aoe2ai, duke),
            "Guard build issuance with native feasibility and duplicate-prevention evidence; witness the resulting building in world state.",
            "A build request may fail, be blocked, or remain pending without meaning the strategic demand is obsolete.",
        ),
        EnginePractice(
            "train.can-queue-witness",
            "lifecycle",
            "Training rules gate on can-train and reason about current/queued counts; completion is a unit-world-state condition.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.CONTRACTED,
            (aoe2ai, duke),
            "Keep train feasibility, queue/pending state, and target-count witness distinct.",
            "Queue acceptance does not mean the requested unit already exists.",
        ),
        EnginePractice(
            "research.can-complete-witness",
            "lifecycle",
            "Research issuance is feasibility-gated and completion is observed through research state, not timer expiry.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.CONTRACTED,
            (scripting, airef),
            "Use can-research as admission and research-completed as the world-state witness.",
            "Research can remain unavailable or blocked without cancelling the strategic reason for wanting it.",
        ),
        EnginePractice(
            "resources.transient-arbitration",
            "resource-control",
            "Shared-resource controls are used as temporary arbitration, while the strategic reason remains elsewhere.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.PARTIAL,
            ("https://gist.github.com/labarilem/e760e38ae1cf18dbcdbf5f4248ead7bd", duke),
            "Model resource claims as transient execution constraints; require explicit release and preserve demand ownership.",
            "Resource shortage changes feasibility/arbitration, not the truth of the strategic objective itself.",
        ),
        EnginePractice(
            "duc.search-state-retained",
            "duc",
            "DUC searches maintain mutable local/remote search state with bounded lists and explicit reset/reuse behavior.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.EVIDENCE_ONLY,
            (airef, limits, performance),
            "Treat search state, list scope, filter scope, and target lifetime as explicit compiler state before accepting DUC lowering.",
            "A retained search target can become stale when the world changes; cardinality also affects cost.",
        ),
        EnginePractice(
            "duc.performance-cardinality",
            "duc-performance",
            "Search, pathing, building-at-point and movement operations have materially different pass costs.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.EVIDENCE_ONLY,
            (performance,),
            "Attach qualitative cost/cardinality metadata before allowing unconstrained repeated DUC loops.",
            "A script can be functionally correct and still produce lag or queue backlog through excessive per-pass work.",
        ),
        EnginePractice(
            "attack.group-state-control",
            "attack-machinery",
            "Community attack loops commonly control attack-groups or attack-now through persistent SNs plus timers/cooldowns.",
            EvidenceClass.COMMUNITY_PRACTICE,
            PracticeStatus.EVIDENCE_ONLY,
            (forum_attack, scripting),
            "Represent attack mode state, activation timing, and release separately from strategic demand ownership.",
            "Attack machinery continues to act until its controlling state is changed; it is not a one-shot function call.",
        ),
        EnginePractice(
            "recovery.intent-preservation",
            "recovery",
            "Temporary capability loss changes execution admissibility but should preserve a still-valid strategic demand.",
            EvidenceClass.COMPILER_POLICY,
            PracticeStatus.CONTRACTED,
            (duke, aoe2ai),
            "Detect only true->false capability transitions; preserve the original demand/execution identity and re-enter through the same can-* path on recovery.",
            "The engine does not provide a generic failure event for native actions, so recovery must derive from world-state/capability observations.",
        ),
        EnginePractice(
            "load.preprocessor-reachable-graph",
            "load-preprocessor",
            "#load and #load-if-defined expand the effective source program and have documented nesting limits.",
            EvidenceClass.ENGINE_FACT,
            PracticeStatus.EVIDENCE_ONLY,
            (limits, airef),
            "Treat auxiliary files and conditional loads as program graph inputs before claiming global storage or rule-order completeness.",
            "The effective program may differ from one physical .per file; source reachability is part of semantics.",
        ),
    )

    lifecycle_contracts = (
        EngineLifecycleContract(
            action="build",
            feasibility_fact="can-build",
            pending_fact="up-pending-objects",
            completion_witness="building-type-count-total",
        ),
        EngineLifecycleContract(
            action="train",
            feasibility_fact="can-train",
            pending_fact="up-pending-objects",
            completion_witness="unit-type-count-total",
        ),
        EngineLifecycleContract(
            action="research",
            feasibility_fact="can-research",
            pending_fact=None,
            completion_witness="research-completed",
        ),
    )
    registry = CommunityEngineSemanticsRegistry(practices, lifecycle_contracts)
    registry.validate()
    return registry
