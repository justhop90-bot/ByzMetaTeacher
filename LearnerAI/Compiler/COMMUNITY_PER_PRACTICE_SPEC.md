# AoE2 .per Community Practice Specification

> Status: research-backed compiler direction
>
> Scope: the reusable AoE2 .per compiler, not Basilisk gameplay policy

## 1. Purpose

The compiler is a general engineering platform for producing correct, auditable, deterministic Age of Empires II AI scripts. It is not the strategy of one civilization and it is not a validator wrapped around one reference bot.

The compiler should make expert community .per practice explicit and machine-checkable while preserving the native language rather than inventing a second AoE2 engine.

The first major client of the compiler will be a new reference AI built from scratch. Basilisk is a separate downstream consumer and must not define the compiler's semantic model.

The central pipeline is:

    AIRef / engine facts
        ->
    native metadata
        ->
    .per source / source AST
        ->
    typed semantic IR
        ->
    deterministic storage + package binding
        ->
    deterministic .per
        ->
    native parser/backend acceptance
        ->
    runtime evidence

Runtime remains the authority for actual game execution. The compiler may prove what the source claims and what the engine documents; it must not pretend static analysis proves gameplay outcomes.

## 2. Evidence hierarchy

The compiler must distinguish four kinds of knowledge.

### ENGINE FACT

Directly documented by AIRef, checked against the native parser/backend, or directly observed from a reproducible engine behavior.

Examples:
- command syntax;
- parameter types;
- Goal/SN/Timer limits;
- DUC list limits;
- known load/preprocessor behavior;
- documented command bugs;
- native rule and line limits.

### COMMUNITY PRACTICE

A pattern demonstrated by experienced AI scripters, reference scripts, AIRef guides, benchmark work, tournament bots, or repeated community usage.

Examples:
- persistent goal cursors;
- explicit cooldown/backoff around mutable SN state;
- retaining DUC search results in groups instead of repeating expensive searches;
- limiting DUC sort/search sizes;
- using engine-native capability facts immediately before actions.

Community practice is evidence for a compiler rule only when the pattern is observable and reproducible. It is not an engine fact.

### COMPILER POLICY

A deliberate choice made to produce deterministic and auditable output.

Examples:
- scalar Goal allocation ranges;
- storage provenance requirements;
- deterministic allocation order;
- refusing implicit Timer reuse;
- requiring persistent state to have an owner.

Compiler policy must never be described as native AoE2 behavior.

### OPEN / UNKNOWN

Anything not established by the above.

Unknown native behavior fails closed where it affects correctness. The compiler must never manufacture semantics merely because a command name looks intuitive.

## 3. What the community actually gives the compiler

AIRef is a knowledge corpus, not just a command glossary. Its current reference covers commands, parameter types, strategic numbers, tables, guides, bugs, DUC, performance benchmarks, patch history, an AI ladder, AI tournament history, the AI Scripters community, and other reference projects.

The compiler should therefore ingest or mirror a normalized subset of:

    Commands
    Parameters
    Facts / Actions
    Comparison / math / type operators
    Unit lines
    Techs
    Object data
    Resource types
    Goal / SN / Timer constraints
    Point / cost / search-state contracts
    DUC actions
    Load-if symbols
    Known bugs
    Performance notes
    Version / patch provenance
    Community idioms
    Reference-bot fixtures

AIRef references:
- https://airef.github.io/commands/commands-index.html
- https://airef.github.io/parameters/parameters-index.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/tables/techs.html
- https://airef.github.io/tables/objects.html
- https://airef.github.io/tables/bug-tracker.html
- https://airef.github.io/resources/res-index.html

## 4. Compiler ceiling

The compiler should evolve through seven increasingly powerful layers.

### Layer 1: Native correctness

Prove that source is structurally legal before asking the game to execute it.

Required knowledge:
- command signatures;
- parameter families;
- fact/action role;
- logical operator arity;
- defconst resolution;
- native identifier resolution;
- source limits;
- rule-element limits;
- load/preprocessor reachability;
- native version applicability.

The pinned native parser remains the final syntax authority.

### Layer 2: Typed state and storage

Treat Goals, Strategic Numbers, Timers, points, and extended goal spans as an explicit memory model.

The compiler must know:
- who owns state;
- why state exists;
- who writes it;
- who consumes it;
- whether it persists across passes;
- whether the native command requires consecutive goals;
- whether a storage range is legal;
- whether another package component already occupies it.

No raw numeric Goal/SN/Timer allocation should appear in semantic source.

### Layer 3: Semantic lifecycle correctness

The compiler must verify causal state transitions rather than infer correctness from rule order or comments.

Minimum contracts:
- demand ownership;
- action feasibility;
- action issuance;
- pending admission;
- completion witness;
- release;
- invalidation / cancellation;
- capability loss;
- recovery without destroying persistent intent.

An action is never its own witness.

A timing observation is never completion evidence.

A persistent demand must survive temporary infeasibility unless explicitly invalidated.

### Layer 4: Package and resource correctness

The compiler must reason across the whole AI package, not only one generated file.

