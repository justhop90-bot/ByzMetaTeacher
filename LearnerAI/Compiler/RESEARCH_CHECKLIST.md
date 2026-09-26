# LearnerAI Compiler Research Checklist

This checklist keeps compiler work subordinate to the actual Byzantine player.

## Already established

### Native .per ecosystem

The community already provides a capable native parser/linter. The pinned aoe2-ai-parser backend is the native authority.

Do not build a replacement native parser, native formatter, native command inventory, native logical-arity checker, native rule-length checker, or package graph validator unless a specific teaching need cannot be handled at the boundary.

### LearnerAI contribution

The semantic contribution is different:

    persistent intent
      -> demand
      -> capability
      -> feasibility
      -> action
      -> pending
      -> world-state witness
      -> release / invalidation
      -> reassess

## Deep cross-check and implementation record (2026-09-26)

This pass was explicitly adversarial: the compiler contracts were checked against the live
Basilisk controller, the checked-in AIRef command schema, current AIRef engine limits,
native/community .per examples, and the CI test runner.

### Evidence established

- AIRef documents 10,000 rules, 32 DE elements per rule, and 255 characters per source line. Nested logical operators count as rule elements and have exact operand counts. citeturn347585search1turn347585search0
- Community .per examples use explicit goals, pending-object facts, can-build/can-* feasibility checks, and direct build actions rather than an opaque manager layer. citeturn347585search2turn347585search4turn347585search5
- The checked-in repository AIRef schema is the compiler's native command-signature authority; semantic adapters remain a smaller Basilisk-owned layer.
- The current Basilisk package already owns a large numeric Goal namespace, so a compiler-local base Goal guess is not a package-level contract.
- The native runtime therefore remains responsible for raw .per legality, while the compiler adds typed semantics that native parsing cannot infer.

### Implemented in this pass

- [x] recursive logical-operator arity validation;
- [x] explicit single-native-command action roots;
- [x] native command arity sourced from the checked-in AIRef schema;
- [x] explicit rejection of native commands without a Basilisk semantic adapter;
- [x] stable reservation of existing runtime bindings;
- [x] duplicate existing-binding detection;
- [x] persistent binding-manifest data model with deterministic JSON round trip;
- [x] compiler-side rule, element, and line-length budgets;
- [x] one-shot initialization chunking under the 32-element DE limit;
- [x] per-pass build arbitration for the native one-build-per-pass constraint;
- [x] regression tests for each hardening edge;
- [x] CI-driven repair of serializer, nested-arity, and initialization lifecycle defects found during implementation.

### GitHub prior-art cross-check (2026-09-26)

The public prior art was compared directly against the current Basilisk compiler:

- `01010100b/AgeScript`: adopt the typed Compilation -> Assembly -> Script separation, explicit intermediate instructions, Goal-backed memory discipline, deterministic lowering, and hard rule-budget enforcement. Do not copy its general-purpose programming language model.
- `JOTworks/AgeOfPython`: adopt AIRef-derived native metadata, explicit parameter typing, compiler-owned Goal memory allocation, and strong separation between source variables and native storage. Do not copy its Python-like frontend or opaque memory conventions.
- `lewisc64/aoe2ai`: adopt named Goal allocation, explicit volatile Goal/Point lifetimes, staged persistent state as a semantic concept, and rule-budget-aware lowering. Do not add its generalized strategy DSL constructs until Basilisk semantics require them.
- `mboop127/AlphaScripter`: retain structured .per representation and game-facing validation ideas as reference only; its genetic optimization model is outside the Basilisk compiler boundary.
- `teshiba/LibAoe2AISharp`: treat programmatic command construction as precedent for typed native wrappers, but keep AIRef as the command authority.

Adoption rule: steal proven storage, IR, lowering, and validation mechanisms; do not steal architecture that turns Basilisk into a generic programming language or universal strategy scheduler.

### Prior-art reuse tranche implemented / in progress

- [x] prior-art decisions recorded in `docs/plans/2026-09-26-basilisk-prior-art-reuse.md`;
- [ ] explicit GoalSpan request/allocation and interval occupancy;
- [ ] deterministic volatile Goal scratch pool;
- [ ] optional end-to-end binding-manifest artifact;
- [x] native GoalSpan storage contracts derived from the checked-in AIRef command schema;
- [x] native storage contract catalog explicitly distinguishes contiguous Goal spans from multiple independent Goal outputs;
- [x] typed capability-provider/dependency semantics implemented and connected to the compile gate;
- [x] current demand language projected into the capability graph without adding source syntax.

### Still required before full-player compilation

- [x] command-specific GoalSpan allocation from native storage contracts;
- [ ] StrategicNumberSlot and TimerSlot allocation;
- [x] explicit Goal occupancy ranges/intervals consumed by the binder when supplied as package inventory;
- [x] automatic binding-manifest write-back as an end-to-end compiler artifact;
- [x] typed capability-provider graph plus provider-contract and admissibility validation passes;
- [x] compiler pipeline projects current SemanticDemand IR into the capability graph before binding/emission;
- [x] actionable projected providers require a native FEASIBILITY predicate while preserving observation/timing semantics;
- [ ] demand ownership and writer/consumer contracts;
- [x] prerequisite dependency graph, deterministic SCC cycle detection, and dead-end diagnostics;
- [ ] resource/conflict semantics matching Basilisk's transient arbitration;
- [ ] first-writer/first-consumer and source-order analysis;
- [ ] action-issuance failure versus pending-state distinction;
- [ ] Castle vertical slice compiled against actual Basilisk semantics.

