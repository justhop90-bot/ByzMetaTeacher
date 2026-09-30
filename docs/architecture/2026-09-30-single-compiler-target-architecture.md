# Single-compiler target architecture

Status: authoritative target architecture, 2026-09-30.
Scope: the generic AoE2DE .per compiler. Byzantine strategy is a first client and validation vehicle, not the generic compiler's semantic owner.

## Mission

Build one compiler that can absorb the durable practice of the AoE2 AI scripting community and compile that knowledge into ordinary, native .per behavior.

The target is not a Basilisk copy, tournament-specific bot, game simulator, universal scheduler, utility optimizer, or second public .per language.

The target is a semantic compiler whose knowledge can represent community control patterns without abandoning native engine semantics.

The governing causal chain is:

OBSERVATION -> ARBITRATION -> EXECUTION -> WITNESS -> RECOVERY -> REASSESSMENT

The action lifecycle underneath it is:

DEMAND -> ADMISSIBILITY -> CAPABILITY -> FEASIBILITY -> ACTION -> WORLD-STATE WITNESS -> RELEASE

Every domain eventually maps onto those chains.

## What the project has to become

The repository must evolve from a collection of successful semantic slices into one typed semantic machine with five properties.

### One semantic program

The compiler assembles one immutable CompilerSemanticProgram containing semantic demands, capability graph, operational loops, persistent-control plan, and domain execution plans.

Domain plans remain typed and owned by their domains. They do not form independent compiler channels with unrelated lifecycle rules.

The public compiler API may retain compatibility parameters while migration occurs. Internally, one assembled program becomes the authoritative compilation object.

### One lifecycle doctrine

Every executable behavior distinguishes strategic demand, permission/admission, provider/capability, execution request, pending state, world-state witness, release, invalidation, recovery, and reassessment.

can-* is never completion. Pending is never world truth. Timers are cadence controls, not truth. Native IDs establish identity, not liveness.

### One evidence doctrine

Every promoted semantic fact remains attributable to one of:
- ENGINE FACT
- COMMUNITY PRACTICE
- COMPILER POLICY
- OPEN / UNKNOWN

Community prevalence is precedent, not engine proof.

Unknown native behavior remains explicit and fail-closed. Runtime probes are evidence acquisition, not compiler inference.

### Native .per remains the executable language

The compiler may introduce typed internal IR, but not a hidden second scripting language.

Semantic IR describes intent and causal structure. Native binding decides whether the engine can express it. The emitter produces ordinary .per using Goals, Strategic Numbers, Timers, conditions, actions, DUC operations, control flow, and source ordering.

### Community knowledge becomes executable doctrine

A corpus entry is not finished when it has been counted or cited.

The maturity path is:

DISCOVERED -> CORROBORATED -> SEMANTICIZED -> EXPRESSIBLE -> LOWERABLE -> VERIFIED

The project exists to move durable community idioms through that pipeline.

## Core IR

The semantic spine is composed of existing typed IRs with one new assembly boundary.

    Evidence / Source Graph
            |
            v
    SemanticDemand
            |
            +--> CapabilityGraph
            |
            +--> PersistentControl
            |
            +--> Resource / Escrow claims
            |
            +--> OperationalLoop
                      |
                      +--> DUC SearchSession / TargetSession
                      +--> Production / Construction / Research lifecycle
                      +--> AttackExecution
                      +--> Native execution plan
            |
            v
    World Witness
            |
            v
    Release / Invalidation
            |
            v
    Recovery / Reassessment

SemanticDemand is the durable strategic intention. It owns identity, requirements, lifecycle storage, execution intent, witness/release contracts, ownership, resource claims, and recovery policy.

CapabilityGraph relates Demand -> Capability -> Provider -> Witness. It never treats a capability predicate as completion.

Persistent Control represents Goals, Strategic Numbers, and Timers as the native persistent-control plane. Symbolic ownership, lifetime, role, recurrence, and cleanup live in semantic IR; native numeric identifiers are assigned by binding.

OperationalLoop is the generic recurrent controller:

OBSERVE -> ADMIT -> REQUEST -> DEBOUNCE -> REOBSERVE -> REASSERT/RETRY

DUC has separate semantic identities for search state and target identity. SearchSession tracks query/filter/index generations and provenance. TargetSession tracks stored native identity, reacquisition, validation, and invalidation. Selected-target lifetime is never treated as object lifetime.

A Witness is a compiler-recognized observation that establishes a world or native state. Issuance and completion are distinct.

Recovery preserves strategic intent while invalidating stale execution state. The generic capability contract is:

LOSS -> BLOCKED -> RECOVERY -> ACTIVE

unless independent evidence establishes terminal invalidation.

## Domain composition

The finished compiler uses one semantic spine for:
- economy and infrastructure;
- construction;
- production and queue control;
- research;
- escrow and resource arbitration;
- DUC search/targeting;
- military composition;
- attack and defense;
- scouting and map knowledge;
- recovery and adaptation.

The implementation order is not the semantic order. The architecture is one system even while evidence arrives in tranches.

## Completion standard

The compiler is finished only when a representative community corpus can be transformed through:

community idiom -> semantic template -> demand/capability/lifecycle -> native .per

and the result is deterministic, provenance-traceable, fail-closed where evidence is absent, native-parser clean, source-order preserving, recoverable under temporary capability loss, and expressive enough to represent strategically important community control patterns.

Test count is a health metric, not the definition of done.

## Remaining capability frontier

The actual remaining frontier is:
1. production composition and queue lifecycle;
2. military composition and counter-policy;
3. attack lifecycle completion/release and controller observations;
4. broader DUC synthesis, not merely individual native operations;
5. escrow arbitration and runtime boundary closure;
6. adaptation/reassessment patterns across the community corpus;
7. broad map/scouting/forward/water/transport idioms;
8. late-game exhaustion and resource-depletion behavior;
9. deeper game-data prerequisites/effects and universal provenance;
10. conversion of the community idiom catalog into reusable semantic templates.

Those are the actual gaps. More wrapper classes are not.

## Architectural non-negotiables

- Do not add a second public compiler API for a domain when an existing channel can be extended safely.
- Do not copy downstream client strategy semantics into generic IR.
- Do not promote community usage into engine fact without evidence.
- Do not convert runtime OPEN questions into static compiler claims.
- Do not replace source ordering or recurrent behavior with an invented scheduler.
- Do not model object liveness from identity alone.
- Do not accept action issuance as completion.
- Do not weaken deterministic build behavior to gain expressive convenience.

## Lab acceptance gate

A semantic change is not accepted merely because unit tests pass.

Minimum sequence:

focused red/green -> compiler regression -> native zero-findings -> cross-platform determinism -> byte/artifact determinism -> documentation/evidence reconciliation

A failed verification step remains failed in project state until repaired or explicitly superseded by a newer verified run.

The repository is the lab notebook. Git history is the experiment history. CI is a measurement instrument. Runtime probes are external evidence acquisition. Documentation records current knowledge, not aspirations.