Required package models:
- imported .per files;
- #load graphs;
- symbol visibility;
- Goal occupancy;
- Goal span occupancy;
- SN occupancy;
- Timer occupancy;
- duplicate defconst ownership;
- initialization dependencies;
- source-order effects;
- same-pass state visibility.

The package is the program.

### Layer 5: Community idiom correctness

The compiler should understand proven .per constructions as reusable semantic patterns.

Initial idiom families:

    Research claim / escrow / completion
    Production demand / capability / queue
    Resource crisis / recovery / hysteresis
    Goal-backed state machine
    Timer cooldown / backoff
    Strategic-number mode switching
    Town-size attack and defensive targeting
    Search -> filter -> target -> action DUC pipeline
    Search-list retention through groups
    DUC target invalidation
    Fog-safe remote targeting
    Point calculation and placement
    Flare-driven coordination
    Build-site feasibility
    Research prerequisite closure
    Package-local module loading

The compiler should recognize these patterns without forcing the programmer to use a new DSL.

### Layer 6: Performance-aware lowering

Logical correctness is insufficient when a script can stall the game.

AIRef performance measurements show that DUC searches are often cheap enough for repeated use, while sorting large lists, long-distance path calculations, direct control of many units, repeated building placement, and chat can become expensive.

The compiler should therefore develop a performance model containing:
- command cost class;
- loop context;
- estimated search cardinality;
- maximum list size;
- sort size;
- repeated-pass frequency;
- path-distance scope;
- direct-control fanout;
- known expensive combinations.

The compiler should produce warnings before runtime when source structure creates a known hot path.

Performance diagnostics remain advisory unless the engine or community evidence establishes a deterministic correctness boundary.

### Layer 7: Reference-bot proof

The reference bot becomes the executable corpus for the compiler.

Every major compiler capability should have:
1. a community evidence reference;
2. a semantic rule;
3. a focused unit/IR test;
4. a minimal generated .per fixture;
5. a native parser acceptance test;
6. a reference-bot integration use.

The bot is not allowed to become a hidden second compiler.

## 5. Reference-bot design

The reference bot should be generic first.

It should intentionally demonstrate:

    Economy
      worker production
      age progression
      resource allocation
      crisis recovery
      farms / wood / gold / stone
      market use

    Research
      prerequisites
      escrow
      claim state
      completion witness
      failure / backoff

    Production
      building demand
      unit demand
      queue pacing
      target satisfaction
      housing / infrastructure

    Military
      composition intent
      threat observation
      defensive response
      attack activation
      target selection
      recovery

    DUC
      local search
      remote search
      filtering
      sorting
      groups
      target-object / target-point
      movement / attack
      search-state lifetime

    Map interaction
      points
      flares
      placement
      path measurements
      terrain / map-point evidence

    Late game
      replenishment
      expansion
      siege support
      trade / economy stabilization
      military reset

Civilization-specific strategy is downstream. The reference bot should not contain Basilisk's Byzantine identity.

## 6. Compiler project structure

The eventual standalone compiler project should have these conceptual packages:

    engine/
        native command schema
        parameter schema
        Goal/SN/Timer contracts
        version / patch provenance
        known bugs

    parser/
        source lexer/parser
        AST
        source locations

    semantic/
        state
        lifecycle
        ownership
        capability
        feasibility
        evidence
        dependencies
        package analysis
        performance

    binding/
        Goal allocation
        GoalSpan allocation
        StrategicNumber allocation
        Timer allocation
        provenance
        package occupancy
        manifests

    community/
        idiom registry
        evidence records
        pattern fixtures
        benchmark metadata

    emitter/
        deterministic .per lowering
        deterministic file ordering
        rule budgeting

    backends/
        pinned native parser
        native acceptance protocol

    reference-bot/
        generic demonstration AI
        golden source fixtures
        integration tests

    research/
        unresolved engine behavior
        benchmark harnesses
        community-source notes

Basilisk belongs outside this project.

## 7. Community-practice registry

Each documented idiom should eventually have a typed record with:

    practice_id
    name
    category
    status
    evidence_source[]
    engine_version[]
    prerequisites[]
    semantic_invariants[]
    anti_patterns[]
    performance_notes[]
    native_commands[]
    fixture[]
    reference_bot_use[]
    diagnostics[]
    provenance

Status values:

    DOCUMENTED
    COMMUNITY-OBSERVED
    BENCHMARKED
    ENGINE-VERIFIED
    COMPILER-ENFORCED
    REFERENCE-BOT-EXERCISED
    OPEN

A community claim must never silently become a compiler invariant.

## 8. First compiler research backlog

Priority 0:
- complete native command/parameter registry;
- complete Goal / GoalSpan / SN / Timer binding;
- package-wide occupancy;
- deterministic source locations;
- deterministic aggregate diagnostics;
- pinned native backend.

Priority 1:
- DUC search-state semantics;
- retained search evidence;
- target-object safety;
- target-point safety;
- point / cost / extended-goal contracts;
- preprocessor/load graph analysis;
- engine bug registry;
- same-pass visibility analysis.

Priority 2:
- performance-aware diagnostics;
- command cost metadata;
- DUC cardinality analysis;
- path-distance budgeting;
- repeated-pass hot-path detection.

