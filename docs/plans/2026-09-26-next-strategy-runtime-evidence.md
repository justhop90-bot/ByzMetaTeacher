# Next Compiler Layer: StrategicEvidenceBinding and StrategyRuntimeState

Implement the next missing compiler layer as a typed runtime-facing semantic subsystem that turns StrategyProfile evidence into live strategic posture, demand activation, strategic invalidation, opportunity-cost override/release, and reassessment.

## Current architecture

    GameData
      -> CivProfile
      -> EffectiveCivData
      -> StrategyProfile
      -> StrategicDemandSpec
      -> StrategyRuntimeState
      -> SemanticDemand / CapabilityDemand
      -> existing lifecycle
      -> .per

Preserve this architecture. Do not create a second execution lifecycle.

The compiler already has typed GameData/CivProfile, deterministic EffectiveCivData, native command metadata, lifecycle through ACTIVE/ISSUED/PENDING/COMPLETE/RELEASED/CANCELLED, capability/provider validation, transient action exclusion, GoalSlot/GoalSpan binding, StrategyPosture, StrategicDemandSpec, StrategicEvidence, StrategicTarget, OpportunityCostPolicy, one-to-many execution mappings, shared factual capability identity, and native CI validation of the Dark -> Feudal -> Castle fixture.

The authoritative runtime player remains Basilisk/Basilisk.per.

## Missing capability

StrategyProfile can now describe that a strategic demand exists. It cannot yet evaluate live game evidence and determine:

- which posture is active now;
- which strategic demands are activated now;
- which strategic demands are merely persistent but currently blocked;
- which strategic demands have become strategically invalid;
- whether an emergency override is allowed to spend protected resources;
- when a posture transition causes a reassessment;
- which observations must persist because they cannot be reconstructed safely from current world state alone.

This is the next compiler boundary.

## New typed IR

Create LearnerAI/Compiler/ir/strategy_runtime.py.

### StrategicObservation

Represent one native or compiler-projected fact.

Minimum semantic kinds:

- CURRENT_AGE
- RESOURCE_AMOUNT
- BUILDING_COUNT
- UNIT_CURRENT_COUNT
- UNIT_QUEUED_COUNT
- UNIT_CURRENT_PLUS_QUEUED
- ENEMY_UNIT_COUNT
- ENEMY_BUILDING_COUNT
- ENEMY_COMPOSITION
- MAP_PROFILE
- OPENING_STATE
- PRESSURE_STATE
- CAPABILITY_STATE
- RESEARCH_STATE

Each observation must carry:

- stable identity;
- semantic type;
- native primitive;
- native parameter contract;
- provenance;
- evidence class: PERSISTENT, EXECUTION, or TIMING/INTERPRETATION.

Do not invent observations that are not supported by checked-in native metadata or existing Basilisk primitives.

### StrategicEvidenceBinding

Convert the existing StrategicEvidence expression into a typed semantic predicate.

Required flow:

    strategic evidence expression
      -> existing parser / expression AST
      -> native parameter/type validation
      -> typed strategic observation/predicate
      -> validated evidence binding

Do not create another AoE2 expression parser.

Reject:

- unknown native primitives;
- wrong native parameter family;
- unresolved identifiers;
- timing-only evidence promoted to strategic truth;
- action-only evidence promoted to strategic truth;
- expressions whose native semantics are not available to the compiler;
- evidence whose meaning changes with civilization without passing through EffectiveCivData.

### StrategyRuntimeState

Create an immutable semantic snapshot containing:

- current posture;
- previous posture;
- active strategic demands;
- strategically blocked demands;
- strategically invalidated demands;
- evaluated evidence state;
- reassessment reason;
- deterministic evaluation fingerprint;
- runtime storage requests only where persistence is genuinely required.

Do not duplicate ACTIVE, ISSUED, PENDING, COMPLETE, RELEASED, or CANCELLED here. Those remain execution lifecycle states.

## Posture evaluation

Evaluate StrategyProfile transitions deterministically.

Required decision form:

    from_postures
      + typed strategic evidence
      + transition priority
      -> next posture

Add deterministic validation for:

- equal-priority transitions with incompatible destinations;
- missing transition evidence;
- timer-only transitions;
- transitions referencing unsupported observations;
- transitions with no reachable destination;
- transition cycles that cannot be justified by reassessment evidence;
- posture changes that would invalidate a completed strategic state without explicit evidence.

Do not introduce a general-purpose finite-state-machine framework.

## Strategic demand activation

Preserve the distinction:

    strategic demand exists
        !=
    strategic demand is executable

A persistent strategic reason may remain true while can-build/can-train/can-research is false.

The runtime layer must represent at least:

- STRATEGIC_INACTIVE
- STRATEGIC_ACTIVE_EXECUTABLE
- STRATEGIC_ACTIVE_BLOCKED
- STRATEGIC_INVALIDATED
- STRATEGIC_COMPLETE

These are strategic semantic categories, not replacements for the existing lifecycle.

Temporary execution failure must not destroy strategic intent.

## Invalidation

Strategic invalidation occurs only from typed invalidation evidence.

Keep separate:

- native feasibility false;
- action not issued;
- pending admission missing;
- execution failure;
- strategic invalidation.

An invalidated strategic demand may cause its execution demand to enter the existing cancellation path, but the compiler must not synthesize strategic invalidation from execution failure.

