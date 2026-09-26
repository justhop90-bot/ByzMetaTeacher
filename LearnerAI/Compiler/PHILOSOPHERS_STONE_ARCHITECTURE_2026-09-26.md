# Philosopher's Stone Architecture — 2026-09-26

## Purpose

The Philosopher's Stone is not a larger Demand/Capability framework.

It is the missing compiler architecture that turns accumulated native/community .per engine knowledge into explicit, typed, evidence-backed semantics without replacing the AoE2 engine or turning Basilisk into a scheduler.

Its purpose is to make the compiler answer, for every supported native construct:

- What native construct is this?
- What engine state does it read?
- What engine state does it write or mutate?
- How long does that state live?
- Can the construct fire repeatedly?
- What can disable or invalidate it?
- What does native feasibility mean?
- What outstanding work can exist after issuance?
- What proves completion?
- What survives temporary failure?
- What storage namespace is consumed?
- What community practice is established?
- What is merely compiler policy?
- What remains unknown?

## Architectural doctrine

The native AoE2 engine remains the runtime authority.

The compiler does not simulate the engine.

The compiler records and validates the semantic contracts necessary to lower a typed program into native .per.

Basilisk strategy remains a downstream client.

No universal scheduler.
No universal manager.
No hidden action-success Boolean.
No artificial recovery FSM.
No second .per language.

## The architecture

    Evidence / AIRef / Native parser
                 |
                 v
    +-----------------------------+
    | Native Knowledge Catalog    |
    | commands / parameters / SNs |
    | limits / versions / quirks  |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Effective Source Graph      |
    | #load / #load-if / source   |
    | order / provenance          |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Native Semantic Binder      |
    | state effects / lifetime    |
    | admission / outputs         |
    | recurrence / side effects   |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Engine State Model          |
    | Goals / SNs / Timers        |
    | queues / pending / DUC      |
    | targets / attack state      |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Rule Execution Semantics    |
    | eligibility / source order  |
    | disable-self / overwrites   |
    | starvation / reachability   |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Semantic IR                 |
    | demand / capability         |
    | feasibility / action       |
    | pending / witness / release |
    | recovery / provenance       |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Static Semantic Gates       |
    | ownership / ordering       |
    | resource / async / DUC      |
    | evidence / cost / closure   |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Deterministic Lowering      |
    | storage binding / emitter   |
    +-----------------------------+
                 |
                 v
    +-----------------------------+
    | Native Backend Gate         |
    | native parser / zero-find   |
    +-----------------------------+
                 |
                 v
               .per
                 |
                 v
             AoE2 runtime

## Component contracts

### 1. Native Knowledge Catalog

Owns raw engine facts.

Inputs:
- AIRef command schema;
- parameter schema;
- Strategic Number inventory;
- data limits;
- patch notes;
- native parser identity.

Outputs:
- native-known;
- native-typed;
- versioned parameter contracts;
- storage/output contracts;
- native support status.

It must not decide strategy meaning.

### 2. Effective Source Graph

Owns the program actually seen by the engine.

It resolves:
- physical source files;
- #load reachability;
- #load-if-defined and #load-if-not-defined;
- conditional branches;
- effective source order;
- source provenance.

It feeds:
- rule numbering;
- storage occupancy;
- constant visibility;
- native semantic analysis.

A single physical .per file is not necessarily the complete program.

### 3. Native Semantic Binder

This is the central missing component.

For every semantically mapped command it records:

NativeCommandContract:
- command identity;
- facts/actions/dual role;
- input parameters;
- output parameters;
- mutable state;
- storage namespaces;
- recurrence;
- side effects;
- action admission;
- completion relationship;
- invalidation/recovery relationship;
- performance class;
- patch/version scope;
- evidence provenance.

The binder is where raw AIRef knowledge becomes compiler-usable engine semantics.

### 4. Engine State Model

The engine state model is typed by native mechanism, not by generic variable.

State families:

GOAL
- scalar Goal;
- GoalSpan;
- persistent Goal;
- execution scratch;
- native output.

STRATEGIC_NUMBER
- active engine control;
- conditional/custom-safe storage;
- obsolete/unused storage;
- patch-sensitive behavior.

TIMER
- disabled;
- armed;
- triggered;
- rearmed;
- owner;
- release/cleanup responsibility.

ASYNC_WORK
- admissible;
- issued;
- pending;
- completed;
- cancelled;
- invalidated.

DUC
- local list;
- remote list;
- search filters;
- search state;
- target object;
- target point;
- group;
- Goal outputs;
- reset semantics.

ATTACK_ENGINE
- attack mode;
- attack-group control;
- exploration dependency;
- cooldown;
- target/release state.

No generic StateValue type may erase these distinctions.

### 5. Rule Execution Semantics

This component models the fact that .per is a recurrent production-rule system.

It tracks:

- eligibility predicate;
- emitted rule order;
- within-rule action order;
- recurrent versus one-shot behavior;
- disable-self lifetime;
- persistent-state writes;
- later writes/overwrites;
- potential preemption;
- starvation;
- unreachable rules;
- open-loop state changes.

Important:

rule_order establishes source precedence.

rule_order does not prove execution.

A rule may never fire.
A rule may fire once.
A rule may fire repeatedly.
A rule may disable itself.
A rule may be dominated by an earlier persistent-state mutation.

The analyzer must represent these as different statuses.

### 6. Asynchronous Work Semantics

Native action issuance produces requests to an engine that continues work after the rule has fired.

The semantic protocol is:

STRATEGIC INTENT
-> ADMISSIBLE
-> ISSUE
-> PENDING
-> WORLD-STATE WITNESS
-> COMPLETE
-> RELEASE / REASSESS

Action issuance never proves completion.