Priority 3:
- community idiom registry;
- golden fixtures;
- reference-bot integration;
- automated evidence provenance;
- practice regression suite.

Priority 4:
- advanced DUC control patterns;
- adaptive military grouping;
- spatial coordination;
- cooperative flare protocols;
- map-topology-aware behavior;
- optional tournament-safe XS boundary.

XS should remain outside the core .per semantic model until its rules are independently specified. Current AIRef guidance explicitly distinguishes tournament-safe XS from functions that can provide cheating or rule-control capabilities.

## 9. Acceptance definition for the compiler

The compiler is mature when it can take a source program containing a nontrivial mix of native facts/actions, persistent state, DUC, points, research, production, timers, and package imports and answer all of these deterministically:

    Is the native construct legal?
    What engine resource does it consume?
    Who owns its persistent state?
    Who writes that state?
    Who consumes it?
    Can the action actually be issued?
    What world evidence proves completion?
    What invalidates the demand?
    What survives temporary failure?
    Is same-pass visibility relied upon?
    Is the package storage collision-free?
    Is the rule within native limits?
    Is the pattern known to be expensive?
    Is the behavior documented by AIRef?
    Is it merely community practice?
    Is the claim still open / unverified?
    Which exact source line produced the finding?

That is a compiler, not a lint script.

## 10. The small strange project: FlareMesh

### Concept

Use allied map flares as a spatial command bus.

Instead of requiring scenario triggers, custom chat protocols, or XS, a human ally places a flare and the AI interprets that flare as a machine-readable service request. The map location supplies the payload; nearby game state determines the meaning.

I found no evidence in the sources reviewed of a community-standard system that turns ordinary ally flares into a general-purpose spatial command bus. That does not prove nobody has ever done it. It does establish that the reviewed AIRef/community material documents the underlying primitives individually rather than this abstraction.

### Problem solved

Cooperative AI is difficult to direct without writing a scenario around it. A human teammate may want:

- cavalry at a location;
- villagers evacuated from a threatened area;
- a defensive group stationed at a choke;
- enemy buildings at a marked point attacked;
- a transport / escort sent to a location;
- a builder group sent to a forward site.

Today that usually requires the AI to infer the request from ordinary game state, use fixed scenario triggers, or rely on brittle custom behavior.

FlareMesh turns the existing flare channel into a human-to-AI API.

### Protocol

A flare is the request envelope.

The AI:

1. detects visible ally flares with up-find-flare / up-find-player-flare;
2. identifies the sender through the documented focus-player approach when sender identity matters;
3. stores the flare point using point goals;
4. inspects the area around the point with DUC / point commands;
5. classifies the request from spatial context;
6. selects a response package;
7. creates a temporary DUC group;
8. dispatches the group with up-target-point / up-target-objects;
9. records the request state in Goals;
10. expires or acknowledges the request using a Timer.

### Example semantic meanings

    Flare near ally villagers + enemy military:
        ESCORT / EVACUATE

    Flare near enemy military building:
        STRIKE

    Flare at empty defensive location:
        HOLD / PATROL

    Flare near unfinished friendly building:
        BUILD SUPPORT

    Repeated flare at the same point:
        REFRESH REQUEST

A second flare could become a cancellation or priority escalation depending on the protocol variant.

### Compiler value

This tiny project exercises an unusually large part of the compiler:

    point storage
    extended Goal spans
    source evidence
    player identity
    search state
    DUC filters
    groups
    target points
    target objects
    persistent request state
    timeout
    package ownership
    same-pass ordering
    performance budgeting
    human/AI coordination

It is deliberately strange because it forces the compiler to model .per as what it actually is: a constrained reactive machine with a tiny persistent memory, a spatial sensor/control layer, and a surprisingly capable command bus.

It is also practically useful. A human could direct a cooperative AI without a trigger-heavy scenario or a new UI language.

## 11. External evidence

AIRef:
- https://airef.github.io/resources/res-index.html
- https://airef.github.io/commands/commands-index.html
- https://airef.github.io/parameters/parameters-index.html
- https://airef.github.io/strategic-numbers/sn-index.html
- https://airef.github.io/resources/articles/data-limits.html
- https://airef.github.io/resources/articles/logical-operators.html
- https://airef.github.io/resources/articles/command-performance.html
- https://airef.github.io/resources/articles/leif-duc-tutorial-intro.html
- https://airef.github.io/tables/up-patch-notes.html
- https://airef.github.io/resources/articles/xs-for-tournaments.html

Community / tooling:
- https://github.com/joerollman/aoe2-ai-parser/blob/main/docs/workflows/validator-diagnostic-codes.md
- https://forums.ageofempires.com/t/ai-scripters-twitch-stream/132240
- https://forums.ageofempires.com/t/king-of-arabia-2-the-first-custom-ai-tournament-for-de/166494

## 12. Guiding rule

The compiler should not become a museum of every strange thing .per can do.

It should become a machine that can distinguish:

    engine fact
    community practice
    compiler policy
    experimental idea

and then make the last three increasingly reproducible without confusing them with the first.
