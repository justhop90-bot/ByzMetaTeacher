# Single-compiler program plan

Date: 2026-09-30.
Parent architecture: docs/architecture/2026-09-30-single-compiler-target-architecture.md.

## Goal

Turn the current collection of mature compiler subsystems into one semantic compiler capable of distilling durable AoE2 community practice into native .per programs.

## Phase 0: semantic program boundary

Status: started on branch single-compiler-foundation.

Deliverables:
- immutable CompilerSemanticProgram envelope;
- existing domain plans composed into one internal object;
- current public compiler call sites remain compatible;
- tests prevent duplicate or nondeterministic assembly.

Acceptance:
- existing compiler behavior unchanged;
- full compiler verification remains green;
- the program envelope becomes the internal owner of cross-domain plan references.

## Phase 1: shared semantic spine

Close the common objects rather than adding more domain-local wrappers:
- demand identity and persistence;
- capability/admission graph;
- persistent-control ownership/lifetime;
- execution request;
- witness/release;
- invalidation;
- recovery/reassessment;
- evidence/provenance.

The compiler must trace one demand across every transition.

## Phase 2: production and composition

Controller:

composition demand -> provider admission -> queue admission -> pending -> birth witness -> reassess

Required:
- current and queued composition;
- provider readiness;
- queue capacity;
- production retry/recovery;
- composition replacement;
- resource claims;
- witness-driven reassessment.

Community patterns:
- current+queued;
- counter-trains;
- persistent military floors;
- age-mode composition changes.

## Phase 3: DUC strategy sessions

Move from command coverage to reusable search/target templates.

Required:
- SearchSession;
- TargetSession;
- persistent identity;
- reacquisition;
- validation;
- invalidation;
- target-dependent execution;
- stale-provenance diagnostics;
- reusable search templates.

## Phase 4: attack controller

Controller:

READY -> PREPARE -> ASSEMBLE -> ATTACK -> PRESS/RETREAT -> REASSESS -> RELEASE/RECOVER

Required:
- composition admission;
- target policy;
- controller controls;
- attack cadence;
- completion witness;
- release semantics;
- reinforcement;
- retargeting;
- recovery.

The current issue-executable NativeAttackLifecyclePlan is a lowering seam, not the finished controller.

## Phase 5: escrow/resource arbitration

Represent community escrow idioms without becoming a universal scheduler.

Required:
- claims;
- reservations;
- ownership;
- release;
- consumption;
- starvation;
- emergency override;
- handoff;
- recovery.

Runtime OPEN questions stay explicit.

## Phase 6: strategy-template compiler

Convert community idioms into reusable semantic templates specifying:
- observations;
- demands;
- capability requirements;
- controls;
- resource claims;
- execution requests;
- witnesses;
- recovery;
- reassessment;
- evidence.

This is the transition from native feature compiler to community-practice compiler.

## Phase 7: strategic synthesis

Compose templates from:
- civilization facts;
- map profile;
- enemy observations;
- strategic state;
- resource constraints;
- available capabilities.

This is not utility optimization. The output is a deterministic policy graph of persistent community-style control loops.

## Phase 8: breadth

Extend the same spine to map/scouting, forward buildings, fortification, siege, monks/relics, water, transport, wonder/endgame, exhaustion/resource depletion, and broader civilization overlays.

## Phase 9: corpus closure

For each durable idiom, track:

source -> precedent -> semantic template -> native lowering -> verification

The corpus becomes a regression suite against semantic erosion.

## Program-level acceptance

The objective is reached when a representative corpus spanning economy, age progression, production, research, military composition, DUC, attack, adaptation, and map conditions can be compiled through one semantic program into deterministic native .per without inventing unsupported engine semantics.

The target is breadth plus causal fidelity, not a larger pile of primitives.