## Opportunity-cost runtime

Use the existing OpportunityCostPolicy.

Represent:

- protected resource active;
- protected resource temporarily overridden;
- protected resource released.

An emergency override must be justified by the currently selected posture and explicit policy metadata.

Do not build:

- global scheduler;
- fair-share allocator;
- invisible resource jobs;
- optimizer.

If runtime resource claims are necessary, lower them into the existing transient resource/conflict IR.

## Strategic reassessment

Support explicit reassessment causes:

- posture change;
- demand activation;
- demand invalidation;
- capability completion;
- capability loss;
- enemy composition change;
- age transition;
- map/opening state change.

Reassessment must not blindly reset execution state.

Example expected semantics:

    BOOM
      -> cavalry pressure observed
      -> FLUSH
      -> Spear strategic demand activates
      -> Castle demand remains strategically active
      -> Castle execution can be blocked by resource policy
      -> pressure disappears
      -> BOOM/Castle trajectory is reconsidered

## Runtime binding

Do not allocate native storage yet merely because a strategic state exists.

First determine whether state can be recomputed from current world observations.

Only state that must persist across passes and cannot be reconstructed safely should request GoalSlot storage.

Use RuntimeBinder for actual storage allocation.

Do not allocate Strategic Numbers until an observed strategy requirement proves they are necessary.

## First vertical slice

Extend the existing Castle fixture to demonstrate live strategic evaluation.

Dark:

- posture unresolved or selected from opening evidence;
- Feudal demand active;
- Castle demand not yet executable.

Feudal BOOM:

- Castle strategic demand active;
- Castle stone protection active;
- minimum defensive Spear demand can remain active;
- Feudal infrastructure demand can execute.

Feudal pressure:

- pressure evidence becomes true;
- posture changes deterministically to FLUSH or RUSH;
- defensive Spear demand becomes active;
- Castle demand remains strategically active unless its own invalidation evidence becomes true;
- Castle stone policy may be overridden only by an explicitly allowed emergency path.

Castle completion:

- Castle world-state witness becomes true;
- Castle strategic demand becomes strategically complete;
- Castle-posture reassessment becomes eligible;
- posture becomes CASTLE-POWER;
- Castle construction opportunity-cost protection releases;
- unrelated execution state remains intact.

## Tests

Use TDD.

Required failing-first tests:

1. persistent Castle reason remains active when can-build Castle is false;
2. strategic invalidation cancels intent only when invalidation evidence is true;
3. timing-only posture transition is rejected;
4. equal-priority incompatible transitions are rejected;
5. posture selection is deterministic when multiple evidence predicates are true;
6. one strategic demand keeps one strategic owner across multiple execution mappings;
7. two strategic demands sharing one factual capability keep distinct strategic identities;
8. protected Castle stone survives ordinary Feudal execution;
9. emergency posture can override protection only when explicitly allowed;
10. Castle completion releases the opportunity-cost policy without resetting unrelated execution state;
11. current-age evidence binds to the native Current Age parameter family;
12. enemy composition evidence is accepted only from verified native observations;
13. unresolved native evidence fails closed rather than becoming false;
14. StrategyRuntimeState contains no second lifecycle state machine;
15. the runtime evaluator works for a synthetic non-Byzantine profile without civilization-specific branches.

Add deterministic runtime-state fingerprints.

## Compiler integration

Add an entry point such as:

    compile_strategy_runtime_profile(profile, effective, runtime_profile)

Required lowering chain:

    StrategyRuntimeState
      -> strategic activation/invalidation
      -> SemanticDemand
      -> ownership
      -> witness
      -> release
      -> invalidation
      -> issuance
      -> capability
      -> resource/conflict
      -> runtime binding
      -> .per

Do not emit .per directly from the runtime evaluator.

## Native verification

Extend .github/workflows/compiler-tests.yml with a strategy-runtime fixture that exercises:

- posture-dependent activation;
- Castle-demand persistence when feasibility is blocked;
- emergency resource override;
- Castle completion and reassessment.

The generated artifact must pass the pinned aoe2-ai-parser validator.

## Repository and community cross-check

Audit before implementation:

- Basilisk/Basilisk.per;
- docs/project/BotDirection.txt;
- docs/project/Basilisk-Controller-Specification.md;
- current opening and pressure strategy modules;
- Castle/BOOM opportunity-cost audits;
- military floor and enemy-composition logic;
- current strategic posture Goal writers/readers;
- current source-order around posture changes.

Use AIRef for native observation/parameter facts; The Duke and Niek/Atilla for community-native age/resource/military state conventions; AgeScript and AgeOfPython only for typed metadata/lowering discipline.

Do not copy another AI's architecture.

## Acceptance

The layer is complete only when the compiler can answer for one actual runtime state:

    What posture is active?
    Why is it active?
    Which strategic demands are active?
    Which are strategically blocked?
    Which are invalidated?
    Which factual capabilities satisfy them?
    Which resource policies protect them?
    What evidence will trigger reassessment?
    What world-state evidence proves strategic completion?

while preserving:

    strategic intent
        != strategic activation
        != execution state
        != feasibility
        != world-state truth

Do not modify Basilisk gameplay rules merely to make the compiler look useful. The compiler must learn to represent the controller that already exists.