## Implemented compiler foundation

- [x] semantic primitive profile;
- [x] lifecycle validation;
- [x] repeated-action prevention;
- [x] pending-state diagnostics;
- [x] negative lifecycle tests;
- [x] native backend subprocess boundary;
- [x] pinned backend identity;
- [x] protocol validation;
- [x] staged artifact validation;
- [x] deterministic diagnostics;
- [x] combined semantic/native report;
- [x] compiler/native integration tests.

## Next compiler work, ordered by player need

### 1. Freeze native tooling

- [ ] reproducible backend installation;
- [ ] manifest verification;
- [ ] archive/source checksum;
- [ ] golden protocol contract;
- [ ] no automatic backend upgrades.

### 2. Demand ownership

The compiler should reject or diagnose:

- missing owner;
- conflicting persistent writers;
- demands with no consumer;
- demand that has no viable capability provider;
- demand that can never release or invalidate.

### 3. Capability providers

Add semantic representation for:

- construction providers;
- production providers;
- research providers;
- economic capability;
- military capability.

The compiler must be able to answer:

What can satisfy this demand?

### 4. Player dependency chains

Model the chain needed for the first vertical slice:

    Castle intent
      -> Castle demand
      -> prerequisite capability
      -> resource protection
      -> construction feasibility
      -> action
      -> Castle witness
      -> Castle economy
      -> production expansion
      -> reassessment

The goal is not a universal planner.

The goal is semantic visibility of the actual player chain.

### 5. Recovery and invalidation

Add diagnostics for:

- temporary failure that incorrectly destroys intent;
- stale demand after strategic invalidation;
- capability loss with unreleased execution state;
- failed action without re-openable demand;
- recovery that cannot return to the original strategic path.

### 6. Resource and conflict semantics

Teach the compiler enough to identify when:

- two demands legitimately compete;
- a claim is required;
- a global resource lock is unjustified;
- a resource owner never releases;
- a lower-priority execution path can starve a strategic demand.

Do not turn this into a universal scheduler.

### 7. Source-order analysis

Where Basilisk-style rule order is deliberate, the compiler should eventually identify:

- first writer;
- first consumer;
- reset-then-recompute chains;
- same-pass visibility assumptions;
- later overwrites;
- unreachable or preempted rules.

### 8. Timing and map-conditioned evidence

The player now has concrete Arabia timing windows and reactions. Compiler responsibility is deliberately limited to semantic guardrails:

- timing primitives are typed as interpretation evidence;
- timing-only action demands are rejected;
- timing cannot prove completion;
- timing-only release is rejected.

Numeric Arabia thresholds remain Strategy tuning data. Do not hard-code the map profile into the compiler.

For positional tower/wall semantics, only engine-native observations should be admitted. Builder count is currently an execution/runtime concern; do not fabricate a compiler primitive for it until a sourced native fact exists.

### 9. Domain-aware teaching diagnostics

Diagnostics should use the player vocabulary:

DEMAND;
CAPABILITY;
FEASIBILITY;
ACTION;
PENDING;
WITNESS;
RELEASE;
INVALIDATION;
REASSESSMENT.

## Deliberately do not build

- replacement native parser;
- generic Python-like language;
- runtime simulator;
- universal scheduler;
- universal manager;
- whole-game optimizer.

## Current verification

The checked-in compiler verification record contains the lifecycle suite plus timing and positional-semantics regression tests.

No GitHub Actions result is being treated as proof for the latest adapter work. Local test results remain local evidence.

## Exit condition for the compiler phase

The compiler phase is not complete when every planned primitive is documented.

It is complete when the compiler can safely express and diagnose the semantic chain required for the Dark -> Feudal -> Castle Byzantine vertical slice.

### Prior-art reuse tranche verification (2026-09-26)

The first reuse tranche is now implemented and CI-verified:

- [x] typed GoalSpan requests with explicit shape, width, contract ID, and native start bounds;
- [x] interval-based collision detection for scalar GoalIds versus contiguous Goal spans;
- [x] deterministic volatile Goal scratch-pool checkout/release with explicit lifetime;
- [x] versioned deterministic binding manifest output;
- [x] staged manifest promotion tied to the native .per validation result;
- [x] AIRef-derived span contracts for contiguous point-pair and four-goal outputs;
- [x] explicit rejection of treating independent multi-Goal outputs such as threat-data fields as one span;
- [x] current compiler fixture remains unchanged in semantic behavior;
- [x] native backend validation and full compiler unittest suite pass on the implementation head.

The remaining compiler work is semantic, not storage plumbing: explicit demand ownership and writer/consumer contracts, richer resource/conflict relations, issuance-failure semantics, source-order analysis, and the Castle vertical slice. The typed capability/provider graph is now integrated as a compile-time validation projection of the current demand language.
