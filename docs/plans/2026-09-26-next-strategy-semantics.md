# Next Compiler Layer: StrategyProfile and Strategic-Demand Binding

Implement the next missing compiler layer as a typed semantic subsystem above EffectiveCivData and below the existing SemanticDemand/Capability lifecycle machinery.

## Current state

The compiler now has typed GameData, CivProfile, deterministic EffectiveCivData, versioned evidence, native engine metadata, lifecycle IR through ACTIVE/ISSUED/PENDING/COMPLETE/RELEASED/CANCELLED, capability/provider validation, transient resource arbitration, runtime Goal binding, and pinned native validation.

The generated Basilisk file is still only a lifecycle fixture. The authoritative runtime player remains Basilisk/Basilisk.per.

## Missing capability

The compiler can now answer what Byzantines can do. It cannot yet represent why the player wants a capability, which strategic posture owns it, what persistent target should survive temporary execution failure, what resource reserve protects the plan, or how strategic intent becomes one or more existing SemanticDemand objects.

## Required architecture

Preserve:

    GameData
      -> CivProfile
      -> EffectiveCivData
      -> StrategyProfile
      -> StrategicDemand
      -> SemanticDemand / CapabilityDemand
      -> existing lifecycle
      -> .per

Do not put strategy back into GameData or native metadata.

## Required typed IR

### StrategyProfile

Create an immutable profile bound to one EffectiveCivData snapshot. It contains supported game/map envelope, strategic postures, strategic demand specifications, target definitions, admissibility/invalidation evidence, opportunity-cost policies, and provenance.

### StrategicPosture

Support the Basilisk vocabulary already present in the controller: FLUSH, RUSH, BOOM, CASTLE-POWER. Posture changes must be evidence-driven, not timer phases.

### StrategicDemandSpec

Every strategic demand must carry stable identity, owner/posture, reason, target or capability intent, priority class, invalidation, resource policy, and an explicit mapping contract to existing execution demands.

The strategic reason must survive temporary feasibility failure.

### StrategicTarget

Support exact target, minimum standing floor, current+queued target, and bounded package target. Keep strategic sufficiency distinct from execution witnesses.

### OpportunityCostPolicy

Represent protected resource intent such as Castle stone protection, Imperial bank protection, emergency defense exceptions, and release on completion or strategic invalidation. This is not a global scheduler.

### AdmissibilityEvidence

Distinguish persistent strategic evidence, transient execution evidence, and timing evidence. Timing must never become strategic truth merely because it is convenient.

## Deterministic lowering contract

Implement:

    StrategicDemandSpec -> SemanticDemand / CapabilityDemand

The bridge must preserve strategy owner, demand identity, capability identity, admissibility, target quantity, invalidation, resource/conflict intent, and provenance.

Do not emit .per directly from StrategyProfile.

## First vertical slice

Build one real Dark -> Feudal -> Castle slice:

1. economic continuation;
2. Feudal transition;
3. minimum early defensive military package;
4. optional Feudal infrastructure;
5. Castle commitment;
6. Castle resource protection;
7. Castle completion;
8. Castle-posture reassessment.

Use the current Byzantine EffectiveCivData snapshot. The Castle demand must demonstrate persistent strategic reason -> capability chain -> resource protection -> native feasibility -> action lifecycle -> world witness -> release -> reassessment.

## Community cross-check

Audit AIRef, The Duke, Niek/Atilla, AgeScript, AgeOfPython, Basilisk/Basilisk.per, docs/project/BotDirection.txt, docs/project/Basilisk-Controller-Specification.md, LearnerAI/Strategy, LearnerAI/Economy, LearnerAI/Production, and the current Castle/BOOM opportunity-cost audits.

Adopt community mechanisms only where their engine behavior is relevant. Do not copy their architecture.

## TDD requirements

First red test: a StrategyProfile containing one Castle strategic demand resolves against Byzantine EffectiveCivData.

Then add negative tests for unavailable entities, missing provider, missing strategic reason, lost strategic identity, missing resource owner, execution failure incorrectly cancelling strategy, late invalidation after completion, and timing-only strategic truth.

Add deterministic fingerprint tests and at least one non-Byzantine fixture to prevent civilization-specific compiler branches.

## Acceptance

The layer is complete only when the compiler can explain why a Castle demand exists, which factual capability satisfies it, what blocks execution, which strategic resource policy protects it, and what world-state observation releases it, while preserving the distinction between strategic intent, capability, feasibility, execution state, and world-state truth.

Do not modify Basilisk gameplay rules merely to make the compiler architecture look useful.

## Implementation result

This planned layer is implemented on main.

The compiler now has StrategyProfile, StrategicDemandSpec, typed strategic evidence, opportunity-cost policy, one-to-many execution mapping, shared factual capability identity, and a native-validated Dark -> Feudal -> Castle fixture.

Final verification for the implementation head:
- CI run 368: generated Basilisk fixture finding_count=0.
- CI run 368: strategy fixture finding_count=0.
- CI run 368: invalidation fixture finding_count=0.
- CI run 368: 190 compiler tests passed.

The next missing layer is not another static strategy type. It is StrategicEvidenceBinding / StrategyRuntimeState, which must evaluate live native observations into posture selection, strategic demand activation/invalidation, opportunity-cost override/release, and reassessment without duplicating the execution lifecycle.
