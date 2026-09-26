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

### 8. Domain-aware teaching diagnostics

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

The checked-in compiler verification record contains 48 tests.

No GitHub Actions result is being treated as proof for the latest adapter work. Local test results remain local evidence.

## Exit condition for the compiler phase

The compiler phase is not complete when every planned primitive is documented.

It is complete when the compiler can safely express and diagnose the semantic chain required for the Dark -> Feudal -> Castle Byzantine vertical slice.