Pending never proves completion.

A timer never proves completion unless the native command explicitly defines timer state as the requested effect.

### 7. Capability Semantics

Capability has two distinct meanings that must never be collapsed:

PROVIDER/CAPABILITY STATE
- Castle exists;
- Barracks exists;
- research completed;
- production infrastructure exists.

EXECUTION FEASIBILITY
- can-build;
- can-train;
- can-research;
- can-afford.

Capability loss is a temporal provider transition:

previous provider/capability = available
current provider/capability = unavailable

Feasibility false is not capability loss.

Recovery returns to the original strategic demand and execution mapping.

### 8. DUC Semantic Subsystem

DUC is implemented as a stateful subsystem, not as individual stateless commands.

Its IR must represent:

SearchSession:
- list kind;
- list contents;
- search query;
- filters;
- retained state;
- reset operation;
- result provenance;
- cardinality.

TargetSession:
- selected target;
- target source list;
- target validity;
- point/object type;
- target invalidation.

DUCGroup:
- group identity;
- membership;
- group lifetime;
- reuse;
- invalidation.

DUCOutput:
- GoalSpan output;
- point;
- search state;
- object data.

A DUC action is valid only when its required list/filter/target state is proven compatible.

### 9. Resource Arbitration

Resource semantics remain transient unless the native engine itself defines a durable control effect.

The model is:

strategic owner
    |
    v
execution demand
    |
    v
temporary resource claim
    |
    v
native action
    |
    v
release / reassess

The compiler must detect:
- missing release;
- conflicting owners;
- starvation;
- accidental global locks.

It must not create a universal priority scheduler.

### 10. Evidence Registry

Every nontrivial engine semantic claim carries:

- evidence class;
- source;
- patch/version;
- confidence;
- observed behavior;
- conflicting evidence, when present.

Promotion path:

OPEN / UNKNOWN
-> EVIDENCE OBSERVED
-> COMMUNITY PRACTICE or ENGINE FACT
-> ENGINE SEMANTICS MAPPED
-> ENFORCEABLE CONTRACT

This prevents “some old bot did it this way” from silently becoming “the engine requires it.”

## Semantic support-state model

The current registry has:

NATIVE_KNOWN
-> NATIVE_TYPED
-> SEMANTICALLY_ADAPTED
-> EXECUTABLE_SAFE

The Philosopher's Stone adds a necessary intermediate semantic state:

NATIVE_KNOWN
-> NATIVE_TYPED
-> SEMANTICALLY_ADAPTED
-> ENGINE_SEMANTICS_MAPPED
-> EXECUTABLE_SAFE

A construct that lacks engine-semantic mapping remains unsupported for higher-level compilation even when its syntax and signature are valid.

## Compiler gates

### Gate A — native identity

Is the construct known to the selected native engine profile?

### Gate B — native typing

Do syntax, parameters, directions, version, and arity match?

### Gate C — semantic mapping

Does the compiler know state effects, lifetime, recurrence, outputs, side effects, and completion semantics?

### Gate D — source-order safety

Are all persistent-state dependencies valid under effective source order and recurrent execution?

### Gate E — async closure

Does every issued action have:
- feasibility;
- pending handling where applicable;
- completion witness;
- release;
- invalidation/cancellation path where applicable?

### Gate F — DUC safety

Are search state, filters, targets, and Goal outputs valid and bounded?

### Gate G — resource closure

Do temporary claims have deterministic ownership and release?

### Gate H — evidence closure

Are community-practice and engine-fact claims explicitly attributed?

### Gate I — deterministic lowering

Can the semantic IR be lowered without hidden mutable compiler state or nondeterministic storage allocation?

### Gate J — native zero-findings

Does the staged emitted .per pass the pinned native parser with zero findings?

## Why this is the Philosopher's Stone

The community already discovered most of these rules empirically.

The old form is:

    weird .per pattern
        -> "this works"
        -> tribal knowledge
        -> another AI copies it
        -> nobody writes down why

The compiler form becomes:

    observed behavior
        -> evidence
        -> native semantic contract
        -> typed state/effect model
        -> diagnostic
        -> deterministic lowering
        -> regression fixture

That is the transformation the architecture is intended to provide.

## Non-goals

Do not use this architecture to build:

- a universal strategy scheduler;
- a general-purpose programming language;
- a whole-engine simulator;
- an optimizer that searches all possible .per programs;
- a Basilisk-specific strategy manager;
- an automatic runtime recovery agent.

## Implementation order

1. Promote native support-state model with ENGINE_SEMANTICS_MAPPED.
2. Build effective source graph for load/preprocessor semantics.
3. Build recurrent rule execution semantics and disable-self lifetime.
4. Generalize Goal/SN/Timer state effects and command-specific output spans.
5. Build asynchronous provider/queue semantics for construction, production, and research.
6. Build DUC SearchSession/TargetSession/Group state.
7. Build attack-engine state semantics on top of the same persistent-state model.
8. Add evidence-strength/version governance.
9. Add performance/cardinality metadata.
10. Only then build a generic reference player on the completed substrate.

## Completion definition

The Philosopher's Stone is complete when the compiler can take a nontrivial expert .per construct and explain it in native engine terms before compiling it:

NATIVE COMMAND
+ PARAMETERS
+ ENGINE STATE EFFECTS
+ LIFETIME
+ RULE ELIGIBILITY
+ SOURCE PRECEDENCE
+ ASYNC WORK
+ WORLD WITNESS
+ RELEASE/RECOVERY
+ STORAGE
+ EVIDENCE
+ COST

and then deterministically lower it to valid .per.

At that point the compiler is no longer merely a typed demand compiler. It is an honest semantic compiler for the real AoE2 .per language and engine.
